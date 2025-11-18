# Plan for Embedded MQTT Broker Implementation and Testing

This document outlines the intended steps for implementing and testing an embedded MQTT broker within the project, which was attempted but encountered issues.

## Goal
To integrate an embedded MQTT broker directly into the application to provide a self-contained messaging solution, reducing external dependencies and simplifying deployment.

## Current Status (as of 2025-11-18)

The core functionality of embedding an MQTT broker using `amqtt` has been successfully implemented and verified by passing tests. The previous issues related to `hbmqtt` and configuration have been resolved.

## What is Done:

### 1. Research and Selection of Embedded MQTT Broker Library
- **Action:** `amqtt` has been successfully identified, selected, and integrated as the embedded MQTT broker library, replacing the unmaintained `hbmqtt`.

### 2. Initial Implementation of Embedded Broker
- **Action:** The `MQTTServer` class in `src/protocol_server.py` has been refactored to use `amqtt`. It now correctly starts, stops, and handles MQTT messages internally, dispatching them to the `EffectDispatcher`.
- **Details:** An internal `paho.mqtt.client` is used within the `MQTTServer` to subscribe to topics and process messages, as `amqtt`'s broker API does not provide a direct callback for incoming messages.
- **Synchronization:** A `_ready_event` mechanism has been implemented to ensure the broker is fully started and ready to accept connections before clients attempt to connect, resolving previous race conditions.

### 4. Development of Unit/Integration Tests (`tests/test_mqtt_broker.py`)
- **Action:** The `tests/test_mqtt_broker.py` file contains comprehensive tests for the embedded MQTT broker's functionality (startup/shutdown, client connection, message publishing/dispatching).
- **Verification:** All tests in `test_mqtt_broker.py` are now passing, confirming the successful implementation and stability of the `amqtt`-based embedded broker.

### Addressing the "Crashing" Issue
- **Resolution:** The previous issues leading to crashes or connection refusals have been resolved through:
    - Replacing `hbmqtt` with `amqtt`.
    - Correctly configuring `amqtt` (initially by removing problematic plugin configurations, then by using a minimal configuration).
    - Implementing a robust readiness check (`_ready_event`) for the broker.
    - Correctly handling `paho.mqtt.client` imports and `MQTTServer` initialization.

## What Needs to Be Done:

### 3. Integration with Existing MQTT Client Logic
- **Action:** Ensure that the project's *other* internal MQTT clients (e.g., `src/device_driver/mqtt_driver.py`, or any other module that connects to an MQTT broker) are configured to connect to this local `MQTTServer` when it is active.
- **Considerations:**
    - **Configuration:** Implement a clear configuration mechanism (e.g., in `config/devices.yaml` or a new dedicated configuration file) to allow users to enable/disable the embedded broker and specify its host/port.
    - **Client Adaptation:** Modify existing MQTT client code to read this configuration and dynamically connect to the embedded broker if enabled, or fall back to an external broker (like `test.mosquitto.org`) otherwise.

### 5. Refinement and Error Handling (Ongoing)
- **Action:** Continue to refine the `MQTTServer` implementation for robustness and production readiness.
- **Considerations:**
    - **Error Handling:** Implement more comprehensive error handling within `MQTTServer`, especially for scenarios like internal client connection loss or message processing failures.
    - **Performance:** Conduct performance testing to ensure the embedded broker can handle the expected load.
    - **`amqtt` Plugins:** Re-evaluate the need for `amqtt` plugins (e.g., `auth_anonymous`, `topic_taboo`, `broker_sys_topic`) that were removed during debugging. If these features are required, they should be re-added with correct `amqtt` configuration.

### Cleanup
- **Action:** Remove temporary debugging artifacts.
- **Considerations:**
    - **Logging Configuration:** Remove or adjust the `logging.basicConfig` added to `tests/conftest.py` if it's not intended for general test runs.
    - **Test Sleep Time:** Remove the increased `asyncio.sleep(2)` from `tests/test_mqtt_broker.py` as the `wait_until_ready` mechanism should make it redundant.
    - **Code Comments:** Ensure all new code is well-commented and follows project conventions.