# PlaySEM Examples

This folder keeps the runnable examples that still add distinct value.

## What to Run

1. `device_registry_demo.py` shows cross-protocol device discovery.
2. `protocols/mqtt_demo.py` starts the embedded MQTT broker and routes effects through the dispatcher and mock driver.
3. `protocols/coap_demo.py` starts the CoAP server and posts sample effects through the dispatcher and mock driver.
4. `protocols/http_demo.py` starts the REST API and submits sample effects through the dispatcher and mock driver.
5. `protocols/upnp_demo.py` serves the UPnP description and control endpoint through the dispatcher and mock driver.
6. `protocols/websocket_demo.py` starts the WebSocket server and exchanges live messages through the dispatcher and mock driver.
7. `protocols/driver_demo.py` shows serial driver usage.

## Platform Server Examples

The platform server example docs were merged into this file. Use the
entrypoint scripts directly:

1. `examples/platform/basic_server.py`
2. `examples/platform/custom_handler_server.py`

## Notes

1. The GUI demo HTML surface was removed from the repository.
2. The platform quickstart content now lives in the core docs guide.
