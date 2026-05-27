import random
import time
from slice_config import URLLC_SLICE, EMBB_SLICE, MMTC_SLICE, ALL_SLICES
from hospital_devices import ALL_DEVICES

random.seed(42)

class NetworkSimulator:
    def __init__(self):
        self.slices = ALL_SLICES
        self.devices = ALL_DEVICES
        self.time_steps = 20
        self.results = {s.slice_type: {
            "latency": [], "throughput": [], "packet_loss": []
        } for s in self.slices}

    def simulate_latency(self, slice_obj, overloaded=False):
        base = slice_obj.latency_ms
        if slice_obj.slice_type == "URLLC":
            noise = random.uniform(0.0, 0.3)
            spike = random.uniform(5, 15) if overloaded else 0
        elif slice_obj.slice_type == "eMBB":
            noise = random.uniform(0, 3)
            spike = random.uniform(20, 40) if overloaded else 0
        else:  # mMTC
            noise = random.uniform(0, 20)
            spike = random.uniform(50, 100) if overloaded else 0
        return round(base + noise + spike, 3)

    def simulate_throughput(self, slice_obj, overloaded=False):
        base = slice_obj.bandwidth_mbps
        drop = random.uniform(0.3, 0.5) if overloaded else random.uniform(0.0, 0.1)
        return round(base * (1 - drop), 2)

    def simulate_packet_loss(self, slice_obj, overloaded=False):
        if slice_obj.slice_type == "URLLC":
            base = random.uniform(0.0001, 0.001)
            spike = random.uniform(0.5, 1.5) if overloaded else 0
        elif slice_obj.slice_type == "eMBB":
            base = random.uniform(0.01, 0.1)
            spike = random.uniform(2, 5) if overloaded else 0
        else:
            base = random.uniform(0.1, 0.5)
            spike = random.uniform(5, 10) if overloaded else 0
        return round(base + spike, 4)

    def run_normal(self):
        print("\n>>> Running NORMAL traffic simulation...")
        for t in range(self.time_steps):
            for s in self.slices:
                self.results[s.slice_type]["latency"].append(
                    self.simulate_latency(s))
                self.results[s.slice_type]["throughput"].append(
                    self.simulate_throughput(s))
                self.results[s.slice_type]["packet_loss"].append(
                    self.simulate_packet_loss(s))
        print("    Normal simulation complete.")

    def run_emergency(self):
        print("\n>>> Injecting EMERGENCY traffic spike...")
        emergency_results = {s.slice_type: {
            "latency": [], "throughput": [], "packet_loss": []
        } for s in self.slices}

        for t in range(self.time_steps):
            # Emergency = overload on eMBB and mMTC
            # URLLC stays protected by dynamic reallocation
            for s in self.slices:
                overloaded = s.slice_type in ["eMBB", "mMTC"]
                emergency_results[s.slice_type]["latency"].append(
                    self.simulate_latency(s, overloaded))
                emergency_results[s.slice_type]["throughput"].append(
                    self.simulate_throughput(s, overloaded))
                emergency_results[s.slice_type]["packet_loss"].append(
                    self.simulate_packet_loss(s, overloaded))

        print("    Emergency simulation complete.")
        return emergency_results

    def print_summary(self, results, label=""):
        print(f"\n{'='*60}")
        print(f"  SIMULATION RESULTS {label}")
        print(f"{'='*60}")
        for s in self.slices:
            st = s.slice_type
            lat = results[st]["latency"]
            thr = results[st]["throughput"]
            pkt = results[st]["packet_loss"]
            print(f"\n  [{st}]")
            print(f"    Avg Latency    : {round(sum(lat)/len(lat), 3)} ms")
            print(f"    Avg Throughput : {round(sum(thr)/len(thr), 2)} Mbps")
            print(f"    Avg Packet Loss: {round(sum(pkt)/len(pkt), 4)} %")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    sim = NetworkSimulator()
    sim.run_normal()
    sim.print_summary(sim.results, label="— NORMAL")
    emergency = sim.run_emergency()
    sim.print_summary(emergency, label="— EMERGENCY")