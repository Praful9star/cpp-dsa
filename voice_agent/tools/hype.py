"""
tools/hype.py — Personal hype engine. Ultra-personalized motivational speeches.

"Hype me up"
"I have an interview in 10 minutes — hype me"
"Pre-game speech"
"I need motivation to study"
"Exam hype"
"""

import datetime
import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

PRAFUL_PROFILE = (
    "18 years old, Lucknow. Built CureCheck.in from scratch. Going to Chandigarh University "
    "for BTech CSE. Learning C++ and DSA. Ambitious, hardworking, building things most 18-year-olds "
    "don't even think about."
)


def generate_hype(context: str = "") -> str:
    hour  = datetime.datetime.now().hour
    tod   = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
    ctx   = f" Specific situation: {context}." if context.strip() else ""
    prompt = (
        f"You are the most legendary hype man in history. Praful needs an ELECTRIC motivational "
        f"speech right now — {tod}.{ctx} About Praful: {PRAFUL_PROFILE}. "
        f"Give him a 4-5 sentence speech that is PERSONAL, SPECIFIC, and makes him feel "
        f"genuinely unstoppable. Reference his real details. No generic clichés. "
        f"Start with something that hits hard. Spoken aloud — no formatting."
    )
    return _ask(prompt, temp=0.95)


def exam_hype() -> str:
    return _ask(
        f"Praful ({PRAFUL_PROFILE}) is about to take an exam. "
        f"3-sentence pre-exam pump-up. Tell him his preparation is locked in, his brain is sharp, "
        f"he's ready. Intense and personal. Go.",
        temp=0.9,
    )


def presentation_hype() -> str:
    return _ask(
        f"Praful ({PRAFUL_PROFILE}) is about to speak or present. "
        f"3-sentence confidence speech. Acknowledge he's built real things, "
        f"remind him the audience is lucky to hear him. Make it calm + powerful.",
        temp=0.9,
    )


def coding_hype() -> str:
    return _ask(
        f"Praful ({PRAFUL_PROFILE}) is about to grind on C++ / DSA. "
        f"Give him a 3-sentence fire speech to get in the zone. "
        f"Reference the fact that every problem he solves makes him sharper for CU and beyond.",
        temp=0.95,
    )


def _ask(prompt: str, temp: float = 0.9) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 220,
        "temperature": temp,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ("Praful, you built CureCheck at 18. You're going to CU for CS. "
                "You already did the hard part. Now go remind them who you are.")
