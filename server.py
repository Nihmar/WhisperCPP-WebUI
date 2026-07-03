import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time

import requests as http_requests
from flask import Flask, jsonify, render_template, request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH) as f:
    config = json.load(f)

WHISPER_URL = config["whisper_url"]
whisper_process: subprocess.Popen | None = None


def _kill_whisper():
    global whisper_process
    if whisper_process is None:
        return
    pid = whisper_process.pid
    log.info("Terminating whisper.cpp (PID %d) ...", pid)
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        try:
            whisper_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
            whisper_process.wait(timeout=3)
        log.info("whisper.cpp stopped.")
    except ProcessLookupError:
        pass
    except Exception as exc:
        log.warning("Error killing whisper.cpp: %s", exc)
    whisper_process = None


def _start_whisper():
    global whisper_process
    cmd = config.get("whisper_server_command")
    if not cmd:
        return
    log.info("Starting whisper.cpp: %s", cmd)
    whisper_process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    time.sleep(2)
    if whisper_process.poll() is not None:
        stderr = whisper_process.stderr.read()
        log.error("whisper.cpp exited immediately. stderr:\n%s", stderr)
        sys.exit(1)
    log.info("whisper.cpp started (PID %d).", whisper_process.pid)


def _shutdown(signum=None, frame=None):
    sig_name = signal.Signals(signum).name if signum else "exit"
    log.info("Received %s, shutting down ...", sig_name)
    _kill_whisper()
    sys.exit(0)


def _ensure_cert():
    cert = os.path.join(BASE_DIR, "cert.pem")
    key = os.path.join(BASE_DIR, "key.pem")
    if os.path.exists(cert) and os.path.exists(key):
        return cert, key
    log.info("Generating self-signed certificate ...")
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key, "-out", cert,
            "-days", "365", "-nodes",
            "-subj", "/CN=whispercpp-webui",
        ],
        check=True,
        capture_output=True,
    )
    log.info("Certificate generated: %s", cert)
    return cert, key


atexit.register(_kill_whisper)
signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

_start_whisper()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    _, ext = os.path.splitext(file.filename)
    if not ext:
        ext = ".wav"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
        file.save(tmp_in.name)
        in_path = tmp_in.name

    wav_path = None
    try:
        if ext.lower() != ".wav":
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                wav_path = tmp_wav.name
            subprocess.run(
                ["ffmpeg", "-y", "-i", in_path,
                 "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                 wav_path],
                capture_output=True, check=True,
            )
            send_path = wav_path
        else:
            send_path = in_path

        with open(send_path, "rb") as f:
            resp = http_requests.post(
                WHISPER_URL,
                files={"file": ("audio.wav", f, "audio/wav")},
            )
        if resp.status_code != 200:
            return jsonify({"error": f"Whisper server error: {resp.text}"}), 500
        transcript = resp.json().get("text", "").strip()
    except subprocess.CalledProcessError as exc:
        err = exc.stderr.decode(errors="replace") if exc.stderr else ""
        return jsonify({"error": f"Audio conversion failed: {err}"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        os.unlink(in_path)
        if wav_path:
            os.unlink(wav_path)

    return jsonify({"text": transcript})


def main():
    cert, key = _ensure_cert()
    log.info("Serving on https://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, ssl_context=(cert, key))


if __name__ == "__main__":
    main()
