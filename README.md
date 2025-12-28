# icalc

**icalc** is a locally hosted, AI-ready calculator webapp designed to train and test AI agents in tool use. It features a modern interface, scientific functions, and a robust state exposure mechanism for programmatic access.

## Features

- **Dual Modes**: Standard and Scientific calculator modes.
- **Premium UI**: Dark mode with Glassmorphism aesthetics.
- **AI Integration**:
  - Exposes internal state via `window.icalcState`.
  - Provides bounding box data for all interactive elements for spatial awareness.
  - Tracks mouse position and history.
- **Remote Bridge**: Includes a Python client (`icalc_bridge.py`) to connect the local app to a remote AI agent server.

## Installation

1.  Clone the repository.
2.  (Optional) Install Python dependencies for the bridge:
    ```bash
    pip install selenium requests
    ```

## Usage

### 1. Run the WebApp
To run the app manually:
```bash
python3 -m http.server 8000
```
Access the calculator at [http://localhost:8000](http://localhost:8000).

### 2. Run the Bridge (With Automatic Web Server)
The bridge script automatically starts a local web server for you.
1.  Ensure you have a ChromeDriver installed.
2.  Run the bridge script:
    ```bash
    python3 icalc_bridge.py
    ```
    This will serve the webapp on port 8000 and connect the Selenium driver to it.
3.  The bridge connects to the calculator and forwards state to your Agent Server (default: `http://localhost:9000/step`).
    
    **Options:**
    - `--vision`: Enable sending screenshots (base64 encoded) in the state.
    - `--rate N`: Set the state update rate to N Hz (default: 60.0).
    - `--port P`: Port to serve the webapp on (default: 8000).
    - `--headless`: Run Chrome in headless mode (recommended for bulk generation).
    - `--agent-url URL`: Full URL of the agent server.

    Example:
    ```bash
    python3 icalc_bridge.py --headless --rate 60 --port 8001 --agent-url http://localhost:9001/step
    ```

## Data Protocol
The app exposes state in the following JSON format:

```json
{
  "readout": "123.45",
  "history": ["1", "+", "2"],
  "mode": "basic",
  "mousePosition": { "x": 100, "y": 200 },
  "interactiveElements": [
    {
      "text": "7",
      "value": "7",
      "rect": { "x": 10, "y": 50, "width": 60, "height": 60 }
    }
  ]
}
```

## Agent Protocol
The Agent Server should reply with one of the following JSON actions:

- **Move Mouse**: `{"type": "move", "x": 100, "y": 200}`
- **Click**: `{"type": "click"}`
- **Keypress**: `{"type": "keypress", "key": "Enter"}` 
  - Supports standard keys: 0-9, +, -, *, /, Enter, Backspace, Escape, m.
  - Supports semantic function keys: "sin", "cos", "tan", "log", "ln", "sqrt", "pi", "e". The bridge will automatically find and click the corresponding buttons.
