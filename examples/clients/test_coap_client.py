#!/usr/bin/env python3
"""
Simple CoAP client to send a test effect to the local CoAP server.

Run server first:
  python examples/coap_server_demo.py

Then run this client:
  python examples/test_coap_client.py
"""

import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def send_test_effect():
    from aiocoap import Context, Message, Code
    from aiocoap.numbers import media_types_rev

    # Build a sample effect
    payload = {
        "effect_type": "light",
        "timestamp": 0,
        "duration": 1500,
        "intensity": 70,
        "location": "front",
        "parameters": {"color": "#33ccff"},
    }

    request = Message(
        code=Code.POST,
        uri="coap://localhost/effects",
        payload=json.dumps(payload).encode("utf-8"),
    )
    request.opt.content_format = media_types_rev.get("application/json", 50)

    ctx = await Context.create_client_context()
    try:
        logging.info("Sending CoAP POST to coap://localhost/effects ...")
        response = await ctx.request(request).response
        logging.info("Response code: %s", response.code)
        if response.payload:
            try:
                data = json.loads(response.payload.decode("utf-8"))
            except json.JSONDecodeError:
                data = response.payload.decode("utf-8", errors="ignore")
            logging.info("Response payload: %s", data)
        else:
            logging.info("No payload in response")
    finally:
        await ctx.shutdown()


if __name__ == "__main__":
    asyncio.run(send_test_effect())
