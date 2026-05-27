from slice_config import URLLC_SLICE, EMBB_SLICE, MMTC_SLICE, TOTAL_BANDWIDTH_MBPS

class EmergencyReallocation:
    def __init__(self):
        self.normal_allocation = {
            "URLLC": URLLC_SLICE.bandwidth_mbps,
            "eMBB":  EMBB_SLICE.bandwidth_mbps,
            "mMTC":  MMTC_SLICE.bandwidth_mbps
        }
        self.emergency_allocation = {}

    def detect_emergency(self, urllc_load_percent):
        if urllc_load_percent > 80:
            print(f"\n  ⚠  EMERGENCY DETECTED — URLLC load at {urllc_load_percent}%!")
            return True
        return False

    def reallocate(self):
        print("\n>>> Starting dynamic resource reallocation...")
        # Steal bandwidth from eMBB and mMTC to protect URLLC
        embb_reduction  = EMBB_SLICE.bandwidth_mbps * 0.40   # cut 40%
        mmtc_reduction  = MMTC_SLICE.bandwidth_mbps * 0.50   # cut 50%
        bonus           = embb_reduction + mmtc_reduction

        self.emergency_allocation = {
            "URLLC": URLLC_SLICE.bandwidth_mbps + bonus,
            "eMBB":  EMBB_SLICE.bandwidth_mbps  - embb_reduction,
            "mMTC":  MMTC_SLICE.bandwidth_mbps  - mmtc_reduction
        }

        print("\n  Bandwidth Reallocation:")
        print(f"  {'Slice':<10} {'Before (Mbps)':>15} {'After (Mbps)':>15} {'Change':>10}")
        print("  " + "-"*52)
        for key in ["URLLC", "eMBB", "mMTC"]:
            before = self.normal_allocation[key]
            after  = round(self.emergency_allocation[key], 1)
            diff   = round(after - before, 1)
            sign   = "+" if diff > 0 else ""
            print(f"  {key:<10} {before:>15} {after:>15} {sign+str(diff):>10}")

        total = sum(self.emergency_allocation.values())
        print(f"\n  Total allocated: {round(total,1)} / {TOTAL_BANDWIDTH_MBPS} Mbps")
        print("\n  ✔  URLLC slice bandwidth boosted — life-critical devices protected.")
        print("  ✔  eMBB and mMTC reduced temporarily during emergency.")

    def restore(self):
        print("\n>>> Emergency resolved — restoring normal allocation...")
        for key, val in self.normal_allocation.items():
            print(f"  {key} restored to {val} Mbps")
        print("  ✔  All slices back to normal.\n")


if __name__ == "__main__":
    er = EmergencyReallocation()
    print("\n" + "="*60)
    print("   DYNAMIC RESOURCE REALLOCATION — EMERGENCY SCENARIO")
    print("="*60)

    # Simulate normal load
    print("\n  [Normal]    URLLC load: 45% — no action needed.")
    er.detect_emergency(45)

    # Simulate emergency
    print("\n  [Emergency] URLLC load spiking to 92%...")
    if er.detect_emergency(92):
        er.reallocate()

    # Restore
    er.restore()