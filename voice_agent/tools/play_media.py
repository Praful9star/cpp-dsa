"""
tools/play_media.py — Play YouTube audio via yt-dlp (installed via pkg) +
                      termux-media-player.

Install once in Termux:  pkg install yt-dlp

Trigger examples:
  "play Believer by Imagine Dragons"
  "play some lo-fi music"
  "stop the music"
"""

import subprocess
import sys
import threading
import json

_current_player: subprocess.Popen | None = None


def play_youtube(query: str) -> str:
    """Search YouTube for query, get stream URL, play via termux-media-player."""
    global _current_player

    stop_media()  # stop anything already playing

    # If it's a URL use directly, otherwise search YouTube
    if query.startswith("http://") or query.startswith("https://"):
        search_arg = query
    else:
        search_arg = f"ytsearch1:{query}"

    try:
        # Use yt-dlp binary (installed via pkg install yt-dlp)
        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-json",
                "--no-playlist",
                "-f", "bestaudio/best",
                search_arg,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return f"Couldn't find '{query}' on YouTube."

        info = json.loads(result.stdout.strip().splitlines()[0])
        title      = info.get("title", "Unknown")
        stream_url = info.get("url") or info.get("webpage_url")

        if not stream_url:
            return "Found the video but couldn't get a playable link."

        # Play in background so agent keeps listening
        def _play():
            global _current_player
            try:
                _current_player = subprocess.Popen(
                    ["termux-media-player", "play", stream_url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _current_player.wait()
            except FileNotFoundError:
                print("[Media] termux-media-player not found.", file=sys.stderr)
            except Exception as e:
                print(f"[Media] Playback error: {e}", file=sys.stderr)

        threading.Thread(target=_play, daemon=True).start()
        return f"Playing: {title}"

    except FileNotFoundError:
        return "yt-dlp is not installed. Run: pkg install yt-dlp"
    except subprocess.TimeoutExpired:
        return "Took too long to fetch that. Try again?"
    except Exception as e:
        return f"Media error: {e}"


def stop_media() -> str:
    """Stop currently playing audio."""
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
