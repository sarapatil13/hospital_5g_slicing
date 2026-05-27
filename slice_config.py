class NetworkSlice:
    def __init__(self, name, slice_type, bandwidth_mbps, latency_ms,
                 reliability, priority, max_devices):
        self.name = name
        self.slice_type = slice_type
        self.bandwidth_mbps = bandwidth_mbps
        self.latency_ms = latency_ms
        self.reliability = reliability
        self.priority = priority
        self.max_devices = max_devices
        self.current_load = 0.0
        self.active_devices = []

URLLC_SLICE = NetworkSlice(
    name="URLLC_Slice", slice_type="URLLC",
    bandwidth_mbps=500, latency_ms=1,
    reliability=99.9999, priority=1, max_devices=10
)
EMBB_SLICE = NetworkSlice(
    name="eMBB_Slice", slice_type="eMBB",
    bandwidth_mbps=1000, latency_ms=10,
    reliability=99.9, priority=2, max_devices=20
)
MMTC_SLICE = NetworkSlice(
    name="mMTC_Slice", slice_type="mMTC",
    bandwidth_mbps=100, latency_ms=100,
    reliability=99.0, priority=3, max_devices=200
)

TOTAL_BANDWIDTH_MBPS = 2000
ALL_SLICES = [URLLC_SLICE, EMBB_SLICE, MMTC_SLICE]

def print_slice_summary():
    print("\n" + "="*60)
    print("   5G NETWORK SLICES — SMART HOSPITAL CONFIGURATION")
    print("="*60)
    for s in ALL_SLICES:
        print(f"\n  Slice      : {s.name}")
        print(f"  Type       : {s.slice_type}")
        print(f"  Bandwidth  : {s.bandwidth_mbps} Mbps")
        print(f"  Latency    : < {s.latency_ms} ms")
        print(f"  Reliability: {s.reliability}%")
        print(f"  Priority   : {s.priority}")
        print(f"  Max Devices: {s.max_devices}")
        print("  " + "-"*40)
    print(f"\n  Total Network Capacity: {TOTAL_BANDWIDTH_MBPS} Mbps")
    print("="*60 + "\n")

if __name__ == "__main__":
    print_slice_summary()