import dataclasses
from typing import Optional, Dict, Any
import aiohttp


JSON = Dict[str, Any]


@dataclasses.dataclass
class HTTPConfig:
    host: str = "localhost"
    port: int = 8080
    path: str = "/api/effects"
    use_ssl: bool = False
    api_key: Optional[str] = None

    @property
    def url(self) -> str:
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.host}:{self.port}{self.path}"


class HTTPHandler:
    def __init__(
        self, global_dispatcher=None, config: Optional[HTTPConfig] = None
    ):
        self.dispatcher = global_dispatcher
        self.config = config or HTTPConfig()

    async def send(self, effect: JSON) -> bool:
        """Send effect via HTTP POST using aiohttp."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.url, json=effect, headers=headers, timeout=5
                ) as resp:
                    resp.raise_for_status()
                    return True
        except Exception as e:
            print(f"[HTTPHandler] send failed: {e}")
            return False
