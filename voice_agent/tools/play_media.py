"""
tools/play_media.py — Music player with queue, autoplay, skip, and proper stop.

Commands supported (detected in brain.py):
  play <query>   → search + build queue of 10 songs, start playing
  next / skip    → skip to next song in queue
  previous       → go back one song
  stop           → stop everything and clear queue
"""

import subprocess
import sys
import threading
import os
import json
import time

AUDIO_FILE   = "/data/data/com.termux/files/home/.agent_audio"
QUEUE_SIZE   = 10   # how many songs to fetch per play request

# ── Shared state ──────────────────────────────────────────────────────────────
_queue:        list[dict] = []   # list of {title, url_or_search}
_queue_index:  int        = 0
_player_proc:  subprocess.Popen | None = None
_download_proc: subprocess.Popen | None = None
_stop_event:   threading.Event = threading.Event()
_lock:         threading.Lock  = threading.Lock()


# ── Public API ────────────────────────────────────────────────────────────────

def play_youtube(query: str) -> str:
    """Search for query, build a queue of similar songs, start playing."""
    global _queue, _queue_index

    _stop_all()

    print(f"\n[Music] Building queue for: {query}")

    # Search for multiple results at once
    search_arg = query if query.startswith("http") else f"ytsearch{QUEUE_SIZE}:{query}"

    try:
        result = subprocess.run(
            [
                "python", "-m", "yt_dlp",
                "--dump-json",
                "--flat-playlist",
                "--no-playlist",
                "--quiet",
                "--no-warnings",
                search_arg,
            ],
            capture_output=True, text=True, timeout=30,
        )

        entries = []
        for line in result.stdout.strip().splitlines():
            try:
                info = json.loads(line)
                title = info.get("title") or info.get("id") or query
                url   = info.get("url") or info.get("webpage_url") or info.get("id")
                if url:
                    entries.append({"title": title, "url": url})
            except Exception:
                continue

        if not entries:
            return f"Couldn't find songs for '{query}'. Try a different search."

        with _lock:
            _queue       = entries
            _queue_index = 0
            _stop_event.clear()

        threading.Thread(target=_play_loop, daemon=True).start()
        first = entries[0]["title"]
        return f"Playing '{first}' and {len(entries)-1} more like it."

    except subprocess.TimeoutExpired:
        return "Took too long to search. Check your internet."
    except Exception as e:
        return f"Music error: {e}"


def skip_next() -> str:
    """Skip to the next song in the queue."""
    global _queue_index
    with _lock:
        if not _queue:
            return "Nothing is queued up."
        _queue_index = (_queue_index + 1) % len(_queue)
        title = _queue[_queue_index]["title"]
    _kill_player()
    return f"Skipping to: {title}"


def skip_prev() -> str:
    """Go back to the previous song."""
    global _queue_index
    with _lock:
        if not _queue:
            return "Nothing is queued up."
        _queue_index = (_queue_index - 1) % len(_queue)
        title = _queue[_queue_index]["title"]
    _kill_player()
    return f"Going back to: {title}"


def stop_media() -> str:
    """Stop playback and clear the queue."""
    _stop_all()
    return "Music stopped."


def now_playing() -> str:
    with _lock:
        if not _queue:
            return "Nothing is playing right now."
        title = _queue[_queue_index]["title"]
        return f"Playing: {title} (song {_queue_index+1} of {len(_queue)})"


# ── Internal playback loop ────────────────────────────────────────────────────

def _play_loop():
    """Runs in a background thread. Downloads and plays songs from the queue."""
    global _queue_index, _player_proc, _download_proc

    while True:
        with _lock:
            if _stop_event.is_set() or not _queue:
                break
            entry = _queue[_queue_index]

        title = entry["title"]
        url   = entry["url"]
        print(f"\n[Music] Downloading: {title}")

        # If url looks like a YouTube ID or search, wrap it
        if not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={url}"

        audio_path = AUDIO_FILE + ".mp3"

        # Remove old file
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

        # Download
        dl = subprocess.run(
            [
                "python", "-m", "yt_dlp",
                "-x", "--audio-format", "mp3",
                "--audio-quality", "6",
                "-o", audio_path,
                "--no-part", "--quiet", "--no-warnings",
                url,
            ],
            capture_output=True, text=True, timeout=90,
        )

        if _stop_event.is_set():
            break

        # Find downloaded file (yt-dlp may rename)
        found = None
        for ext in [".mp3", ".m4a", ".opus", ".webm", ".ogg"]:
            candidate = AUDIO_FILE + ext
            if os.path.exists(candidate):
                found = candidate
                break

        if not found:
            print(f"[Music] Download failed for: {title}")
        else:
            print(f"[Music] Playing: {title}")
            try:
                _player_proc = subprocess.Popen(
                    ["termux-media-player", "play", found],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                # Wait for song to finish OR for skip/stop signal
                while _player_proc.poll() is None:
                    if _stop_event.is_set():
                        _player_proc.terminate()
                        return
                    # Check if index changed (skip/prev happened)
                    with _lock:
                        current_idx = _queue_index
                    if found != AUDIO_FILE + ".mp3":
                        break
                    time.sleep(0.5)
            except Exception as e:
                print(f"[Music] Player error: {e}", file=sys.stderr)

        if _stop_event.is_set():
            break

        # Auto-advance to next song
        with _lock:
            _queue_index = (_queue_index + 1) % len(_queue)
            if _queue_index == 0:
                # Looped back — stop after one full cycle
                _stop_event.set()
                break

    print("\n[Music] Queue finished.")


def _kill_player():
    """Kill the current player process so _play_loop picks up the new index."""
    global _player_proc
    try:
        subprocess.run(["termux-media-player", "stop"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
    except Exception:
        pass
    if _player_proc:
        try:
            _player_proc.terminate()
        except Exception:
            pass
        _player_proc = None


def _stop_all():
    """Stop everything and clear state."""
    global _queue, _queue_index, _player_proc
    _stop_event.set()
    _kill_player()
    with _lock:
        _queue       = []
        _queue_index = 0
    time.sleep(0.3)
    _stop_event.clear()
