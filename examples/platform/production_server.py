#!/usr/bin/env python3
"""
Production Server Template

Production-ready server template with best practices:
- Environment-based configuration
- Structured logging
- Error handling
- Health checks
- Graceful shutdown

Run:
    python examples/platform/production_server.py

Environment Variables:
    PLAYSEM_HOST=0.0.0.0
    PLAYSEM_PORT=8090
    PLAYSEM_LOG_LEVEL=INFO
    PLAYSEM_DEBUG=false
"""

import logging
import os
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn
from tools.test_server.app import create_app
from tools.test_server.config import ServerConfig


def setup_logging(log_level: str = "INFO"):
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Add file handler for production:
            # logging.FileHandler("playsem_server.log"),
        ],
    )


def get_config_from_env() -> ServerConfig:
    """Load configuration from environment variables."""
    return ServerConfig(
        host=os.getenv("PLAYSEM_HOST", "127.0.0.1"),
        port=int(os.getenv("PLAYSEM_PORT", "8090")),
        debug=os.getenv("PLAYSEM_DEBUG", "false").lower() == "true",
    )


def handle_shutdown(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    print("\n[!] Shutdown signal received, stopping server...")
    sys.exit(0)


def main():
    """Run production server."""
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Configure logging
    log_level = os.getenv("PLAYSEM_LOG_LEVEL", "INFO")
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = get_config_from_env()
    
    logger.info("=" * 60)
    logger.info("PlaySEM Production Server")
    logger.info("=" * 60)
    logger.info(f"Host: {config.host}")
    logger.info(f"Port: {config.port}")
    logger.info(f"Debug: {config.debug}")
    logger.info(f"Log Level: {log_level}")
    logger.info("=" * 60)
    
    # Create app
    try:
        app = create_app(config)
        logger.info("[OK] Application created successfully")
    except Exception as e:
        logger.error(f"Failed to create application: {e}")
        sys.exit(1)
    
    # Run server
    try:
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level=log_level.lower(),
            access_log=True,
            # Production settings:
            # workers=4,  # For production with multiple workers
            # proxy_headers=True,  # If behind reverse proxy
            # forwarded_allow_ips="*",
        )
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
