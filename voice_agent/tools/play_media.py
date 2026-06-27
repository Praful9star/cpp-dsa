"""
tools/play_media.py — Play YouTube audio by downloading to a temp file first,
then playing via termux-media-player.

yt-dlp is installed as python-yt-dlp via pkg — call it as a Python module.
"""

import subprocess
import sys
import threading
import os

AUDIO_FILE = "/data/data/com.termux/files/home/audio_temp.mp3"

_current_player: subprocess.Popen | None = None


def play_youtube(query: str) -> str:
    global _current_player

    stop_media()  # stop anything already playing

    if query.startswith("http://") or query.startswith("https://"):
        search_arg = query
    else:
        search_arg = f"ytsearch1:{query}"

    # Remove old temp file
    try:
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)
    except Exception:
        pass

    try:
        # Download audio to temp file using yt-dlp as a Python module
        result = subprocess.run(
            [
                "python", "-m", "yt_dlp",
                "--no-playlist",
                "-x",                          # extract audio only
                "--audio-format", "mp3",
                "--audio-quality", "5",        # medium quality, faster download
                "-o", AUDIO_FILE,
                "--no-part",
                "--quiet",
                "--no-warnings",
                search_arg,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # yt-dlp may rename file — find what was actually saved
        audio_path = AUDIO_FILE
        if not os.path.exists(audio_path):
            # Try without extension
            base = AUDIO_FILE.replace(".mp3", "")
            for ext in [".mp3", ".m4a", ".opus", ".webm", ".ogg"]:
                if os.path.exists(base + ext):
                    audio_path = base + ext
                    break

        if not os.path.exists(audio_path):
            return f"Couldn't download '{query}'. Try again?"

        # Get song title from yt-dlp output
        title = query  # fallback
        if result.stdout:
            for line in result.stdout.splitlines():
                if "Destination" in line or ".mp3" in line:
                    title = line.split("/")[-1].replace(".mp3", "").strip()
                    break

        # Play the downloaded file in background
        def _play():
            global _current_player
            try:
                _current_player = subprocess.Popen(
                    ["termux-media-player", "play", audio_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _current_player.wait()
            except FileNotFoundError:
                print("[Media] termux-media-player not found.", file=sys.stderr)
            except Exception as e:
                print(f"[Media] Playback error: {e}", file=sys.stderr)

        threading.Thread(target=_play, daemon=True).start()
        return f"Playing: {query}"

    except subprocess.TimeoutExpired:
        return "Download timed out. Check your internet and try again."
    except Exception as e:
        return f"Media error: {e}"


def stop_media() -> str:
    global _current_player
    try:
        subprocess.run(
            ["termux-media-player", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        pass
    if _current_player:
        try:
            _current_player.terminate()
        except Exception:
            pass
        _current_player = None
    return "Stopped."
