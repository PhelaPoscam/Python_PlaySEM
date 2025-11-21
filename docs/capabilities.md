# Device Capabilities Schema

This document defines the JSON shape used to describe a device's supported effects and parameters.

## Top-level

- `device_id`: string — Identifier of the device the spec applies to.
- `effects`: array — List of supported effects.

## Effect object

- `effect_type`: string — One of `light`, `wind`, `vibration`, `scent`, or vendor-specific.
- `parameters`: array — Parameter capability descriptors.

## Parameter object

- `name`: string — Parameter name, e.g., `intensity`, `duration`, `color`.
- `type`: string — One of `int`, `float`, `bool`, `string`.
- `default`: any — Optional default value.
- Constraints (optional):
  - `min`: number — Minimum value for numeric types.
  - `max`: number — Maximum value for numeric types.
  - `step`: number — Step for numeric types.
  - `enum`: array — Allowed values for enumerated parameters.
  - `format`: string — Hint for UI formatting (e.g., `#RRGGBB` for colors).
  - `unit`: string — Display unit (e.g., `ms`, `%`).

## Examples

### Light device

```json
{
  "device_id": "mock_light_1",
  "effects": [
    {
      "effect_type": "light",
      "parameters": [
        {"name": "intensity", "type": "int", "min": 0, "max": 255, "default": 128, "unit": "%"},
        {"name": "duration", "type": "int", "min": 1, "max": 60000, "default": 1000, "unit": "ms"},
        {"name": "color", "type": "string", "format": "#RRGGBB", "default": "#FFFFFF"}
      ]
    }
  ]
}
```

### Vibration device

```json
{
  "device_id": "mock_vibration_1",
  "effects": [
    {
      "effect_type": "vibration",
      "parameters": [
        {"name": "intensity", "type": "int", "min": 0, "max": 100, "default": 50, "unit": "%"},
        {"name": "duration", "type": "int", "min": 1, "max": 10000, "default": 1000, "unit": "ms"},
        {"name": "pattern", "type": "string", "enum": ["constant", "pulse", "ramp"]}
      ]
    }
  ]
}
```

## Notes

- Parameters named `intensity` and `duration` are treated specially by some UIs and mapped to core fields.
- Unknown parameters are forwarded in `parameters` to drivers for device-specific behavior.
- Clients should validate values against provided constraints before sending.
