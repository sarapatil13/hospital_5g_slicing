# 5G Smart Hospital Dashboard - Real-Time Plotly Enhancements

## 📊 Overview

The Streamlit dashboard has been enhanced with **professional real-time Plotly charts** for monitoring 5G network slicing metrics. All charts update live as metrics stream from the Prometheus exporter.

## ✨ New Features

### 1. **Real-Time Monitoring Charts Section**
   - Professional 2×2 grid layout with 4 separate charts
   - Dark cyberpunk styling matching the dashboard theme
   - Smooth animations and responsive design
   - Auto-updating every 2 seconds (configurable)

### 2. **Chart Types**

#### URLLC Latency Chart (Top-Left)
- **Metric**: Network slice latency in milliseconds
- **Style**: Cyan line (#00d4ff) with filled area
- **Data Points**: Last 120 measurements (~4 minutes)
- **Marker Type**: Circle markers
- **Use Case**: Monitor ultra-reliable low-latency communication performance

#### eMBB Throughput Chart (Top-Right)
- **Metric**: Enhanced mobile broadband throughput in Mbps
- **Style**: Red line (#ff6b6b) with filled area
- **Data Points**: Last 120 measurements (~4 minutes)
- **Marker Type**: Diamond markers
- **Use Case**: Track high-speed broadband network performance

#### mMTC Packet Loss Chart (Bottom-Left)
- **Metric**: Massive machine-type communication packet loss percentage
- **Style**: Green line (#51cf66) with filled area
- **Data Points**: Last 120 measurements (~4 minutes)
- **Marker Type**: Square markers
- **Use Case**: Monitor IoT device communication reliability

#### Emergency Events Timeline (Bottom-Right)
- **Events**: Emergency START and END events
- **Visual Indicators**: Red diamonds (START), Green diamonds (END)
- **Timeline Format**: Chronological display of emergency events
- **Use Case**: Track emergency alert history and duration

### 3. **Historical Data Storage**
- Session state maintains up to **120 data points** per metric
- Ring buffer pattern prevents memory leaks
- 4-minute rolling window at 2-second intervals
- Emergency events stored separately (up to 100 events)
- Data persists across dashboard refreshes

### 4. **Interactive Features**
- **Hover Details**: Display precise metric values when hovering
- **Responsive Layout**: Charts adapt to screen size
- **Dark Theme**: Cyberpunk-styled dark backgrounds with grid lines
- **Professional Colors**: 
  - URLLC: #00d4ff (Cyan)
  - eMBB: #ff6b6b (Red)
  - mMTC: #51cf66 (Green)
  - Emergency: #ff4757 (Alert Red)

### 5. **Chart Configuration**
All charts use professional telecom monitoring UI design with:
- Dark plot backgrounds (rgba(30, 41, 59, 0.5))
- Subtle grid lines for readability
- Monospace fonts for technical feel
- Hover information in unified format
- Proper margins and sizing

## 🏗️ Architecture

### Session State Structure
```python
st.session_state.metrics_history = {
    'timestamps': deque(maxlen=120),      # HH:MM:SS format
    'urllc_latency': deque(maxlen=120),   # milliseconds
    'embb_throughput': deque(maxlen=120), # Mbps
    'mmtc_packet_loss': deque(maxlen=120),# percentage
    'emergency_events': deque(maxlen=100),# [{time, type, duration}]
    'last_emergency_state': bool          # For state change detection
}
```

### Core Functions

#### `update_metrics_history(metrics: Dict)`
- Extracts current metric values
- Appends to historical deques
- Detects emergency state changes
- Records emergency events with timestamps

#### `create_urllc_latency_chart()`
- Generates URLLC latency chart
- Returns Plotly Figure object
- Renders with responsive width

#### `create_embb_throughput_chart()`
- Generates eMBB throughput chart
- Returns Plotly Figure object
- Renders with responsive width

#### `create_mmtc_packet_loss_chart()`
- Generates mMTC packet loss chart
- Returns Plotly Figure object
- Renders with responsive width

#### `create_emergency_timeline_chart()`
- Generates emergency events timeline
- Shows event markers with start/end status
- Returns Plotly Figure object

## 📈 Data Flow

```
Metrics Endpoint (http://localhost:8000/metrics)
          ↓
    fetch_metrics()
          ↓
   update_metrics_history()
          ↓
  Session State (deque storage)
          ↓
    Chart Functions
          ↓
   Plotly Rendering
```

## 🚀 Usage

### Manual Refresh
- Click "🔄 Refresh Metrics" button to force update
- Dashboard automatically updates if auto-refresh is enabled

### Auto-Refresh
- Enable "Auto-refresh (2s interval)" checkbox
- Dashboard reloads metrics every 2 seconds
- Charts update with new data points automatically

### Raw Metrics
- Check "Show raw Prometheus metrics" to view unprocessed data
- Displays full Prometheus text format output

## 📊 Dashboard Sections (Ordered)

1. **Header & System Status** - Connection status, last update time
2. **Emergency Alert System** - Emergency detection and alert counts
3. **Network Slice QoS Metrics** - Current latency/throughput/loss values (3 cards)
4. **Real-Time Monitoring Charts** - 4 Plotly charts with historical data ✨
5. **Open5GS Core Services** - Service health status (amfd, smfd, upfd)
6. **Hospital Devices** - Device status table
7. **Live Monitoring Controls** - Refresh buttons and checkboxes

## 🎨 Styling Details

### Colors (Cyberpunk Theme)
- Cyan (#00d4ff): URLLC, primary UI
- Red (#ff6b6b): eMBB, emergency
- Green (#51cf66): mMTC, alerts
- Dark Blue (#1e293b): Cards background
- Slate (#94a3b8): Text/labels

### Chart Styling
- Template: plotly_dark
- Font: Monospace for technical appearance
- Grid: Subtle rgba(100, 100, 100, 0.2)
- Fill: Semi-transparent areas under lines
- Markers: Slice-specific shapes (circle, diamond, square)

## 📦 Dependencies

### New Required Package
- **plotly** ≥5.0.0 - Interactive charting library

### Already Installed
- streamlit ≥1.20.0
- pandas ≥1.3.0
- requests ≥2.28.0
- prometheus-client ≥0.14.0

## ⚙️ Configuration Parameters

- **MAX_HISTORY**: 120 (data points kept per metric)
- **REFRESH_INTERVAL**: 2 seconds
- **Emergency Events Queue**: 100 events max
- **Chart Height**: 400px (latency/throughput/loss), 300px (timeline)

## 🔧 Installation & Setup

### 1. Install Dependencies
```bash
cd /home/sara/hospital_5g_slicing
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Main Application
```bash
python3 enhanced_main.py
```

### 3. Run Dashboard
In a separate terminal:
```bash
streamlit run enhanced_dashboard.py
```

### 4. View Dashboard
Open browser to: `http://localhost:8501`

## 📝 Implementation Notes

### Real-Time Updates
- Charts fetch metrics every 2 seconds via `fetch_metrics()`
- Historical data automatically accumulated in session state
- No fake data - all values from NetworkSimulator
- Smooth animations via Plotly rendering

### Performance
- Deque data structures (O(1) append/pop)
- Limited history prevents memory growth
- Plotly efficiently handles 120 data points
- No freezing or lag with auto-refresh enabled

### Error Handling
- Charts render gracefully with insufficient data
- Shows "Collecting historical data..." message initially
- Handles connection errors to metrics endpoint
- Emergency events detection prevents missed state changes

## 🎯 Key Metrics Monitored

| Metric | Slice | Range | Unit | Chart |
|--------|-------|-------|------|-------|
| Latency | URLLC | 1-2 | ms | Latency Chart |
| Throughput | eMBB | 600-700 | Mbps | Throughput Chart |
| Packet Loss | mMTC | 5-15 | % | Loss Chart |
| Emergencies | All | — | Events | Timeline Chart |

## 🚨 Emergency Detection

- Latency > 5ms OR Packet Loss > 1% triggers EMERGENCY state
- Emergency events recorded with timestamp
- Timeline shows START/END transitions
- Real-time detection in EmergencyDetector component

## 📱 Responsive Design

- Charts automatically scale with browser width
- 2×2 grid on desktop/tablet
- Cards stack responsively on mobile
- Touch-friendly on all devices

## 🔗 Related Components

- **metrics_exporter.py**: Provides /metrics endpoint (non-blocking)
- **enhanced_network_simulator.py**: Generates real metrics
- **enhanced_main.py**: Orchestrates all components
- **open5gs_monitor.py**: Monitors 5G services

## 📚 References

- [Plotly Documentation](https://plotly.com/python/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Prometheus Text Format](https://prometheus.io/docs/instrumenting/exposition_formats/)
- [5G Network Slicing](https://en.wikipedia.org/wiki/Network_slicing)

---

**Last Updated**: May 28, 2026  
**Dashboard Version**: 2.0 (Enhanced with Real-Time Charts)  
**Status**: ✅ Production Ready
