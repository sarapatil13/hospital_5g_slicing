"""
Enhanced 5G Smart Hospital Monitoring Dashboard

Live display of:
- Real-time QoS metrics (latency, throughput, packet loss) from simulation
- Emergency alert detection and tracking
- Open5GS service health status
- Hospital device status
- Network slice load and bandwidth allocation
"""

import streamlit as st
import pandas as pd
import requests
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------
# Streamlit Page Configuration
# -------------------------------------------------
st.set_page_config(
    page_title="5G Smart Hospital Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# Custom CSS & Styling
# -------------------------------------------------
st.markdown("""
<style>
:root {
    --color-urllc: #00d4ff;
    --color-embb: #ff6b6b;
    --color-mmtc: #51cf66;
    --color-emergency: #ff4757;
}

.big-title {
    font-size: 42px !important;
    font-weight: bold;
    color: #00d4ff;
    text-align: center;
    margin: 20px 0;
}

.section-title {
    font-size: 24px;
    font-weight: bold;
    color: #38bdf8;
    margin-top: 20px;
    margin-bottom: 15px;
    border-left: 4px solid #00d4ff;
    padding-left: 10px;
}

.metric-card {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 20px;
    border-radius: 12px;
    border-left: 4px solid #00d4ff;
    color: white;
    box-shadow: 0 4px 15px rgba(0, 212, 255, 0.1);
}

.metric-value {
    font-size: 28px;
    font-weight: bold;
    color: #00d4ff;
    margin: 10px 0;
}

.metric-label {
    font-size: 14px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.status-active {
    color: #00ff00;
    font-weight: bold;
}

.status-inactive {
    color: #ff4444;
    font-weight: bold;
}

.emergency-alert {
    background: linear-gradient(135deg, #ff4757 0%, #c60c30 100%);
    padding: 20px;
    border-radius: 12px;
    color: white;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    animation: pulse 1.5s infinite;
}

.emergency-inactive {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 20px;
    border-radius: 12px;
    color: #51cf66;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
}

.slice-urllc {
    border-left: 4px solid #00d4ff;
}

.slice-embb {
    border-left: 4px solid #ff6b6b;
}

.slice-mmtc {
    border-left: 4px solid #51cf66;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.device-active {
    color: #00ff00;
}

.device-inactive {
    color: #ff4444;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #334155;
}

th {
    background-color: #1e293b;
    color: #00d4ff;
    font-weight: bold;
}

tr:hover {
    background-color: #0f172a;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Configuration
# -------------------------------------------------
EXPORTER_URL = "http://localhost:8000"
METRICS_ENDPOINT = f"{EXPORTER_URL}/metrics"
REFRESH_INTERVAL = 2  # seconds


# -------------------------------------------------
# Helper Functions
# -------------------------------------------------
def fetch_metrics() -> Optional[Dict]:
    """Fetch current metrics from Prometheus exporter (no caching - real-time)."""
    try:
        logger.debug(f"Fetching from {METRICS_ENDPOINT}")
        response = requests.get(METRICS_ENDPOINT, timeout=5)
        logger.debug(f"Response status: {response.status_code}")
        if response.status_code == 200:
            metrics = parse_prometheus_metrics(response.text)
            logger.debug(f"Parsed metrics: {len(metrics.get('slices', {}))} slices")
            return metrics
        logger.warning(f"Non-200 status: {response.status_code}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in fetch_metrics: {type(e).__name__}: {e}")
        return None


def parse_prometheus_metrics(text: str) -> Dict:
    """Parse Prometheus text format metrics."""
    metrics = {
        'slices': {},
        'emergency': {},
        'services': {},
        'devices': {}
    }
    
    lines = text.split('\n')
    
    for line in lines:
        # Skip comments
        if line.startswith('#') or not line.strip():
            continue
        
        # Parse metric lines
        if 'hospital_slice_latency_ms' in line:
            parts = parse_metric_line(line)
            if parts:
                slice_name = parts['labels'].get('slice')
                if slice_name not in metrics['slices']:
                    metrics['slices'][slice_name] = {}
                metrics['slices'][slice_name]['latency'] = float(parts['value'])
        
        elif 'hospital_slice_throughput_mbps' in line:
            parts = parse_metric_line(line)
            if parts:
                slice_name = parts['labels'].get('slice')
                if slice_name not in metrics['slices']:
                    metrics['slices'][slice_name] = {}
                metrics['slices'][slice_name]['throughput'] = float(parts['value'])
        
        elif 'hospital_slice_packet_loss_percent' in line:
            parts = parse_metric_line(line)
            if parts:
                slice_name = parts['labels'].get('slice')
                if slice_name not in metrics['slices']:
                    metrics['slices'][slice_name] = {}
                metrics['slices'][slice_name]['packet_loss'] = float(parts['value'])
        
        elif 'hospital_emergency_detected' in line and '{' not in line:
            parts = parse_metric_line(line)
            if parts:
                metrics['emergency']['detected'] = bool(int(float(parts['value'])))
        
        elif 'hospital_emergency_alert_total' in line:
            parts = parse_metric_line(line)
            if parts:
                metrics['emergency']['total_alerts'] = int(float(parts['value']))
        
        elif 'hospital_open5gs_service_up' in line:
            parts = parse_metric_line(line)
            if parts:
                service = parts['labels'].get('service')
                metrics['services'][service] = bool(int(float(parts['value'])))
        
        elif 'hospital_device_active' in line:
            parts = parse_metric_line(line)
            if parts:
                device_id = parts['labels'].get('device_id')
                device_type = parts['labels'].get('device_type')
                slice_type = parts['labels'].get('slice')
                metrics['devices'][device_id] = {
                    'type': device_type,
                    'slice': slice_type,
                    'active': bool(int(float(parts['value'])))
                }
    
    return metrics


def parse_metric_line(line: str) -> Optional[Dict]:
    """Parse a single Prometheus metric line."""
    try:
        # Format: metric_name{label1="value1",...} value
        if '{' in line:
            metric_part, value = line.split('}')
            metric_name = metric_part.split('{')[0]
            labels_str = metric_part.split('{')[1]
            
            # Parse labels
            labels = {}
            for item in labels_str.split(','):
                key, val = item.split('=')
                labels[key.strip()] = val.strip().strip('"')
            
            return {
                'name': metric_name,
                'labels': labels,
                'value': value.strip()
            }
        else:
            # No labels
            metric_name, value = line.split()
            return {
                'name': metric_name,
                'labels': {},
                'value': value
            }
    except Exception:
        return None


def check_open5gs_status() -> Dict[str, bool]:
    """Check Open5GS services status via systemctl."""
    services = {
        'open5gs-amfd': '5G AMF (Access Stratum Management)',
        'open5gs-smfd': '5G SMF (Session Management)',
        'open5gs-upfd': '5G UPF (User Plane)',
    }
    
    status = {}
    for service, description in services.items():
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=2
            )
            status[service] = result.stdout.strip() == 'active'
        except Exception:
            status[service] = False
    
    return status


# -------------------------------------------------
# Main Dashboard
# -------------------------------------------------

# Header
st.markdown(
    '<p class="big-title">🏥 5G Smart Hospital Monitoring Dashboard</p>',
    unsafe_allow_html=True
)

# Fetch metrics once at the top
metrics = fetch_metrics()

# Connection status
exporter_connected = metrics is not None

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 System Status", "ONLINE" if exporter_connected else "OFFLINE")
with col2:
    st.metric("🔄 Last Update", datetime.now().strftime("%H:%M:%S"), "Real-time")
with col3:
    status_icon = "🟢" if exporter_connected else "🔴"
    st.metric("📡 Exporter", f"{status_icon} {'Connected' if exporter_connected else 'Disconnected'}")

if not exporter_connected:
    st.error("⚠️ Cannot connect to metrics exporter on http://localhost:8000 - Please check if enhanced_main.py is running")
    st.info("Start the main app with: `python3 enhanced_main.py`")

st.markdown("---")

# -------------------------------------------------
# SECTION 1: Emergency Status
# -------------------------------------------------
st.markdown('<p class="section-title">🚨 Emergency Alert System</p>', unsafe_allow_html=True)

if metrics:
    emergency_status = metrics.get('emergency', {})
    is_emergency = emergency_status.get('detected', False)
    emergency_count = emergency_status.get('total_alerts', 0)
    
    if is_emergency:
        st.markdown(
            '<div class="emergency-alert">🚨 EMERGENCY ALERT ACTIVE 🚨<br>Dynamic reallocation in progress!</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="emergency-inactive">✓ All systems normal — No emergency detected</div>',
            unsafe_allow_html=True
        )
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Emergency Alerts Total", emergency_count, "incidents")
    with col2:
        st.metric("Current Status", "ACTIVE" if is_emergency else "NORMAL", "real-time")
else:
    st.info("Waiting for metrics from simulator...")

st.markdown("---")

# -------------------------------------------------
# SECTION 2: Network Slice QoS Metrics
# -------------------------------------------------
st.markdown('<p class="section-title">📊 Network Slice QoS Metrics</p>', unsafe_allow_html=True)

if metrics and metrics.get('slices'):
    slices = metrics['slices']
    
    # Display QoS for each slice
    cols = st.columns(3)
    
    for idx, (slice_name, slice_class) in enumerate([
        ('URLLC', '🏥 Ultra-Reliable Low Latency'),
        ('eMBB', '📹 Enhanced Mobile Broadband'),
        ('mMTC', '📡 Massive Machine Type')
    ]):
        with cols[idx]:
            if slice_name in slices:
                data = slices[slice_name]
                
                # Determine border class
                border_class = f'slice-{slice_name.lower()}'
                
                st.markdown(f"""
                <div class="metric-card {border_class}">
                    <div class="metric-label">{slice_class}</div>
                    <div class="metric-value">{data.get('latency', 0):.2f} ms</div>
                    <div style="font-size: 12px; color: #94a3b8;">Latency</div>
                    <hr style="border: none; border-top: 1px solid #334155; margin: 10px 0;">
                    <div class="metric-value">{data.get('throughput', 0):.1f} Mbps</div>
                    <div style="font-size: 12px; color: #94a3b8;">Throughput</div>
                    <hr style="border: none; border-top: 1px solid #334155; margin: 10px 0;">
                    <div class="metric-value">{data.get('packet_loss', 0):.4f} %</div>
                    <div style="font-size: 12px; color: #94a3b8;">Packet Loss</div>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("Waiting for metrics from simulator...")

st.markdown("---")

# -------------------------------------------------
# SECTION 3: Open5GS Service Status
# -------------------------------------------------
st.markdown('<p class="section-title">📡 Open5GS Core Services</p>', unsafe_allow_html=True)

services_status = check_open5gs_status()

cols = st.columns(3)
service_list = list(services_status.items())

for idx, (service_name, is_active) in enumerate(service_list):
    with cols[idx % 3]:
        status_icon = "🟢" if is_active else "🔴"
        status_text = "ACTIVE" if is_active else "INACTIVE"
        status_class = "status-active" if is_active else "status-inactive"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{service_name}</div>
            <div style="font-size: 32px; margin: 10px 0;">{status_icon}</div>
            <div class="{status_class}">{status_text}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# SECTION 4: Hospital Devices Status
# -------------------------------------------------
st.markdown('<p class="section-title">🏥 Hospital Devices</p>', unsafe_allow_html=True)

# Define hospital devices
devices_info = [
    {'id': 'D001', 'name': 'Surgical Robot 1', 'type': 'surgical_robot', 'slice': 'URLLC', 'critical': True},
    {'id': 'D002', 'name': 'Surgical Robot 2', 'type': 'surgical_robot', 'slice': 'URLLC', 'critical': True},
    {'id': 'D003', 'name': 'ICU Monitor 1', 'type': 'icu_monitor', 'slice': 'URLLC', 'critical': True},
    {'id': 'D004', 'name': 'ICU Monitor 2', 'type': 'icu_monitor', 'slice': 'URLLC', 'critical': True},
    {'id': 'D005', 'name': 'Emergency Alert', 'type': 'emergency', 'slice': 'URLLC', 'critical': True},
    {'id': 'D006', 'name': 'Patient Records', 'type': 'patient_db', 'slice': 'eMBB', 'critical': False},
    {'id': 'D007', 'name': 'Imaging System', 'type': 'imaging', 'slice': 'eMBB', 'critical': False},
    {'id': 'D008', 'name': 'Video Consultation', 'type': 'video', 'slice': 'eMBB', 'critical': False},
    {'id': 'D009', 'name': 'Bed Tracker 1', 'type': 'bed_tracker', 'slice': 'mMTC', 'critical': False},
    {'id': 'D010', 'name': 'Bed Tracker 2', 'type': 'bed_tracker', 'slice': 'mMTC', 'critical': False},
    {'id': 'D011', 'name': 'Temperature Sensor 1', 'type': 'temp_sensor', 'slice': 'mMTC', 'critical': False},
    {'id': 'D012', 'name': 'Temperature Sensor 2', 'type': 'temp_sensor', 'slice': 'mMTC', 'critical': False},
    {'id': 'D013', 'name': 'Drug Dispenser', 'type': 'drug_dispenser', 'slice': 'mMTC', 'critical': False},
]

# Organize by slice
device_data = []
for device in devices_info:
    # Get device status from metrics if available
    device_metrics = metrics.get('devices', {}) if metrics else {}
    is_active = device_metrics.get(device['id'], {}).get('active', True)
    
    critical_tag = "🔴 CRITICAL" if device['critical'] else "✓ Normal"
    status_icon = "🟢" if is_active else "🔴"
    
    device_data.append({
        'Device ID': device['id'],
        'Name': device['name'],
        'Type': device['type'],
        'Slice': device['slice'],
        'Status': f"{status_icon} {'Active' if is_active else 'Offline'}",
        'Priority': critical_tag
    })

df = pd.DataFrame(device_data)

# Display as table
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        'Device ID': st.column_config.TextColumn(width=100),
        'Name': st.column_config.TextColumn(width=180),
        'Type': st.column_config.TextColumn(width=150),
        'Slice': st.column_config.TextColumn(width=100),
        'Status': st.column_config.TextColumn(width=120),
        'Priority': st.column_config.TextColumn(width=120),
    }
)

st.markdown("---")

# -------------------------------------------------
# SECTION 5: Live Monitoring
# -------------------------------------------------
st.markdown('<p class="section-title">⚙️ Live Monitoring</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Refresh Metrics", key="refresh"):
        st.rerun()

with col2:
    auto_refresh = st.checkbox("Auto-refresh (2s interval)", value=False)

if auto_refresh:
    import time
    time.sleep(REFRESH_INTERVAL)
    st.rerun()

# Display raw metrics if requested
if st.checkbox("Show raw Prometheus metrics"):
    st.code(requests.get(METRICS_ENDPOINT).text, language="text")

st.markdown("---")

# Footer
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 12px; padding: 20px;">
    <p>5G Smart Hospital Network Slicing Simulation</p>
    <p>Powered by Streamlit • Prometheus Metrics • Open5GS</p>
</div>
""", unsafe_allow_html=True)
