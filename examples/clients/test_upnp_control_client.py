import asyncio
import aiohttp
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.aiohttp import AiohttpRequester
from async_upnp_client.ssdp import SsdpListener

async def main():
    """
    Discover a PlaySEM UPnP server, send an effect command, and print the response.
    """
    print("Discovering PlaySEM UPnP servers for 10 seconds...")

    playsem_device_info = None

    async def on_device_discovered(device):
        nonlocal playsem_device_info
        if "PlaySEM" in device.friendly_name and not playsem_device_info:
            playsem_device_info = device
            print(f"Found PlaySEM server: {device.friendly_name} at {device.location}")

    listener = SsdpListener(on_device_discovered)
    await listener.async_start()
    await asyncio.sleep(10)
    await listener.async_stop()

    if not playsem_device_info:
        print("No PlaySEM UPnP server found.")
        return

    # Create the device
    requester = AiohttpRequester()
    factory = UpnpFactory(requester)
    try:
        playsem_device = await factory.async_create_device(playsem_device_info.location)
    except Exception as e:
        print(f"Error creating device: {e}")
        return

    print(f"Successfully created device: {playsem_device.name}")

    # Get the PlaySEM service
    playsem_service = playsem_device.service("urn:schemas-upnp-org:service:PlaySEM:1")
    if not playsem_service:
        print("Could not find PlaySEM service on the device.")
        return

    print(f"  - Control URL: {playsem_service.control_url}")

    # Construct the SOAP request
    soap_body = f"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:SendEffect xmlns:u="{playsem_service.service_type}">
            <EffectType>vibration</EffectType>
            <Duration>1000</Duration>
            <Intensity>80</Intensity>
            <Location>everywhere</Location>
            <Parameters>{{}}</Parameters>
        </u:SendEffect>
    </s:Body>
</s:Envelope>
"""

    headers = {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SOAPAction": f'"{playsem_service.service_type}#SendEffect"',
    }

    # Send the request
    print("\nSending 'vibration' effect via UPnP...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(playsem_service.control_url, headers=headers, data=soap_body) as response:
                response_text = await response.text()
                print(f"Response status: {response.status}")
                print(f"Response body:\n{response_text}")

                if response.status == 200:
                    print("\nEffect sent successfully!")
                else:
                    print("\nFailed to send effect.")

        except aiohttp.ClientError as e:
            print(f"Error sending request: {e}")


if __name__ == "__main__":
    asyncio.run(main())