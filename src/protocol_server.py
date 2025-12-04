"""
Protocol servers for receiving sensory effect requests.

This module implements various protocol servers (WebSocket, etc.)
that can receive effect requests from external applications and dispatch
them to the effect dispatcher.
"""

import asyncio
import json
import logging
import threading
import html
import struct
from typing import Optional, Callable, Dict, Any

from .effect_dispatcher import EffectDispatcher
from .effect_metadata import EffectMetadata, EffectMetadataParser
from .protocol_servers.mqtt_server import MQTTServer
from .protocol_servers.websocket_server import WebSocketServer
from .protocol_servers.coap_server import CoAPServer
from .protocol_servers.upnp_server import UPnPServer
from .protocol_servers.http_server import HTTPServer
