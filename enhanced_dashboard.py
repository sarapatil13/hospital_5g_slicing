"""
5G Smart Hospital Dashboard
- Manual emergency trigger button
- Live graphs showing normal vs emergency conditions
- Alerts panel
- Open5GS response simulation
"""

import streamlit as st
import pandas as pd
import requests
import subprocess
import time
import logging
from datetime import datetime
from typing import Dict, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="5G Smart Hospital Dashboard", page_icon="🏥", layout="wide")

st.markdown("""
<style>
.big-title { font-size:38px!important; font-weight:bold; color:#00d4ff; text-align:center; margin:16px 0; }
.section-title { font-size:20px; font-weight:bold; color:#38bdf8; margin-top:18px; margin-bottom:10px;
                 border-left:4px solid #00d4ff; padding-left:10px; }
.metric-card { background:linear-gradient(135deg,#1e293b,#0f172a); padding:16px; border-radius:10px;
               color:white; box-shadow:0 4px 12px rgba(0,212,255,.1); margin-bottom:6px; }
.metric-value { font-size:26px; font-weight:bold; color:#00d4ff; margin:6px 0; }
.metric-label { font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; }
.slice-urllc { border-left:4px solid #00d4ff; }
.slice-embb  { border-left:4px solid #ff6b6b; }
.slice-mmtc  { border-left:4px solid #51cf66; }

.alert-box {
    background: linear-gradient(135deg,#3d0000,#1a0000);
    border: 2px solid #ff4757;
    border-radius: 12px; padding: 20px; text-align: center;
    animation: pulse 1s infinite;
}
.alert-box h2 { color:#ff4757; font-size:28px; margin:0 0 8px; }
.alert-box p  { color:#ffaaaa; margin:4px 0; font-size:14px; }

.normal-box {
    background: linear-gradient(135deg,#0d2b1a,#061a10);
    border: 2px solid #51cf66;
    border-radius: 12px; padding: 20px; text-align: center;
}
.normal-box h2 { color:#51cf66; font-size:24px; margin:0 0 8px; }
.normal-box p  { color:#86efac; margin:4px 0; font-size:14px; }

.realloc-box {
    background:#1e293b; border-left:4px solid #ffa600;
    border-radius:8px; padding:14px; margin:8px 0;
    font-family: monospace; font-size:13px; color:#e2e8f0;
}

.svc-up   { background:#0d2b1a; border:1px solid #51cf66; border-radius:8px;
             padding:12px; text-align:center; color:#51cf66; font-weight:bold; }
.svc-down { background:#3d0000; border:1px solid #ff4757; border-radius:8px;
             padding:12px; text-align:center; color:#ff4757; font-weight:bold; }
.svc-stressed { background:#2d1a00; border:1px solid #ffa600; border-radius:8px;
                padding:12px; text-align:center; color:#ffa600; font-weight:bold; }

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.75} }
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────
EXPORTER_URL     = "http://localhost:8000"
METRICS_ENDPOINT = f"{EXPORTER_URL}/metrics"
REFRESH_INTERVAL = 2
MAX_HISTORY      = 120

SLA = {
    "URLLC": {"latency": 1.0,  "throughput": 400,  "packet_loss": 0.001},
    "eMBB":  {"latency": 10.0, "throughput": 800,  "packet_loss": 0.1},
    "mMTC":  {"latency": 100.0,"throughput": 50,   "packet_loss": 1.0},
}
SLICE_COLORS = {"URLLC":"#00d4ff","eMBB":"#ff6b6b","mMTC":"#51cf66"}
FILL_COLORS  = {"URLLC":"rgba(0,212,255,0.08)","eMBB":"rgba(255,107,107,0.08)","mMTC":"rgba(81,207,102,0.08)"}

# ── Session state ───────────────────────────────────────
def _init():
    if "h" not in st.session_state:
        st.session_state.h = {
            "ts":    deque(maxlen=MAX_HISTORY),
            "phase": deque(maxlen=MAX_HISTORY),
            "lat":   {s: deque(maxlen=MAX_HISTORY) for s in SLA},
            "thr":   {s: deque(maxlen=MAX_HISTORY) for s in SLA},
            "pkt":   {s: deque(maxlen=MAX_HISTORY) for s in SLA},
            "last_emerg": False,
            "events": deque(maxlen=30),
        }
    if "demo_emergency" not in st.session_state:
        st.session_state.demo_emergency = False
    if "demo_start_time" not in st.session_state:
        st.session_state.demo_start_time = None
    if "alerts" not in st.session_state:
        st.session_state.alerts = deque(maxlen=10)

_init()

# ── Fetch & parse ───────────────────────────────────────
def fetch_metrics() -> Optional[Dict]:
    try:
        r = requests.get(METRICS_ENDPOINT, timeout=5)
        if r.status_code == 200:
            return parse(r.text)
    except Exception:
        pass
    return None

def parse(text: str) -> Dict:
    out = {"slices":{},"emergency":{},"services":{},"devices":{}}
    for line in text.split("\n"):
        if line.startswith("#") or not line.strip():
            continue
        p = parse_line(line)
        if not p: continue
        if   "hospital_slice_latency_ms"          in line:
            out["slices"].setdefault(p["l"]["slice"],{})["latency"]    = float(p["v"])
        elif "hospital_slice_throughput_mbps"      in line:
            out["slices"].setdefault(p["l"]["slice"],{})["throughput"] = float(p["v"])
        elif "hospital_slice_packet_loss_percent"  in line:
            out["slices"].setdefault(p["l"]["slice"],{})["packet_loss"]= float(p["v"])
        elif "hospital_emergency_detected" in line and "{" not in line:
            out["emergency"]["detected"]     = bool(int(float(p["v"])))
        elif "hospital_emergency_alert_total" in line:
            out["emergency"]["total_alerts"] = int(float(p["v"]))
        elif "hospital_open5gs_service_up" in line:
            out["services"][p["l"]["service"]] = bool(int(float(p["v"])))
        elif "hospital_device_active" in line:
            d = p["l"]
            out["devices"][d["device_id"]] = {"type":d["device_type"],"slice":d["slice"],
                                               "active":bool(int(float(p["v"])))}
    return out

def parse_line(line):
    try:
        if "{" in line:
            mp, val = line.split("}")
            labels = {}
            for item in mp.split("{")[1].split(","):
                k,v = item.split("=")
                labels[k.strip()] = v.strip().strip('"')
            return {"l":labels,"v":val.strip()}
        else:
            _, val = line.split()
            return {"l":{},"v":val}
    except:
        return None

def push_history(metrics, is_demo_emerg):
    h   = st.session_state.h
    now = datetime.now().strftime("%H:%M:%S")
    # phase = demo override OR real detector
    sim_emerg = metrics.get("emergency",{}).get("detected", False) if metrics else False
    is_emerg  = is_demo_emerg or sim_emerg
    phase     = "emergency" if is_emerg else "normal"

    h["ts"].append(now)
    h["phase"].append(phase)
    for s in SLA:
        d = metrics.get("slices",{}).get(s,{}) if metrics else {}
        # during demo emergency, inject visible spikes on eMBB and mMTC
        lat = d.get("latency", 0)
        thr = d.get("throughput", 0)
        pkt = d.get("packet_loss", 0)
        if is_demo_emerg and s != "URLLC":
            import random
            lat = lat + random.uniform(20, 60)   # spike
            thr = thr * random.uniform(0.4, 0.6) # drop
            pkt = pkt + random.uniform(2, 8)     # jump
        h["lat"][s].append(round(lat,3))
        h["thr"][s].append(round(thr,2))
        h["pkt"][s].append(round(pkt,4))

    was = h["last_emerg"]
    if is_emerg and not was:
        h["events"].appendleft({"ts":now,"type":"START","src":"DEMO" if is_demo_emerg else "AUTO"})
        st.session_state.alerts.appendleft(
            {"ts":now,"level":"crit","msg":"🚨 EMERGENCY STARTED — URLLC load critical, reallocation triggered"})
    elif not is_emerg and was:
        h["events"].appendleft({"ts":now,"type":"END","src":"DEMO" if is_demo_emerg else "AUTO"})
        st.session_state.alerts.appendleft(
            {"ts":now,"level":"ok","msg":"✅ EMERGENCY RESOLVED — All slices restored to normal allocation"})
    h["last_emerg"] = is_emerg
    return is_emerg

def add_alert(level, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.alerts.appendleft({"ts":ts,"level":level,"msg":msg})

# ── Chart helpers ───────────────────────────────────────
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,30,48,0.8)",
    font=dict(color="#e2e8f0", family="monospace"),
    hovermode="x unified", legend=dict(orientation="h", y=-0.25),
    margin=dict(l=40,r=60,t=50,b=40),
    xaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.15)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(100,100,100,0.15)"),
)

def shade_emergency(fig, ts_list, phase_list):
    in_e, x0 = False, None
    for ts, ph in zip(ts_list, phase_list):
        if ph == "emergency" and not in_e:
            x0, in_e = ts, True
        elif ph == "normal" and in_e:
            fig.add_vrect(x0=x0, x1=ts, fillcolor="rgba(255,71,87,0.13)",
                          line_width=0, annotation_text="⚠ Emergency",
                          annotation_font=dict(color="#ff4757",size=10),
                          annotation_position="top left")
            in_e = False
    if in_e and x0 and ts_list:
        fig.add_vrect(x0=x0, x1=ts_list[-1], fillcolor="rgba(255,71,87,0.13)",
                      line_width=0, annotation_text="⚠ Emergency",
                      annotation_font=dict(color="#ff4757",size=10),
                      annotation_position="top left")

def chart_latency(ts, phase):
    fig = go.Figure()
    for s,col in SLICE_COLORS.items():
        fig.add_trace(go.Scatter(x=ts, y=list(st.session_state.h["lat"][s]),
            name=s, mode="lines", line=dict(color=col,width=2.5),
            hovertemplate=f"<b>{s}</b> %{{y:.2f}} ms<extra></extra>"))
    for s,col in SLICE_COLORS.items():
        fig.add_hline(y=SLA[s]["latency"], line_dash="dot", line_color=col, line_width=1,
                      annotation_text=f"{s} SLA", annotation_position="right",
                      annotation_font=dict(color=col,size=10))
    shade_emergency(fig, ts, phase)
    fig.update_layout(title="⏱ Latency (ms) — all slices", height=320, **BASE_LAYOUT)
    return fig

def chart_throughput(ts, phase):
    fig = go.Figure()
    for s,col in SLICE_COLORS.items():
        fig.add_trace(go.Scatter(x=ts, y=list(st.session_state.h["thr"][s]),
            name=s, mode="lines", line=dict(color=col,width=2.5),
            fill="tozeroy", fillcolor=FILL_COLORS[s],
            hovertemplate=f"<b>{s}</b> %{{y:.1f}} Mbps<extra></extra>"))
    shade_emergency(fig, ts, phase)
    fig.update_layout(title="📶 Throughput (Mbps) — all slices", height=320, **BASE_LAYOUT)
    return fig

def chart_packet_loss(ts, phase):
    fig = go.Figure()
    for s,col in SLICE_COLORS.items():
        fig.add_trace(go.Bar(x=ts, y=list(st.session_state.h["pkt"][s]),
            name=s, marker_color=col, opacity=0.85,
            hovertemplate=f"<b>{s}</b> %{{y:.4f}}%<extra></extra>"))
    shade_emergency(fig, ts, phase)
    fig.update_layout(title="📉 Packet Loss (%) — all slices", height=300,
                      barmode="group", **BASE_LAYOUT)
    return fig

def chart_comparison():
    h = st.session_state.h
    phases = list(h["phase"])
    ni = [i for i,p in enumerate(phases) if p=="normal"]
    ei = [i for i,p in enumerate(phases) if p=="emergency"]
    if not ni or not ei:
        return None

    def avg(lst, idxs):
        vals = list(lst)
        return round(sum(vals[i] for i in idxs)/len(idxs),3)

    fig = make_subplots(rows=1, cols=3,
        subplot_titles=["Latency (ms)","Throughput (Mbps)","Packet Loss (%)"],
        horizontal_spacing=0.1)

    for ci, key in enumerate(["lat","thr","pkt"], start=1):
        for phase_name, idxs, color in [("Normal",ni,"#51cf66"),("Emergency",ei,"#ff4757")]:
            fig.add_trace(go.Bar(
                name=phase_name, x=list(SLA.keys()),
                y=[avg(h[key][s], idxs) for s in SLA],
                marker_color=color, opacity=0.85,
                showlegend=(ci==1),
                hovertemplate=f"<b>{phase_name}</b><br>%{{x}}: %{{y:.3f}}<extra></extra>"),
                row=1, col=ci)

    fig.update_layout(
        title="🔄 Normal vs Emergency — Average Comparison",
        barmode="group", height=340,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(20,30,48,0.8)",
        font=dict(color="#e2e8f0",family="monospace"),
        legend=dict(orientation="h",y=-0.2),
        margin=dict(l=40,r=40,t=60,b=40))
    for i in range(1,4):
        fig.update_xaxes(showgrid=False, row=1, col=i)
        fig.update_yaxes(gridcolor="rgba(100,100,100,0.15)", row=1, col=i)
    return fig

# ════════════════════════════════════════════════
#  MAIN DASHBOARD
# ════════════════════════════════════════════════
st.markdown('<p class="big-title">🏥 5G Smart Hospital Network Dashboard</p>',
            unsafe_allow_html=True)

metrics = fetch_metrics()
connected = metrics is not None
is_emerg = push_history(metrics, st.session_state.demo_emergency)

# ── Top status bar ──────────────────────────────
c1,c2,c3,c4 = st.columns(4)
c1.metric("System",      "🟢 ONLINE" if connected else "🔴 OFFLINE")
c2.metric("Last Update", datetime.now().strftime("%H:%M:%S"))
c3.metric("Phase",       "🚨 EMERGENCY" if is_emerg else "✅ NORMAL")
total_ev = len([e for e in st.session_state.h["events"] if e["type"]=="START"])
c4.metric("Emergency Events", total_ev)

if not connected:
    st.error("⚠️ Cannot connect to http://localhost:8000 — run `python3 enhanced_main.py` first")

st.markdown("---")

# ════════════════════════════════════════════════
# SECTION 1 — EMERGENCY CONTROL + ALERT
# ════════════════════════════════════════════════
st.markdown('<p class="section-title">🚨 Emergency Control</p>', unsafe_allow_html=True)

btn_col, status_col = st.columns([1, 2])

with btn_col:
    st.markdown("**Simulate emergency for demo:**")
    if not st.session_state.demo_emergency:
        if st.button("🚨 TRIGGER EMERGENCY", type="primary", use_container_width=True):
            st.session_state.demo_emergency = True
            st.session_state.demo_start_time = datetime.now()
            add_alert("crit", "🚨 DEMO EMERGENCY triggered manually")
            st.rerun()
    else:
        elapsed = (datetime.now() - st.session_state.demo_start_time).seconds if st.session_state.demo_start_time else 0
        st.markdown(f"<div style='color:#ff4757;font-size:13px;margin-bottom:8px;'>⏱ Emergency active for {elapsed}s</div>",
                    unsafe_allow_html=True)
        if st.button("✅ RESOLVE EMERGENCY", type="secondary", use_container_width=True):
            st.session_state.demo_emergency = False
            st.session_state.demo_start_time = None
            add_alert("ok","✅ Emergency manually resolved — restoring normal bandwidth allocation")
            st.rerun()

    st.markdown("""
    <div style='background:#1e293b;border-radius:6px;padding:10px;font-size:11px;color:#94a3b8;margin-top:8px;'>
      <b style='color:#ffa600;'>What happens when triggered:</b><br>
      • eMBB &amp; mMTC latency spikes<br>
      • Their throughput drops 40–60%<br>
      • URLLC stays protected (slice isolation)<br>
      • Open5GS AMF/SMF show stress response<br>
      • Bandwidth auto-reallocated to URLLC
    </div>
    """, unsafe_allow_html=True)

with status_col:
    if is_emerg:
        st.markdown("""
        <div class="alert-box">
          <h2>🚨 EMERGENCY ACTIVE</h2>
          <p>URLLC load critical — dynamic reallocation triggered</p>
          <p>Surgical robots &amp; ICU monitors: <b style='color:white;'>PROTECTED ✓</b></p>
          <p>eMBB &amp; mMTC: <b style='color:#ffaaaa;'>BANDWIDTH REDUCED</b></p>
        </div>
        """, unsafe_allow_html=True)

        # Show reallocation table
        st.markdown("""
        <div class="realloc-box">
          <b style='color:#ffa600;'>⚡ Live Bandwidth Reallocation:</b><br><br>
          <span style='color:#94a3b8;'>Slice &nbsp;&nbsp;&nbsp;&nbsp; Before &nbsp;&nbsp; After &nbsp;&nbsp; Change</span><br>
          <span style='color:#00d4ff;'>URLLC &nbsp;&nbsp;&nbsp; 500 Mbps → <b>1100 Mbps</b> &nbsp; +600 ✓</span><br>
          <span style='color:#ff6b6b;'>eMBB &nbsp;&nbsp;&nbsp;&nbsp; 1000 Mbps → <b>600 Mbps</b> &nbsp;&nbsp; −400</span><br>
          <span style='color:#51cf66;'>mMTC &nbsp;&nbsp;&nbsp;&nbsp; 100 Mbps → <b>50 Mbps</b> &nbsp;&nbsp;&nbsp; −50</span><br><br>
          <span style='color:#51cf66;'>✔ Life-critical devices protected</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="normal-box">
          <h2>✅ ALL SYSTEMS NORMAL</h2>
          <p>All slices operating within SLA</p>
          <p>URLLC: 500 Mbps &nbsp;|&nbsp; eMBB: 1000 Mbps &nbsp;|&nbsp; mMTC: 100 Mbps</p>
          <p>No reallocation needed</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════
# SECTION 2 — OPEN5GS RESPONSE
# ════════════════════════════════════════════════
st.markdown('<p class="section-title">📡 Open5GS Core Network Response</p>', unsafe_allow_html=True)

st.markdown("""
<div style='background:rgba(30,41,59,0.6);border-left:3px solid #00d4ff;padding:10px 14px;
border-radius:6px;margin-bottom:12px;font-size:12px;color:#94a3b8;'>
<b style='color:#00d4ff;'>How Open5GS responds to emergency:</b>
AMF handles device re-registration when URLLC load spikes.
SMF creates new high-priority sessions for critical devices.
UPF reprioritises data plane traffic — URLLC packets get forwarded first.
</div>
""", unsafe_allow_html=True)

svc_cols = st.columns(5)
services = {
    "AMF": {"role":"Access Management","urllc":True,  "embb":False,"color_normal":"#51cf66"},
    "SMF": {"role":"Session Management","urllc":True, "embb":True, "color_normal":"#51cf66"},
    "UPF": {"role":"User Plane",        "urllc":True, "embb":True, "color_normal":"#51cf66"},
    "UDM": {"role":"User Data Mgmt",    "urllc":False,"embb":False,"color_normal":"#51cf66"},
    "NRF": {"role":"Network Registry",  "urllc":False,"embb":False,"color_normal":"#51cf66"},
}

for i, (svc, info) in enumerate(services.items()):
    with svc_cols[i]:
        if is_emerg and info["urllc"]:
            # Stressed but handling the emergency
            st.markdown(f"""
            <div class="svc-stressed">
              <div style='font-size:22px;'>⚡</div>
              <div style='font-size:15px;font-weight:bold;'>{svc}</div>
              <div style='font-size:10px;margin:4px 0;'>{info['role']}</div>
              <div style='font-size:11px;'>STRESSED</div>
              <div style='font-size:10px;color:#ffd580;'>Handling URLLC priority</div>
            </div>
            """, unsafe_allow_html=True)
        elif is_emerg and info["embb"]:
            st.markdown(f"""
            <div class="svc-stressed">
              <div style='font-size:22px;'>⚠️</div>
              <div style='font-size:15px;font-weight:bold;'>{svc}</div>
              <div style='font-size:10px;margin:4px 0;'>{info['role']}</div>
              <div style='font-size:11px;'>DEGRADED</div>
              <div style='font-size:10px;color:#ffd580;'>eMBB sessions deprioritised</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="svc-up">
              <div style='font-size:22px;'>🟢</div>
              <div style='font-size:15px;font-weight:bold;'>{svc}</div>
              <div style='font-size:10px;margin:4px 0;color:#86efac;'>{info['role']}</div>
              <div style='font-size:11px;'>ACTIVE</div>
              <div style='font-size:10px;'>Normal operation</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════
# SECTION 3 — LIVE GRAPHS
# ════════════════════════════════════════════════
st.markdown('<p class="section-title">📈 Live Graphs — Normal &amp; Emergency</p>',
            unsafe_allow_html=True)

st.markdown("""
<div style='background:rgba(30,41,59,0.5);border-left:3px solid #ffa600;
padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:12px;color:#94a3b8;'>
<b style='color:#ffa600;'>Reading the graphs:</b>
🔴 Red shaded = emergency phase active &nbsp;|&nbsp;
Dashed lines = SLA thresholds &nbsp;|&nbsp;
URLLC (blue) should stay flat even during emergency — that proves slicing works.
</div>
""", unsafe_allow_html=True)

h  = st.session_state.h
ts = list(h["ts"])
ph = list(h["phase"])

if len(ts) >= 2:
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(chart_latency(ts, ph), use_container_width=True,
                        config={"displayModeBar":False})
    with c2:
        st.plotly_chart(chart_throughput(ts, ph), use_container_width=True,
                        config={"displayModeBar":False})

    st.plotly_chart(chart_packet_loss(ts, ph), use_container_width=True,
                    config={"displayModeBar":False})

    cmp = chart_comparison()
    if cmp:
        st.markdown("#### Normal vs Emergency — Side-by-Side Average")
        st.plotly_chart(cmp, use_container_width=True, config={"displayModeBar":False})
    else:
        st.info("💡 Trigger the emergency above — once you resolve it, the comparison chart appears here showing the difference.")
else:
    st.info("Collecting data… graphs appear in a few seconds. Make sure `python3 enhanced_main.py` is running.")

st.markdown("---")

# ════════════════════════════════════════════════
# SECTION 4 — ALERT LOG
# ════════════════════════════════════════════════
st.markdown('<p class="section-title">🔔 Alert Log</p>', unsafe_allow_html=True)

alerts = list(st.session_state.alerts)
if alerts:
    html = '<div style="background:#0f172a;border-radius:10px;padding:14px;max-height:200px;overflow-y:auto;">'
    for a in alerts:
        color = "#ff4757" if a["level"]=="crit" else "#51cf66"
        html += f'<div style="color:{color};font-family:monospace;font-size:12px;margin:3px 0;">[{a["ts"]}] {a["msg"]}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
else:
    st.markdown('<div style="background:#0f172a;border-radius:10px;padding:14px;color:#94a3b8;font-size:13px;">No alerts yet — trigger an emergency to see alerts appear here.</div>',
                unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════
# SECTION 5 — QoS CARDS
# ════════════════════════════════════════════════
st.markdown('<p class="section-title">📊 Current QoS per Slice</p>', unsafe_allow_html=True)

if metrics and metrics.get("slices"):
    cols = st.columns(3)
    for idx,(s,label) in enumerate([
        ("URLLC","🏥 Ultra-Reliable Low Latency"),
        ("eMBB", "📹 Enhanced Mobile Broadband"),
        ("mMTC", "📡 Massive Machine Type")
    ]):
        d = metrics["slices"].get(s,{})
        lat = d.get("latency",0)
        thr = d.get("throughput",0)
        pkt = d.get("packet_loss",0)
        ok  = lat<=SLA[s]["latency"] and thr>=SLA[s]["throughput"] and pkt<=SLA[s]["packet_loss"]
        badge_color = "#51cf66" if ok else "#ff4757"
        badge = "✅ SLA MET" if ok else "🚨 SLA BREACH"
        with cols[idx]:
            st.markdown(f"""
            <div class="metric-card slice-{s.lower()}">
              <div class="metric-label">{label}</div>
              <div style="color:{badge_color};font-size:12px;margin:4px 0;">{badge}</div>
              <div class="metric-value">{lat:.2f} ms</div>
              <div style="font-size:11px;color:#94a3b8;">Latency (SLA ≤{SLA[s]['latency']}ms)</div>
              <hr style="border:none;border-top:1px solid #334155;margin:8px 0;">
              <div class="metric-value">{thr:.1f} Mbps</div>
              <div style="font-size:11px;color:#94a3b8;">Throughput</div>
              <hr style="border:none;border-top:1px solid #334155;margin:8px 0;">
              <div class="metric-value">{pkt:.4f}%</div>
              <div style="font-size:11px;color:#94a3b8;">Packet Loss</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Waiting for metrics…")

st.markdown("---")

# ════════════════════════════════════════════════
# SECTION 6 — DEVICES
# ════════════════════════════════════════════════
st.markdown('<p class="section-title">🏥 Hospital Devices</p>', unsafe_allow_html=True)

devices_info = [
    {"id":"D001","name":"Surgical Robot 1",    "slice":"URLLC","critical":True},
    {"id":"D002","name":"Surgical Robot 2",    "slice":"URLLC","critical":True},
    {"id":"D003","name":"ICU Monitor 1",       "slice":"URLLC","critical":True},
    {"id":"D004","name":"ICU Monitor 2",       "slice":"URLLC","critical":True},
    {"id":"D005","name":"Emergency Alert",     "slice":"URLLC","critical":True},
    {"id":"D006","name":"Patient Records",     "slice":"eMBB", "critical":False},
    {"id":"D007","name":"Imaging System",      "slice":"eMBB", "critical":False},
    {"id":"D008","name":"Video Consultation",  "slice":"eMBB", "critical":False},
    {"id":"D009","name":"Bed Tracker 1",       "slice":"mMTC","critical":False},
    {"id":"D010","name":"Bed Tracker 2",       "slice":"mMTC","critical":False},
    {"id":"D011","name":"Temperature Sensor 1","slice":"mMTC","critical":False},
    {"id":"D012","name":"Temperature Sensor 2","slice":"mMTC","critical":False},
    {"id":"D013","name":"Drug Dispenser",      "slice":"mMTC","critical":False},
]
dev_m = metrics.get("devices",{}) if metrics else {}
rows = []
for d in devices_info:
    active = dev_m.get(d["id"],{}).get("active",True)
    # during emergency, non-critical devices may show degraded
    degraded = is_emerg and not d["critical"]
    status = "🟢 Active" if (active and not degraded) else ("⚠️ Degraded" if degraded else "🔴 Offline")
    rows.append({"ID":d["id"],"Name":d["name"],"Slice":d["slice"],
                 "Status":status,"Priority":"🔴 Critical" if d["critical"] else "✓ Normal"})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Controls ──────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Refresh"):
        st.rerun()
with col2:
    if st.checkbox("Auto-refresh every 2s", value=False):
        time.sleep(REFRESH_INTERVAL)
        st.rerun()

if st.checkbox("Show raw Prometheus metrics"):
    try:
        st.code(requests.get(METRICS_ENDPOINT).text, language="text")
    except:
        st.error("Could not fetch")

st.markdown("""
<div style="text-align:center;color:#94a3b8;font-size:12px;padding:16px;">
  5G Smart Hospital Network Slicing · Streamlit · Prometheus · Open5GS
</div>
""", unsafe_allow_html=True)