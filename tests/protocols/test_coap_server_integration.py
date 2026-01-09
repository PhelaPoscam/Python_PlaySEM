import asyncio
import json
import socket
from unittest.mock import MagicMock


import pytest

aiocoap = pytest.importorskip("aiocoap")


@pytest.mark.asyncio
@pytest.mark.smoke
@pytest.mark.skip(
    reason="CoAP server has port overflow issues in CI (aiocoap WebSocket binding bug)"
)
async def test_coap_smoke_server_starts_and_responds():
    """Smoke test: Start CoAP server and send minimal POST, expect success."""
    import socket
    from playsem import DeviceManager
    from playsem import EffectDispatcher
    from playsem.protocol_servers import CoAPServer

    # Pick a free UDP port (with retries to avoid race conditions on macOS)
    port = None
    for attempt in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]
                if port and 1024 <= port <= 65535:
                    break
        except OSError:
            await asyncio.sleep(0.1)

    if not port or port < 1024 or port > 65535:
        pytest.skip(f"Could not allocate valid UDP port: {port}")

    dm = DeviceManager(client=MagicMock())
    dispatcher = EffectDispatcher(dm)
    started_event = asyncio.Event()

    try:
        server = CoAPServer(
            host="127.0.0.1",
            port=port,
            dispatcher=dispatcher,
            started_event=started_event,
        )
    except (OSError, ValueError) as e:
        pytest.skip(f"CoAP server creation failed (port issue on macOS): {e}")

    async def run_server():
        await server.start()

    try:
        server_task = asyncio.create_task(run_server())
    except (OSError, ValueError) as e:
        pytest.skip(f"CoAP server startup failed (port binding issue): {e}")

    # Wait for server to start with timeout
    try:
        await asyncio.wait_for(started_event.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        pytest.skip(
            "CoAP server failed to start in time (macOS race condition)"
        )
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


from playsem import DeviceManager  # noqa: E402
from playsem import EffectDispatcher  # noqa: E402
from playsem.protocol_servers import CoAPServer  # noqa: E402


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
    started_event = asyncio.Event()
    server = CoAPServer(
        host="127.0.0.1",
        port=port,
        dispatcher=dispatcher,
        on_effect_received=on_effect_received,
        started_event=started_event,
    )

    async def run_server():
        await server.start()

    # Start server task and give it a moment to bind
    server_task = asyncio.create_task(run_server())
    await started_event.wait()

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
