"""
agent.py — Phase 2: Voice loop with persistent SQLite memory.

Each session:
  - Loads past conversation history from DB
  - Loads long-term facts about Praful
  - After each user message, auto-extracts any new facts worth saving
  - Saves every turn to DB so nothing is forgotten between sessions
"""

import subprocess
import sys
import time

import config
import stt
import tts
import brain
import memory

config.validate_phase1()

# ── One-time DB setup + seed Praful's facts ───────────────────────────────────
memory.init_db()

PRAFUL_FACTS = [
    "User's name is Praful.",
    "Praful is 18 years old.",
    "Praful lives in Lucknow, India.",
    "Praful is going to Chandigarh University in July for B.Tech CSE (core).",
    "Praful built CureCheck.in — his own web product.",
    "Praful is learning C++ and interested in DSA and software development.",
]
memory.seed_facts(PRAFUL_FACTS)


# ── Helpers ───────────────────────────────────────────────────────────────────

def acquire_wake_lock():
    try:
        subprocess.Popen(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def release_wake_lock():
    try:
        subprocess.run(["termux-wake-unlock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def notify(title: str, message: str):
    try:
        subprocess.Popen(
            ["termux-notification", "--title", title, "--content", message, "--id", "1"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def print_status(state: str):
    labels = {
        "listening": "🎙  LISTENING",
        "thinking":  "🧠  THINKING ",
        "speaking":  "🔊  SPEAKING ",
        "sleeping":  "💤  SLEEPING ",
    }
    print(f"\r[{labels.get(state, state.upper())}]  ", end="", flush=True)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    acquire_wake_lock()
    print("\n=== Voice Agent — Phase 2 (Memory) ===")
    print(f"  Model  : {config.GROQ_MODEL}")
    print(f"  TTS    : {config.TTS_BACKEND}")
    print(f"  DB     : {config.DB_PATH}")
    print(f"  Sleep  : say \"{config.SLEEP_PHRASE}\"")
    print(f"  Quit   : Ctrl+C\n")

    # Load history from last session
    conversation = memory.load_recent_history()
    facts_context = memory.facts_as_context()

    print(f"  Loaded {len(conversation)//2} past turns from memory.")
    print(f"  Facts known: {len(memory.get_all_facts())}\n")

    # Greeting — different if we have history vs fresh start
    if conversation:
        greeting = "Hey Praful, I'm back! What's up?"
    else:
        greeting = "Hey Praful! I'm up and listening. What's on your mind?"

    print_status("speaking")
    notify("Agent", "Ready")
    tts.speak(greeting)
    memory.save_turn("assistant", greeting)
    conversation.append({"role": "assistant", "content": greeting})

    sleeping = False

    while True:
        try:
            if sleeping:
                print_status("sleeping")
                time.sleep(2)
                text = stt.listen()
                if not text:
                    continue
                print(f"\n[You] {text}")
                if config.WAKE_PHRASE in text.lower():
                    sleeping = False
                    reply = "I'm back! What do you need?"
                    tts.speak(reply)
                    memory.save_turn("assistant", reply)
                    conversation.append({"role": "assistant", "content": reply})
                continue

            # ── Listen ────────────────────────────────────────────────────────
            print_status("listening")
            text = stt.listen()

            if not text:
                continue

            print(f"\n[You] {text}")

            # Sleep command
            if config.SLEEP_PHRASE in text.lower():
                sleeping = True
                farewell = "Alright, going to sleep. Say 'hey buddy' when you need me."
                print_status("speaking")
                tts.speak(farewell)
                memory.save_turn("assistant", farewell)
                conversation.append({"role": "assistant", "content": farewell})
                continue

            # Save user turn
            memory.save_turn("user", text)
            conversation.append({"role": "user", "content": text})

            # Auto-extract facts in background (non-blocking feel)
            memory.maybe_extract_fact(text)

            # Trim in-memory context window
            max_msgs = config.CONTEXT_WINDOW_TURNS * 2
            if len(conversation) > max_msgs:
                conversation = conversation[-max_msgs:]

            # Refresh facts context (might have new facts from this turn)
            facts_context = memory.facts_as_context()

            # ── Think ─────────────────────────────────────────────────────────
            print_status("thinking")
            notify("Agent", "Thinking...")
            reply = brain.chat(conversation, facts_context)

            print(f"\n[Agent] {reply}")

            # Save assistant turn
            memory.save_turn("assistant", reply)
            conversation.append({"role": "assistant", "content": reply})

            # ── Speak ─────────────────────────────────────────────────────────
            print_status("speaking")
            notify("Agent", "Speaking...")
            tts.speak(reply)

        except KeyboardInterrupt:
            print("\n\nCaught Ctrl+C — shutting down.")
            break

        except Exception as e:
            print(f"\n[Loop error] {e}", file=sys.stderr)
            tts.speak("Oops, something went wrong. Let's try again.")
            time.sleep(1)

    release_wake_lock()
    print("Agent stopped. Goodbye!")


if __name__ == "__main__":
    run()
