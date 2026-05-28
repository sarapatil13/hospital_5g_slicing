#!/usr/bin/env python3
"""Minimal test HTTP server for Prometheus metrics."""

import socket
import threading
import time

def create_minimal_server():
    """Create a minimal HTTP server that responds to /metrics."""
    
    def handle_client(client_socket, addr):
        try:
            request = client_socket.recv(1024).decode()
            if '/metrics' in request:
                response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 10\r\n\r\nhello test"
                client_socket.send(response)
            client_socket.close()
        except:
            pass
    
    def run_server():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 8001))
        server.listen(1)
        print("Test server listening on port 8001")
        
        for _ in range(5):  # Accept 5 requests then stop
            try:
                client, addr = server.accept()
                threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()
            except:
                break
        server.close()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    thread = create_minimal_server()
    time.sleep(1)
    
    # Test the server
    import requests
    try:
        response = requests.get("http://localhost:8001/metrics", timeout=3)
        print(f"✓ Server working! Response: {response.text}")
    except Exception as e:
        print(f"✗ Server error: {e}")
