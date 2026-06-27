"""
config.py — Load and validate environment variables.
All secrets come from a .env file or the shell environment — never hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file if present

# ── Required ─────────────────────────────────────────────────────────────────
# Free Groq API key — get one at https://console.groq.com
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── Groq model to use (free) ─────────────────────────────────────────────────
# llama-3.3-70b-versatile  → smartest, still free
# llama-3.1-8b-instant     → fastest, good for quick replies
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── TTS backend: "termux" (free default) or "elevenlabs" (paid, richer voice)
TTS_BACKEND = os.environ.get("TTS_BACKEND", "termux").lower()

# ElevenLabs — only needed when TTS_BACKEND=elevenlabs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # default: "Bella"

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
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set.\n"
            "Get a free key at https://console.groq.com and add it to your .env file."
        )
    if TTS_BACKEND == "elevenlabs" and not ELEVENLABS_API_KEY:
        raise EnvironmentError(
            "TTS_BACKEND=elevenlabs but ELEVENLABS_API_KEY is not set."
        )
