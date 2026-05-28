# Quick Start Guide - 5G Hospital Slicing Monitoring

## 1-Minute Setup

```bash
# Terminal 1: Install & run main app
pip install -r requirements.txt
python3 enhanced_main.py

# Terminal 2: Launch dashboard
streamlit run enhanced_dashboard.py

# Terminal 3: Verify metrics
curl http://localhost:8000/metrics | grep hospital_slice_latency
```

Open browser: **http://localhost:8501**

## What You'll See

### Dashboard (Streamlit - port 8501)
- **Emergency Status**: Real-time alert indicator
- **QoS Metrics**: Latency, throughput, packet loss per slice
- **Service Health**: Open5GS service status
- **Device Status**: 13 hospital devices health

### Metrics Endpoint (port 8000)
```bash
curl http://localhost:8000/metrics

# Output example:
hospital_slice_latency_ms{slice="URLLC"} 1.25
hospital_slice_throughput_mbps{slice="URLLC"} 495.50
hospital_slice_packet_loss_percent{slice="URLLC"} 0.0005
hospital_emergency_detected 0
hospital_open5gs_service_up{service="amfd"} 1
```

## Architecture in 30 Seconds

```
Real Simulation    →    Metrics Collector    →    Prometheus Exporter
     (1Hz)            (thread-safe storage)        (HTTP :8000)
        ↓                      ↓                           ↓
    QoS Data           In-Memory Buffers          Prometheus Format
   Latency, BW,        Emergency State           /metrics endpoint
   Packet Loss         Device Health             Grafana Compatible
```

## Key Features

✅ **Real Data**: Metrics from NetworkSimulator, not random
✅ **Professional**: Prometheus-compatible format
✅ **Live**: Dashboard updates every 2 seconds
✅ **Monitoring**: Open5GS service health tracking
✅ **Alerts**: Emergency detection with thresholds
✅ **Production**: Thread-safe, modular code

## File Mapping

| File | Purpose | When to Use |
|------|---------|-------------|
| `enhanced_main.py` | Start here | Launch complete system |
| `metrics_exporter.py` | Prometheus integration | Core monitoring |
| `enhanced_network_simulator.py` | Generate metrics | Provides real data |
| `open5gs_monitor.py` | Service monitoring | Track health |
| `enhanced_dashboard.py` | Streamlit UI | View live data |

## Troubleshooting

**Dashboard blank**: Check if exporter is running on :8000
```bash
curl http://localhost:8000/health
```

**No metrics**: Check simulator thread is running
```bash
ps aux | grep enhanced
```

**Services showing offline**: Verify Open5GS
```bash
systemctl status open5gs-amfd
```

## Demo Walkthrough (10 min)

1. **Show Normal Mode** (first 30 seconds)
   - Point to real QoS metrics
   - Show all services active
   - Explain slice design (URLLC, eMBB, mMTC)

2. **Trigger Emergency** (observe around 30-60s mark)
   - Emergency alert appears
   - URLLC metrics spike
   - Watch reallocation indicator

3. **Show Prometheus Format** (Terminal 3)
   ```bash
   watch -n 2 'curl -s http://localhost:8000/metrics | grep hospital'
   ```

## Ports

- **:8000** - Prometheus metrics endpoint
- **:8501** - Streamlit dashboard

## Stopping

Press **Ctrl+C** in Terminal 1 to shut down all components gracefully.

---

**Ready to demo!** 🚀
