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
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import plotly.graph_objects as go
from collections import deque

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
MAX_HISTORY = 120  # Keep 120 data points (4 minutes at 2s intervals)

# -------------------------------------------------
# Session State Initialization
# -------------------------------------------------
if 'metrics_history' not in st.session_state:
    st.session_state.metrics_history = {
        'timestamps': deque(maxlen=MAX_HISTORY),
        'urllc_latency': deque(maxlen=MAX_HISTORY),
        'embb_throughput': deque(maxlen=MAX_HISTORY),
        'mmtc_packet_loss': deque(maxlen=MAX_HISTORY),
        'emergency_events': deque(maxlen=100),
        'last_emergency_state': False
    }

if 'chart_config' not in st.session_state:
    st.session_state.chart_config = {
        'template': 'plotly_dark',
        'margin': dict(l=40, r=40, t=40, b=40)
    }


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


def create_urllc_latency_chart():
    """Create real-time URLLC latency chart."""
    history = st.session_state.metrics_history
    
    if len(history['timestamps']) == 0:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(history['timestamps']),
        y=list(history['urllc_latency']),
        mode='lines+markers',
        name='URLLC Latency',
        line=dict(color='#00d4ff', width=3),
        marker=dict(size=6, color='#00d4ff', symbol='circle'),
        fill='tozeroy',
        fillcolor='rgba(0, 212, 255, 0.1)',
        hovertemplate='<b>URLLC Latency</b><br>Time: %{x}<br>Latency: %{y:.2f} ms<extra></extra>'
    ))
    
    fig.update_layout(
        title='📊 URLLC Latency Monitoring',
        xaxis_title='Time',
        yaxis_title='Latency (ms)',
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30, 41, 59, 0.5)',
        font=dict(color='#e2e8f0', family='monospace'),
        margin=dict(l=40, r=40, t=60, b=40),
        height=400,
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
    )
    
    return fig


def create_embb_throughput_chart():
    """Create real-time eMBB throughput chart."""
    history = st.session_state.metrics_history
    
    if len(history['timestamps']) == 0:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(history['timestamps']),
        y=list(history['embb_throughput']),
        mode='lines+markers',
        name='eMBB Throughput',
        line=dict(color='#ff6b6b', width=3),
        marker=dict(size=6, color='#ff6b6b', symbol='diamond'),
        fill='tozeroy',
        fillcolor='rgba(255, 107, 107, 0.1)',
        hovertemplate='<b>eMBB Throughput</b><br>Time: %{x}<br>Throughput: %{y:.1f} Mbps<extra></extra>'
    ))
    
    fig.update_layout(
        title='📈 eMBB Throughput Monitoring',
        xaxis_title='Time',
        yaxis_title='Throughput (Mbps)',
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30, 41, 59, 0.5)',
        font=dict(color='#e2e8f0', family='monospace'),
        margin=dict(l=40, r=40, t=60, b=40),
        height=400,
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
    )
    
    return fig


def create_mmtc_packet_loss_chart():
    """Create real-time mMTC packet loss chart."""
    history = st.session_state.metrics_history
    
    if len(history['timestamps']) == 0:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(history['timestamps']),
        y=list(history['mmtc_packet_loss']),
        mode='lines+markers',
        name='mMTC Packet Loss',
        line=dict(color='#51cf66', width=3),
        marker=dict(size=6, color='#51cf66', symbol='square'),
        fill='tozeroy',
        fillcolor='rgba(81, 207, 102, 0.1)',
        hovertemplate='<b>mMTC Packet Loss</b><br>Time: %{x}<br>Loss: %{y:.4f} %<extra></extra>'
    ))
    
    fig.update_layout(
        title='📉 mMTC Packet Loss Monitoring',
        xaxis_title='Time',
        yaxis_title='Packet Loss (%)',
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30, 41, 59, 0.5)',
        font=dict(color='#e2e8f0', family='monospace'),
        margin=dict(l=40, r=40, t=60, b=40),
        height=400,
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
    )
    
    return fig


def create_emergency_timeline_chart():
    """Create emergency alerts timeline chart."""
    history = st.session_state.metrics_history
    
    if len(history['emergency_events']) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No emergency events recorded", xref="paper", yref="paper",
                          x=0.5, y=0.5, showarrow=False, font=dict(size=14, color='#94a3b8'))
        fig.update_layout(
            title='🚨 Emergency Events Timeline',
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(30, 41, 59, 0.5)',
            height=300,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    events = list(history['emergency_events'])
    event_times = [e['time'] for e in events]
    event_durations = [e['duration'] for e in events]
    event_colors = ['#ff4757' if e['type'] == 'START' else '#51cf66' for e in events]
    event_labels = [f"Emergency {e['type']}" for e in events]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=event_times,
        y=[1]*len(event_times),
        mode='markers+text',
        marker=dict(size=12, color=event_colors, symbol='diamond'),
        text=event_labels,
        textposition='top center',
        hovertemplate='<b>%{text}</b><br>Time: %{x}<extra></extra>'
    ))
    
    fig.update_layout(
        title='🚨 Emergency Events Timeline',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(30, 41, 59, 0.5)',
        font=dict(color='#e2e8f0', family='monospace'),
        margin=dict(l=40, r=40, t=60, b=40),
        height=300,
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.2)'),
        yaxis=dict(visible=False),
        hovermode='closest'
    )
    
    return fig


def update_metrics_history(metrics: Dict):
    """Update historical metrics in session state."""
    if not metrics or not metrics.get('slices'):
        return
    
    slices = metrics['slices']
    current_time = datetime.now().strftime('%H:%M:%S')
    
    # Update history
    history = st.session_state.metrics_history
    history['timestamps'].append(current_time)
    
    if 'URLLC' in slices:
        history['urllc_latency'].append(slices['URLLC'].get('latency', 0))
    
    if 'eMBB' in slices:
        history['embb_throughput'].append(slices['eMBB'].get('throughput', 0))
    
    if 'mMTC' in slices:
        history['mmtc_packet_loss'].append(slices['mMTC'].get('packet_loss', 0))
    
    # Track emergency events
    is_emergency = metrics.get('emergency', {}).get('detected', False)
    last_state = history['last_emergency_state']
    
    if is_emergency and not last_state:
        # Emergency started
        history['emergency_events'].append({
            'time': current_time,
            'type': 'START',
            'duration': 0
        })
    elif not is_emergency and last_state:
        # Emergency ended
        history['emergency_events'].append({
            'time': current_time,
            'type': 'END',
            'duration': 0
        })
    
    history['last_emergency_state'] = is_emergency


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

# Update historical metrics for charts
if metrics:
    update_metrics_history(metrics)

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
# SECTION 3: Real-Time Monitoring Charts
# -------------------------------------------------
st.markdown('<p class="section-title">📊 Real-Time Monitoring Charts</p>', unsafe_allow_html=True)

if metrics and st.session_state.metrics_history['timestamps']:
    # Create a 2x2 grid of charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        urllc_chart = create_urllc_latency_chart()
        if urllc_chart:
            st.plotly_chart(urllc_chart, use_container_width=True, config={'responsive': True})
    
    with chart_col2:
        embb_chart = create_embb_throughput_chart()
        if embb_chart:
            st.plotly_chart(embb_chart, use_container_width=True, config={'responsive': True})
    
    chart_col3, chart_col4 = st.columns(2)
    
    with chart_col3:
        mmtc_chart = create_mmtc_packet_loss_chart()
        if mmtc_chart:
            st.plotly_chart(mmtc_chart, use_container_width=True, config={'responsive': True})
    
    with chart_col4:
        emergency_chart = create_emergency_timeline_chart()
        if emergency_chart:
            st.plotly_chart(emergency_chart, use_container_width=True, config={'responsive': True})
    
    # Display chart summary
    st.markdown("""
    <div style="background: rgba(30, 41, 59, 0.5); padding: 15px; border-radius: 8px; margin-top: 15px;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0;">
            💡 <b>Chart Info:</b> Charts display the last 120 data points (≈4 minutes). 
            Each data point represents a 2-second interval. Hover over charts for precise values.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    if not metrics:
        st.info("Waiting for connection to metrics exporter...")
    else:
        st.info("Collecting historical data for charts (need at least 1 data point)...")

st.markdown("---")

# -------------------------------------------------
# SECTION 4: Open5GS Service Status
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
# SECTION 5: Hospital Devices Status
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
# SECTION 6: Live Monitoring
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
