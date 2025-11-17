# src/main.py

from src.config_loader import load_config
from src.device_manager import DeviceManager
from src.effect_dispatcher import EffectDispatcher


def main():
    config = load_config("config.xml")
    device_manager = DeviceManager(
        broker_address=config.communication_service_broker
    )
    effect_dispatcher = EffectDispatcher(device_manager=device_manager)

    # Example: Dispatch a light effect
    effect_dispatcher.dispatch_effect("light", {"intensity": "high"})


if __name__ == "__main__":
    main()
