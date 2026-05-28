#!/usr/bin/env python3
"""Quick test of the metrics exporter HTTP endpoint."""

import sys
import requests
import time

# Test the exporter endpoint
print("Testing Prometheus metrics exporter...")
url = "http://localhost:8000/metrics"

try:
    print(f"Requesting: {url}")
    response = requests.get(url, timeout=3)
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Content length: {len(response.text)}")
    print(f"\nFirst 500 chars:\n{response.text[:500]}")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out - server not responding")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Connection failed - {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

print("\n✓ Metrics exporter working!")
