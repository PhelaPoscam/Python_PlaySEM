"""Shared network utilities for PlaySEM tools and examples."""

import socket


def get_local_ip() -> str:
    """Return the preferred local IPv4 address, falling back to loopback."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        if s:
            s.close()
    return str(ip)
