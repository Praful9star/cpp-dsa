"""
tools/ghost_writer.py — Turn voice rambling into polished writing.

Praful talks stream-of-consciousness and Buddy turns it into:
- A blog post
- A LinkedIn post
- An email
- A cover letter
- A tweet thread
- An essay
- A cold DM

"Ghost write a blog post about: [rambling thoughts]"
"Turn this into a LinkedIn post: [ideas]"
"Write me a tweet thread about [topic]"
"Draft an email to my professor: [situation]"
"Write a cold DM to [context]"
"""

import re
import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

FORMAT_PROMPTS = {
    "blog": (
        "Turn this raw input into a compelling blog post by Praful (18, built CureCheck.in, "
        "CS student, Lucknow). Hook opening, 3-4 paragraphs, strong closing. "
        "Voice: personal, confident, like a builder sharing lessons. No filler. No markdown headers."
    ),
    "linkedin": (
        "Turn this into a high-performing LinkedIn post by Praful (18, built CureCheck.in, "
        "going to CU for CS). Hook first line that stops the scroll. Personal story. "
        "1-2 key insights. Soft call to action. Conversational but professional. Under 200 words."
    ),
    "tweet": (
        "Turn this into a Twitter/X thread by Praful (18, builder, CS student). "
        "5-7 tweets. First tweet is the hook. Each tweet stands alone. "
        "End with something memorable. Format as: 1/ ... 2/ ... etc."
    ),
    "email": (
        "Turn this into a polished email by Praful (18, CS student). "
        "Subject line, greeting, clear body, professional closing. "
        "Tone: respectful but confident. No waffle."
    ),
    "cover_letter": (
        "Turn this into a compelling cover letter by Praful (18, built CureCheck.in, "
        "going to CU for CS). Highlight his self-taught skills and entrepreneurial spirit. "
        "3 paragraphs. Confident, not desperate. End strong."
    ),
    "cold_dm": (
        "Turn this into a perfect cold DM by Praful. Short (under 80 words). "
        "Leads with value or a specific observation. Not generic. "
        "No 'hey I love your work'. Natural closer."
    ),
    "essay": (
        "Turn this into a well-structured short essay by Praful (18, builder, learner). "
        "Thesis, 2-3 body paragraphs, conclusion. "
        "Voice: clear, thoughtful, no fluff. Under 300 words."
    ),
}


def ghost_write(query: str) -> str:
    t = query.lower()
    fmt, raw = _detect_format(t, query)

    if not raw.strip():
        formats = ", ".join(FORMAT_PROMPTS.keys())
        return f"What should I write? Say: 'ghost write a blog post about [your ideas]'. Formats: {formats}."

    system_prompt = FORMAT_PROMPTS.get(fmt, FORMAT_PROMPTS["blog"])
    full_prompt = f"{system_prompt}\n\nRaw input from Praful: {raw}"

    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": 500,
        "temperature": 0.82,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"].strip()
        return f"Here's your {fmt}: {result}"
    except Exception as e:
        return f"Ghost write failed: {e}"


def _detect_format(t: str, original: str) -> tuple[str, str]:
    fmt_map = {
        "blog": ["blog", "blog post", "article"],
        "linkedin": ["linkedin", "linked in"],
        "tweet": ["tweet", "twitter", "thread", "x post"],
        "email": ["email", "e-mail", "mail to"],
        "cover_letter": ["cover letter", "application letter", "job application"],
        "cold_dm": ["cold dm", "cold message", "dm to", "outreach"],
        "essay": ["essay", "write up", "writeup"],
    }
    detected = "blog"
    for fmt, keywords in fmt_map.items():
        if any(k in t for k in keywords):
            detected = fmt
            break

    # Strip the format trigger from the raw content
    strip_patterns = [
        r"ghost write (a |an )?(blog post|linkedin post|tweet thread|email|cover letter|cold dm|essay|article|thread|writeup)\s*(about|for|on|to)?\s*[:\-]?\s*",
        r"turn this into (a |an )?(blog post|linkedin post|tweet|email|cover letter|cold dm|essay)\s*[:\-]?\s*",
        r"write (me )?(a |an )?(blog post|linkedin post|tweet thread|email|cover letter|cold dm|essay)\s*(about|for|on|to)?\s*[:\-]?\s*",
    ]
    raw = original
    for pattern in strip_patterns:
        raw = re.sub(pattern, "", raw, flags=re.IGNORECASE).strip()

    return detected, raw
