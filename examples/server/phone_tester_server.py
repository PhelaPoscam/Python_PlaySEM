#!/usr/bin/env python3
"""
Simple HTTP server for phone vibration tester.
Serves the phone_tester.html on a mobile-friendly local server.

Usage:
    python phone_tester_server.py

Then open on your phone:
    http://YOUR_PC_IP:8091
"""

import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Create a socket to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "localhost"


class CustomHandler(SimpleHTTPRequestHandler):
    """Custom handler to serve from the control_panel directory."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve from the examples/web path
        web_dir = Path(__file__).parent.parent / "web"
        super().__init__(*args, directory=str(web_dir), **kwargs)

    def end_headers(self):
        # Add CORS headers for mobile access
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header(
            "Cache-Control", "no-store, no-cache, must-revalidate"
        )
        super().end_headers()

    def log_message(self, format, *args):
        # Custom logging
        print(f"📱 {self.address_string()} - {format % args}")


def main():
    host = "0.0.0.0"  # Listen on all interfaces
    port = 8091

    print("\n" + "=" * 60)
    print("📱 Phone Vibration Tester Server")
    print("=" * 60)

    local_ip = get_local_ip()

    print(f"\n🌐 Server running at:")
    print(f"   Local:   http://localhost:{port}/phone_tester.html")
    print(f"   Network: http://{local_ip}:{port}/phone_tester.html")

    print(f"\n📱 On your phone:")
    print(f"   1. Make sure phone is on same WiFi network")
    print(f"   2. Open browser and go to:")
    print(f"      http://{local_ip}:{port}/phone_tester.html")
    print(f"   3. Tap any button to test vibration!")

    print(f"\n💡 Tips:")
    print(f"   • If IP doesn't work, check your firewall")
    print(f"   • Make sure phone isn't in silent/vibrate-off mode")
    print(f"   • Chrome/Safari work best for Vibration API")

    print(f"\n⚙️  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    try:
        server = HTTPServer((host, port), CustomHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⚠️  Shutting down server...")
        server.shutdown()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
