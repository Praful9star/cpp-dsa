"""
stt.py — Speech-to-text via Termux:API.

termux-speech-to-text listens on the mic and writes the recognized text to
stdout. We capture that and return it as a plain Python string.

Returns None if nothing was heard or the command failed.
"""

import subprocess
import sys


def listen() -> str | None:
    """
    Blocks until the user stops speaking, then returns the recognized text.
    Returns None on error or if nothing was captured.
    """
    try:
        result = subprocess.run(
            ["termux-speech-to-text"],
            capture_output=True,
            text=True,
            timeout=30,  # give up after 30 s of silence
        )

        text = result.stdout.strip()

        if result.returncode != 0 or not text:
            # Log stderr for debugging without crashing
            if result.stderr:
                print(f"[STT warning] {result.stderr.strip()}", file=sys.stderr)
            return None

        return text

    except FileNotFoundError:
        print(
            "[STT error] 'termux-speech-to-text' not found.\n"
            "Install Termux:API app and run: pkg install termux-api",
            file=sys.stderr,
        )
        return None

    except subprocess.TimeoutExpired:
        print("[STT] Timed out waiting for speech.", file=sys.stderr)
        return None

    except Exception as e:
        print(f"[STT error] {e}", file=sys.stderr)
        return None
