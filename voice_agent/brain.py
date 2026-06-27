"""
brain.py — Intent detection + single Groq call for everything.
"""

import re
import requests
import config

from tools.web_search  import web_search
from tools.play_media  import play_youtube, stop_media, skip_next, skip_prev, now_playing
from tools.reminders   import set_reminder, cancel_reminders, list_reminders
from tools.notes       import add_note, read_notes, delete_notes, count_notes
from tools.calculator  import calculate
from tools.weather     import get_weather
from tools.system      import (get_battery, set_volume, torch,
                                get_clipboard, set_clipboard, get_time, get_ip, tell_joke)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are Buddy — Praful's personal AI, smart, warm, witty, a bit sarcastic sometimes.
Talk like a real friend. Short natural sentences — no bullet points, no markdown.
You're running on his Android tablet in Termux. Use his name occasionally.
You have memory of past chats and know things about him.{facts}"""


# ── Intent map ────────────────────────────────────────────────────────────────
# Each entry: (list_of_trigger_keywords, handler_function_or_None)
# Order matters — more specific triggers first.

def detect_and_run(text: str) -> tuple[str | None, bool]:
    """
    Returns (tool_result_or_None, handled).
    If handled=True and result is not None, pass result to Groq to speak.
    If handled=True and result is None, it was handled inline (return from caller).
    """
    t = text.lower().strip()

    # ── Music controls (no Groq needed) ──────────────────────────────────────
    if any(k in t for k in ["next song", "next track", "skip this", "skip song", "play next"]):
        return skip_next(), True

    if any(k in t for k in ["previous song", "previous track", "go back", "last song"]):
        return skip_prev(), True

    if any(k in t for k in ["stop music", "stop the music", "stop playing",
                              "stop song", "pause music", "turn off music"]):
        return stop_media(), True

    if any(k in t for k in ["what's playing", "what song", "now playing", "current song"]):
        return now_playing(), True

    # ── Torch ─────────────────────────────────────────────────────────────────
    if any(k in t for k in ["torch on", "flashlight on", "turn on torch", "turn on flashlight"]):
        return torch(True), True
    if any(k in t for k in ["torch off", "flashlight off", "turn off torch", "turn off flashlight"]):
        return torch(False), True

    # ── Volume ────────────────────────────────────────────────────────────────
    if any(k in t for k in ["volume up", "turn it up", "louder", "increase volume"]):
        return set_volume("up"), True
    if any(k in t for k in ["volume down", "turn it down", "quieter", "lower the volume"]):
        return set_volume("down"), True
    if any(k in t for k in ["mute", "silence"]) and "music" not in t:
        return set_volume("mute"), True
    if "max volume" in t or "full volume" in t:
        return set_volume("max"), True
    m = re.search(r"(?:set|volume).{0,10}(\d+)\s*(?:percent|%)?", t)
    if m and "volume" in t:
        return set_volume("set", int(m.group(1))), True

    # ── Time & Date ───────────────────────────────────────────────────────────
    if any(k in t for k in ["what time", "what's the time", "current time", "what day", "today's date", "what date"]):
        return get_time(), True

    # ── Battery ───────────────────────────────────────────────────────────────
    if any(k in t for k in ["battery", "charge level", "how much charge"]):
        return get_battery(), True

    # ── IP / Network ──────────────────────────────────────────────────────────
    if any(k in t for k in ["my ip", "ip address", "what's my ip"]):
        return get_ip(), True

    # ── Clipboard ─────────────────────────────────────────────────────────────
    if any(k in t for k in ["what's in my clipboard", "read clipboard", "clipboard says"]):
        return get_clipboard(), True
    for kw in ["copy to clipboard", "copy this to clipboard", "set clipboard to"]:
        if kw in t:
            content = text[t.index(kw) + len(kw):].strip(" :\"'")
            return set_clipboard(content), True

    # ── Jokes ─────────────────────────────────────────────────────────────────
    if any(k in t for k in ["tell me a joke", "say a joke", "joke", "make me laugh", "funny"]):
        return tell_joke(), True

    # ── Weather ───────────────────────────────────────────────────────────────
    if any(k in t for k in ["weather", "temperature", "rain", "forecast", "will it rain", "hot outside", "cold outside"]):
        return get_weather(text), False  # pass to Groq to speak naturally

    # ── Calculator ────────────────────────────────────────────────────────────
    if any(k in t for k in ["calculate", "what is", "percent of", "convert",
                              "times", "divided by", "plus", "minus", "square root",
                              "how many", "how much is"]):
        # Only trigger if there are numbers in the text
        if any(c.isdigit() for c in t):
            return calculate(text), True

    # ── Reminders & Alarms ────────────────────────────────────────────────────
    if any(k in t for k in ["remind me", "set a timer", "timer for", "set alarm", "alarm for", "wake me"]):
        return set_reminder(text), True
    if any(k in t for k in ["cancel reminder", "cancel alarm", "cancel timer"]):
        return cancel_reminders(), True
    if any(k in t for k in ["my reminders", "active reminders", "list reminders"]):
        return list_reminders(), True

    # ── Notes ─────────────────────────────────────────────────────────────────
    if any(k in t for k in ["note that", "save a note", "write this down", "remember that", "add a note"]):
        for kw in ["note that", "save a note", "write this down", "remember that", "add a note"]:
            if kw in t:
                content = text[t.index(kw) + len(kw):].strip(" :")
                return add_note(content), True

    if any(k in t for k in ["read my notes", "show my notes", "what are my notes", "my notes"]):
        return read_notes(), False  # let Groq speak them naturally

    if any(k in t for k in ["delete my notes", "clear my notes", "wipe notes"]):
        return delete_notes(), True

    if any(k in t for k in ["how many notes"]):
        return count_notes(), True

    # ── Music playback ────────────────────────────────────────────────────────
    for trigger in ["play ", "put on ", "listen to ", "stream "]:
        if trigger in t:
            query = text[t.index(trigger) + len(trigger):].strip()
            if query:
                return play_youtube(query), False  # Groq confirms naturally

    # ── Web search ────────────────────────────────────────────────────────────
    SEARCH_KW = [
        "search", "look up", "google", "find out", "who is", "who won",
        "latest news", "news about", "tell me about", "current", "score",
        "weather in", "price of", "when did", "where is", "what happened",
        "results of", "any updates on", "what's happening",
    ]
    if any(k in t for k in SEARCH_KW):
        return web_search(text), False  # Groq speaks the result naturally

    return None, False  # pure conversation


# ── Main chat function ────────────────────────────────────────────────────────

def chat(conversation_history: list, facts_context: str = "") -> str:
    user_text = conversation_history[-1]["content"] if conversation_history else ""

    tool_result, instant = detect_and_run(user_text)

    # Instant responses — return immediately without calling Groq
    if tool_result and instant:
        print(f"\n[Tool result] {tool_result}")
        return tool_result

    # Build Groq messages
    system   = SYSTEM_PROMPT.format(facts=facts_context)
    messages = [{"role": "system", "content": system}]
    messages += conversation_history[:-1]

    if tool_result:
        combined = (
            f"{user_text}\n\n"
            f"[Data — respond naturally based on this, don't read it robotically]:\n"
            f"{tool_result[:1400]}"
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
        "temperature": 0.85,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        return "Can't reach the internet right now."
    except requests.exceptions.Timeout:
        return "That took too long — try again?"
    except requests.exceptions.HTTPError:
        status = getattr(resp, "status_code", 0)
        print(f"[Brain] HTTP {status}: {resp.text[:200]}")
        if status == 401:
            return "API key issue — check GROQ_API_KEY in your .env file."
        if status == 429:
            return "Rate limited — give me a second."
        return "Something went wrong talking to Groq."
    except Exception as e:
        print(f"[Brain error] {e}")
        return "Something went wrong. Try again?"
