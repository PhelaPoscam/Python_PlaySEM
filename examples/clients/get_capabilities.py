#!/usr/bin/env python3
"""
Example client: Fetch device capabilities from the HTTP API.

Usage:
    python examples/clients/get_capabilities.py \
        --device-id mock_light_1 \
        [--host 127.0.0.1] \
        [--port 8081] \
        [--api-key YOUR_KEY]

Notes:
- Works with the HTTP server in src/protocol_server.py (started by your main server app)
- Uses only Python stdlib (urllib.request), no extra dependencies required
"""

import argparse
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def main():
    parser = argparse.ArgumentParser(description="Fetch device capabilities")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8081, help="Server port (default: 8081)"
    )
    parser.add_argument(
        "--device-id",
        required=True,
        help="Device ID to query, e.g. mock_light_1",
    )
    parser.add_argument(
        "--api-key", default=None, help="Optional API key for the HTTP server"
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/api/capabilities/{args.device_id}"
    headers = {"User-Agent": "PythonPlaySEM-CapabilitiesClient/1.0"}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=5) as resp:
            data = resp.read()
            try:
                parsed = json.loads(data.decode("utf-8"))
            except Exception:
                print(data.decode("utf-8"))
                return 0
            print(json.dumps(parsed, indent=2))
            return 0
    except HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
        return 2
    except URLError as e:
        print(f"URLError: {e.reason}")
        return 3
    except Exception as e:
        print(f"Error: {e}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
