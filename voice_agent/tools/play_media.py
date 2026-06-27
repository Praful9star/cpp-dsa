"""
tools/play_media.py — Play YouTube audio or video via yt-dlp + termux-media-player.

No API key needed. Works with search queries or direct YouTube URLs.

Install: pip install yt-dlp
         (yt-dlp is already a Python package — no separate binary needed)

Trigger examples:
  "play Believer by Imagine Dragons"
  "play some lo-fi music"
  "play https://youtube.com/watch?v=..."
"""

import subprocess
import sys
import threading
import yt_dlp

# Track the currently playing process so we can stop it
_current_process: subprocess.Popen | None = None
_current_thread: threading.Thread | None = None


def play_youtube(query: str) -> str:
    """
    Search YouTube for `query` (or use it as a direct URL),
    extract the audio stream URL, and play it via termux-media-player.
    Returns a status string for the LLM.
    """
    global _current_process, _current_thread

    # Stop any currently playing audio first
    stop_media()

    # If it looks like a URL, use it directly; otherwise search YouTube
    if query.startswith("http://") or query.startswith("https://"):
        search_query = query
    else:
        search_query = f"ytsearch1:{query}"

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

            # If it was a search, grab the first result
            if "entries" in info:
                info = info["entries"][0]

            stream_url = info.get("url")
            title      = info.get("title", "Unknown")

            if not stream_url:
                return "Couldn't find a playable stream for that."

        # Play in background thread so the agent can keep listening
        def _play():
            global _current_process
            try:
                _current_process = subprocess.Popen(
                    ["termux-media-player", "play", stream_url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                _current_process.wait()
            except FileNotFoundError:
                print("[Media] termux-media-player not found. Install termux-api.", file=sys.stderr)
            except Exception as e:
                print(f"[Media] Playback error: {e}", file=sys.stderr)

        _current_thread = threading.Thread(target=_play, daemon=True)
        _current_thread.start()

        return f"Playing: {title}"

    except yt_dlp.utils.DownloadError as e:
        return f"Couldn't find '{query}' on YouTube: {e}"
    except Exception as e:
        return f"Media playback failed: {e}"


def stop_media() -> str:
    """Stop whatever is currently playing."""
    global _current_process
    try:
        subprocess.run(
            ["termux-media-player", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        pass
    if _current_process:
        try:
            _current_process.terminate()
        except Exception:
            pass
        _current_process = None
    return "Stopped."
