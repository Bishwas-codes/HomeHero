"""
Instant Public Tunnel Utility for Viva & Mobile Demonstrations
Uses Port 443 (HTTPS port) to bypass Wi-Fi/ISP firewalls.
"""

import subprocess
import sys

def main():
    print("=" * 65)
    print("🚀 Starting Instant Public HTTPS Tunnel for HomeHero (Port 5000)")
    print("=" * 65)
    print("Connecting via Port 443 (Firewall-safe)...")
    print("Press Ctrl+C to stop sharing.\n")
    
    # Use -p 443 so it is never blocked by Wi-Fi or ISP routers
    cmd = ["ssh", "-p", "443", "-R", "80:localhost:5000", "a.pinggy.io"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nTunnel stopped.")

if __name__ == "__main__":
    main()
