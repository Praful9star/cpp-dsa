"""
brain.py — Single-call approach: detect intent → run tool → one Groq call.

No two-step tool-calling API. Just keyword detection + one clean API call.
Much more reliable on mobile.
"""

import re
import requests
import config
from tools.web_search    import web_search
from tools.telegram_send import send_telegram
from tools.play_media    import play_youtube, stop_media

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a close friend of Praful — smart, curious, warm, and witty.
Talk like a real person. Keep replies short and natural (spoken out loud).
No bullet points, no markdown — just normal sentences.
Use his name occasionally but not every reply.{facts}"""


# ── Intent detection via simple keyword matching ──────────────────────────────

SEARCH_TRIGGERS = [
    "search", "look up", "google", "find out", "what is", "who is",
    "who won", "latest", "news about", "tell me about", "current",
    "score", "weather", "price", "how much", "when did", "where is",
]

PLAY_TRIGGERS = ["play ", "put on ", "listen to ", "stream "]
STOP_TRIGGERS = ["stop", "pause", "mute", "quiet", "silence the music", "stop the music", "stop playing"]
TELEGRAM_TRIGGERS = ["tell ", "message ", "send ", "text "]


def detect_intent(text: str):
    """
    Returns (intent, arg) where intent is one of:
    'search', 'play', 'stop', 'telegram', or 'chat'
    """
    t = text.lower().strip()

    # Stop music
    if any(t.startswith(w) or w in t for w in STOP_TRIGGERS):
        if "music" in t or "playing" in t or "song" in t or "audio" in t or t in ("stop", "pause"):
            return ("stop", "")

    # Play music/video
    for trigger in PLAY_TRIGGERS:
        if trigger in t:
            query = text[t.index(trigger) + len(trigger):].strip()
            if query:
                return ("play", query)

    # Telegram
    for trigger in TELEGRAM_TRIGGERS:
        if t.startswith(trigger):
            rest = text[len(trigger):].strip()
            # "tell mom I'll be home" → recipient=mom, message=I'll be home
            match = re.match(r"(\w+)\s+(.+)", rest, re.IGNORECASE)
            if match:
                recipient = match.group(1)
                message   = match.group(2).lstrip("that ").lstrip("saying ").strip()
                return ("telegram", {"recipient": recipient, "message": message})
            return ("telegram", {"recipient": "", "message": rest})

    # Web search
    if any(kw in t for kw in SEARCH_TRIGGERS):
        return ("search", text)

    return ("chat", "")


# ── Main chat function ────────────────────────────────────────────────────────

def chat(conversation_history: list, facts_context: str = "") -> str:
    """
    Detect intent → optionally run a tool → single Groq call → return reply.
    """
    user_text   = conversation_history[-1]["content"] if conversation_history else ""
    intent, arg = detect_intent(user_text)

    tool_result = ""

    if intent == "search":
        print(f"\n[Tool] web_search('{user_text}')")
        tool_result = web_search(user_text)

    elif intent == "play":
        print(f"\n[Tool] play_youtube('{arg}')")
        tool_result = play_youtube(arg)

    elif intent == "stop":
        print("\n[Tool] stop_media()")
        return stop_media()  # no need to call Groq for this

    elif intent == "telegram":
        print(f"\n[Tool] send_telegram({arg})")
        tool_result = send_telegram(arg.get("message", ""), arg.get("recipient", ""))

    # Build messages for Groq
    system = SYSTEM_PROMPT.format(facts=facts_context)
    messages = [{"role": "system", "content": system}]

    # Inject tool result as extra context before the last user message
    history = conversation_history[:-1]  # everything except the last user message
    messages += history

    if tool_result:
        # Give Groq the raw data and ask it to reply naturally
        combined = (
            f"{user_text}\n\n"
            f"[Tool result — use this to answer, but speak naturally, not like a report]:\n"
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
