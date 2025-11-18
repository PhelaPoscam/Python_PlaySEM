# Timeline Player Feature

This document was moved here from examples/control_panel/TIMELINE_PLAYER.md to consolidate reference documentation under docs/reference/.

Below is the original content preserved in full.

---

# Timeline Player Feature

The control panel now supports uploading and playing **SERenderer.xml** timeline files, bringing it closer to the original [PlaySEM SERenderer](https://github.com/estevaosaleme/PlaySEM_SERenderer) project.

## What's New

### 1. Improved Control Panel Workflow

The UI has been reorganized for a more logical flow:

1. **🔌 Control Panel Connection** – Connect the web UI to the backend
2. **📡 Protocol Servers** – Start servers (MQTT, CoAP, HTTP, UPnP, WebSocket) for external clients
3. **🔍 Device Discovery & Management** – Scan and connect devices (requires protocol servers for network discovery)
4. **⚡ Effect Testing** – Send individual effects to connected devices
5. **🎬 Timeline Player** – Upload and play XML timeline files
6. **📊 System Statistics** & **📝 Activity Log**

### 2. Timeline Player

Upload and play **MPEG-V XML** or **SERenderer.xml** files to trigger synchronized sensory effects:

- **Upload** `.xml` files containing effect timelines
- **Play/Pause/Stop** timeline playback
- **Real-time position tracking** during playback
- Effects are dispatched to all connected devices

## XML Timeline Format

The timeline player supports MPEG-V XML format. Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SEM title="Sample Sensory Effect Timeline">
    <metadata>
        <title>Action Scene Demo</title>
        <author>PlaySEM</author>
    </metadata>
    
    <SensoryEffects>
        <Effect type="vibration" timestamp="0" duration="500" intensity="80" location="center"/>
        <Effect type="light" timestamp="200" duration="800" intensity="100" color="#FF0000"/>
        <Effect type="wind" timestamp="500" duration="1000" intensity="60"/>
        <Effect type="vibration" timestamp="1500" duration="700" intensity="100"/>
    </SensoryEffects>
</SEM>
```

### Supported Effect Types

- `vibration` – Haptic feedback
- `light` – RGB lighting effects (supports `color` attribute)
- `wind` – Fan/wind effects
- `scent` – Olfactory effects
- `temperature` – Thermal effects

### Effect Attributes

- `type` – Effect type (required)
- `timestamp` – Start time in milliseconds (default: 0)
- `duration` – Duration in milliseconds (default: 1000)
- `intensity` – Intensity 0-100 (optional)
- `location` – Spatial location: `left`, `right`, `center`, `everywhere` (default: `everywhere`)
- Additional attributes: `color` (for light), `scent`, `direction`, `temperature`

## Usage

1. **Start the control panel server:**
   ```powershell
   python examples\control_panel\control_panel_server.py
   ```

2. **Open your browser:**
   ```
   http://localhost:8090
   ```

3. **Connect the UI** to the backend (WebSocket)

4. **(Optional) Start protocol servers** if you want external clients to send effects

5. **Connect devices** (Serial, Bluetooth, MQTT, or Mock)

6. **Upload a timeline:**
   - Click **"📁 Upload .xml Timeline"** in the Timeline Player section
   - Select a `.xml` file (e.g., `sample_timeline.xml`)
   - The timeline will be parsed and loaded

7. **Play the timeline:**
   - Click **▶️ Play** to start playback
   - Effects will be dispatched to connected devices at their specified timestamps
   - Use **⏸️ Pause** / **▶️ Resume** / **���️ Stop** to control playback

## Sample Timeline

A sample timeline is provided in `examples/control_panel/sample_timeline.xml` with 8 effects spanning ~4.5 seconds.

## Implementation Details

### Backend (`control_panel_server.py`)

- **Timeline object** manages effect scheduling and playback
- **XML parser** converts MPEG-V XML to `EffectTimeline` objects
- **WebSocket messages:**
  - `upload_timeline` – Upload XML content
  - `play_timeline` – Start playback
  - `pause_timeline` / `resume_timeline` – Pause/resume
  - `stop_timeline` – Stop and reset
  - `get_timeline_status` – Query current status
- **HTTP endpoint:** `POST /api/timeline/upload` (for file uploads)

### Frontend (`control_panel.html`)

- **File upload button** reads `.xml` files
- **Timeline info display** shows effect count and duration
- **Playback controls** (Play, Pause, Resume, Stop)
- **Position tracking** displays current playback position

### XML Parser (`src/xml_timeline_parser.py`)

- Parses **MPEG-V XML** format
- Supports both **attribute-based** and **element-based** XML
- Normalizes effect type names (e.g., `LightEffect` → `light`)
- Extracts metadata (title, author, etc.)
- Returns `EffectTimeline` objects compatible with `src/timeline.py`

## Compatibility

This implementation aims to be compatible with the original PlaySEM SERenderer XML format, making it easier to reuse existing timeline files from the [PlaySEM_SERenderer](https://github.com/estevaosaleme/PlaySEM_SERenderer) project.

## Future Enhancements

- **Visual timeline editor** for creating/editing timelines in the browser
- **Timeline scrubbing** to jump to specific positions
- **Loop playback** option
- **Export** timelines to XML
- **Synchronized video playback** with timelines
