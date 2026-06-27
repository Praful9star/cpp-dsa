"""
brain.py — Groq API with tool/function calling (Phase 3).
"""

import json
import requests
import config
from tools.web_search    import web_search
from tools.telegram_send import send_telegram
from tools.play_media    import play_youtube, stop_media

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BASE_SYSTEM_PROMPT = """You are a close friend of Praful — smart, curious, warm, and witty.
Talk like a real person. Keep replies short and natural (this is spoken out loud).
No bullet points, no markdown — just normal sentences.
Use his name occasionally but not every reply.
If you don't know something current, use the web_search tool.
When you call play_youtube, just confirm you're playing it — don't pretend it's already playing before calling the tool.{facts}"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information, news, facts, or anything "
                "you don't know. Use when Praful asks something that needs up-to-date knowledge."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram",
            "description": (
                "Send a Telegram message on Praful's behalf. "
                "Use when he says 'tell X...', 'message X saying...', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Name of the person to message."},
                    "message":   {"type": "string", "description": "The message text to send."},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": (
                "Download and play music or a YouTube video. "
                "Use when Praful says 'play [song/artist/genre]', 'put on music', etc. "
                "This downloads the audio first so it may take 10-20 seconds."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song, artist, genre, or YouTube URL."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_media",
            "description": "Stop whatever music or audio is currently playing.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _run_tool(name: str, args: dict) -> str:
    print(f"\n[Tool] {name}({args})")
    if name == "web_search":
        return web_search(args.get("query", ""))
    if name == "send_telegram":
        return send_telegram(args.get("message", ""), args.get("recipient", ""))
    if name == "play_youtube":
        return play_youtube(args.get("query", ""))
    if name == "stop_media":
        return stop_media()
    return f"Unknown tool: {name}"


def _post(headers: dict, payload: dict) -> dict:
    resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Attach response body to the error message for easier debugging
        try:
            body = resp.json()
            raise requests.exceptions.HTTPError(
                f"HTTP {resp.status_code}: {body}", response=resp
            ) from e
        except Exception:
            raise
    return resp.json()


def chat(conversation_history: list, facts_context: str = "") -> str:
    system   = BASE_SYSTEM_PROMPT.format(facts=facts_context)
    messages = [{"role": "system", "content": system}] + conversation_history

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # ── First call ─────────────────────────────────────────────────────────
        payload = {
            "model": config.GROQ_MODEL,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "max_tokens": 1024,
            "temperature": 0.8,
        }
        resp   = _post(headers, payload)
        choice = resp["choices"][0]

        if choice["finish_reason"] != "tool_calls":
            return choice["message"]["content"].strip()

        # ── Tool calls ────────────────────────────────────────────────────────
        assistant_msg = choice["message"]
        messages.append(assistant_msg)

        for tool_call in assistant_msg.get("tool_calls", []):
            fn_name = tool_call["function"]["name"]
            fn_args = json.loads(tool_call["function"]["arguments"])
            result  = _run_tool(fn_name, fn_args)
            # Truncate very long tool results to avoid token overflows
            if len(result) > 1500:
                result = result[:1500] + "...[truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

        # ── Second call: final spoken reply ───────────────────────────────────
        payload2 = {
            "model": config.GROQ_MODEL,
            "messages": messages,
            "max_tokens": 256,
            "temperature": 0.8,
        }
        resp2 = _post(headers, payload2)
        return resp2["choices"][0]["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return "I can't reach the internet right now. Check your connection?"
    except requests.exceptions.Timeout:
        return "That took too long. Try again?"
    except requests.exceptions.HTTPError as e:
        print(f"[Brain HTTP error] {e}")
        resp_obj = e.response
        if resp_obj is not None:
            if resp_obj.status_code == 401:
                return "My API key seems wrong — check GROQ_API_KEY in your .env file."
            if resp_obj.status_code == 429:
                return "I'm being rate-limited. Give me a second and try again."
            return f"API error {resp_obj.status_code}. Try again?"
        return "Couldn't connect to Groq. Check your internet."
    except Exception as e:
        print(f"[Brain error] {e}")
        return "Something went wrong on my end. Try again?"
