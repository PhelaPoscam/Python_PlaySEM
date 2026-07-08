/**
 * PlaySEM Fan Controller — Arduino Sketch
 *
 * Receives newline-delimited JSON commands from PlaySEM's SerialDriver
 * and drives a PWM fan/motor on Pin 9.
 *
 * Supported commands:
 *   {"command": "set_speed", "params": {"speed": 80}}
 *   {"command": "set_direction", "params": {"direction": "forward"}}
 *   {"command": "off"} or {"command": "reset"}
 *
 * Hardware:
 *   - Arduino Uno/Nano/Mega or ESP32
 *   - Fan/motor connected to Pin 9 via MOSFET or L298N
 *
 * Dependencies (Arduino Library Manager):
 *   - ArduinoJson by Benoit Blanchon
 */

#include <Arduino.h>
#include <ArduinoJson.h>

const int FAN_PWM_PIN = 9;  // PWM pin -> MOSFET gate / L298N ENA

void setup() {
  Serial.begin(115200);
  pinMode(FAN_PWM_PIN, OUTPUT);
  analogWrite(FAN_PWM_PIN, 0);

  // Signal readiness to PlaySEM
  Serial.println("{\"status\":\"ready\",\"device\":\"fan_controller\"}");
}

/**
 * Map PlaySEM's 0-100% speed to Arduino's 0-255 PWM range.
 */
int speedToPwm(int speedPercent) {
  speedPercent = constrain(speedPercent, 0, 100);
  return map(speedPercent, 0, 100, 0, 255);
}

void handleCommand(JsonDocument& doc) {
  const char* cmd = doc["command"];
  JsonObject params = doc["params"];

  if (cmd == nullptr) {
    Serial.println("{\"error\":\"missing command\"}");
    return;
  }

  if (strcmp(cmd, "set_speed") == 0) {
    int speedPercent = params["speed"] | 0;
    int pwmValue = speedToPwm(speedPercent);
    analogWrite(FAN_PWM_PIN, pwmValue);

    // Optional: read direction if provided
    const char* dir = params["direction"];
    const char* dirStr = (dir != nullptr) ? dir : "forward";

    Serial.print("{\"status\":\"ok\",\"command\":\"set_speed\",\"speed_pct\":");
    Serial.print(speedPercent);
    Serial.print(",\"pwm\":");
    Serial.print(pwmValue);
    Serial.print(",\"direction\":\"");
    Serial.print(dirStr);
    Serial.println("\"}");
  }
  else if (strcmp(cmd, "set_direction") == 0) {
    const char* dir = params["direction"] | "forward";
    // Direction is informational for a single-PWM fan.
    // For an H-bridge (L298N), drive IN1/IN2 pins here.
    Serial.print("{\"status\":\"ok\",\"command\":\"set_direction\",\"direction\":\"");
    Serial.print(dir);
    Serial.println("\"}");
  }
  else if (strcmp(cmd, "off") == 0 || strcmp(cmd, "reset") == 0) {
    analogWrite(FAN_PWM_PIN, 0);
    Serial.println("{\"status\":\"ok\",\"command\":\"off\"}");
  }
  else {
    Serial.print("{\"error\":\"unknown_command\",\"command\":\"");
    Serial.print(cmd);
    Serial.println("\"}");
  }
}

void loop() {
  if (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, line);

    if (!error) {
      handleCommand(doc);
    } else {
      Serial.print("{\"error\":\"invalid_json\",\"detail\":\"");
      Serial.print(error.c_str());
      Serial.println("\"}");
    }
  }
}
