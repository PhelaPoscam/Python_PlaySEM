# src/device_manager.py
import asyncio
import inspect
import threading
import logging
from typing import Dict, List, Any, Optional

from playsem.config.loader import ConfigLoader
from playsem.drivers.base_driver import BaseDriver

logger = logging.getLogger(__name__)


class DeviceManager:
    """
    Manages all active device drivers and routes commands to the correct
    driver based on device ID.
    """

    def __init__(
        self,
        drivers: Optional[List[BaseDriver]] = None,
        config_loader: Optional[ConfigLoader] = None,
        client: Optional[Any] = None,
        connectivity_driver: Optional[Any] = None,
        async_bridge_timeout: Optional[float] = 5.0,
    ):
        """
        Initializes the DeviceManager.

        Args:
            drivers: A list of initialized driver instances (e.g., SerialDriver).
            config_loader: An initialized ConfigLoader instance.
            client: Legacy MQTT client for backwards compatibility in tests.
            connectivity_driver: Optional connectivity driver for single driver mode.
            async_bridge_timeout: Timeout in seconds for blocking async
                bridge calls. Set to None to disable timeout.
        """
        # Legacy mode: if a raw client is provided, use a simple publish-based driver
        self._legacy_mode = client is not None
        self._single_driver_mode = connectivity_driver is not None
        self.async_bridge_timeout = async_bridge_timeout
        self.device_to_driver: Dict[str, BaseDriver] = {}

        if self._legacy_mode:
            logger.info("Initializing DeviceManager in legacy client mode.")
            self.driver = _LegacyPublishDriver(client)
        elif self._single_driver_mode:
            logger.info(
                "Initializing DeviceManager with single connectivity driver."
            )
            self.connectivity_driver = connectivity_driver
        else:
            drivers = drivers or []
            logger.info(
                f"Initializing DeviceManager with {len(drivers)} drivers."
            )
            self.drivers_by_interface: Dict[str, BaseDriver] = {
                driver.get_interface_name(): driver for driver in drivers
            }
            if config_loader is None:
                raise ValueError(
                    "config_loader is required when not using legacy client mode"
                )
            self.config_loader = config_loader

            self._map_devices_to_drivers()
            self.connect_all()

    def _map_devices_to_drivers(self):
        """
        Builds a mapping from each deviceId to its corresponding driver instance
        using the loaded configuration.
        """
        devices_config = self.config_loader.load_devices_config()
        devices = devices_config.get("devices", [])

        logger.info(f"Mapping {len(devices)} devices to their drivers.")

        for device in devices:
            device_id = device.get("deviceId")
            interface_name = device.get("connectivityInterface")

            if not device_id or not interface_name:
                logger.warning(
                    f"Skipping device with missing 'deviceId' or 'connectivityInterface': {device}"
                )
                continue

            driver = self.drivers_by_interface.get(interface_name)
            if driver:
                self.device_to_driver[device_id] = driver
                logger.info(
                    f"Device '{device_id}' mapped to driver for interface '{interface_name}'."
                )
            else:
                logger.warning(
                    f"No driver found for interface '{interface_name}' needed by device '{device_id}'. "
                    f"This device will not be controllable."
                )

        if not self.device_to_driver:
            logger.warning("No devices were successfully mapped to drivers.")

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Sends a command to a specific device. The manager routes it to the
        correct driver.

        Args:
            device_id: The ID of the target device.
            command: The command to send (e.g., "set_power").
            params: A dictionary of parameters for the command.

        Returns:
            True if the command was sent successfully, False otherwise.
        """
        if params is None:
            params = {}

        # Legacy publish mode
        if self._legacy_mode:
            try:
                payload = str({"command": command, "params": params})
                self.driver.client.publish(device_id, payload)
                return True
            except Exception as e:
                logger.error(f"Legacy publish failed: {e}")
                return False

        # Single connectivity driver mode
        if self._single_driver_mode and self.connectivity_driver is not None:
            try:
                result = self.connectivity_driver.send_command(
                    device_id, command, params
                )
                return bool(self._resolve_maybe_async(result))
            except Exception as e:
                logger.error(f"Single-driver send failed: {e}")
                return False

        driver = self.device_to_driver.get(device_id)
        if not driver:
            logger.error(
                f"No driver found for device_id '{device_id}'. Cannot send command."
            )
            return False

        logger.info(
            f"Sending command '{command}' to device '{device_id}' via {driver.get_driver_type()} driver."
        )
        try:
            result = driver.send_command(device_id, command, params)
            return bool(self._resolve_maybe_async(result))
        except Exception as e:
            logger.error(
                f"Failed to send command to device '{device_id}': {e}"
            )
            return False

    def connect_all(self):
        """Connects all managed drivers."""
        logger.info("Connecting all drivers...")
        for interface_name, driver in self.drivers_by_interface.items():
            try:
                if not self._driver_is_connected(driver):
                    result = driver.connect()
                    self._resolve_maybe_async(result)
                    logger.info(
                        f"Driver for interface '{interface_name}' connected."
                    )
            except Exception as e:
                logger.error(
                    f"Failed to connect driver for interface '{interface_name}': {e}"
                )

    def disconnect_all(self):
        """Disconnects all managed drivers."""
        logger.info("Disconnecting all drivers...")
        for interface_name, driver in self.drivers_by_interface.items():
            try:
                if self._driver_is_connected(driver):
                    result = driver.disconnect()
                    self._resolve_maybe_async(result)
                    logger.info(
                        f"Driver for interface '{interface_name}' disconnected."
                    )
            except Exception as e:
                logger.error(
                    f"Failed to disconnect driver for interface '{interface_name}': {e}"
                )

    # --- Backwards compatibility helpers ---
    def connect(self):
        """Connect single connectivity driver (legacy path)."""
        if self._single_driver_mode and self.connectivity_driver is not None:
            try:
                if hasattr(self.connectivity_driver, "connect"):
                    result = self.connectivity_driver.connect()
                    self._resolve_maybe_async(result)
            except Exception:
                pass

    def disconnect(self):
        """Disconnect single connectivity driver (legacy path)."""
        if self._single_driver_mode and self.connectivity_driver is not None:
            try:
                if hasattr(self.connectivity_driver, "disconnect"):
                    result = self.connectivity_driver.disconnect()
                    self._resolve_maybe_async(result)
            except Exception:
                pass

    def _resolve_maybe_async(self, result: Any) -> Any:
        """Resolve sync/async driver calls in sync DeviceManager paths."""
        if not inspect.isawaitable(result):
            return result

        return self._run_awaitable_blocking(result)

    def _driver_is_connected(self, driver: Any) -> bool:
        """Resolve sync/async is_connected checks to bool."""
        status = driver.is_connected()
        return bool(self._resolve_maybe_async(status))

    def _run_awaitable_blocking(self, awaitable: Any) -> Any:
        """Run awaitable in current thread or isolated loop thread."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(awaitable)

        holder: Dict[str, Any] = {}

        def _runner():
            try:
                holder["result"] = asyncio.run(awaitable)
            except Exception as exc:
                holder["error"] = exc

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

        if self.async_bridge_timeout is None:
            thread.join()
        else:
            thread.join(timeout=self.async_bridge_timeout)

        if thread.is_alive():
            raise TimeoutError(
                "Async bridge execution timed out after "
                f"{self.async_bridge_timeout} second(s)"
            )

        if "error" in holder:
            raise holder["error"]
        return holder.get("result")

    def get_all_driver_info(self) -> Dict[str, Any]:
        """Gets status information from all managed drivers."""
        info: Dict[str, Any] = {}

        if self._legacy_mode:
            info["legacy"] = {"connected": True}
        elif self._single_driver_mode and self.connectivity_driver is not None:
            if hasattr(self.connectivity_driver, "get_driver_info"):
                info["single"] = self.connectivity_driver.get_driver_info()
            else:
                info["single"] = {
                    "type": type(self.connectivity_driver).__name__,
                }
        else:
            info.update(
                {
                    interface_name: driver.get_driver_info()
                    for interface_name, driver in self.drivers_by_interface.items()
                }
            )

        info["_manager"] = {"async_bridge_timeout": self.async_bridge_timeout}
        return info

    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Gets configuration information for a specific device.
        """
        devices_config = self.config_loader.load_devices_config()
        for device in devices_config.get("devices", []):
            if not isinstance(device, dict):
                continue
            if device.get("deviceId") == device_id:
                return device
        return None

    def get_driver_for_device(self, device_id: str) -> Optional[Any]:
        """Return the concrete driver instance for a device id."""
        if self._legacy_mode:
            return None

        if self._single_driver_mode and self.connectivity_driver is not None:
            return self.connectivity_driver

        return self.device_to_driver.get(device_id)

    def get_device_capabilities(
        self, device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Query capabilities for a device from its mapped driver."""
        driver = self.get_driver_for_device(device_id)
        if driver is None or not hasattr(driver, "get_capabilities"):
            return None

        try:
            caps = driver.get_capabilities(device_id)
        except Exception as exc:
            logger.error(
                f"Failed to get capabilities for device '{device_id}': {exc}"
            )
            return None

        if isinstance(caps, dict):
            return caps
        return None


class _LegacyPublishDriver:
    """Minimal driver wrapper exposing a 'client' with publish() for legacy tests."""

    def __init__(self, client: Any):
        self.client = client

    def is_connected(self) -> bool:
        return True

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None
