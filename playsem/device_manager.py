# src/device_manager.py
import asyncio
import inspect
import threading
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from playsem.config.loader import ConfigLoader
from playsem.drivers.base_driver import BaseDriver, BaseDiscovery
from playsem.command_envelope import CommandEnvelope
from playsem.device_registry import DeviceRegistry

logger = logging.getLogger(__name__)


@dataclass
class _CircuitState:
    """Per-device circuit breaker state."""

    state: str = "closed"
    failures: int = 0
    opened_at: Optional[float] = None
    last_error: Optional[str] = None


class DeviceManager:
    """
    Manages all active device drivers and routes commands to the correct
    driver based on device ID.

    Supports three initialization modes, all unified under a single code path:
    - Multi-driver mode: map devices to specific drivers via config
    - Single-driver mode: all devices route to one connectivity driver
    - Legacy mode: wrap a raw MQTT client as a driver
    """

    def __init__(
        self,
        drivers: Optional[List[BaseDriver]] = None,
        config_loader: Optional[ConfigLoader] = None,
        client: Optional[Any] = None,
        connectivity_driver: Optional[Any] = None,
        async_bridge_timeout: Optional[float] = 5.0,
        circuit_breaker_failure_threshold: Optional[int] = None,
        circuit_breaker_reset_timeout: float = 30.0,
        device_registry: Optional[DeviceRegistry] = None,
    ) -> None:
        """
        Initializes the DeviceManager.

        Args:
            drivers: A list of initialized driver instances (e.g., SerialDriver).
            config_loader: An initialized ConfigLoader instance.
            client: Legacy MQTT client for backwards compatibility in tests.
            connectivity_driver: Optional connectivity driver for single driver mode.
            async_bridge_timeout: Timeout in seconds for blocking async
                bridge calls. Set to None to disable timeout.
            circuit_breaker_failure_threshold: Optional number of consecutive
                failures that opens a per-device circuit. None disables it.
            circuit_breaker_reset_timeout: Seconds before an open circuit allows
                a half-open probe.
        """
        self.async_bridge_timeout = async_bridge_timeout
        self.circuit_breaker_failure_threshold = (
            circuit_breaker_failure_threshold
        )
        self.circuit_breaker_reset_timeout = max(
            0.0, circuit_breaker_reset_timeout
        )
        self.device_to_driver: Dict[str, BaseDriver] = {}
        self._device_locks: Dict[str, threading.RLock] = {}
        self._device_locks_guard = threading.RLock()
        self._async_device_locks: Dict[
            tuple[Optional[asyncio.AbstractEventLoop], str], asyncio.Lock
        ] = {}
        self._circuit_states: Dict[str, _CircuitState] = {}
        self.device_registry = device_registry
        self._queues: Dict[str, asyncio.PriorityQueue] = {}
        self._workers: Dict[str, asyncio.Task] = {}
        self._async_running = False
        self.dead_letter_queue: List[CommandEnvelope] = []
        self._scanners: List[BaseDiscovery] = []
        self.drivers_by_interface: Dict[str, BaseDriver] = {}
        self._default_driver: Optional[Any] = None
        self.config_loader: Optional[ConfigLoader] = config_loader
        self.connectivity_driver = connectivity_driver

        if client is not None:
            # Legacy mode: wrap raw client as a driver
            logger.info("Initializing DeviceManager in legacy client mode.")
            self._default_driver = _LegacyPublishDriver(client)
        elif connectivity_driver is not None:
            # Single driver mode
            logger.info(
                "Initializing DeviceManager with single connectivity driver."
            )
            self._default_driver = connectivity_driver
            if isinstance(connectivity_driver, BaseDiscovery):
                self.register_scanner(connectivity_driver)
        else:
            # Multi-driver mode
            drivers = drivers or []
            logger.info(
                f"Initializing DeviceManager with {len(drivers)} drivers."
            )
            self.drivers_by_interface = {
                driver.get_interface_name(): driver for driver in drivers
            }
            if config_loader is None:
                raise ValueError(
                    "config_loader is required when not using legacy client mode"
                )
            self._map_devices_to_drivers()
            self.connect_all()

            for driver in drivers:
                if isinstance(driver, BaseDiscovery):
                    self.register_scanner(driver)

    @property
    def connectivity_driver(self) -> Optional[Any]:
        return getattr(self, "_connectivity_driver", None)

    @connectivity_driver.setter
    def connectivity_driver(self, value: Optional[Any]) -> None:
        self._connectivity_driver = value
        if not self.device_to_driver:
            self._default_driver = value

    def _resolve_driver(self, device_id: str) -> Optional[Any]:
        """Resolve the driver for a device, falling back to default."""
        return self.device_to_driver.get(device_id) or self._default_driver

    def _map_devices_to_drivers(self) -> None:
        """
        Builds a mapping from each deviceId to its corresponding driver instance
        using the loaded configuration.
        """
        if self.config_loader is None:
            return

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
        try:
            result: Any = self._run_awaitable_blocking(
                self.async_send_command(device_id, command, params)
            )
            return bool(result)
        except Exception as e:
            logger.error(
                f"Exception in send_command for device '{device_id}': {e}"
            )
            return False

    async def async_send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Asynchronously sends a command to a specific device without creating
        new threads for awaitable driver calls.
        """
        if params is None:
            params = {}

        driver = self._resolve_driver(device_id)
        if not driver:
            logger.error(
                f"No driver found for device_id '{device_id}'. Cannot send command."
            )
            return False

        async_lock = self._get_async_device_lock(device_id)
        async with async_lock:
            device_lock = self._get_device_lock(device_id)
            with device_lock:
                if not self._circuit_allows_request(device_id):
                    return False

            driver_name = (
                driver.get_driver_type()
                if hasattr(driver, "get_driver_type")
                else type(driver).__name__
            )
            logger.info(
                f"Async sending command '{command}' to device "
                f"'{device_id}' via {driver_name} driver."
            )
            try:
                if inspect.iscoroutinefunction(driver.send_command):
                    success = await driver.send_command(
                        device_id, command, params
                    )
                else:

                    def _run_sync():
                        return driver.send_command(device_id, command, params)

                    result = await asyncio.to_thread(_run_sync)
                    if inspect.isawaitable(result):
                        success = await result
                    else:
                        success = result

                success = bool(success)
                with device_lock:
                    self._record_circuit_outcome(device_id, success)
                return success
            except Exception as e:
                logger.error(
                    f"Failed to async send command to device '{device_id}': {e}"
                )
                with device_lock:
                    self._record_circuit_failure(device_id, str(e))
                return False

    async def start_async_workers(self) -> None:
        """Starts the per-device async background workers."""
        self._async_running = True
        logger.info("Starting async device workers.")
        for device_id in self.device_to_driver.keys():
            self._ensure_worker(device_id)

    async def stop_async_workers(self) -> None:
        """Stops all running async device workers."""
        self._async_running = False
        logger.info("Stopping async device workers.")
        for task in self._workers.values():
            task.cancel()
        await asyncio.gather(*self._workers.values(), return_exceptions=True)
        self._workers.clear()

    def _ensure_worker(self, device_id: str) -> None:
        """Ensure a queue and worker task exist for a given device_id."""
        if not self._async_running:
            return
        with self._device_locks_guard:
            if device_id not in self._queues:
                self._queues[device_id] = asyncio.PriorityQueue(maxsize=100)
            if (
                device_id not in self._workers
                or self._workers[device_id].done()
            ):
                self._workers[device_id] = asyncio.create_task(
                    self._device_worker(device_id)
                )

    async def async_submit_envelope(self, envelope: CommandEnvelope) -> Any:
        """
        Submit a command envelope to the appropriate per-device queue.
        """
        device_id = envelope.device_id
        self._ensure_worker(device_id)

        if device_id not in self._queues:
            return {
                "status": "rejected",
                "error": f"No queue for device {device_id}",
            }

        queue = self._queues[device_id]
        try:
            item = (envelope.priority, envelope.created_at, envelope)
            await asyncio.wait_for(queue.put(item), timeout=0.05)
            return {
                "status": "queued",
                "accepted": True,
                "delivered": False,
                "device_id": device_id,
            }
        except asyncio.TimeoutError:
            return {
                "status": "rejected",
                "accepted": False,
                "delivered": False,
                "error": "device queue full",
            }

    async def _device_worker(self, device_id: str) -> None:
        """Background worker that drains the queue for a single device."""
        queue = self._queues[device_id]
        logger.info(f"Async worker started for device '{device_id}'")
        while self._async_running:
            try:
                priority, created_at, envelope = await queue.get()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker for '{device_id}' queue get error: {e}")
                continue

            if envelope.deadline_ms is not None:
                elapsed_ms = (time.monotonic() - envelope.created_at) * 1000.0
                if elapsed_ms > envelope.deadline_ms:
                    logger.warning(
                        f"Envelope for '{device_id}' expired before dispatch."
                    )
                    queue.task_done()
                    continue

            attempts = 0
            max_attempts = 1 if envelope.delivery_mode == "best_effort" else 3
            success = False

            while attempts < max_attempts and not success:
                attempts += 1
                success = await self.async_send_command(
                    device_id, envelope.command, envelope.params
                )
                if not success and attempts < max_attempts:
                    await asyncio.sleep(0.1 * attempts)

            if not success:
                logger.warning(
                    f"Dead-lettering envelope for '{device_id}' after {attempts} attempts."
                )
                self.dead_letter_queue.append(envelope)

            queue.task_done()

    def connect_all(self) -> None:
        """Connects all managed drivers."""
        logger.info("Connecting all drivers...")
        if self._default_driver is not None:
            try:
                if not self._driver_is_connected(self._default_driver):
                    result = self._default_driver.connect()
                    self._resolve_maybe_async(result)
                    logger.info("Default driver connected.")
            except Exception as e:
                logger.error(f"Failed to connect default driver: {e}")
            return

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

    async def async_connect_all(self) -> None:
        """Connects all managed drivers asynchronously."""
        logger.info("Connecting all drivers asynchronously...")
        drivers = self._all_drivers()
        for driver in drivers:
            try:
                if not await driver.is_connected():
                    await driver.connect()
                    logger.info(
                        f"Driver {driver.get_driver_type()} connected."
                    )
            except Exception as e:
                logger.error(
                    f"Failed to connect driver {driver.get_driver_type()}: {e}"
                )

    def disconnect_all(self) -> None:
        """Disconnects all managed drivers."""
        logger.info("Disconnecting all drivers...")
        if self._default_driver is not None:
            try:
                if self._driver_is_connected(self._default_driver):
                    result = self._default_driver.disconnect()
                    self._resolve_maybe_async(result)
                    logger.info("Default driver disconnected.")
            except Exception as e:
                logger.error(f"Failed to disconnect default driver: {e}")
            return

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

    async def async_disconnect_all(self) -> None:
        """Disconnects all managed drivers asynchronously."""
        logger.info("Disconnecting all drivers asynchronously...")
        drivers = self._all_drivers()
        for driver in drivers:
            try:
                if await driver.is_connected():
                    await driver.disconnect()
                    logger.info(
                        f"Driver {driver.get_driver_type()} disconnected."
                    )
            except Exception as e:
                logger.error(
                    f"Failed to disconnect driver {driver.get_driver_type()}: {e}"
                )

    # --- Backwards compatibility helpers ---
    def connect(self) -> None:
        """Connect single connectivity driver (legacy path)."""
        if self._default_driver is not None:
            try:
                if hasattr(self._default_driver, "connect"):
                    result = self._default_driver.connect()
                    self._resolve_maybe_async(result)
            except Exception as exc:
                logger.error(f"Default driver connect failed: {exc}")

    def disconnect(self) -> None:
        """Disconnect single connectivity driver (legacy path)."""
        if self._default_driver is not None:
            try:
                if hasattr(self._default_driver, "disconnect"):
                    result = self._default_driver.disconnect()
                    self._resolve_maybe_async(result)
            except Exception as exc:
                logger.error(f"Default driver disconnect failed: {exc}")

    def _all_drivers(self) -> List[Any]:
        """Return all unique driver instances."""
        if self._default_driver is not None:
            return [self._default_driver]
        return list(self.drivers_by_interface.values())

    def _get_device_lock(self, device_id: str) -> threading.RLock:
        """Return the lock that serializes commands for one logical device."""
        with self._device_locks_guard:
            lock = self._device_locks.get(device_id)
            if lock is None:
                lock = threading.RLock()
                self._device_locks[device_id] = lock
            return lock

    def _get_async_device_lock(self, device_id: str) -> asyncio.Lock:
        """Return the async lock that serializes async commands for one logical device."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        key = (loop, device_id)

        with self._device_locks_guard:
            lock = self._async_device_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._async_device_locks[key] = lock
            return lock

    def _circuit_enabled(self) -> bool:
        """Return whether per-device circuit breaking is enabled."""
        return (
            self.circuit_breaker_failure_threshold is not None
            and self.circuit_breaker_failure_threshold > 0
        )

    def _sync_circuit_state_to_registry(
        self, device_id: str, state: _CircuitState
    ) -> None:
        """Synchronizes circuit breaker status to the device registry if configured."""
        if self.device_registry is not None:
            self.device_registry.update_circuit_status(
                device_id=device_id,
                state=state.state,
                failures=state.failures,
                last_error=state.last_error,
            )

    def _get_circuit_state(self, device_id: str) -> _CircuitState:
        state = self._circuit_states.get(device_id)
        if state is None:
            state = _CircuitState()
            self._circuit_states[device_id] = state
            self._sync_circuit_state_to_registry(device_id, state)
        return state

    def _circuit_allows_request(self, device_id: str) -> bool:
        """Return True when the device circuit can accept a command."""
        if not self._circuit_enabled():
            return True

        state = self._get_circuit_state(device_id)
        if state.state != "open":
            return True

        opened_at = state.opened_at or 0.0
        if (
            time.monotonic() - opened_at
        ) >= self.circuit_breaker_reset_timeout:
            state.state = "half_open"
            logger.info(f"Circuit for device '{device_id}' moved to half-open")
            self._sync_circuit_state_to_registry(device_id, state)
            return True

        logger.warning(f"Circuit for device '{device_id}' is open")
        return False

    def _record_circuit_outcome(self, device_id: str, success: bool) -> None:
        if success:
            self._record_circuit_success(device_id)
        else:
            self._record_circuit_failure(
                device_id, "driver returned unsuccessful result"
            )

    def _record_circuit_success(self, device_id: str) -> None:
        if not self._circuit_enabled():
            return

        state = self._get_circuit_state(device_id)
        state.state = "closed"
        state.failures = 0
        state.opened_at = None
        state.last_error = None
        self._sync_circuit_state_to_registry(device_id, state)

    def _record_circuit_failure(self, device_id: str, error: str) -> None:
        if not self._circuit_enabled():
            return

        state = self._get_circuit_state(device_id)
        state.failures += 1
        state.last_error = error

        threshold = self.circuit_breaker_failure_threshold or 1
        if state.failures >= threshold or state.state == "half_open":
            state.state = "open"
            state.opened_at = time.monotonic()
            logger.warning(
                f"Circuit for device '{device_id}' opened after "
                f"{state.failures} failure(s): {error}"
            )
        self._sync_circuit_state_to_registry(device_id, state)

    def get_queue_depths(self) -> Dict[str, int]:
        """Return per-device queue depths for monitoring."""
        return {dev_id: q.qsize() for dev_id, q in self._queues.items()}

    def get_circuit_info(self, device_id: str) -> Dict[str, Any]:
        """Return circuit breaker status for a device."""
        if not self._circuit_enabled():
            return {"enabled": False}

        state = self._get_circuit_state(device_id)
        return {
            "enabled": True,
            "state": state.state,
            "failures": state.failures,
            "opened_at": state.opened_at,
            "last_error": state.last_error,
            "failure_threshold": self.circuit_breaker_failure_threshold,
            "reset_timeout": self.circuit_breaker_reset_timeout,
        }

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
        """Run awaitable in current thread or isolated loop thread.

        When called from a thread that already has a running event loop
        (e.g. a FastAPI handler), a fresh loop is created in a dedicated
        thread so that ``asyncio.run`` dead-lock is avoided.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop in this thread — safe to use asyncio.run directly.
            return asyncio.run(awaitable)

        holder: Dict[str, Any] = {}

        def _runner() -> None:
            """Create a brand-new event loop and run the coroutine."""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                holder["result"] = new_loop.run_until_complete(awaitable)
            except Exception as exc:
                holder["error"] = exc
            finally:
                # Cancel any orphaned tasks before closing the loop.
                pending = asyncio.all_tasks(new_loop)
                for task in pending:
                    task.cancel()
                if pending:
                    new_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                new_loop.close()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()

        if self.async_bridge_timeout is None:
            thread.join()
        else:
            thread.join(timeout=self.async_bridge_timeout)
            if thread.is_alive():
                logger.warning(
                    "Async bridge execution exceeded timeout of "
                    f"{self.async_bridge_timeout}s. Waiting for "
                    "completion to avoid orphaned thread corruption."
                )
                thread.join()

        if "error" in holder:
            raise holder["error"]
        return holder.get("result")

    def get_all_driver_info(self) -> Dict[str, Any]:
        """Gets status information from all managed drivers."""
        info: Dict[str, Any] = {}

        if self._default_driver is not None:
            if hasattr(self._default_driver, "get_driver_info"):
                info["default"] = self._resolve_maybe_async(
                    self._default_driver.get_driver_info()
                )
            else:
                info["default"] = {
                    "type": type(self._default_driver).__name__,
                }
        else:
            info.update(
                {
                    interface_name: self._resolve_maybe_async(
                        driver.get_driver_info()
                    )
                    for interface_name, driver in self.drivers_by_interface.items()
                }
            )

        info["_manager"] = {"async_bridge_timeout": self.async_bridge_timeout}
        if self._circuit_enabled():
            info["_manager"].update(
                {
                    "circuit_breaker_failure_threshold": (
                        self.circuit_breaker_failure_threshold
                    ),
                    "circuit_breaker_reset_timeout": (
                        self.circuit_breaker_reset_timeout
                    ),
                    "circuit_breakers": {
                        device_id: self.get_circuit_info(device_id)
                        for device_id in self._circuit_states
                    },
                }
            )
        return info

    def get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Gets configuration information for a specific device."""
        if self.config_loader is None:
            return None
        devices_config = self.config_loader.load_devices_config()
        for device in devices_config.get("devices", []):
            if not isinstance(device, dict):
                continue
            if device.get("deviceId") == device_id:
                return device
        return None

    def get_driver_for_device(self, device_id: str) -> Optional[Any]:
        """Return the concrete driver instance for a device id."""
        return self._resolve_driver(device_id)

    def get_device_capabilities(
        self, device_id: str
    ) -> Optional[Dict[str, Any]]:
        """Query capabilities for a device from its mapped driver."""
        driver = self._resolve_driver(device_id)
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

    def register_scanner(self, scanner: BaseDiscovery) -> None:
        """Register a device discovery/scanner module."""
        if scanner not in self._scanners:
            self._scanners.append(scanner)
            logger.info(
                f"Registered discovery scanner for interface: {scanner.get_interface_name()}"
            )

    async def discover_all_devices(self) -> List[Dict[str, Any]]:
        """
        Scan/discover devices across all registered scanners in parallel.
        """
        if not self._scanners:
            logger.warning("No discovery scanners registered.")
            return []

        tasks = [scanner.discover_devices() for scanner in self._scanners]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_devices = []
        for scanner, res in zip(self._scanners, results):
            if isinstance(res, Exception):
                logger.error(
                    f"Discovery scanner '{scanner.get_interface_name()}' failed: {res}"
                )
            elif isinstance(res, list):
                logger.info(
                    f"Scanner '{scanner.get_interface_name()}' discovered {len(res)} device(s)"
                )
                for dev in res:
                    all_devices.append(dev)
                    if self.device_registry is not None:
                        try:
                            protocols = dev.get(
                                "protocols", [scanner.get_interface_name()]
                            )
                            self.device_registry.register_device(
                                device_data={
                                    "id": dev["id"],
                                    "name": dev.get("name") or dev["id"],
                                    "type": dev.get("type") or "unknown",
                                    "address": dev.get("address"),
                                    "protocols": protocols,
                                    "capabilities": dev.get(
                                        "capabilities", {}
                                    ),
                                    "metadata": dev.get("metadata", {}),
                                },
                                source_protocol=scanner.get_interface_name(),
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to auto-register discovered device '{dev['id']}': {e}"
                            )
            else:
                logger.warning(
                    f"Scanner '{scanner.get_interface_name()}' returned invalid type: {type(res)}"
                )

        return all_devices


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

    def get_driver_type(self) -> str:
        return "legacy"

    def get_interface_name(self) -> str:
        return "legacy"

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        payload = str({"command": command, "params": params or {}})
        self.client.publish(device_id, payload)
        return True
