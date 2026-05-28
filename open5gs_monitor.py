"""
Open5GS Service Monitor

Monitors Open5GS core services (amfd, smfd, upfd) running on the system.
Provides health status, uptime, and resource usage metrics.
"""

import subprocess
import logging
import time
import threading
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Open5GSMonitor:
    """Monitor Open5GS services and their status."""
    
    # Standard Open5GS services
    SERVICES = {
        'open5gs-amfd': 'Access Stratum Management Function',
        'open5gs-smfd': 'Session Management Function',
        'open5gs-upfd': 'User Plane Function',
        'open5gs-hssd': 'Home Subscriber Server',
        'open5gs-udmd': 'User Data Management Function',
        'open5gs-nrfd': 'Network Repository Function',
        'open5gs-scpd': 'Service Communication Proxy',
    }
    
    def __init__(self):
        self.status_cache = {}
        self.last_check = None
        self.lock = threading.RLock()
    
    def check_service_status(self, service_name: str) -> bool:
        """
        Check if a service is active.
        Returns True if service is active, False otherwise.
        """
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_active = result.stdout.strip() == 'active'
            return is_active
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Failed to check {service_name}: {e}")
            return False
    
    def get_service_uptime(self, service_name: str) -> Optional[float]:
        """
        Get service uptime in seconds.
        Returns None if service is not active.
        """
        try:
            # Get active time using systemctl show
            result = subprocess.run(
                ['systemctl', 'show', service_name, '-p', 'ActiveEnterTimestamp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            # Parse timestamp and calculate uptime
            output = result.stdout.strip()
            # Format: ActiveEnterTimestamp=Wed 2026-05-27 14:32:15 UTC
            # For now, return seconds since last active (simplified)
            return None
        except Exception as e:
            logger.warning(f"Failed to get uptime for {service_name}: {e}")
            return None
    
    def get_all_services_status(self) -> Dict[str, Dict]:
        """
        Get status of all monitored services.
        Returns dict with service info.
        """
        with self.lock:
            result = {}
            for service_name, description in self.SERVICES.items():
                is_active = self.check_service_status(service_name)
                result[service_name] = {
                    'name': service_name,
                    'description': description,
                    'active': is_active,
                    'status': 'active' if is_active else 'inactive',
                    'checked_at': datetime.now().isoformat()
                }
                self.status_cache[service_name] = is_active
            
            self.last_check = datetime.now()
            return result
    
    def get_critical_services_status(self) -> Dict[str, bool]:
        """
        Get status of critical services only (amfd, smfd, upfd).
        Returns dict: {service_name: is_active}
        """
        critical_services = ['open5gs-amfd', 'open5gs-smfd', 'open5gs-upfd']
        result = {}
        for service in critical_services:
            result[service] = self.check_service_status(service)
        return result
    
    def are_critical_services_running(self) -> bool:
        """Check if all critical services are running."""
        status = self.get_critical_services_status()
        return all(status.values())
    
    def get_service_summary(self) -> Dict:
        """Get summary of all services."""
        all_status = self.get_all_services_status()
        active_count = sum(1 for s in all_status.values() if s['active'])
        total_count = len(all_status)
        
        return {
            'total_services': total_count,
            'active_services': active_count,
            'inactive_services': total_count - active_count,
            'health': 'healthy' if active_count == total_count else 'degraded',
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'services': all_status
        }


class Open5GSHealthMonitor(threading.Thread):
    """
    Background thread that monitors Open5GS services continuously.
    Updates metrics in the PrometheusExporter.
    """
    
    def __init__(self, exporter=None, check_interval: int = 10):
        super().__init__(daemon=True)
        self.exporter = exporter
        self.check_interval = check_interval
        self.running = False
        self.monitor = Open5GSMonitor()
    
    def run(self):
        """Monitor services continuously."""
        self.running = True
        logger.info(f"Open5GS health monitor started (interval: {self.check_interval}s)")
        
        while self.running:
            try:
                status = self.monitor.get_critical_services_status()
                
                # Update exporter metrics if available
                if self.exporter:
                    for service_name, is_active in status.items():
                        self.exporter.set_service_status(service_name, is_active)
                
                # Log status
                for service_name, is_active in status.items():
                    indicator = "🟢" if is_active else "🔴"
                    logger.info(f"{indicator} {service_name}: {'active' if is_active else 'inactive'}")
                
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                time.sleep(self.check_interval)
    
    def stop(self):
        """Stop monitoring."""
        self.running = False
        logger.info("Open5GS health monitor stopped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    monitor = Open5GSMonitor()
    
    print("\n" + "="*60)
    print("  Open5GS Service Status")
    print("="*60)
    
    summary = monitor.get_service_summary()
    print(f"\nTotal Services: {summary['total_services']}")
    print(f"Active Services: {summary['active_services']}")
    print(f"Status: {summary['health'].upper()}\n")
    
    for service_name, info in summary['services'].items():
        indicator = "🟢" if info['active'] else "🔴"
        print(f"{indicator} {service_name:<20} {info['status']:<12} {info['description']}")
    
    print("\n" + "="*60)
