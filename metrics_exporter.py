"""
Prometheus Metrics Exporter - Simplified Non-Blocking Version

Provides thread-safe metrics export without blocking HTTP responses.
"""

import threading
import time
from datetime import datetime
from typing import Dict, Optional
from prometheus_client import Counter, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Thread-safe metrics collection."""
    
    def __init__(self):
        self.lock = threading.RLock()
        self.metrics = {'latency': {}, 'throughput': {}, 'packet_loss': {}}
        self.emergency_count = 0
        self.emergency_active = False
        self.last_metric_timestamp = None
        
    def record_metrics(self, slice_type: str, latency_ms: float, throughput_mbps: float, packet_loss_percent: float):
        """Record metrics for a slice."""
        with self.lock:
            if slice_type not in self.metrics['latency']:
                self.metrics['latency'][slice_type] = []
                self.metrics['throughput'][slice_type] = []
                self.metrics['packet_loss'][slice_type] = []
            
            if len(self.metrics['latency'][slice_type]) >= 100:
                self.metrics['latency'][slice_type].pop(0)
                self.metrics['throughput'][slice_type].pop(0)
                self.metrics['packet_loss'][slice_type].pop(0)
            
            self.metrics['latency'][slice_type].append(latency_ms)
            self.metrics['throughput'][slice_type].append(throughput_mbps)
            self.metrics['packet_loss'][slice_type].append(packet_loss_percent)
            self.last_metric_timestamp = datetime.now()
    
    def set_emergency(self, active: bool):
        """Set emergency state."""
        with self.lock:
            self.emergency_active = active
            if active:
                self.emergency_count += 1
    
    def get_latest_metric(self, metric_type: str, slice_type: str) -> Optional[float]:
        """Get latest metric."""
        with self.lock:
            values = self.metrics[metric_type].get(slice_type, [])
            return values[-1] if values else None
    
    def get_state(self) -> Dict:
        """Get state snapshot."""
        with self.lock:
            return {
                'emergency_active': self.emergency_active,
                'emergency_count': self.emergency_count,
                'last_update': self.last_metric_timestamp,
                'slices': list(self.metrics['latency'].keys())
            }


class PrometheusExporter:
    """Non-blocking Prometheus metrics exporter."""
    
    def __init__(self, metrics_collector: MetricsCollector, port: int = 8000):
        self.collector = metrics_collector
        self.port = port
        self.registry = CollectorRegistry()
        self.server = None
        self.server_thread = None
        self._cached_metrics = b"# No metrics yet\n"
        self._metrics_lock = threading.Lock()
        
        self._setup_metrics()
        self._start_updater_thread()
    
    def _setup_metrics(self):
        """Initialize Prometheus metrics."""
        self.latency_gauge = Gauge('hospital_slice_latency_ms', 'Latency in ms', ['slice'], registry=self.registry)
        self.throughput_gauge = Gauge('hospital_slice_throughput_mbps', 'Throughput in Mbps', ['slice'], registry=self.registry)
        self.packet_loss_gauge = Gauge('hospital_slice_packet_loss_percent', 'Packet loss %', ['slice'], registry=self.registry)
        self.emergency_gauge = Gauge('hospital_emergency_detected', 'Emergency status', registry=self.registry)
        self.emergency_counter = Counter('hospital_emergency_alert_total', 'Emergency count', registry=self.registry)
        self.service_status_gauge = Gauge('hospital_open5gs_service_up', 'Service up', ['service'], registry=self.registry)
        self.device_health_gauge = Gauge('hospital_device_active', 'Device active', ['device_id', 'device_type', 'slice'], registry=self.registry)
    
    def _start_updater_thread(self):
        """Start background thread to update metrics cache."""
        def update_loop():
            while True:
                try:
                    state = self.collector.get_state()
                    
                    for slice_type in state['slices']:
                        lat = self.collector.get_latest_metric('latency', slice_type)
                        thr = self.collector.get_latest_metric('throughput', slice_type)
                        pkt = self.collector.get_latest_metric('packet_loss', slice_type)
                        
                        if lat is not None:
                            self.latency_gauge.labels(slice=slice_type).set(lat)
                        if thr is not None:
                            self.throughput_gauge.labels(slice=slice_type).set(thr)
                        if pkt is not None:
                            self.packet_loss_gauge.labels(slice=slice_type).set(pkt)
                    
                    emergency_state = 1 if state['emergency_active'] else 0
                    self.emergency_gauge.set(emergency_state)
                    
                    with self._metrics_lock:
                        self._cached_metrics = generate_latest(self.registry)
                    
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Metrics updater error: {e}")
                    time.sleep(0.5)
        
        thread = threading.Thread(target=update_loop, daemon=True, name="MetricsUpdater")
        thread.start()
    
    def set_service_status(self, service_name: str, is_active: bool):
        """Update service status."""
        status = 1 if is_active else 0
        self.service_status_gauge.labels(service=service_name).set(status)
    
    def set_device_health(self, device_id: str, device_type: str, slice_type: str, is_active: bool):
        """Update device health."""
        status = 1 if is_active else 0
        self.device_health_gauge.labels(device_id=device_id, device_type=device_type, slice=slice_type).set(status)
    
    def get_metrics(self) -> bytes:
        """Get cached metrics (non-blocking)."""
        with self._metrics_lock:
            return self._cached_metrics
    
    def start(self):
        """Start HTTP server."""
        def run_server():
            try:
                handler = self._get_handler()
                self.server = HTTPServer(('0.0.0.0', self.port), handler)
                logger.info(f"Prometheus exporter started on http://0.0.0.0:{self.port}/metrics")
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"HTTP server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True, name="HTTPServer")
        self.server_thread.start()
        time.sleep(0.2)
    
    def stop(self):
        """Stop HTTP server."""
        if self.server:
            self.server.shutdown()
    
    def _get_handler(self):
        """Create HTTP request handler."""
        exporter = self
        
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    if self.path == '/metrics':
                        metrics_data = exporter.get_metrics()
                        self.send_response(200)
                        self.send_header('Content-Type', CONTENT_TYPE_LATEST)
                        self.send_header('Content-Length', str(len(metrics_data)))
                        self.end_headers()
                        self.wfile.write(metrics_data)
                    elif self.path == '/health':
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(b'{"status":"ok"}')
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    logger.error(f"Handler error: {e}")
            
            def log_message(self, format, *args):
                pass
        
        return MetricsHandler


class EmergencyDetector:
    """Emergency condition detector."""
    
    def __init__(self, metrics_collector: MetricsCollector, latency_threshold_ms: float = 5.0, packet_loss_threshold_percent: float = 1.0):
        self.collector = metrics_collector
        self.latency_threshold = latency_threshold_ms
        self.packet_loss_threshold = packet_loss_threshold_percent
        self.emergency_active = False
    
    def check_emergency(self) -> bool:
        """Check for emergency conditions."""
        urllc_latency = self.collector.get_latest_metric('latency', 'URLLC')
        urllc_packet_loss = self.collector.get_latest_metric('packet_loss', 'URLLC')
        
        emergency = False
        if urllc_latency and urllc_latency > self.latency_threshold:
            emergency = True
        if urllc_packet_loss and urllc_packet_loss > self.packet_loss_threshold:
            emergency = True
        
        if emergency and not self.emergency_active:
            self.collector.set_emergency(True)
            self.emergency_active = True
            logger.critical("🚨 EMERGENCY ALERT ACTIVATED")
        elif not emergency and self.emergency_active:
            self.collector.set_emergency(False)
            self.emergency_active = False
            logger.info("✓ Emergency resolved")
        
        return emergency
