"""
Enhanced Network Simulator with Real-Time Metrics Emission

Extends the original NetworkSimulator to emit metrics to MetricsCollector
for real-time monitoring and Prometheus export.
"""

import random
import time
import threading
import logging
from typing import Optional, Callable
from slice_config import URLLC_SLICE, EMBB_SLICE, MMTC_SLICE, ALL_SLICES
from hospital_devices import ALL_DEVICES

logger = logging.getLogger(__name__)
random.seed(42)


class EnhancedNetworkSimulator:
    """
    Enhanced network simulator that emits real metrics.
    
    Emit metrics to a MetricsCollector for real-time monitoring.
    Supports continuous simulation mode for live dashboards.
    """
    
    def __init__(self, metrics_collector=None):
        self.slices = ALL_SLICES
        self.devices = ALL_DEVICES
        self.metrics_collector = metrics_collector
        self.time_steps = 20
        self.running = False
        self.results = {s.slice_type: {
            "latency": [], "throughput": [], "packet_loss": []
        } for s in self.slices}
    
    def simulate_latency(self, slice_obj, overloaded=False):
        """Simulate latency with optional overload condition."""
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
        """Simulate throughput with optional overload condition."""
        base = slice_obj.bandwidth_mbps
        drop = random.uniform(0.3, 0.5) if overloaded else random.uniform(0.0, 0.1)
        return round(base * (1 - drop), 2)
    
    def simulate_packet_loss(self, slice_obj, overloaded=False):
        """Simulate packet loss percentage with optional overload condition."""
        if slice_obj.slice_type == "URLLC":
            base = random.uniform(0.0001, 0.001)
            spike = random.uniform(0.5, 1.5) if overloaded else 0
        elif slice_obj.slice_type == "eMBB":
            base = random.uniform(0.01, 0.1)
            spike = random.uniform(2, 5) if overloaded else 0
        else:  # mMTC
            base = random.uniform(0.1, 0.5)
            spike = random.uniform(5, 10) if overloaded else 0
        return round(base + spike, 4)
    
    def _emit_metrics(self, slice_type: str, latency_ms: float,
                      throughput_mbps: float, packet_loss_percent: float):
        """Emit metrics to collector if available."""
        if self.metrics_collector:
            self.metrics_collector.record_metrics(
                slice_type, latency_ms, throughput_mbps, packet_loss_percent
            )
    
    def run_normal(self, emit_metrics: bool = True):
        """Run normal traffic simulation with optional metric emission."""
        logger.info(">>> Running NORMAL traffic simulation...")
        for t in range(self.time_steps):
            for s in self.slices:
                lat = self.simulate_latency(s)
                thr = self.simulate_throughput(s)
                pkt = self.simulate_packet_loss(s)
                
                self.results[s.slice_type]["latency"].append(lat)
                self.results[s.slice_type]["throughput"].append(thr)
                self.results[s.slice_type]["packet_loss"].append(pkt)
                
                if emit_metrics:
                    self._emit_metrics(s.slice_type, lat, thr, pkt)
        
        logger.info("    Normal simulation complete.")
    
    def run_emergency(self, emit_metrics: bool = True):
        """Run emergency scenario with optional metric emission."""
        logger.info(">>> Injecting EMERGENCY traffic spike...")
        emergency_results = {s.slice_type: {
            "latency": [], "throughput": [], "packet_loss": []
        } for s in self.slices}
        
        for t in range(self.time_steps):
            # Emergency = overload on eMBB and mMTC
            # URLLC stays protected by dynamic reallocation
            for s in self.slices:
                overloaded = s.slice_type in ["eMBB", "mMTC"]
                lat = self.simulate_latency(s, overloaded)
                thr = self.simulate_throughput(s, overloaded)
                pkt = self.simulate_packet_loss(s, overloaded)
                
                emergency_results[s.slice_type]["latency"].append(lat)
                emergency_results[s.slice_type]["throughput"].append(thr)
                emergency_results[s.slice_type]["packet_loss"].append(pkt)
                
                if emit_metrics:
                    self._emit_metrics(s.slice_type, lat, thr, pkt)
        
        logger.info("    Emergency simulation complete.")
        return emergency_results
    
    def run_continuous(self, duration_seconds: int = 60, step_interval: float = 1.0,
                       normal_steps: int = 5, emergency_steps: int = 5):
        """
        Run continuous simulation for live dashboard display.
        
        Alternates between normal and emergency scenarios to simulate realistic
        network behavior.
        
        Args:
            duration_seconds: Total simulation duration
            step_interval: Delay between simulation steps
            normal_steps: Number of steps in normal phase
            emergency_steps: Number of steps in emergency phase
        """
        self.running = True
        logger.info(f">>> Starting continuous simulation ({duration_seconds}s)...")
        
        start_time = time.time()
        phase = "normal"
        phase_steps = 0
        
        while self.running and (time.time() - start_time) < duration_seconds:
            for s in self.slices:
                overloaded = (phase == "emergency" and s.slice_type in ["eMBB", "mMTC"])
                
                lat = self.simulate_latency(s, overloaded)
                thr = self.simulate_throughput(s, overloaded)
                pkt = self.simulate_packet_loss(s, overloaded)
                
                self._emit_metrics(s.slice_type, lat, thr, pkt)
            
            phase_steps += 1
            
            # Switch phases
            if phase == "normal" and phase_steps >= normal_steps:
                phase = "emergency"
                phase_steps = 0
                logger.warning("⚠ Switching to EMERGENCY phase")
            elif phase == "emergency" and phase_steps >= emergency_steps:
                phase = "normal"
                phase_steps = 0
                logger.info("✓ Switching to NORMAL phase")
            
            time.sleep(step_interval)
        
        self.running = False
        logger.info("Continuous simulation stopped.")
    
    def print_summary(self, results, label=""):
        """Print simulation results summary."""
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


class SimulationThread(threading.Thread):
    """Background thread for continuous network simulation."""
    
    def __init__(self, simulator, duration_seconds: int = 60, name: str = "Simulation"):
        super().__init__(daemon=True, name=name)
        self.simulator = simulator
        self.duration = duration_seconds
    
    def run(self):
        """Run continuous simulation."""
        self.simulator.run_continuous(
            duration_seconds=self.duration,
            step_interval=1.0,
            normal_steps=5,
            emergency_steps=5
        )
    
    def stop(self):
        """Stop the simulation."""
        self.simulator.running = False


if __name__ == "__main__":
    # Demo: Run enhanced simulator
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    sim = EnhancedNetworkSimulator()
    sim.run_normal()
    sim.print_summary(sim.results, label="— NORMAL")
    
    emergency = sim.run_emergency()
    sim.print_summary(emergency, label="— EMERGENCY")
