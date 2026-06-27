"""
agent.py — Phase 1: The main voice loop.

Flow each turn:
  1. Listen  (termux-speech-to-text)
  2. Think   (Claude API via brain.py)
  3. Speak   (termux-tts-speak or ElevenLabs via tts.py)
  4. Repeat  (unless the user says the sleep phrase)

Run with:
    python agent.py

Exit:  say "go to sleep" (configurable in .env via SLEEP_PHRASE)
       or press Ctrl+C

Uses termux-wake-lock so Android doesn't kill the process in the background.
"""

import subprocess
import sys
import time

import config
import stt
import tts
import brain

config.validate_phase1()  # crash early if API key is missing


# ── Helpers ───────────────────────────────────────────────────────────────────

def acquire_wake_lock():
    """Keep Android from suspending Termux while the agent is running."""
    try:
        subprocess.Popen(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass  # termux-wake-lock not installed — soft fail, not critical


def release_wake_lock():
    try:
        subprocess.run(["termux-wake-unlock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def notify(title: str, message: str):
    """Optional visual status via termux-notification (non-critical)."""
    try:
        subprocess.Popen(
            ["termux-notification", "--title", title, "--content", message, "--id", "1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def print_status(state: str):
    """Print a simple status line so you can see what's happening in the terminal."""
    symbols = {"listening": "🎙 ", "thinking": "🧠 ", "speaking": "🔊 ", "sleeping": "💤 "}
    sym = symbols.get(state, "  ")
    print(f"\r[{sym}{state.upper()}]  ", end="", flush=True)


# ── Conversation history ──────────────────────────────────────────────────────
# In Phase 1 this lives only in memory (lost on exit).
# Phase 2 will persist it to SQLite.

conversation: list[dict] = []


def add_turn(role: str, content: str):
    """Append a message and trim to the configured rolling window."""
    conversation.append({"role": role, "content": content})

    # Keep only the last N turns (N pairs = 2*N messages).
    # This prevents the context from growing forever.
    max_messages = config.CONTEXT_WINDOW_TURNS * 2
    if len(conversation) > max_messages:
        del conversation[: len(conversation) - max_messages]


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    acquire_wake_lock()
    print("\n=== Voice Agent — Phase 1 ===")
    print(f"  Model   : {config.CLAUDE_MODEL}")
    print(f"  TTS     : {config.TTS_BACKEND}")
    print(f"  Sleep   : say \"{config.SLEEP_PHRASE}\"")
    print(f"  Quit    : Ctrl+C\n")

    # Greet the user on startup
    greeting = "Hey! I'm up and listening. What's on your mind?"
    print_status("speaking")
    notify("Agent", "Ready")
    tts.speak(greeting)
    add_turn("assistant", greeting)

    sleeping = False

    while True:
        try:
            if sleeping:
                # ── Sleeping mode: just wait quietly ──────────────────────────
                print_status("sleeping")
                notify("Agent", "Sleeping — say the wake phrase to resume")
                time.sleep(2)

                # We still need to listen so we can detect the wake phrase.
                # termux-speech-to-text will block until it hears something.
                text = stt.listen()
                if not text:
                    continue

                print(f"\n[You said] {text}")

                if config.WAKE_PHRASE in text.lower():
                    sleeping = False
                    tts.speak("I'm back! What do you need?")
                    add_turn("assistant", "I'm back! What do you need?")
                continue

            # ── Awake mode ────────────────────────────────────────────────────
            print_status("listening")
            text = stt.listen()

            if not text:
                # Nothing heard — try again
                continue

            print(f"\n[You said] {text}")

            # Check for sleep command
            if config.SLEEP_PHRASE in text.lower():
                sleeping = True
                farewell = "Alright, I'll take a nap. Say 'hey buddy' when you need me."
                print_status("speaking")
                tts.speak(farewell)
                add_turn("assistant", farewell)
                continue

            # ── Ask Claude ────────────────────────────────────────────────────
            add_turn("user", text)
            print_status("thinking")
            notify("Agent", "Thinking...")

            reply = brain.chat(conversation)
            print(f"\n[Agent]    {reply}")

            add_turn("assistant", reply)

            print_status("speaking")
            notify("Agent", "Speaking...")
            tts.speak(reply)

        except KeyboardInterrupt:
            print("\n\nCaught Ctrl+C — shutting down.")
            break

        except Exception as e:
            # Catch-all so a random error doesn't kill the whole loop
            print(f"\n[Loop error] {e}", file=sys.stderr)
            tts.speak("Oops, something went wrong on my end. Let's try again.")
            time.sleep(1)

    release_wake_lock()
    print("Agent stopped. Goodbye!")


if __name__ == "__main__":
    run()
