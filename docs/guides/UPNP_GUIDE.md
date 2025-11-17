# UPnP Server Guide - PythonPlaySEM

This guide explains how to use the UPnP (Universal Plug and Play) server for automatic device discovery on your local network.

## 🎯 What is UPnP/SSDP?

**UPnP** (Universal Plug and Play) is a set of networking protocols that allows devices to discover each other automatically. **SSDP** (Simple Service Discovery Protocol) is the discovery mechanism used by UPnP.

### Key Features:
- **Zero-configuration networking**: Devices announce themselves automatically
- **Multicast discovery**: Clients send M-SEARCH requests; devices respond
- **Service advertisement**: Devices periodically broadcast their presence
- **Compatible with original PlaySEM**: Works with Java PlaySEM clients

---

## 🚀 Quick Start

### 1. Start the UPnP Server

```powershell
# From project root
.\.venv\Scripts\python.exe examples\upnp_server_demo.py
```

The server will:
- Join the SSDP multicast group (239.255.255.250:1900)
- Advertise itself on the network
- Respond to discovery requests
- Send periodic announcements (every 15 minutes)

### 2. Discover Devices

In another terminal:

```powershell
# Discover all PlaySEM devices on network
.\.venv\Scripts\python.exe examples\test_upnp_client.py
```

You should see output like:

```
📡 Discovered 1 UPnP Device(s)
═══════════════════════════════════════════

🔹 Device 1:
   Address:       192.168.1.100
   Location:      http://192.168.1.100:8080/description.xml
   Server:        Python/3.14 UPnP/1.1 PlaySEM/1.0.0
   USN:           uuid:12345678-1234-1234-1234-123456789abc::urn:schemas-upnp-org:device:PlaySEM:1
   Search Target: urn:schemas-upnp-org:device:PlaySEM:1
```

---

## 📝 Using the UPnP Server in Your Code

### Basic Example

```python
import asyncio
from src.protocol_server import UPnPServer
from src.effect_dispatcher import EffectDispatcher
from src.device_manager import DeviceManager

async def main():
    # Create device manager and dispatcher
    device_manager = DeviceManager()
    dispatcher = EffectDispatcher(device_manager)
    
    # Create UPnP server
    server = UPnPServer(
        friendly_name="My PlaySEM Server",
        dispatcher=dispatcher,
        location_url="http://192.168.1.100:8080/description.xml"
    )
    
    # Start advertising
    await server.start()
    print(f"Server UUID: {server.uuid}")
    print("Server is now discoverable!")
    
    # Keep running
    await asyncio.sleep(3600)  # Run for 1 hour
    
    # Cleanup
    await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Configuration

```python
from src.protocol_server import UPnPServer
from src.effect_metadata import EffectMetadata

def on_effect_received(effect: EffectMetadata):
    """Callback when effect is received via UPnP."""
    print(f"Effect: {effect.effect_type}, Intensity: {effect.intensity}")

server = UPnPServer(
    friendly_name="PlaySEM Production Server",
    dispatcher=dispatcher,
    uuid="uuid:custom-uuid-here",  # Optional: provide your own UUID
    location_url="http://10.0.0.5:9000/device.xml",
    manufacturer="Your Company",
    model_name="Custom PlaySEM Device",
    model_version="2.0.0",
    on_effect_received=on_effect_received
)
```

---

## 🔧 How It Works

### SSDP Protocol

1. **Server Startup**:
   - Binds to UDP port 1900
   - Joins multicast group 239.255.255.250
   - Sends NOTIFY alive messages

2. **Discovery (M-SEARCH)**:
   - Client sends M-SEARCH to multicast group
   - Server responds with device information
   - Response includes location URL for device description

3. **Periodic Announcements**:
   - Server sends NOTIFY alive every 15 minutes
   - Keeps devices informed of server presence

4. **Graceful Shutdown**:
   - Server sends NOTIFY byebye messages
   - Tells clients the device is going offline

### Device Description XML

The server provides a UPnP device description XML:

```xml
<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>1</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:PlaySEM:1</deviceType>
    <friendlyName>PlaySEM Python Server</friendlyName>
    <manufacturer>PlaySEM Community</manufacturer>
    <modelName>PlaySEM Python Server</modelName>
    <modelNumber>1.0.0</modelNumber>
    <UDN>uuid:12345678-1234-1234-1234-123456789abc</UDN>
    <serviceList>
      <service>
        <serviceType>urn:schemas-upnp-org:service:PlaySEM:1</serviceType>
        <serviceId>urn:upnp-org:serviceId:PlaySEM</serviceId>
        <SCPDURL>/scpd.xml</SCPDURL>
        <controlURL>/control</controlURL>
        <eventSubURL>/event</eventSubURL>
      </service>
    </serviceList>
  </device>
</root>
```

Access it programmatically:

```python
xml = server.get_device_description_xml()
print(xml)
```

---

## 🌐 Network Configuration

### Firewall Settings

Make sure UDP port 1900 is open for:
- **Inbound**: Receive M-SEARCH requests
- **Outbound**: Send NOTIFY announcements

Windows PowerShell (as Administrator):

```powershell
# Allow UDP 1900 inbound
New-NetFirewallRule -DisplayName "SSDP Discovery" -Direction Inbound -Protocol UDP -LocalPort 1900 -Action Allow

# Allow UDP multicast outbound
New-NetFirewallRule -DisplayName "SSDP Multicast" -Direction Outbound -Protocol UDP -RemoteAddress 239.255.255.250 -Action Allow
```

### Multiple Network Interfaces

If you have multiple network adapters (Wi-Fi + Ethernet), the server will join the multicast group on all interfaces. You can verify with:

```powershell
# Windows: Show multicast group memberships
netsh interface ipv4 show joins
```

---

## 🐛 Troubleshooting

### Server Not Discoverable

**Problem**: Discovery client doesn't find the server

**Solutions**:
1. Check firewall allows UDP port 1900
2. Verify both server and client are on same network/subnet
3. Ensure no VPN is blocking multicast traffic
4. Try disabling Windows Defender Firewall temporarily to test

```powershell
# Check if SSDP port is listening
netstat -an | Select-String "1900"
```

### "Address Already in Use" Error

**Problem**: Port 1900 is already bound by another application

**Solutions**:
1. Close other UPnP services (Windows Media Player Network Sharing, etc.)
2. Kill conflicting process:

```powershell
# Find process using port 1900
Get-NetUDPEndpoint -LocalPort 1900 | Select-Object LocalPort, OwningProcess
# Kill the process
Stop-Process -Id <PID> -Force
```

3. Use a different discovery port (modify `SSDP_PORT` constant)

### Discovery Works, But Description XML Unreachable

**Problem**: M-SEARCH succeeds, but HTTP GET to location URL fails

**Solutions**:
1. Verify the `location_url` is accessible from client
2. Use correct local IP address (not 0.0.0.0 or localhost)
3. Start an HTTP server to serve the description XML:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler

class DescriptionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/description.xml':
            self.send_response(200)
            self.send_header('Content-Type', 'text/xml')
            self.end_headers()
            self.wfile.write(server.get_device_description_xml().encode())

# Run HTTP server on port 8080
http_server = HTTPServer(('0.0.0.0', 8080), DescriptionHandler)
http_server.serve_forever()
```

### Multicast Not Working on Wi-Fi

**Problem**: Discovery works on Ethernet but not Wi-Fi

**Solutions**:
1. Enable IGMP snooping on your Wi-Fi router
2. Check router settings for multicast filtering
3. Try connecting server and client to same AP (avoid mesh/repeaters)

---

## 🔬 Testing

Run the UPnP test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_upnp_server.py -v
```

Expected output:
```
tests/test_upnp_server.py::test_upnp_server_initialization PASSED
tests/test_upnp_server.py::test_upnp_server_service_types PASSED
tests/test_upnp_server.py::test_device_description_xml PASSED
tests/test_upnp_server.py::test_upnp_server_start_stop PASSED
...
===================== 17 passed in 0.39s =====================
```

---

## 📚 Protocol Details

### M-SEARCH Request Format

```http
M-SEARCH * HTTP/1.1
HOST: 239.255.255.250:1900
MAN: "ssdp:discover"
MX: 3
ST: urn:schemas-upnp-org:device:PlaySEM:1
```

### M-SEARCH Response Format

```http
HTTP/1.1 200 OK
CACHE-CONTROL: max-age=1800
EXT:
LOCATION: http://192.168.1.100:8080/description.xml
SERVER: Python/3.14 UPnP/1.1 PlaySEM/1.0.0
ST: urn:schemas-upnp-org:device:PlaySEM:1
USN: uuid:12345678-1234-1234-1234-123456789abc::urn:schemas-upnp-org:device:PlaySEM:1
```

### NOTIFY Alive Format

```http
NOTIFY * HTTP/1.1
HOST: 239.255.255.250:1900
CACHE-CONTROL: max-age=1800
LOCATION: http://192.168.1.100:8080/description.xml
NT: urn:schemas-upnp-org:device:PlaySEM:1
NTS: ssdp:alive
SERVER: Python/3.14 UPnP/1.1 PlaySEM/1.0.0
USN: uuid:12345678-1234-1234-1234-123456789abc::urn:schemas-upnp-org:device:PlaySEM:1
```

### NOTIFY Byebye Format

```http
NOTIFY * HTTP/1.1
HOST: 239.255.255.250:1900
NT: urn:schemas-upnp-org:device:PlaySEM:1
NTS: ssdp:byebye
USN: uuid:12345678-1234-1234-1234-123456789abc::urn:schemas-upnp-org:device:PlaySEM:1
```

---

## 🔗 Integration with Other Servers

Run UPnP alongside other protocol servers:

```python
import asyncio
from src.protocol_server import UPnPServer, WebSocketServer, MQTTServer

async def main():
    device_manager = DeviceManager()
    dispatcher = EffectDispatcher(device_manager)
    
    # Start all servers
    upnp = UPnPServer("PlaySEM Multi-Protocol", dispatcher)
    websocket = WebSocketServer(host="0.0.0.0", port=8765, dispatcher=dispatcher)
    mqtt = MQTTServer("localhost", dispatcher)
    
    await upnp.start()
    await websocket.start()
    mqtt.start()
    
    print("All servers running:")
    print(f"  UPnP:      discoverable on network")
    print(f"  WebSocket: ws://0.0.0.0:8765")
    print(f"  MQTT:      localhost:1883")
    
    await asyncio.sleep(3600)
    
    # Cleanup
    await upnp.stop()
    await websocket.stop()
    mqtt.stop()

asyncio.run(main())
```

---

## 📖 Additional Resources

- [UPnP Device Architecture Specification](http://upnp.org/specs/arch/UPnP-arch-DeviceArchitecture-v1.1.pdf)
- [SSDP Internet Draft](https://tools.ietf.org/html/draft-cai-ssdp-v1-03)
- [Original PlaySEM Paper](https://example.com/playsem-paper)

---

**Last Updated**: November 17, 2025  
**Python Version**: 3.14.0  
**UPnP Version**: 1.1
