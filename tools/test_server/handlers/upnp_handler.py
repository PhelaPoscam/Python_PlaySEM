import dataclasses
import textwrap
from typing import Optional, Dict, Any

import requests


type JSON = Dict[str, Any]


@dataclasses.dataclass
class UPnPConfig:
    device_name: str = "PlaySEM Device"
    device_type: str = "urn:schemas-upnp-org:device:PlaySEM:1"
    control_url: Optional[str] = None


class UPnPHandler:
    def __init__(self, global_dispatcher=None, config: Optional[UPnPConfig] = None):
        self.dispatcher = global_dispatcher
        self.config = config or UPnPConfig()

    async def send(self, effect: JSON) -> bool:
        if not self.config.control_url:
            print("[UPnPHandler] control_url not set; skipping send")
            return False

        effect_type = str(effect.get("effect_type") or effect.get("type") or "unknown")
        duration = str(effect.get("duration", 1000))
        intensity = str(effect.get("intensity", 50))
        location = str(effect.get("location", ""))
        parameters = effect.get("parameters", {})

        envelope = textwrap.dedent(
            f"""
            <?xml version="1.0"?>
            <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
              <s:Body>
                <u:SendEffect xmlns:u="urn:schemas-playsem:service:Effects:1">
                  <EffectType>{effect_type}</EffectType>
                  <Duration>{duration}</Duration>
                  <Intensity>{intensity}</Intensity>
                  <Location>{location}</Location>
                  <Parameters>{requests.utils.requote_uri(str(parameters))}</Parameters>
                </u:SendEffect>
              </s:Body>
            </s:Envelope>
            """
        ).strip()

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"urn:schemas-playsem:service:Effects:1#SendEffect"',
        }

        try:
            resp = requests.post(self.config.control_url, data=envelope.encode("utf-8"), headers=headers, timeout=5)
            resp.raise_for_status()
            return True
        except Exception as e:  # pragma: no cover - network/UPnP failures are runtime
            print(f"[UPnPHandler] send failed: {e}")
            return False
