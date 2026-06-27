"""
agent.py — Full Jarvis agent with proactive monitoring and streak tracking.
"""

import subprocess
import sys
import time
import datetime
import sqlite3
import threading

import config
import stt
import tts
import brain
import memory
from tools.procrastination import detect as _is_procrastinating, call_out as _procrastination_callout

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


# ── Streak tracking ───────────────────────────────────────────────────────────

def update_streak() -> int:
    """Increment daily streak and return current count."""
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.execute("""CREATE TABLE IF NOT EXISTS streak (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_date TEXT, count INTEGER DEFAULT 0
        )""")
        row = conn.execute("SELECT last_date, count FROM streak WHERE id=1").fetchone()
        today = str(datetime.date.today())

        if not row:
            conn.execute("INSERT INTO streak VALUES (1, ?, 1)", (today,))
            count = 1
        elif row[0] == today:
            count = row[1]
        elif row[0] == str(datetime.date.today() - datetime.timedelta(days=1)):
            count = row[1] + 1
            conn.execute("UPDATE streak SET last_date=?, count=? WHERE id=1", (today, count))
        else:
            count = 1
            conn.execute("UPDATE streak SET last_date=?, count=1 WHERE id=1", (today,))

        conn.commit()
        conn.close()
        return count
    except Exception:
        return 0


# ── Proactive battery warning (background thread) ─────────────────────────────

_battery_warned = False

def _battery_monitor():
    global _battery_warned
    while True:
        time.sleep(120)  # check every 2 minutes
        try:
            import json
            result = subprocess.run(
                ["termux-battery-status"], capture_output=True, text=True, timeout=5
            )
            data = json.loads(result.stdout)
            pct  = data.get("percentage", 100)
            plugged = data.get("plugged", "").lower()

            if pct <= 20 and "ac" not in plugged and "usb" not in plugged and not _battery_warned:
                _battery_warned = True
                tts.speak(f"Hey Praful, heads up — battery is at {pct} percent. Plug in soon.")
            elif pct > 25:
                _battery_warned = False
        except Exception:
            pass


# ── Emotion detection ─────────────────────────────────────────────────────────

FRUSTRATION_WORDS = {"ugh", "damn", "shit", "stupid", "idiot", "hate", "annoying",
                      "frustrating", "useless", "terrible", "worst", "broke", "crash"}
HAPPY_WORDS       = {"awesome", "great", "nice", "love", "perfect", "amazing",
                      "excellent", "wonderful", "yes", "yay", "cool", "solid"}

def detect_emotion(text: str) -> str:
    words = set(text.lower().split())
    if words & FRUSTRATION_WORDS:
        return "frustrated"
    if words & HAPPY_WORDS:
        return "happy"
    return "neutral"


# ── Auto night silence ────────────────────────────────────────────────────────

def is_night_time() -> bool:
    """Between midnight and 6 AM — go fully silent."""
    hour = datetime.datetime.now().hour
    return 0 <= hour < 6


# ── Termux helpers ────────────────────────────────────────────────────────────

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

def notify(title: str, body: str):
    try:
        subprocess.Popen(
            ["termux-notification", "--title", title, "--content", body, "--id", "1", "--priority", "low"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

def print_status(state: str):
    icons = {"idle": "💤 IDLE", "listening": "🎙  LISTENING",
             "thinking": "🧠 THINKING", "speaking": "🔊 SPEAKING"}
    print(f"\r[{icons.get(state, state.upper())}]   ", end="", flush=True)

GARBAGE = {"", "you", "the", "a", "um", "uh", "hmm", "hm", "ah", ".", "mm", "oh"}

def listen_clean() -> str | None:
    text = stt.listen()
    if not text:
        return None
    cleaned = text.strip().lower()
    if cleaned in GARBAGE or len(cleaned) < 3:
        return None
    return text.strip()


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    acquire_wake_lock()

    streak = update_streak()

    print("\n╔══════════════════════════════════════╗")
    print("║         Buddy — Your Jarvis          ║")
    print("╠══════════════════════════════════════╣")
    print(f"║  Model  : {config.GROQ_MODEL[:28]:<28}║")
    print(f"║  Wake   : \"{config.WAKE_PHRASE}\"              ║")
    print(f"║  Sleep  : \"{config.SLEEP_PHRASE}\"        ║")
    print(f"║  Streak : {streak} day{'s' if streak != 1 else ''}                         ║")
    print("╚══════════════════════════════════════╝\n")

    # Start background battery monitor
    threading.Thread(target=_battery_monitor, daemon=True).start()

    conversation  = memory.load_recent_history()
    facts_context = memory.facts_as_context()
    print(f"  {len(conversation)//2} past turns | {len(memory.get_all_facts())} facts | streak: {streak} days\n")

    notify("Buddy", f"Say '{config.WAKE_PHRASE}' to start | Streak: {streak} days")

    sleeping           = True
    consecutive_errors = 0
    last_emotion       = "neutral"

    while True:
        try:
            # ── Auto night silence ─────────────────────────────────────────────
            if is_night_time() and not sleeping:
                sleeping = True
                tts.speak("It's late. Going quiet — say hey buddy if you really need me.")

            # ── IDLE: wake word only ───────────────────────────────────────────
            if sleeping:
                print_status("idle")
                text = listen_clean()
                if not text:
                    continue
                print(f"\n[Heard] {text}")
                if config.WAKE_PHRASE in text.lower():
                    sleeping = False
                    hour = datetime.datetime.now().hour
                    if hour < 12:
                        greeting = f"Good morning Praful! Day {streak} streak. What's up?"
                    elif hour < 17:
                        greeting = "Hey! I'm here. What do you need?"
                    else:
                        greeting = "Evening! What's going on?"
                    print_status("speaking")
                    notify("Buddy", "Awake")
                    tts.speak(greeting)
                    memory.save_turn("assistant", greeting)
                    conversation.append({"role": "assistant", "content": greeting})
                continue

            # ── AWAKE ──────────────────────────────────────────────────────────
            print_status("listening")
            notify("Buddy", "Listening...")
            text = listen_clean()

            if not text:
                consecutive_errors += 1
                if consecutive_errors >= 4:
                    tts.speak("Still here whenever you're ready.")
                    consecutive_errors = 0
                continue

            consecutive_errors = 0
            print(f"\n[You] {text}")

            # Sleep command
            if config.SLEEP_PHRASE in text.lower():
                sleeping = True
                tts.speak(f"Going idle. Say '{config.WAKE_PHRASE}' when you need me.")
                notify("Buddy", "Idle")
                continue

            # Good night → respond warmly then go idle
            if any(k in text.lower() for k in ["good night", "goodnight", "going to sleep",
                                                 "going to bed", "sleep mode"]):
                reply = brain.chat(conversation, facts_context)
                print(f"\n[Buddy] {reply}")
                memory.save_turn("assistant", reply)
                conversation.append({"role": "assistant", "content": reply})
                tts.speak(reply)
                sleeping = True
                notify("Buddy", "Sleep mode — say 'hey buddy' to wake me")
                continue

            # Procrastination detector — fires passively on lazy language
            if _is_procrastinating(text):
                callout = _procrastination_callout(text)
                print(f"\n[Buddy] {callout}")
                tts.speak(callout)
                memory.save_turn("assistant", callout)
                conversation.append({"role": "assistant", "content": callout})
                continue

            # Emotion detection — adjust response if frustrated
            emotion = detect_emotion(text)
            if emotion == "frustrated" and last_emotion != "frustrated":
                tts.speak("Hey, take a breath. I've got you.")
                time.sleep(0.5)
            last_emotion = emotion

            # Save + extract facts
            memory.save_turn("user", text)
            conversation.append({"role": "user", "content": text})
            memory.maybe_extract_fact(text)

            max_msgs = config.CONTEXT_WINDOW_TURNS * 2
            if len(conversation) > max_msgs:
                conversation = conversation[-max_msgs:]
            facts_context = memory.facts_as_context()

            # Think
            print_status("thinking")
            notify("Buddy", "Thinking...")
            reply = brain.chat(conversation, facts_context)

            # Speak
            print(f"\n[Buddy] {reply}")
            memory.save_turn("assistant", reply)
            conversation.append({"role": "assistant", "content": reply})
            print_status("speaking")
            notify("Buddy", reply[:60])
            tts.speak(reply)

        except KeyboardInterrupt:
            print("\n\nShutting down Buddy...")
            break
        except Exception as e:
            print(f"\n[Error] {e}", file=sys.stderr)
            consecutive_errors += 1
            if consecutive_errors < 4:
                tts.speak("Had a hiccup. Let's keep going.")
            time.sleep(1)

    release_wake_lock()
    notify("Buddy", "Offline")
    print("Buddy offline. Bye!")


if __name__ == "__main__":
    run()
