"""
tools/chaos_daemon.py — The Chaos Daemon: random unpredictable interventions.

Runs as a background thread. Randomly, at intervals of 20-90 minutes,
fires one of many wild interruptions:
- Random philosophical question
- Sudden life fact that hits different
- "Did you know" with obscure knowledge
- Random challenge (do 10 pushups, drink water, close your eyes for 30 sec)
- Sudden motivational ambush
- Plot twist suggestion for Praful's life
- Reality check
- Random compliment that's weirdly specific

"Start chaos mode" / "Enable chaos"
"Stop chaos" / "Disable chaos"
"Chaos status"
"""

import threading
import time
import random
import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_running = False
_thread: threading.Thread | None = None

CHAOS_TYPES = [
    "philosophical_question",
    "obscure_fact",
    "sudden_challenge",
    "reality_check",
    "plot_twist",
    "random_compliment",
    "life_reminder",
    "pattern_interrupt",
]

CHALLENGES = [
    "Drop and do 15 pushups. Right now. I'm waiting.",
    "Drink a full glass of water. Now. Your brain runs on it.",
    "Close your eyes for 30 seconds and breathe. Do it.",
    "Write down one thing you're grateful for in the next 30 seconds.",
    "Text someone you haven't talked to in a while. Right now.",
    "Stand up and stretch for 60 seconds. Your posture is probably terrible.",
    "Look away from all screens for 2 minutes. Nature, ceiling, anything.",
    "Name 3 things you can see, 2 you can hear, 1 you can feel. Grounding check.",
]

FACTS = [
    "Your brain generates about 70,000 thoughts per day. Most of them are the same as yesterday.",
    "The inventor of the frisbee was turned into a frisbee when he died. His ashes were molded into one.",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
    "Every atom in your body was forged in a star that exploded billions of years ago.",
    "You share 50% of your DNA with a banana. Think about that.",
    "The average person walks 100,000 miles in their lifetime — more than 4 times around Earth.",
    "Wombats produce cube-shaped poop. They're the only animal that does this.",
    "A day on Venus is longer than a year on Venus.",
    "The universe is not only stranger than we suppose, but stranger than we can suppose.",
    "You are living in the most technologically advanced moment in all of human history, right now.",
]

PLOT_TWISTS = [
    "What if the thing you're avoiding is actually your destiny calling?",
    "Plot twist: the 'obstacle' in your way is actually the path.",
    "What if you're not behind in life — what if everyone else is just rushing for no reason?",
    "Alternate timeline: you made the scary decision. What happens next?",
    "The version of you that exists in 5 years is watching right now. What do they need you to do today?",
    "What if your biggest 'weakness' is actually your most interesting quality?",
]

REALITY_CHECKS = [
    "Most of the things you're worried about won't matter in 5 years. Seriously.",
    "You're 18 and already built a web product. Most people never build anything. Remember that.",
    "The comfort zone feels safe but nothing grows there.",
    "Success is just consistent small actions done over a long period. That's it.",
    "The people you compare yourself to also compare themselves to someone else.",
]


def start_chaos() -> str:
    global _running, _thread
    if _running:
        return "Chaos is already active. Brace yourself."
    _running = True
    _thread = threading.Thread(target=_daemon_loop, daemon=True)
    _thread.start()
    return "Chaos daemon activated. Expect the unexpected."


def stop_chaos() -> str:
    global _running
    _running = False
    return "Chaos daemon stopped. Back to predictability."


def chaos_status() -> str:
    return f"Chaos daemon: {'active — anything can happen' if _running else 'inactive'}."


def fire_random() -> str:
    """Manually trigger one random chaos event."""
    return _generate_event()


def _daemon_loop():
    while _running:
        delay = random.randint(20 * 60, 90 * 60)  # 20-90 minutes
        time.sleep(delay)
        if not _running:
            break
        try:
            import tts
            event = _generate_event()
            print(f"\n[🌀 CHAOS] {event}")
            tts.speak(event)
        except Exception:
            pass


def _generate_event() -> str:
    chaos_type = random.choice(CHAOS_TYPES)

    if chaos_type == "sudden_challenge":
        return "⚡ CHAOS INTERRUPT: " + random.choice(CHALLENGES)

    if chaos_type == "obscure_fact":
        return "Random fact that just hit me: " + random.choice(FACTS)

    if chaos_type == "plot_twist":
        return random.choice(PLOT_TWISTS)

    if chaos_type == "reality_check":
        return random.choice(REALITY_CHECKS)

    # Use Groq for dynamic events
    prompts = {
        "philosophical_question": (
            "Ask Praful (18, Lucknow, CS student) one deeply uncomfortable philosophical question "
            "he's never been asked before. Max 1 sentence. Make it hit."
        ),
        "random_compliment": (
            "Give Praful a weirdly specific, genuine compliment about something unusual. "
            "Not generic — specific to who he is. 1-2 sentences."
        ),
        "life_reminder": (
            "Give Praful one unexpected life reminder — something people forget but really matters. "
            "Not motivational poster stuff. Real and specific. 1-2 sentences."
        ),
        "pattern_interrupt": (
            "Praful is probably in a routine right now. Give him a 1-sentence pattern interrupt "
            "— something that breaks his autopilot thinking and makes him see something differently."
        ),
    }
    prompt = prompts.get(chaos_type, prompts["philosophical_question"])
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": config.GROQ_MODEL,
               "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 100, "temperature": 0.98}
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return random.choice(REALITY_CHECKS)
