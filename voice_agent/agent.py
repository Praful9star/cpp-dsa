"""
agent.py — Phase 4: Wake word, sound cues, robust error handling.

Wake word: say "hey buddy" → agent wakes and listens for your command.
Sleep:     say "go to sleep" → goes back to idle (wake word only mode).
Quit:      Ctrl+C

Flow when AWAKE:
  beep → listen → think → speak → beep → listen → ...

Flow when SLEEPING (idle):
  silently listen for wake word only → wake up on "hey buddy"
"""

import subprocess
import sys
import time
import os

import config
import stt
import tts
import brain
import memory

config.validate_phase1()

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


# ── Audio cues ────────────────────────────────────────────────────────────────
# Short beep files stored in ~/sounds/. We generate them once using termux-tts
# as a workaround — or just use a tiny subprocess bell.

def beep_done():
    """Terminal bell after agent finishes speaking."""
    print("\a", end="", flush=True)


# ── Termux helpers ────────────────────────────────────────────────────────────

def acquire_wake_lock():
    try:
        subprocess.Popen(["termux-wake-lock"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def release_wake_lock():
    try:
        subprocess.run(["termux-wake-unlock"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def notify(title: str, body: str):
    try:
        subprocess.Popen(
            ["termux-notification", "--title", title,
             "--content", body, "--id", "1", "--priority", "low"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


def print_status(state: str):
    icons = {
        "idle":     "💤 IDLE     ",
        "listening": "🎙  LISTENING",
        "thinking":  "🧠 THINKING ",
        "speaking":  "🔊 SPEAKING ",
    }
    print(f"\r[{icons.get(state, state.upper())}]  ", end="", flush=True)


# ── STT with garbage filtering ────────────────────────────────────────────────
# Sometimes STT returns noise or very short garbage strings.

GARBAGE = {"", "you", "the", "a", "um", "uh", "hmm", "hm", "ah", "."}

def listen_clean() -> str | None:
    """Listen and return text, or None if nothing useful was heard."""
    text = stt.listen()
    if not text:
        return None
    cleaned = text.strip().lower()
    if cleaned in GARBAGE or len(cleaned) < 2:
        return None
    return text.strip()


# ── Check internet before making API calls ────────────────────────────────────

def has_internet() -> bool:
    try:
        requests_mod = __import__("requests")
        requests_mod.get("https://api.groq.com", timeout=4)
        return True
    except Exception:
        return False


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    acquire_wake_lock()

    print("\n╔══════════════════════════════╗")
    print("║   Voice Agent — Phase 4      ║")
    print("╠══════════════════════════════╣")
    print(f"║  Model : {config.GROQ_MODEL[:22]:<22}║")
    print(f"║  Wake  : \"{config.WAKE_PHRASE}\"        ║")
    print(f"║  Sleep : \"{config.SLEEP_PHRASE}\"   ║")
    print(f"║  Quit  : Ctrl+C              ║")
    print("╚══════════════════════════════╝\n")

    conversation   = memory.load_recent_history()
    facts_context  = memory.facts_as_context()

    print(f"  Loaded {len(conversation)//2} past turns | {len(memory.get_all_facts())} facts known\n")

    notify("Agent", f"Say '{config.WAKE_PHRASE}' to start")

    sleeping = True   # start in idle/wake-word mode
    consecutive_errors = 0

    while True:
        try:
            # ── IDLE: listen only for wake word ───────────────────────────────
            if sleeping:
                print_status("idle")
                text = listen_clean()
                if not text:
                    continue

                print(f"\n[Heard] {text}")

                if config.WAKE_PHRASE in text.lower():
                    sleeping = False
                    wake_reply = "Hey, I'm here! What's up?"
                    print_status("speaking")
                    notify("Agent", "Listening...")
                    tts.speak(wake_reply)
                    memory.save_turn("assistant", wake_reply)
                    conversation.append({"role": "assistant", "content": wake_reply})
                continue

            # ── AWAKE: full listen → think → speak loop ───────────────────────
            print_status("listening")
            notify("Agent", "Listening...")

            text = listen_clean()

            if not text:
                # Heard nothing useful — stay awake but prompt gently
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    tts.speak("I didn't catch that. I'm still here when you're ready.")
                    consecutive_errors = 0
                continue

            consecutive_errors = 0
            print(f"\n[You] {text}")

            # Sleep command
            if config.SLEEP_PHRASE in text.lower():
                sleeping = True
                farewell = f"Got it, going idle. Say '{config.WAKE_PHRASE}' when you need me."
                print_status("speaking")
                tts.speak(farewell)
                memory.save_turn("assistant", farewell)
                conversation.append({"role": "assistant", "content": farewell})
                notify("Agent", f"Idle — say '{config.WAKE_PHRASE}'")
                continue

            # Save user turn + extract facts
            memory.save_turn("user", text)
            conversation.append({"role": "user", "content": text})
            memory.maybe_extract_fact(text)

            # Trim context window
            max_msgs = config.CONTEXT_WINDOW_TURNS * 2
            if len(conversation) > max_msgs:
                conversation = conversation[-max_msgs:]

            facts_context = memory.facts_as_context()

            # ── Think ─────────────────────────────────────────────────────────
            print_status("thinking")
            notify("Agent", "Thinking...")

            reply = brain.chat(conversation, facts_context)

            # ── Speak ─────────────────────────────────────────────────────────
            print(f"\n[Agent] {reply}")
            memory.save_turn("assistant", reply)
            conversation.append({"role": "assistant", "content": reply})

            print_status("speaking")
            notify("Agent", reply[:60])
            tts.speak(reply)
            beep_done()

        except KeyboardInterrupt:
            print("\n\nStopping agent...")
            break

        except Exception as e:
            print(f"\n[Error] {e}", file=sys.stderr)
            consecutive_errors += 1
            if consecutive_errors < 4:
                tts.speak("Oops, something went wrong. Let's try again.")
            time.sleep(1)

    release_wake_lock()
    notify("Agent", "Stopped")
    print("Agent stopped. Bye!")


if __name__ == "__main__":
    run()
