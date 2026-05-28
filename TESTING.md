# Testing & Validation Guide

## Pre-Deployment Checklist

### 1. System Requirements
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check pip
pip --version

# Check Open5GS services
systemctl status open5gs-amfd
systemctl status open5gs-smfd
systemctl status open5gs-upfd
# All should show "active (running)"
```

### 2. Dependencies Installation
```bash
cd /home/sara/hospital_5g_slicing

# Install required packages
pip install -r requirements.txt

# Verify installation
python3 -c "import prometheus_client; print('✓ prometheus_client')"
python3 -c "import streamlit; print('✓ streamlit')"
python3 -c "import pandas; print('✓ pandas')"
python3 -c "import requests; print('✓ requests')"
```

---

## Component Testing

### Test 1: Metrics Exporter

**File**: `metrics_exporter.py`

```bash
# Run the exporter in isolation
python3 metrics_exporter.py

# Expected output:
# [INFO] Prometheus exporter started on http://0.0.0.0:8000/metrics
# [INFO] Exporter running. Test with:
# [INFO]   curl http://localhost:8000/metrics
# [INFO]   curl http://localhost:8000/health
```

**Validation**:
```bash
# In another terminal, check metrics endpoint
curl http://localhost:8000/metrics

# Should return Prometheus text format starting with:
# # HELP hospital_slice_latency_ms Current network slice latency...
# # TYPE hospital_slice_latency_ms gauge

# Check health endpoint
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

**Expected Behavior**:
- ✅ HTTP server starts on :8000
- ✅ /metrics endpoint returns Prometheus format
- ✅ /health endpoint returns JSON
- ✅ No errors in logging

### Test 2: Network Simulator

**File**: `enhanced_network_simulator.py`

```bash
# Run simulator in standalone mode
python3 enhanced_network_simulator.py

# Expected output:
# [INFO] >>> Running NORMAL traffic simulation...
# [INFO]     Normal simulation complete.
# [INFO] ============================================================
# [INFO]   SIMULATION RESULTS — NORMAL
# [INFO] ============================================================
# [INFO]   [URLLC]
# [INFO]     Avg Latency    : 1.234 ms
# [INFO]     Avg Throughput : 494.50 Mbps
# [INFO]     Avg Packet Loss: 0.0004 %
```

**Validation**:
- ✅ Generates consistent metrics
- ✅ URLLC latency < 2ms (base 1ms + noise)
- ✅ URLLC throughput ~495 Mbps (base 500)
- ✅ URLLC packet loss < 0.002%

### Test 3: Open5GS Monitor

**File**: `open5gs_monitor.py`

```bash
python3 open5gs_monitor.py

# Expected output:
# ============================================================
#   Open5GS Service Status
# ============================================================
# 
# Total Services: 7
# Active Services: 3+
# Status: HEALTHY or DEGRADED
# 
# 🟢 open5gs-amfd      active       ...
# 🟢 open5gs-smfd      active       ...
# 🟢 open5gs-upfd      active       ...
```

**Validation**:
- ✅ Detects at least 3 active critical services
- ✅ Status query works without errors
- ✅ Proper formatting with indicators

### Test 4: Enhanced Main Application

**File**: `enhanced_main.py`

```bash
# Terminal 1: Run main application
python3 enhanced_main.py

# Expected startup sequence:
# [INFO] 5G SMART HOSPITAL NETWORK SLICING - MONITORING SYSTEM
# [INFO] [1/5] Initializing metrics collector...
# [INFO]       ✓ Metrics collector ready
# [INFO] [2/5] Starting Prometheus exporter...
# [INFO]       ✓ Prometheus exporter listening on http://0.0.0.0:8000/metrics
# [INFO] [3/5] Initializing emergency detector...
# [INFO]       ✓ Emergency detector ready
# [INFO] [4/5] Initializing network simulator...
# [INFO]       ✓ Network simulator ready
# [INFO] [5/5] Starting Open5GS service monitor...
# [INFO]       ✓ Open5GS monitor started
# [INFO] 🚀 HOSPITAL SLICING APPLICATION RUNNING
```

**Validation** (in Terminal 2):
```bash
# Check metrics are being generated
curl http://localhost:8000/metrics | grep -c "hospital_"
# Should return > 10 metrics

# Check specific metrics exist
curl http://localhost:8000/metrics | grep "hospital_slice_latency_ms"
# Should return lines like:
# hospital_slice_latency_ms{slice="URLLC"} 1.25
# hospital_slice_latency_ms{slice="eMBB"} 10.5
# hospital_slice_latency_ms{slice="mMTC"} 87.3

# Monitor continuous updates
watch -n 1 'curl -s http://localhost:8000/metrics | grep hospital_slice_latency_ms'
# Values should update every 1-2 seconds
```

**Validation** (in Terminal 3):
```bash
# Check all threads are running
ps aux | grep python3 | grep -v grep
# Should show:
# - enhanced_main.py (main process)
# - StreamlitThread (if dashboard running)
# - SimulationThread
# - MonitoringThread
# - Open5GSHealthMonitor
```

### Test 5: Streamlit Dashboard

**File**: `enhanced_dashboard.py`

```bash
# Terminal 2: Run dashboard
streamlit run enhanced_dashboard.py

# Expected output:
# [INFO]    URL: http://localhost:8501
# [INFO]    [session: <id>]
# [INFO]    1 file added, 1 file modified
```

**Browser Validation** (http://localhost:8501):
- ✅ Page loads without errors
- ✅ Title: "🏥 5G Smart Hospital Monitoring Dashboard"
- ✅ Emergency Status panel visible
- ✅ Network Slice QoS metrics displayed (3 cards)
- ✅ Open5GS Service Status (3 services)
- ✅ Hospital Devices table (13 rows)
- ✅ Auto-refresh working (data updates every 2s)
- ✅ No red error messages

**Dashboard Content Validation**:

**Section 1: Emergency Status**
- Should show "✓ All systems normal" or "🚨 EMERGENCY ALERT ACTIVE"
- Emergency count should be 0+ (counter)
- Status should be "NORMAL" or "ACTIVE"

**Section 2: QoS Metrics**
- URLLC: latency 1-3ms, throughput 490-500 Mbps, loss <0.001%
- eMBB: latency 8-12ms, throughput 900-950 Mbps, loss 0.05-0.1%
- mMTC: latency 85-100ms, throughput 95-100 Mbps, loss 0.2-0.5%

**Section 3: Open5GS Services**
- amfd: 🟢 ACTIVE
- smfd: 🟢 ACTIVE
- upfd: 🟢 ACTIVE

**Section 4: Hospital Devices**
- 13 devices listed with columns: Device ID, Name, Type, Slice, Status, Priority
- All devices should show 🟢 Active status

---

## Integration Testing

### Test 6: Full System Integration

**Sequence**:
1. Start enhanced_main.py (Terminal 1)
2. Wait 5 seconds for initialization
3. Verify exporter working: `curl http://localhost:8000/health`
4. Start dashboard (Terminal 2)
5. Wait 3 seconds for Streamlit startup
6. Access dashboard in browser
7. Check metrics flowing through dashboard

**Validation Checklist**:
```bash
# T+10s: Metrics should be flowing
curl http://localhost:8000/metrics | wc -l
# Should return > 50 lines

# T+15s: Dashboard should show metrics
curl http://localhost:8501 -s | grep "hospital_slice_latency"
# Should find metric values

# T+20s: Emergency detector should be working
curl http://localhost:8000/metrics | grep hospital_emergency
# Should show emergency_detected and emergency_alert_total

# T+25s: Services should be monitored
curl http://localhost:8000/metrics | grep hospital_open5gs_service_up
# Should show 3 service metrics
```

---

## Emergency Scenario Testing

### Test 7: Emergency Alert Detection

**Expected Behavior** (Auto-generated after ~30 seconds):
1. Simulator enters emergency phase
2. URLLC metrics spike
3. EmergencyDetector triggers
4. Dashboard shows alert
5. Metrics show emergency_detected = 1

**Manual Testing** (if auto-trigger not occurring):

Edit `enhanced_network_simulator.py` to increase spike magnitude:
```python
# In simulate_latency() for URLLC
spike = random.uniform(10, 20) if overloaded else 0  # increased from 5-15
```

Or reduce threshold in `enhanced_main.py`:
```python
self.detector = EmergencyDetector(
    self.metrics_collector,
    latency_threshold_ms=2.0,  # reduced from 5.0
    packet_loss_threshold_percent=0.5  # reduced from 1.0
)
```

**Verification**:
- Dashboard shows 🚨 EMERGENCY ALERT ACTIVE
- Emergency count increments
- Latency/loss values appear in red
- Logs show "EMERGENCY ALERT ACTIVATED"

### Test 8: Continuous Operation

**Duration Test** (5 minutes):
```bash
# Run for 5 minutes and check stability
time python3 enhanced_main.py  # Should complete cleanly
```

**Memory Leak Test**:
```bash
# Monitor memory usage over time
watch -n 5 'ps aux | grep python3 | grep enhanced_main'
# Memory should stabilize after 30s, not increase continuously
```

**CPU Usage**:
```bash
top -p $(pgrep -f enhanced_main.py)
# Should show < 20% total CPU usage
```

---

## Performance Benchmarks

### Expected Resource Usage

| Metric | Expected | Threshold |
|--------|----------|-----------|
| Simulator CPU | ~5% | <10% |
| Exporter CPU | <1% | <2% |
| Monitor CPU | <1% | <2% |
| Dashboard CPU | ~10% | <20% |
| Total Memory | ~60 MB | <150 MB |
| Metric Generation | 1 Hz | ±0.1 Hz |
| Dashboard Refresh | 2s | 1-5s |

### Throughput Metrics

```bash
# Requests per second to exporter
ab -n 100 -c 5 http://localhost:8000/metrics
# Should handle >100 req/s without errors

# Concurrent dashboard users
streamlit run enhanced_dashboard.py &
streamlit run enhanced_dashboard.py &
# Should handle 2+ instances without issues
```

---

## Validation Checklist

### Pre-Launch
- [ ] Python 3.8+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Open5GS services running (3/7 active minimum)
- [ ] Ports 8000 and 8501 available
- [ ] No other processes using those ports

### Component Startup
- [ ] metrics_exporter.py starts without errors
- [ ] enhanced_network_simulator.py generates metrics
- [ ] open5gs_monitor.py detects services
- [ ] enhanced_main.py initializes all components
- [ ] Prometheus exporter responds to HTTP requests

### Metrics Quality
- [ ] Real data (not random/fake)
- [ ] URLLC metrics < baseline + noise
- [ ] eMBB metrics reasonable
- [ ] mMTC metrics as expected
- [ ] Packet loss values realistic
- [ ] Metrics update regularly (1+ Hz)

### Dashboard Display
- [ ] Page loads without errors
- [ ] QoS metrics cards show current values
- [ ] Service status shows correct state
- [ ] Device table lists all 13 devices
- [ ] Emergency alert section responsive
- [ ] Auto-refresh working (2s interval)
- [ ] No network errors in console

### Integration
- [ ] Simulator → Collector → Exporter → Dashboard pipeline working
- [ ] Emergency detector triggers appropriately
- [ ] Open5GS monitor updates metrics
- [ ] All components shutdown gracefully on Ctrl+C

### Documentation
- [ ] README.md updated
- [ ] QUICKSTART.md covers basic setup
- [ ] SETUP.md provides technical details
- [ ] ANALYSIS.md documents architecture

---

## Troubleshooting Flowchart

```
┌─ Dashboard shows no data?
│  ├─ Check exporter running: curl http://localhost:8000/metrics
│  ├─ Check simulator thread: ps aux | grep enhanced
│  └─ Check logs for errors
│
├─ Exporter not responding?
│  ├─ Check port 8000 available: lsof -i :8000
│  ├─ Check firewall: sudo iptables -L
│  └─ Restart: pkill -f enhanced_main
│
├─ Services showing offline?
│  ├─ Check services: systemctl status open5gs-*
│  ├─ Start services: systemctl start open5gs-amfd
│  └─ Check permissions for systemctl
│
├─ Dashboard crashes?
│  ├─ Check Streamlit version: pip show streamlit
│  ├─ Clear cache: rm -rf ~/.streamlit
│  └─ Restart: streamlit run enhanced_dashboard.py --logger.level=debug
│
└─ Memory issues?
   ├─ Check ring buffer size in MetricsCollector
   ├─ Reduce retention: metrics 50 values instead of 100
   └─ Increase system memory if needed
```

---

## Demo Validation

For BE minor project demo (10 minutes):

1. **Setup** (2 min)
   - Start enhanced_main.py ✓
   - Start dashboard ✓
   - Verify metrics flowing ✓

2. **Normal Mode** (2 min)
   - Show real QoS metrics ✓
   - Explain slice design ✓
   - Point to active services ✓

3. **Emergency Mode** (3 min)
   - Observe latency/loss spike ✓
   - Show emergency alert ✓
   - Explain reallocation ✓

4. **Metrics Export** (2 min)
   - Show /metrics endpoint ✓
   - Explain Prometheus format ✓
   - Demo Grafana compatibility ✓

5. **Q&A** (1 min)
   - Answer questions ✓
   - Discuss architecture ✓
   - Highlight real data ✓

---

**Testing Status**: ✅ All tests documented and can be run independently
**Last Updated**: May 27, 2026
