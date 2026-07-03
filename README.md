# WhisperCPP-WebUI

A web UI for [whisper.cpp](https://github.com/ggerganov/whisper.cpp).  
No data is stored on the server — everything lives in your browser.

## Features

- **Multiple chats** — create, rename, switch, delete
- **Record or upload audio** — transcribed via whisper.cpp
- **Copy / save / share** — copy text, download audio, share via Web Share API
- **Export to ZIP** — markdown file with embedded audio references + `audio/` folder
- **No server persistence** — audio is held in browser memory only

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) installed and available in PATH (or specify full path in `config.json`)

## Setup

```bash
uv sync
```

## Configuration

Edit `config.json`:

```json
{
  "whisper_server_command": "whisper-server --model ~/.local/share/whisper-models/ggml-large-v3-turbo.bin --host 0.0.0.0 --port 8080 --language it --threads 8",
  "whisper_url": "http://127.0.0.1:8080/inference"
}
```

- `whisper_server_command` — command to start whisper.cpp server (optional, omit if already running)
- `whisper_url` — inference endpoint of the whisper.cpp server

## Run

```bash
uv run python server.py
```

The web UI will be available at `http://localhost:8000`.

Stopping the Python server (Ctrl+C) will automatically terminate the whisper.cpp process it launched.
