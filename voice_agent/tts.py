"""
tts.py — Text-to-speech abstraction.

Two backends, swapped via TTS_BACKEND env var:
  "termux"     → free, uses termux-tts-speak (default)
  "elevenlabs" → paid, richer voice via ElevenLabs API

Both expose the same single function: speak(text)
"""

import subprocess
import sys
import config


def speak(text: str) -> None:
    """Say the given text out loud using the configured TTS backend."""
    if not text:
        return

    if config.TTS_BACKEND == "elevenlabs":
        _speak_elevenlabs(text)
    else:
        _speak_termux(text)


# ── Termux backend ────────────────────────────────────────────────────────────

def _speak_termux(text: str) -> None:
    try:
        subprocess.run(
            ["termux-tts-speak", text],
            check=True,
            timeout=120,  # long text can take a while
        )
    except FileNotFoundError:
        print(
            "[TTS error] 'termux-tts-speak' not found.\n"
            "Install Termux:API app and run: pkg install termux-api",
            file=sys.stderr,
        )
    except subprocess.TimeoutExpired:
        print("[TTS] Speech timed out.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"[TTS error] termux-tts-speak failed: {e}", file=sys.stderr)


# ── ElevenLabs backend ────────────────────────────────────────────────────────

def _speak_elevenlabs(text: str) -> None:
    """
    Stream audio from ElevenLabs and pipe it straight to termux-media-player.
    Requires: pip install elevenlabs
    """
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import stream as el_stream
    except ImportError:
        print(
            "[TTS error] 'elevenlabs' package not installed.\n"
            "Run: pip install elevenlabs",
            file=sys.stderr,
        )
        return

    try:
        client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
        audio_stream = client.text_to_speech.stream(
            text=text,
            voice_id=config.ELEVENLABS_VOICE_ID,
            model_id="eleven_turbo_v2",
        )
        # el_stream plays via the default audio output
        el_stream(audio_stream)
    except Exception as e:
        print(f"[TTS error] ElevenLabs failed: {e}", file=sys.stderr)
        print("[TTS] Falling back to termux-tts-speak.", file=sys.stderr)
        _speak_termux(text)
