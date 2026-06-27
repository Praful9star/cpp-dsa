"""
tools/wingman.py — AI Wingman: craft perfect messages for any situation.

"Wingman: help me reply to Rohit who said 'are you coming tomorrow'"
"Help me text my professor about the assignment"
"How do I apologize to my friend"
"Perfect reply to: she said I'm weird"
"Draft a message to my crush"
"""

import re
import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def craft_reply(query: str) -> str:
    t = query.lower()

    if any(k in t for k in ["professor", "teacher", "sir", "ma'am", "madam", "faculty", "college"]):
        tone = "formal, polite and professional"
        vibe = "he's a student making a respectful request"
    elif any(k in t for k in ["crush", "girl", "boy", "like her", "like him", "dm"]):
        tone = "casual, confident and naturally charming — smooth but not trying too hard"
        vibe = "he wants to come across as interesting and genuine"
    elif any(k in t for k in ["apolog", "sorry", "forgive", "messed up", "my fault"]):
        tone = "sincere, genuine and not defensive"
        vibe = "he actually means it and wants to make it right"
    elif any(k in t for k in ["angry", "annoyed", "upset", "fight", "argue", "rude"]):
        tone = "calm, assertive and direct — firm without being aggressive"
        vibe = "he wants to be taken seriously without escalating"
    elif any(k in t for k in ["funny", "savage", "roast", "witty", "comeback"]):
        tone = "witty and sharp with perfect comedic timing"
        vibe = "he wants the funniest possible reply"
    else:
        tone = "natural, confident and real"
        vibe = "he wants to sound like himself but better"

    prompt = (
        f"Praful (18, Lucknow, CS student) needs help with this message situation: '{query}'. "
        f"Tone needed: {tone}. Context: {vibe}. "
        f"Give 3 versions — Short (1 sentence), Medium (2-3 sentences), Bold (confident, memorable). "
        f"Label them Short:, Medium:, Bold:. No explanations — just the messages."
    )
    return _ask(prompt, tokens=300)


def comeback(their_message: str) -> str:
    prompt = (
        f"Someone said to Praful: '{their_message}'. "
        f"Give him 3 perfect replies labeled: Savage:, Smooth:, Funny:. "
        f"Each max 1 sentence. No explanations."
    )
    return _ask(prompt, tokens=180)


def icebreaker(context: str) -> str:
    prompt = (
        f"Praful needs an opening message for: '{context}'. "
        f"Give 3 icebreaker openers — one question-based, one observation-based, one bold. "
        f"Label them Q:, Obs:, Bold:. Each under 2 sentences. Original — no cringe."
    )
    return _ask(prompt, tokens=200)


def _ask(prompt: str, tokens: int = 300) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": tokens,
        "temperature": 0.88,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Wingman offline: {e}"
