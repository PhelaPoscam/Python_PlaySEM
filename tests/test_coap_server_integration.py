import asyncio
import json
import socket
from unittest.mock import MagicMock


import pytest

aiocoap = pytest.importorskip("aiocoap")


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_coap_smoke_server_starts_and_responds():
    """Smoke test: Start CoAP server and send a minimal POST, expect success response."""
    import socket
    from src.device_manager import DeviceManager
    from src.effect_dispatcher import EffectDispatcher
    from src.protocol_servers import CoAPServer

    # Pick a free UDP port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    dm = DeviceManager(client=MagicMock())
    dispatcher = EffectDispatcher(dm)
    server = CoAPServer(host="127.0.0.1", port=port, dispatcher=dispatcher)

    async def run_server():
        await server.start()

    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(1.0)  # Increased wait time for server to bind
    try:
        from aiocoap import Context, Message, Code, error as aiocoap_error
        from aiocoap.numbers import ContentFormat

        payload = {"effect_type": "light", "intensity": 1}
        uri = f"coap://127.0.0.1:{port}/effects"
        request = Message(
            code=Code.POST,
            uri=uri,
            payload=json.dumps(payload).encode("utf-8"),
        )
        request.opt.content_format = ContentFormat.by_media_type(
            "application/json"
        )
        client = await Context.create_client_context()
        try:
            try:
                response = await client.request(request).response
                assert response.code.is_successful()
            except aiocoap_error.NetworkError as e:
                pytest.fail(f"NetworkError during CoAP smoke test: {e}")
        finally:
            await client.shutdown()
    finally:
        await server.stop()
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task


from src.device_manager import DeviceManager  # noqa: E402
from src.effect_dispatcher import EffectDispatcher  # noqa: E402
from src.protocol_server import CoAPServer  # noqa: E402


@pytest.mark.skip(reason="Network integration test that may hang in CI")
@pytest.mark.asyncio
async def test_coap_server_receives_and_dispatches_effect():
    # Pick a free UDP port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    received = {}

    def on_effect_received(effect):
        received["effect"] = effect

    # Mock MQTT client for DeviceManager to avoid network usage
    mock_client = MagicMock()

    dm = DeviceManager(client=mock_client)
    dispatcher = EffectDispatcher(dm)
    server = CoAPServer(
        host="127.0.0.1",
        port=port,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
    )

    async def run_server():
        await server.start()

    # Start server task and give it a moment to bind
    server_task = asyncio.create_task(run_server())
    await asyncio.sleep(0.2)

    try:
        # Prepare client request
        from aiocoap import Context, Message, Code  # type: ignore
        from aiocoap.numbers import ContentFormat  # type: ignore

        payload = {
            "effect_type": "light",
            "timestamp": 0,
            "duration": 500,
            "intensity": 30,
            "location": "front",
            "parameters": {"color": "#ffcc00"},
        }

        uri = f"coap://127.0.0.1:{port}/effects"
        request = Message(
            code=Code.POST,
            uri=uri,
            payload=json.dumps(payload).encode("utf-8"),
        )
        request.opt.content_format = ContentFormat.by_media_type(
            "application/json"
        )

        client = await Context.create_client_context()
        try:
            response = await client.request(request).response
            # Basic checks on response
            assert response.code.is_successful(), f"CoAP code: {response.code}"
            assert response.payload, "Expected JSON payload"
            data = json.loads(response.payload.decode("utf-8"))
            assert data.get("success") is True
            assert data.get("effect_type") == "light"
        finally:
            await client.shutdown()

        # Callback should have captured effect
        assert "effect" in received
        assert received["effect"].effect_type == "light"
    finally:
        # Stop server
        await server.stop()
        # Cancel server task if still running
        if not server_task.done():
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task
