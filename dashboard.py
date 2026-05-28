import streamlit as st
import pandas as pd
import subprocess
from network_simulator import NetworkSimulator

# -------------------------------------------------
# Page Config
# -------------------------------------------------
st.set_page_config(
    page_title="5G Smart Hospital Dashboard",
    page_icon="🏥",
    layout="wide"
)

# -------------------------------------------------
# Custom CSS
# -------------------------------------------------
st.markdown("""
<style>
.big-title {
    font-size:40px !important;
    font-weight:bold;
    color:#00d4ff;
    text-align:center;
}

.metric-card {
    background-color:#111827;
    padding:20px;
    border-radius:15px;
    text-align:center;
    color:white;
    box-shadow:0px 0px 10px rgba(0,0,0,0.3);
}

.section-title {
    font-size:28px;
    font-weight:bold;
    color:#38bdf8;
    margin-top:20px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown(
    '<p class="big-title">🏥 5G Smart Hospital Monitoring Dashboard</p>',
    unsafe_allow_html=True
)

st.markdown("---")

# -------------------------------------------------
# Open5GS Status
# -------------------------------------------------
st.markdown(
    '<p class="section-title">📡 Open5GS Core Status</p>',
    unsafe_allow_html=True
)

services = [
    "open5gs-amfd",
    "open5gs-smfd",
    "open5gs-upfd"
]

cols = st.columns(3)

for idx, service in enumerate(services):
    result = subprocess.run(
        ["systemctl", "is-active", service],
        capture_output=True,
        text=True
    )

    status = result.stdout.strip()

    color = "🟢" if status == "active" else "🔴"

    cols[idx].markdown(f"""
    <div class="metric-card">
        <h3>{service}</h3>
        <h2>{color} {status.upper()}</h2>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# Run Simulation
# -------------------------------------------------
st.markdown(
    '<p class="section-title">🚑 Emergency Traffic Simulation</p>',
    unsafe_allow_html=True
)

sim = NetworkSimulator()

sim.run_normal()
emergency = sim.run_emergency()

# -------------------------------------------------
# Process Metrics
# -------------------------------------------------
data = {
    "Slice": [],
    "Latency": [],
    "Throughput": [],
    "Packet Loss": []
}

for slice_name in emergency:
    lat = sum(emergency[slice_name]["latency"]) / len(emergency[slice_name]["latency"])
    thr = sum(emergency[slice_name]["throughput"]) / len(emergency[slice_name]["throughput"])
    pkt = sum(emergency[slice_name]["packet_loss"]) / len(emergency[slice_name]["packet_loss"])

    data["Slice"].append(slice_name)
    data["Latency"].append(round(lat, 2))
    data["Throughput"].append(round(thr, 2))
    data["Packet Loss"].append(round(pkt, 2))

df = pd.DataFrame(data)

# -------------------------------------------------
# KPI Cards
# -------------------------------------------------
st.markdown(
    '<p class="section-title">📊 QoS Performance Metrics</p>',
    unsafe_allow_html=True
)

k1, k2, k3 = st.columns(3)

k1.markdown(f"""
<div class="metric-card">
<h3>Lowest Latency</h3>
<h1>{min(df['Latency'])} ms</h1>
</div>
""", unsafe_allow_html=True)

k2.markdown(f"""
<div class="metric-card">
<h3>Highest Throughput</h3>
<h1>{max(df['Throughput'])} Mbps</h1>
</div>
""", unsafe_allow_html=True)

k3.markdown(f"""
<div class="metric-card">
<h3>Max Packet Loss</h3>
<h1>{max(df['Packet Loss'])} %</h1>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# Data Table
# -------------------------------------------------
st.subheader("📋 Slice Metrics Table")

st.dataframe(df, use_container_width=True)

# -------------------------------------------------
# Charts
# -------------------------------------------------
c1, c2 = st.columns(2)

with c1:
    st.subheader("📈 Latency Comparison")
    st.bar_chart(df.set_index("Slice")["Latency"])

with c2:
    st.subheader("📈 Throughput Comparison")
    st.bar_chart(df.set_index("Slice")["Throughput"])

st.subheader("📈 Packet Loss Comparison")
st.bar_chart(df.set_index("Slice")["Packet Loss"])

st.markdown("---")

# -------------------------------------------------
# Footer
# -------------------------------------------------
st.success("✅ Open5GS-powered Smart Hospital Slicing System Running Successfully")
