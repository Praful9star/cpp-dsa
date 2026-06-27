"""
brain.py — Intent detection + single Groq call.
"""

import re
import requests
import config
from tools.web_search    import web_search
from tools.telegram_send import send_telegram
from tools.play_media    import play_youtube, stop_media, skip_next, skip_prev, now_playing

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a close friend of Praful — smart, curious, warm, and witty.
Talk like a real person. Keep replies short and natural (spoken out loud).
No bullet points, no markdown — just normal sentences.
Use his name occasionally but not every reply.{facts}"""


# ── Intent detection ──────────────────────────────────────────────────────────

SEARCH_TRIGGERS = [
    "search", "look up", "google", "find out", "what is", "who is",
    "who won", "latest", "news about", "tell me about", "current",
    "score", "weather", "price", "how much", "when did", "where is",
    "what's happening", "any updates", "results of",
]

PLAY_TRIGGERS  = ["play ", "put on ", "listen to ", "stream "]
STOP_TRIGGERS  = ["stop music", "stop the music", "stop playing", "stop song",
                   "pause music", "pause the music", "turn off music", "mute music"]
NEXT_TRIGGERS  = ["next song", "next track", "skip", "next one", "play next"]
PREV_TRIGGERS  = ["previous song", "previous track", "go back", "last song", "play previous"]
NOW_TRIGGERS   = ["what's playing", "what song", "current song", "what are you playing"]
TELEGRAM_TRIGGERS = ["tell ", "message ", "send ", "text "]


def detect_intent(text: str):
    t = text.lower().strip()

    if any(kw in t for kw in STOP_TRIGGERS):
        return ("stop", "")

    if any(kw in t for kw in NEXT_TRIGGERS):
        return ("next", "")

    if any(kw in t for kw in PREV_TRIGGERS):
        return ("prev", "")

    if any(kw in t for kw in NOW_TRIGGERS):
        return ("nowplaying", "")

    for trigger in PLAY_TRIGGERS:
        if trigger in t:
            query = text[t.index(trigger) + len(trigger):].strip()
            if query:
                return ("play", query)

    for trigger in TELEGRAM_TRIGGERS:
        if t.startswith(trigger):
            rest = text[len(trigger):].strip()
            match = re.match(r"(\w+)\s+(.+)", rest, re.IGNORECASE)
            if match:
                recipient = match.group(1)
                message   = match.group(2).lstrip("that ").lstrip("saying ").strip()
                return ("telegram", {"recipient": recipient, "message": message})
            return ("telegram", {"recipient": "", "message": rest})

    if any(kw in t for kw in SEARCH_TRIGGERS):
        return ("search", text)

    return ("chat", "")


# ── Main chat function ────────────────────────────────────────────────────────

def chat(conversation_history: list, facts_context: str = "") -> str:
    user_text   = conversation_history[-1]["content"] if conversation_history else ""
    intent, arg = detect_intent(user_text)

    tool_result = ""

    if intent == "stop":
        return stop_media()

    elif intent == "next":
        return skip_next()

    elif intent == "prev":
        return skip_prev()

    elif intent == "nowplaying":
        return now_playing()

    elif intent == "play":
        print(f"\n[Tool] play_youtube('{arg}')")
        tool_result = play_youtube(arg)

    elif intent == "search":
        print(f"\n[Tool] web_search('{user_text}')")
        tool_result = web_search(user_text)

    elif intent == "telegram":
        print(f"\n[Tool] send_telegram({arg})")
        tool_result = send_telegram(arg.get("message", ""), arg.get("recipient", ""))

    # Build messages
    system   = SYSTEM_PROMPT.format(facts=facts_context)
    messages = [{"role": "system", "content": system}]
    messages += conversation_history[:-1]  # history minus last user msg

    if tool_result:
        combined = (
            f"{user_text}\n\n"
            f"[Info for your reply — speak naturally, not like a report]:\n"
            f"{tool_result[:1200]}"
        )
        messages.append({"role": "user", "content": combined})
    else:
        messages.append({"role": "user", "content": user_text})

    return _call_groq(messages)


def _call_groq(messages: list) -> str:
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "max_tokens": 256,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return "I can't reach the internet right now."
    except requests.exceptions.Timeout:
        return "That took too long — try again?"
    except requests.exceptions.HTTPError:
        status = resp.status_code if resp else 0
        print(f"[Brain] HTTP {status}: {resp.text[:200]}")
        if status == 401:
            return "API key issue — check GROQ_API_KEY in your .env file."
        if status == 429:
            return "Rate limited — give me a second and try again."
        return f"Groq returned an error ({status}). Try again?"
    except Exception as e:
        print(f"[Brain error] {e}")
        return "Something went wrong. Try again?"
