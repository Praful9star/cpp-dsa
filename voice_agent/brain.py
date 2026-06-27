"""
brain.py — Full Jarvis brain. Intent detection + Groq for everything.
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
from tools.system      import get_battery, set_volume, torch, get_clipboard, set_clipboard, get_time, get_ip, tell_joke
from tools.briefing    import morning_briefing
from tools.apps        import open_app, make_call, send_whatsapp
from tools.sms         import send_sms, read_sms
from tools.news        import get_news
from tools.translate   import translate
from tools.dsa         import problem_of_the_day, random_problem, start_quiz, next_quiz_question, explain_concept
from tools.expenses    import add_expense, get_expenses, delete_expenses
from tools.fun         import roast_me, tell_story, rap_battle, start_debate, get_quote, internet_speed, days_until
from tools.modes       import set_mode, get_mode_prompt, current_mode_status
from tools.vision      import look_and_describe
from tools.youtube_summary import summarize_youtube
from tools.journal     import add_journal_entry, read_journal, brain_dump, journal_stats, clear_journal
from tools.pomodoro    import start_pomodoro, stop_pomodoro, pomodoro_status
from tools.finance     import get_crypto_price, get_stock_price, market_summary
from tools.fake_call   import schedule_fake_call, cancel_fake_call
from tools.spaced_repetition import mark_struggle, mark_understood, get_due_reviews, list_all_cards

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BASE_SYSTEM = """You are Buddy — Praful's personal Jarvis. Smart, warm, witty, a bit sarcastic.
Talk like a real friend. Short natural sentences — no bullet points, no markdown, no lists.
You run on his Android tablet. You know him well.{mode}{facts}"""

_quiz_active = False


def detect_and_run(text: str):
    """Returns (result, instant, special) where special is a Groq prompt override or None."""
    global _quiz_active
    t = text.lower().strip()

    # ── Morning/Evening briefing ──────────────────────────────────────────────
    if any(k in t for k in ["good morning", "morning briefing", "good evening", "good afternoon",
                              "what's my day", "brief me", "daily briefing", "start my day"]):
        return morning_briefing(), False, None

    # ── Music controls ────────────────────────────────────────────────────────
    if any(k in t for k in ["next song", "next track", "skip this", "skip song", "play next"]):
        return skip_next(), True, None
    if any(k in t for k in ["previous song", "previous track", "last song"]):
        return skip_prev(), True, None
    if any(k in t for k in ["stop music", "stop the music", "stop playing", "stop song", "pause music"]):
        return stop_media(), True, None
    if any(k in t for k in ["what's playing", "what song", "now playing", "current song"]):
        return now_playing(), True, None
    for trigger in ["play ", "put on ", "listen to ", "stream "]:
        if trigger in t:
            query = text[t.index(trigger) + len(trigger):].strip()
            if query:
                return play_youtube(query), False, None

    # ── Torch / Flashlight ────────────────────────────────────────────────────
    if any(k in t for k in ["torch on", "flashlight on", "turn on torch", "turn on flashlight", "light on"]):
        return torch(True), True, None
    if any(k in t for k in ["torch off", "flashlight off", "turn off torch", "turn off flashlight", "light off"]):
        return torch(False), True, None

    # ── Volume ────────────────────────────────────────────────────────────────
    if any(k in t for k in ["volume up", "turn it up", "louder", "increase volume", "turn up"]):
        return set_volume("up"), True, None
    if any(k in t for k in ["volume down", "turn it down", "quieter", "lower the volume", "turn down"]):
        return set_volume("down"), True, None
    if any(k in t for k in ["mute", "silence"]) and "music" not in t:
        return set_volume("mute"), True, None
    if "max volume" in t or "full volume" in t:
        return set_volume("max"), True, None
    m = re.search(r"(?:set|volume).{0,10}(\d+)\s*(?:percent|%)?", t)
    if m and "volume" in t:
        return set_volume("set", int(m.group(1))), True, None

    # ── Time & Date ───────────────────────────────────────────────────────────
    if any(k in t for k in ["what time", "what's the time", "current time", "what day", "today's date", "what date"]):
        return get_time(), True, None

    # ── Battery ───────────────────────────────────────────────────────────────
    if any(k in t for k in ["battery", "charge level", "how much charge"]):
        return get_battery(), True, None

    # ── IP / Network ──────────────────────────────────────────────────────────
    if any(k in t for k in ["my ip", "ip address", "what's my ip"]):
        return get_ip(), True, None

    # ── Speed test ────────────────────────────────────────────────────────────
    if any(k in t for k in ["speed test", "internet speed", "how fast is my internet", "test my internet"]):
        return internet_speed(), True, None

    # ── Clipboard ─────────────────────────────────────────────────────────────
    if any(k in t for k in ["what's in my clipboard", "read clipboard", "clipboard"]):
        return get_clipboard(), True, None
    for kw in ["copy to clipboard", "copy this", "set clipboard"]:
        if kw in t:
            content = text[t.index(kw) + len(kw):].strip(" :\"'")
            return set_clipboard(content), True, None

    # ── Jokes ─────────────────────────────────────────────────────────────────
    if any(k in t for k in ["tell me a joke", "say a joke", "joke", "make me laugh"]):
        return tell_joke(), True, None

    # ── Weather ───────────────────────────────────────────────────────────────
    if any(k in t for k in ["weather", "temperature", "rain", "forecast", "will it rain"]):
        return get_weather(text), False, None

    # ── News ──────────────────────────────────────────────────────────────────
    if any(k in t for k in ["news", "headlines", "what's happening", "current events", "latest news"]):
        return get_news(text), False, None

    # ── Translation ───────────────────────────────────────────────────────────
    if any(k in t for k in ["translate", "how do you say", "what is", "in hindi", "in french",
                              "in spanish", "in german", "in japanese"]):
        if any(lang in t for lang in ["hindi", "french", "spanish", "german", "japanese",
                                       "english", "arabic", "urdu", "punjabi", "tamil"]):
            return translate(text), True, None

    # ── Calculator / Conversion ───────────────────────────────────────────────
    if any(k in t for k in ["calculate", "percent of", "convert", "times", "divided by",
                              "plus", "minus", "square root", "power of"]):
        if any(c.isdigit() for c in t):
            return calculate(text), True, None
    if any(k in t for k in ["how much is", "what's", "what is"]) and any(c.isdigit() for c in t):
        result = calculate(text)
        if "couldn't" not in result:
            return result, True, None

    # ── Open apps ─────────────────────────────────────────────────────────────
    if t.startswith("open ") or "launch " in t or "start " in t:
        app = re.sub(r"^(open|launch|start)\s+", "", t).strip()
        if app:
            return open_app(app), True, None

    # ── Calls ─────────────────────────────────────────────────────────────────
    if t.startswith("call "):
        name = text[5:].strip()
        return make_call(name), True, None

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    if "whatsapp" in t and any(k in t for k in ["send", "message", "tell", "text"]):
        m = re.search(r"(?:whatsapp|message|tell|text)\s+(\w+)\s+(?:saying?|that|:)?\s*(.+)", t)
        if m:
            return send_whatsapp(m.group(1), m.group(2)), True, None

    # ── SMS ───────────────────────────────────────────────────────────────────
    if any(k in t for k in ["send sms", "send a text", "text message to"]):
        m = re.search(r"(?:text|sms)\s+(?:to\s+)?(\w+)\s+(?:saying?|that|:)?\s*(.+)", t)
        if m:
            return send_sms(m.group(1), m.group(2)), True, None
    if any(k in t for k in ["read my messages", "read sms", "check messages", "any messages"]):
        return read_sms(), False, None

    # ── Reminders & Alarms ────────────────────────────────────────────────────
    if any(k in t for k in ["remind me", "set a timer", "timer for", "set alarm", "alarm for", "wake me"]):
        return set_reminder(text), True, None
    if any(k in t for k in ["cancel reminder", "cancel alarm", "cancel timer"]):
        return cancel_reminders(), True, None
    if any(k in t for k in ["my reminders", "active reminders", "list reminders"]):
        return list_reminders(), True, None

    # ── Notes ─────────────────────────────────────────────────────────────────
    for kw in ["note that", "save a note", "write this down", "add a note"]:
        if kw in t:
            content = text[t.index(kw) + len(kw):].strip(" :")
            return add_note(content), True, None
    if any(k in t for k in ["read my notes", "show my notes", "my notes"]):
        return read_notes(), False, None
    if any(k in t for k in ["delete my notes", "clear my notes"]):
        return delete_notes(), True, None

    # ── Expenses ─────────────────────────────────────────────────────────────
    if any(k in t for k in ["i spent", "spent ", "i paid", "paid "]):
        if any(c.isdigit() for c in t):
            return add_expense(text), True, None
    if any(k in t for k in ["how much did i spend", "my expenses", "show expenses", "spending"]):
        period = "week" if "week" in t else ("month" if "month" in t else "today")
        return get_expenses(period), False, None
    if "delete expenses" in t or "clear expenses" in t:
        return delete_expenses(), True, None

    # ── Countdown ─────────────────────────────────────────────────────────────
    if any(k in t for k in ["how many days until", "how long until", "days until", "countdown to"]):
        event = re.sub(r"how (many days|long) until|days until|countdown to", "", t).strip()
        return days_until(event), True, None

    # ── DSA / C++ ────────────────────────────────────────────────────────────
    if any(k in t for k in ["problem of the day", "today's problem", "dsa problem"]):
        return problem_of_the_day(), False, None
    if any(k in t for k in ["give me a problem", "random problem", "practice problem"]):
        return random_problem(), False, None
    if any(k in t for k in ["quiz me", "start quiz", "test me on c++", "test my knowledge"]):
        _quiz_active = True
        return start_quiz(), False, None
    if _quiz_active and any(k in t for k in ["next", "answer", "i don't know", "skip", "tell me"]):
        return next_quiz_question(text), False, None
    if any(k in t for k in ["explain", "what is a", "what are", "how does", "teach me"]):
        if any(k in t for k in ["array", "linked list", "tree", "graph", "stack", "queue",
                                  "hash", "sort", "search", "pointer", "recursion", "dp",
                                  "dynamic", "binary", "heap", "trie", "bfs", "dfs", "c++",
                                  "class", "object", "template", "vector", "map", "set"]):
            return None, False, _dsa_explain_prompt(text)

    # ── Modes ─────────────────────────────────────────────────────────────────
    if any(k in t for k in ["focus mode", "chill mode", "study mode", "normal mode",
                              "i'm studying", "im studying", "let's relax", "lets relax"]):
        return set_mode(t), True, None
    if "what mode" in t or "current mode" in t:
        return current_mode_status(), True, None

    # ── Fun: Roast / Story / Rap / Debate / Quote ─────────────────────────────
    if any(k in t for k in ["roast me", "roast yourself", "say something mean"]):
        return None, False, _roast_prompt()
    if any(k in t for k in ["tell me a story", "make up a story", "tell a story"]):
        return None, False, _story_prompt()
    if any(k in t for k in ["rap battle", "spit some bars", "rap for me", "freestyle"]):
        return None, False, _rap_prompt()
    if any(k in t for k in ["let's debate", "lets debate", "debate"]):
        topic = re.sub(r"let'?s debate|debate", "", t).strip(" :") or "whether pineapple belongs on pizza"
        return None, False, _debate_prompt(topic)
    if any(k in t for k in ["quote", "motivate me", "inspire me", "give me a quote"]):
        return get_quote(), True, None

    # ── What should I do today / plan my day ──────────────────────────────────
    if any(k in t for k in ["what should i do today", "plan my day", "what to do today"]):
        reminders = list_reminders()
        return None, False, _day_plan_prompt(reminders)

    # ── Summarize conversation ─────────────────────────────────────────────────
    if any(k in t for k in ["summarize our conversation", "what did we talk about", "recap"]):
        return None, False, "SUMMARIZE"

    # ── Camera / Vision ───────────────────────────────────────────────────────
    if any(k in t for k in ["what do you see", "look at this", "what's in front",
                              "describe what you see", "read this text", "read the",
                              "what food is", "who is this", "what is this",
                              "point the camera", "use the camera", "take a photo"]):
        return look_and_describe(text), False, None

    # ── YouTube Summarizer ────────────────────────────────────────────────────
    if any(k in t for k in ["summarize this video", "summarize youtube", "what is this video",
                              "video summary", "youtube.com", "youtu.be"]):
        return summarize_youtube(text), False, None

    # ── Journal ───────────────────────────────────────────────────────────────
    for kw in ["journal entry", "add to journal", "journal:", "diary entry"]:
        if kw in t:
            content = text[t.index(kw) + len(kw):].strip(" :")
            return add_journal_entry(content or text), True, None
    if any(k in t for k in ["brain dump", "dump my thoughts", "everything on my mind"]):
        return None, False, "BRAIN_DUMP"
    if any(k in t for k in ["read my journal", "show my journal", "my journal entries"]):
        return read_journal(), False, None
    if any(k in t for k in ["journal stats", "how many journal", "journal count"]):
        return journal_stats(), True, None
    if "clear journal" in t or "delete journal" in t:
        return clear_journal(), True, None

    # ── Pomodoro ──────────────────────────────────────────────────────────────
    if any(k in t for k in ["start pomodoro", "pomodoro", "focus timer", "start focus"]):
        if any(k in t for k in ["stop", "cancel", "end"]):
            return stop_pomodoro(), True, None
        if any(k in t for k in ["status", "how long", "time left"]):
            return pomodoro_status(), True, None
        return start_pomodoro(text), True, None
    if any(k in t for k in ["stop pomodoro", "cancel pomodoro", "end pomodoro"]):
        return stop_pomodoro(), True, None
    if any(k in t for k in ["pomodoro status", "pomodoro count", "how many pomodoros"]):
        return pomodoro_status(), True, None

    # ── Finance: Crypto ───────────────────────────────────────────────────────
    CRYPTO_KW = ["bitcoin", "ethereum", "crypto", "btc", "eth", "dogecoin", "doge",
                  "solana", "sol", "cardano", "ripple", "matic", "polygon", "shiba",
                  "binance", "bnb", "litecoin", "polkadot", "chainlink", "avax",
                  "tron", "pepe", "coin price"]
    if any(k in t for k in CRYPTO_KW):
        return get_crypto_price(text), False, None

    # ── Finance: Stocks ───────────────────────────────────────────────────────
    STOCK_KW = ["stock", "share price", "market", "sensex", "nifty", "nasdaq",
                 "apple stock", "tesla", "reliance", "tcs stock", "infosys stock"]
    if any(k in t for k in STOCK_KW):
        if "market summary" in t or "market snapshot" in t:
            return market_summary(), False, None
        return get_stock_price(text), False, None

    # ── Fake / Escape Call ────────────────────────────────────────────────────
    if any(k in t for k in ["fake call", "escape call", "rescue call", "call me in",
                              "pretend call", "fake incoming"]):
        if any(k in t for k in ["cancel", "stop"]):
            return cancel_fake_call(), True, None
        return schedule_fake_call(text), True, None

    # ── Spaced Repetition / DSA Review ───────────────────────────────────────
    if any(k in t for k in ["i'm struggling with", "struggling with", "don't understand",
                              "i don't get", "confused about", "weak at", "bad at"]):
        concept = re.sub(r"i'?m? ?(struggling with|don'?t (understand|get)|confused about|weak at|bad at)\s*", "", t).strip()
        if concept:
            return mark_struggle(concept), True, None
    if any(k in t for k in ["i got it", "i understand now", "mark understood",
                              "understood", "i know this now"]):
        concept = re.sub(r"(i got it|i understand now|mark understood|understood|i know this now)[,\s]*", "", t).strip()
        if concept:
            return mark_understood(concept), True, None
        return "Which concept did you understand? Say 'I got it — recursion' for example.", True, None
    if any(k in t for k in ["what should i review", "review cards", "due reviews",
                              "what to review", "my weak spots"]):
        return get_due_reviews(), False, None
    if any(k in t for k in ["list review cards", "all review cards", "my flashcards"]):
        return list_all_cards(), False, None

    # ── Personality Mirror / Mood Analysis ───────────────────────────────────
    if any(k in t for k in ["how am i doing", "my mood", "personality mirror",
                              "mood report", "how's my mental", "how have i been"]):
        return None, False, "MOOD_MIRROR"

    # ── Fact Check ────────────────────────────────────────────────────────────
    if any(k in t for k in ["fact check", "is that true", "is it true", "verify that",
                              "that's not true", "are you sure about"]):
        return None, False, "FACT_CHECK"

    # ── Sleep Mode ────────────────────────────────────────────────────────────
    if any(k in t for k in ["good night", "goodnight", "i'm going to sleep",
                              "im going to sleep", "going to bed", "sleep mode"]):
        return None, False, "GOOD_NIGHT"

    # ── Web search ────────────────────────────────────────────────────────────
    SEARCH_KW = ["search", "look up", "google", "find out", "who is", "who won",
                  "latest", "news about", "tell me about", "score", "price of",
                  "when did", "where is", "what happened", "results of"]
    if any(k in t for k in SEARCH_KW):
        return web_search(text), False, None

    return None, False, None


# ── Special Groq prompts ──────────────────────────────────────────────────────

def _roast_prompt():
    return ("You are roasting Praful as a friend would — funny, not mean. "
            "Use what you know about him: 18 years old, from Lucknow, going to CU for CS, "
            "built CureCheck.in, learning C++. Roast him in 3-4 sentences. Keep it funny and warm.")

def _story_prompt():
    return ("Tell Praful a short, fun story — 5-6 sentences. Make him the hero. "
            "Include something from his real life (Lucknow, coding, CU). Make it exciting.")

def _rap_prompt():
    return ("Spit a short freestyle rap (8 lines) about Praful. "
            "Reference Lucknow, coding, C++, CureCheck, Chandigarh University. "
            "Make it hype and fun. Rhyme scheme: AABB or ABAB.")

def _debate_prompt(topic: str):
    return (f"Debate Praful on this topic: '{topic}'. Pick a side randomly and argue it "
            f"confidently in 3-4 sentences. Be witty. Don't be neutral — commit to a position.")

def _dsa_explain_prompt(query: str):
    return (f"Praful (18, learning C++ and DSA) asked: '{query}'. "
            f"Explain it like a smart friend teaching a beginner — clear, simple, with an analogy if possible. "
            f"Keep it under 5 sentences. Spoken out loud so no code blocks — describe the concept in words.")

def _day_plan_prompt(reminders: str):
    import datetime
    hour = datetime.datetime.now().hour
    time_of_day = "morning" if hour < 12 else ("afternoon" if hour < 17 else "evening")
    return (f"It's {time_of_day}. Praful wants to know what to do today. "
            f"His reminders: {reminders}. "
            f"He's 18, learning C++ and DSA, going to CU in July, and built CureCheck.in. "
            f"Suggest 3-4 things he could do today — keep it practical and motivating. "
            f"Spoken naturally, no lists.")


# ── Main chat ─────────────────────────────────────────────────────────────────

def chat(conversation_history: list, facts_context: str = "") -> str:
    user_text = conversation_history[-1]["content"] if conversation_history else ""

    result, instant, special_prompt = detect_and_run(user_text)

    if result and instant:
        return result

    mode_prompt   = get_mode_prompt()
    system        = BASE_SYSTEM.format(mode=mode_prompt, facts=facts_context)
    messages      = [{"role": "system", "content": system}]
    messages     += conversation_history[:-1]

    if special_prompt == "SUMMARIZE":
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in conversation_history[-20:])
        messages.append({"role": "user", "content":
            f"Summarize what we talked about in this session in 3-4 natural sentences:\n{history_text}"})

    elif special_prompt == "BRAIN_DUMP":
        # Brain dump: use the last user message as the raw dump
        result = brain_dump(user_text)
        return result

    elif special_prompt == "MOOD_MIRROR":
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in conversation_history[-50:]
            if m["role"] == "user"
        )
        messages.append({"role": "user", "content":
            f"Analyze Praful's recent messages and give a candid mood/personality report. "
            f"Look for stress signals, energy levels, focus patterns, emotional tone. "
            f"Be honest but kind — like a friend who notices things. 4-5 natural sentences.\n\n"
            f"Recent messages:\n{history_text[:3000]}"})

    elif special_prompt == "FACT_CHECK":
        # Find the last assistant claim to fact-check
        last_claim = ""
        for m in reversed(conversation_history[:-1]):
            if m["role"] == "assistant":
                last_claim = m["content"]
                break
        search_result = ""
        try:
            from tools.web_search import web_search
            search_result = web_search(last_claim[:100])
        except Exception:
            pass
        messages.append({"role": "user", "content":
            f"Praful wants to fact-check this statement: '{last_claim}'. "
            f"Web search results: {search_result[:800]}. "
            f"Tell him if it's accurate, partially true, or wrong — and why. Be direct and specific."})

    elif special_prompt == "GOOD_NIGHT":
        hour = __import__("datetime").datetime.now().hour
        messages.append({"role": "user", "content":
            f"Praful is going to sleep (it's {hour}:00). Say good night warmly, give him one "
            f"motivating thought for tomorrow, and remind him of his streak. Keep it under 3 sentences."})

    elif special_prompt:
        messages.append({"role": "user", "content": special_prompt})
    elif result:
        combined = (f"{user_text}\n\n"
                    f"[Data — respond naturally based on this]:\n{result[:1400]}")
        messages.append({"role": "user", "content": combined})
    else:
        messages.append({"role": "user", "content": user_text})

    return _call_groq(messages)


def _call_groq(messages: list) -> str:
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": config.GROQ_MODEL, "messages": messages, "max_tokens": 300, "temperature": 0.85}
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
        if status == 429:
            return "Rate limited — give me a second."
        return "Something went wrong talking to Groq."
    except Exception as e:
        print(f"[Brain error] {e}")
        return "Something went wrong. Try again?"
