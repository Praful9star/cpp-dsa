"""
config.py — Load and validate environment variables.
All secrets come from a .env file or the shell environment — never hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file if present

# ── Required ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── TTS backend: "termux" (free default) or "elevenlabs" (paid, richer voice)
TTS_BACKEND = os.environ.get("TTS_BACKEND", "termux").lower()

# ElevenLabs — only needed when TTS_BACKEND=elevenlabs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # default: "Bella"

# ── Claude model to use ───────────────────────────────────────────────────────
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

# ── Phrase that puts the agent to "sleep" (stops the listen loop) ─────────────
SLEEP_PHRASE = os.environ.get("SLEEP_PHRASE", "go to sleep").lower()
WAKE_PHRASE  = os.environ.get("WAKE_PHRASE",  "hey buddy").lower()

# ── How many recent conversation turns to pass as context ─────────────────────
CONTEXT_WINDOW_TURNS = int(os.environ.get("CONTEXT_WINDOW_TURNS", "10"))

# ── SQLite database path ──────────────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "memory.db")  # relative to project dir

# ── Telegram (Phase 3) — leave blank for now ─────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")


def validate_phase1():
    """Call this on startup to catch missing config early."""
    if not ANTHROPIC_API_KEY:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or export it in your shell."
        )
    if TTS_BACKEND == "elevenlabs" and not ELEVENLABS_API_KEY:
        raise EnvironmentError(
            "TTS_BACKEND=elevenlabs but ELEVENLABS_API_KEY is not set."
        )
