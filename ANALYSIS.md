# 5G Hospital Slicing Project Analysis & Integration Plan

## Current Architecture

### Existing Components
1. **network_simulator.py** - Simulates QoS metrics per slice (latency, throughput, packet loss)
2. **slice_config.py** - Defines URLLC, eMBB, mMTC slices with real parameters
3. **hospital_devices.py** - 13 devices across slices (surgical robots, ICU monitors, imaging systems, IoT sensors)
4. **emergency_scenario.py** - Dynamic bandwidth reallocation logic
5. **dashboard.py** - Streamlit UI with basic Open5GS status checks
6. **main.py** - CLI runner for simulations

### Key Observations
- ✅ Real network slice parameters (bandwidth, latency, reliability, priority)
- ✅ Realistic device mix (critical URLLC, broadband eMBB, IoT mMTC)
- ✅ Emergency detection logic (URLLC load > 80%)
- ⚠️ Metrics generated per time-step but not exposed for monitoring
- ⚠️ No persistent metric collection
- ⚠️ No Prometheus integration
- ⚠️ Dashboard only shows Open5GS status, not simulation metrics

## Integration Strategy

### Architecture Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring & Metrics Stack              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  NetworkSimulator (Real QoS Metrics)                        │
│         │                                                    │
│         ├──> MetricsCollector (In-Memory Storage)           │
│         │         │                                          │
│         └────────>│─── PrometheusExporter (HTTP :8000)      │
│                   │     └─> Gauge: latency, throughput      │
│                   │     └─> Counter: packet_loss_total      │
│                   │     └─> Gauge: slice_load, bandwidth    │
│                   │     └─> Gauge: open5gs_service_status   │
│                   │     └─> Gauge: emergency_detected       │
│                   │                                          │
│                   └──> EmergencyDetector                     │
│                         └─> Triggers alerts & reallocation   │
│                                                              │
│  Streamlit Dashboard (Live Display)                         │
│         │                                                    │
│         └──> Fetches metrics from PrometheusExporter        │
│              Displays real-time KPIs & alerts               │
│              Shows Open5GS service status                   │
│              Shows device health                            │
│                                                              │
│  Grafana (Optional)                                         │
│         └──> Scrapes :8000/metrics for long-term storage   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### New Modules
1. **metrics_exporter.py**
   - PrometheusExporter class
   - MetricsCollector for thread-safe metric storage
   - HTTP endpoint on port 8000 for Prometheus scraping
   - Real metrics from NetworkSimulator
   
2. **open5gs_monitor.py**
   - Open5GS service health checks
   - Service uptime tracking
   - CPU/memory polling via systemctl and ps

3. **enhanced_network_simulator.py**
   - Modified NetworkSimulator with real-time metric emission
   - Event-based metric collection
   - Thread-safe operation for concurrent access

4. **enhanced_dashboard.py**
   - Live metric display from exporter
   - Real-time QoS KPI cards
   - Emergency alert panel
   - Service health dashboard
   - Automatic refresh

### Data Flow
1. **Simulation Loop** (thread 1):
   - NetworkSimulator runs time-step simulation
   - Emits real latency, throughput, packet loss values
   - MetricsCollector stores them

2. **Prometheus Exporter** (thread 2):
   - HTTP server on :8000
   - Exposes metrics in Prometheus text format
   - Can be scraped by Grafana/Prometheus

3. **Streamlit Dashboard** (main thread):
   - Fetches current metrics from exporter
   - Updates every 2 seconds
   - Shows emergency alerts
   - Displays slice KPIs

### Metrics Definition

#### Latency (Gauge)
- `hospital_slice_latency_ms{slice="URLLC"}` → current value
- `hospital_slice_latency_ms{slice="eMBB"}` → current value
- `hospital_slice_latency_ms{slice="mMTC"}` → current value

#### Throughput (Gauge)
- `hospital_slice_throughput_mbps{slice="URLLC"}` → current value
- `hospital_slice_throughput_mbps{slice="eMBB"}` → current value
- `hospital_slice_throughput_mbps{slice="mMTC"}` → current value

#### Packet Loss (Counter + Gauge)
- `hospital_slice_packet_loss_total{slice="URLLC"}` → cumulative count
- `hospital_slice_packet_loss_percent{slice="URLLC"}` → current % value

#### Bandwidth (Gauge)
- `hospital_slice_bandwidth_allocated_mbps{slice="URLLC"}` → allocated bandwidth
- `hospital_slice_bandwidth_used_mbps{slice="URLLC"}` → used bandwidth

#### Load (Gauge)
- `hospital_slice_load_percent{slice="URLLC"}` → load %

#### Emergency (Counter + Gauge)
- `hospital_emergency_alert_total` → count of emergencies
- `hospital_emergency_detected{state="active"}` → 1 if emergency, 0 if normal

#### Open5GS Services (Gauge)
- `hospital_open5gs_service_up{service="amfd"}` → 1=active, 0=inactive
- `hospital_open5gs_service_up{service="smfd"}` → 1=active, 0=inactive
- `hospital_open5gs_service_up{service="upfd"}` → 1=active, 0=inactive

#### Device Health (Gauge)
- `hospital_device_active{device_id="D001", device_type="surgical_robot"}` → 1=active, 0=offline

## Implementation Steps

1. **Create metrics_exporter.py** - Core Prometheus integration
2. **Create open5gs_monitor.py** - Service health monitoring
3. **Enhance network_simulator.py** - Real-time metric emission
4. **Enhance emergency_scenario.py** - Emergency event tracking
5. **Enhance dashboard.py** - Live metric display
6. **Update requirements.txt** - Add prometheus_client, requests
7. **Update main.py** - Run all components concurrently

## Testing Strategy
- Unit tests for MetricsCollector
- Integration test: Simulator → Exporter → Prometheus format
- Manual test: curl localhost:8000/metrics
- Dashboard test: Live data display

## BE Minor Project Demo Benefits
✅ Real network simulation (not fake data)
✅ Production-grade monitoring stack
✅ Prometheus/Grafana compatible
✅ Clean separation of concerns
✅ Multi-threading for concurrent operation
✅ Professional metrics naming conventions
✅ Emergency alert detection & tracking
✅ Open5GS integration (already running in WSL Ubuntu)
✅ Live Streamlit dashboard
