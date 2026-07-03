# WhisperCPP-WebUI — AGENTS.md

## Run

```bash
uv run python server.py
```
Serves on `https://0.0.0.0:8000`. Self-signed cert generated on first run (HTTPS needed for microphone access).

## Architecture

- **Single Flask app** (`server.py`) serving one template (`templates/index.html`).
- **All state is client-side** — chats, messages, blobs in `localStorage` (`wchats`, `wchat_active`, `wtheme`). Audio blobs live in a JS `blobs` object (browser memory only).
- **whisper.cpp server** is auto-started as a subprocess from `config.json` → `whisper_server_command`. Pointed at by `whisper_url` (endpoint: `/inference`).
- **Audio pipeline**: browser MediaRecorder → WebM → Flask saves temp file → ffmpeg converts to 16kHz/mono/PCM-s16le WAV → whisper.cpp server → transcript returned.
- **No npm/build step** — frontend is vanilla CSS+JS inline in the single HTML file. JSZip loaded from CDN for ZIP export.

## Key gotchas

- **whisper.cpp only accepts WAV** input. Server-side ffmpeg conversion is essential. If ffmpeg is missing, transcription fails.
- **Mobile sidebar** at ≤700px viewport: sidebar hidden off-screen, burger button toggles it, tappable overlay closes it. `createChat()` auto-closes sidebar on mobile.
- **No active chat + record/attach**: `send()` calls `createChat()` to auto-create one.
- **No persistence**: reloading the page loses all audio blobs. Chat metadata (names, texts) survives via localStorage.
- **Rename chat**: `startRename()` replaces the name span with an input; on blur/Enter it calls `renderChat()` to also update the top bar title.
- **Export ZIP**: produces `chat.md` with `![](audio/...)` markdown links + `audio/` folder. Uses JSZip.
- **No lint/test scripts** in the project — skip if asked.
