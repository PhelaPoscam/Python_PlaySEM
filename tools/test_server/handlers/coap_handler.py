import dataclasses
from typing import Optional, Dict, Any

try:
    from aiocoap import Context, Message, Code
    from aiocoap.numbers import media_types_rev
except ImportError:
    Context = None
    Message = None
    Code = None
    media_types_rev = None


type JSON = Dict[str, Any]


@dataclasses.dataclass
class CoAPConfig:
    host: str = "localhost"
    port: int = 5683
    path: str = "effects"

    @property
    def uri(self) -> str:
        return f"coap://{self.host}:{self.port}/{self.path}"


class CoAPHandler:
    def __init__(self, global_dispatcher=None, config: Optional[CoAPConfig] = None):
        self.dispatcher = global_dispatcher
        self.config = config or CoAPConfig()

    async def send(self, effect: JSON) -> bool:
        if Context is None:
            print("[CoAPHandler] aiocoap not installed; skipping send")
            return False
        try:
            import json
            payload = json.dumps(effect).encode("utf-8")
            ctx = await Context.create_client_context()
            msg = Message(code=Code.POST, uri=self.config.uri, payload=payload)
            if media_types_rev:
                msg.opt.content_format = media_types_rev.get("application/json", 50)
            await ctx.request(msg).response
            await ctx.shutdown()
            return True
        except Exception as e:
            print(f"[CoAPHandler] send failed: {e}")
            return False
