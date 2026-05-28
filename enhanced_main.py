"""
Main Application Orchestrator

Coordinates all components:
1. Metrics collector (collects simulation data)
2. Prometheus exporter (serves metrics on HTTP)
3. Network simulator (generates real QoS metrics)
4. Open5GS monitor (tracks service health)
5. Emergency detector (monitors for alert conditions)

Architecture:
- Metrics collector: Thread-safe in-memory storage
- Prometheus exporter: HTTP server on :8000/metrics
- Simulator: Generates metrics continuously
- Monitor: Polls Open5GS services every 10s
- Detector: Checks emergency conditions every step
"""

import threading
import time
import logging
import signal
import sys
from typing import Optional

from metrics_exporter import MetricsCollector, PrometheusExporter, EmergencyDetector
from enhanced_network_simulator import EnhancedNetworkSimulator, SimulationThread
from open5gs_monitor import Open5GSHealthMonitor
from emergency_scenario import EmergencyReallocation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class HospitalSlicingApplication:
    """Main application orchestrator."""
    
    def __init__(self):
        self.running = False
        self.components = {}
        self.threads = []
    
    def initialize(self):
        """Initialize all components."""
        logger.info("="*70)
        logger.info("  5G SMART HOSPITAL NETWORK SLICING - MONITORING SYSTEM")
        logger.info("="*70)
        
        # 1. Create metrics collector
        logger.info("\n[1/5] Initializing metrics collector...")
        self.metrics_collector = MetricsCollector()
        self.components['metrics'] = self.metrics_collector
        logger.info("      ✓ Metrics collector ready")
        
        # 2. Create and start Prometheus exporter
        logger.info("\n[2/5] Starting Prometheus exporter...")
        self.exporter = PrometheusExporter(
            self.metrics_collector,
            port=8000
        )
        self.exporter.start()
        self.components['exporter'] = self.exporter
        logger.info("      ✓ Prometheus exporter listening on http://0.0.0.0:8000/metrics")
        
        # 3. Create emergency detector
        logger.info("\n[3/5] Initializing emergency detector...")
        self.detector = EmergencyDetector(
            self.metrics_collector,
            latency_threshold_ms=5.0,
            packet_loss_threshold_percent=1.0
        )
        self.components['detector'] = self.detector
        logger.info("      ✓ Emergency detector ready (thresholds: latency>5ms, loss>1%)")
        
        # 4. Create network simulator
        logger.info("\n[4/5] Initializing network simulator...")
        self.simulator = EnhancedNetworkSimulator(
            metrics_collector=self.metrics_collector
        )
        self.components['simulator'] = self.simulator
        logger.info("      ✓ Network simulator ready")
        
        # 5. Start Open5GS health monitor
        logger.info("\n[5/5] Starting Open5GS service monitor...")
        self.health_monitor = Open5GSHealthMonitor(
            exporter=self.exporter,
            check_interval=10
        )
        self.health_monitor.start()
        self.threads.append(self.health_monitor)
        self.components['health_monitor'] = self.health_monitor
        logger.info("      ✓ Open5GS monitor started (10s interval)")
        
        # 6. Initialize emergency reallocation engine
        logger.info("\n[6/6] Initializing emergency reallocation engine...")
        self.reallocation_engine = EmergencyReallocation()
        self.components['reallocation'] = self.reallocation_engine
        logger.info("      ✓ Dynamic reallocation engine ready")
        
        logger.info("\n" + "="*70)
        logger.info("  All components initialized successfully!")
        logger.info("="*70)
        logger.info("\n📊 DASHBOARD: streamlit run enhanced_dashboard.py")
        logger.info("📈 PROMETHEUS: curl http://localhost:8000/metrics")
        logger.info("🏥 DEVICE CONFIG: See hospital_devices.py")
        logger.info("🔧 SERVICE CONFIG: See slice_config.py")
        logger.info("\n")
    
    def start_simulation(self, duration_seconds: int = 300):
        """Start continuous network simulation in background."""
        logger.info(f"Starting {duration_seconds}s continuous simulation...")
        
        sim_thread = SimulationThread(
            self.simulator,
            duration_seconds=duration_seconds,
            name="SimulationThread"
        )
        sim_thread.start()
        self.threads.append(sim_thread)
        
        logger.info("✓ Simulation thread started")
        return sim_thread
    
    def start_monitoring_loop(self, check_interval: float = 2.0):
        """Start background monitoring loop."""
        def monitor_loop():
            logger.info(f"Starting monitoring loop (interval: {check_interval}s)...")
            while self.running:
                try:
                    # Check emergency conditions
                    is_emergency = self.detector.check_emergency()
                    
                    # Log current metrics
                    state = self.metrics_collector.get_state()
                    slices = state['slices']
                    
                    for slice_type in slices:
                        lat = self.metrics_collector.get_latest_metric('latency', slice_type)
                        thr = self.metrics_collector.get_latest_metric('throughput', slice_type)
                        loss = self.metrics_collector.get_latest_metric('packet_loss', slice_type)
                        
                        if lat:
                            logger.debug(
                                f"{slice_type}: latency={lat:.2f}ms "
                                f"throughput={thr:.1f}Mbps loss={loss:.4f}%"
                            )
                    
                    time.sleep(check_interval)
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(check_interval)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True, name="MonitoringThread")
        monitor_thread.start()
        self.threads.append(monitor_thread)
        logger.info("✓ Monitoring thread started")
    
    def run(self, duration_seconds: int = 300):
        """Run the complete application."""
        self.running = True
        
        try:
            # Initialize components
            self.initialize()
            
            # Start simulation
            self.start_simulation(duration_seconds=duration_seconds)
            
            # Start monitoring
            self.start_monitoring_loop(check_interval=2.0)
            
            logger.info("\n" + "="*70)
            logger.info("  🚀 HOSPITAL SLICING APPLICATION RUNNING")
            logger.info("="*70)
            logger.info("\nNext steps:")
            logger.info("  1. In another terminal: streamlit run enhanced_dashboard.py")
            logger.info("  2. Open browser: http://localhost:8501")
            logger.info("  3. View live metrics and emergency alerts")
            logger.info("\nPress Ctrl+C to stop...\n")
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("\n\nShutdown signal received...")
            self.shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown all components."""
        logger.info("\n" + "="*70)
        logger.info("  SHUTTING DOWN - CLEANING UP RESOURCES")
        logger.info("="*70)
        
        self.running = False
        
        # Stop simulator
        if 'simulator' in self.components:
            self.components['simulator'].running = False
            logger.info("✓ Simulator stopped")
        
        # Stop health monitor
        if 'health_monitor' in self.components:
            self.components['health_monitor'].stop()
            logger.info("✓ Health monitor stopped")
        
        # Stop exporter
        if 'exporter' in self.components:
            self.components['exporter'].stop()
            logger.info("✓ Prometheus exporter stopped")
        
        # Wait for threads
        logger.info("\nWaiting for threads to terminate...")
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2)
        
        logger.info("\n" + "="*70)
        logger.info("  ✓ ALL COMPONENTS SHUT DOWN SUCCESSFULLY")
        logger.info("="*70 + "\n")
        
        sys.exit(0)


def print_startup_guide():
    """Print comprehensive startup guide."""
    print("\n" + "="*70)
    print("  5G SMART HOSPITAL NETWORK SLICING - STARTUP GUIDE")
    print("="*70)
    print("\nQUICK START:")
    print("  # Terminal 1: Run main application (you are here)")
    print("  $ python3 main.py")
    print("\n  # Terminal 2: Launch Streamlit dashboard")
    print("  $ streamlit run enhanced_dashboard.py")
    print("\n  # Terminal 3: View Prometheus metrics")
    print("  $ watch -n 2 'curl -s http://localhost:8000/metrics | grep hospital'")
    print("\nDASHBOARD:")
    print("  URL: http://localhost:8501")
    print("  Shows:")
    print("    • Real-time network slice QoS metrics")
    print("    • Emergency alert status & history")
    print("    • Open5GS service health")
    print("    • Hospital device status")
    print("\nPROMETHEUS METRICS:")
    print("  URL: http://localhost:8000/metrics")
    print("  Compatible with Grafana, Datadog, Prometheus")
    print("\nARCHITECTURE:")
    print("  • MetricsCollector: Real-time metrics storage")
    print("  • PrometheusExporter: HTTP endpoint for scraping")
    print("  • EnhancedNetworkSimulator: Generates realistic QoS data")
    print("  • Open5GSHealthMonitor: Tracks service status")
    print("  • EmergencyDetector: Monitors URLLC conditions")
    print("\nFILE STRUCTURE:")
    print("  metrics_exporter.py ............ Prometheus integration")
    print("  enhanced_network_simulator.py . Real metrics generation")
    print("  open5gs_monitor.py ............ Service health monitoring")
    print("  enhanced_dashboard.py ......... Streamlit UI")
    print("  main.py ....................... Application orchestrator")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print_startup_guide()
    
    app = HospitalSlicingApplication()
    
    # Run for 5 minutes (300 seconds) - adjust as needed
    app.run(duration_seconds=300)
