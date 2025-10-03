#!/usr/bin/env python3
import asyncio
import json
import os
import tempfile
import time
import subprocess
import websockets

# ----------------------------
# Config (can be overridden via env)
# ----------------------------
HOST = os.environ.get("WS_HOST", "0.0.0.0")
PORT = int(os.environ.get("WS_PORT", "8000"))

# Use your local clone path OR the HF repo name.
# Examples:
#   "/Users/delias/learning/AI/back/whisper-turbo"
#   "mlx-community/whisper-turbo"
# MODEL_REPO = os.environ.get("MLX_MODEL_REPO", "mlx-community/whisper-turbo")
MODEL_REPO = "./whisper-turbo"

# How often to run partial inference (seconds)
MIN_INFER_INTERVAL = float(os.environ.get("MIN_INFER_INTERVAL", "1.2"))

# ----------------------------
# MLX Whisper
# ----------------------------
import mlx_whisper  # uses Apple Silicon (MLX) by default

def transcribe_with_mlx(wav_path: str, language: str | None = None) -> str:
    """
    Run MLX Whisper on a WAV file and return plain text.
    """
    result = mlx_whisper.transcribe(
        wav_path,
        path_or_hf_repo=MODEL_REPO,
        language=language,       # None = auto; "en", "es", etc. to bias
        task="transcribe",
        verbose=False,
    )
    return (result.get("text") or "").strip()

# ----------------------------
# WebSocket handler
# ----------------------------
async def handle_conn(ws):
    print("[conn] client connected")
    tmp_dir = tempfile.TemporaryDirectory()
    webm_path = os.path.join(tmp_dir.name, "stream.webm")
    wav_path  = os.path.join(tmp_dir.name, "stream.wav")
    last_text = ""
    language  = None
    last_infer_ts = 0.0

    # create/empty sink file
    open(webm_path, "wb").close()

    try:
        async for message in ws:
            if isinstance(message, bytes):
                # append audio to the growing webm file
                with open(webm_path, "ab") as f:
                    f.write(message)

                # rate-limit partial updates
                now = time.time()
                if now - last_infer_ts >= MIN_INFER_INTERVAL:
                    last_infer_ts = now
                    # convert to 16 kHz mono wav
                    try:
                        subprocess.run(
                            ["ffmpeg", "-loglevel", "quiet", "-y",
                             "-i", webm_path, "-ac", "1", "-ar", "16000",
                             "-f", "wav", wav_path],
                            check=True
                        )
                        text = transcribe_with_mlx(wav_path, language=language)
                        if text and text != last_text:
                            last_text = text
                            await ws.send(json.dumps({"type": "partial", "text": text}))
                    except subprocess.CalledProcessError:
                        # too short/fragmented yet—ignore
                        pass

            else:
                # control messages are JSON
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                mtype = data.get("type")
                if mtype == "start":
                    language = data.get("language")  # "en", "es", or None
                    open(webm_path, "wb").close()
                    last_text = ""
                    await ws.send(json.dumps({"type": "ready"}))
                    print(f"[start] language={language}")

                elif mtype == "stop":
                    print("[stop] finalizing")
                    try:
                        subprocess.run(
                            ["ffmpeg", "-loglevel", "quiet", "-y",
                             "-i", webm_path, "-ac", "1", "-ar", "16000",
                             "-f", "wav", wav_path],
                            check=True
                        )
                        text = transcribe_with_mlx(wav_path, language=language)
                        await ws.send(json.dumps({"type": "final", "text": text}))
                    except subprocess.CalledProcessError:
                        # fall back to last partial
                        await ws.send(json.dumps({"type": "final", "text": last_text}))
                    break
    finally:
        tmp_dir.cleanup()
        print("[conn] client disconnected")

# ----------------------------
# Server bootstrap
# ----------------------------
async def main():
    print(f"[startup] MLX Whisper backend")
    print(f"  - WS: ws://{HOST}:{PORT}")
    print(f"  - Model repo/path: {MODEL_REPO}")
    print(f"  - MIN_INFER_INTERVAL: {MIN_INFER_INTERVAL}s")
    async with websockets.serve(handle_conn, HOST, PORT, max_size=2**25):
        print("[ready] WebSocket server listening")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    # unbuffered output so you see logs immediately
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    asyncio.run(main())
