"""
tools/youtube_summary.py — Summarize YouTube videos via subtitles + Groq.

"Summarize this video: youtube.com/watch?v=..."
"What is this video about: youtu.be/..."
"""

import subprocess
import os
import re
import json
import tempfile
import requests
import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def summarize_youtube(query: str) -> str:
    url = _extract_url(query)
    if not url:
        return "Give me the YouTube URL and I'll summarize it. Like: 'summarize youtube.com/watch?v=...'"

    subtitles = _fetch_subtitles(url)
    if subtitles:
        return _ask_groq(subtitles, "subtitle transcript")

    meta = _fetch_meta(url)
    if meta:
        return _ask_groq(meta, "video metadata")

    return "Couldn't get subtitles or description for that video."


def _extract_url(query: str) -> str | None:
    m = re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w\-]+(?:&\S*)?', query)
    return m.group(0) if m else None


def _fetch_subtitles(url: str) -> str | None:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["python", "-m", "yt_dlp",
                 "--write-auto-sub", "--skip-download",
                 "--sub-format", "vtt", "--sub-lang", "en",
                 "-o", os.path.join(tmpdir, "video"), url],
                capture_output=True, text=True, timeout=60,
            )
            for fname in os.listdir(tmpdir):
                if fname.endswith(".vtt"):
                    with open(os.path.join(tmpdir, fname)) as f:
                        return _clean_vtt(f.read())
    except Exception:
        pass
    return None


def _clean_vtt(vtt: str) -> str:
    lines, seen = [], set()
    for line in vtt.splitlines():
        line = re.sub(r'<[^>]+>', '', line).strip()
        if not line or '-->' in line or line.startswith('WEBVTT') or re.match(r'^\d+$', line):
            continue
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return ' '.join(lines)[:4000]


def _fetch_meta(url: str) -> str | None:
    try:
        res = subprocess.run(
            ["python", "-m", "yt_dlp", "--dump-json", "--no-playlist", url],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(res.stdout)
        title = data.get("title", "")
        desc = (data.get("description") or "")[:1200]
        return f"Title: {title}\nDescription: {desc}"
    except Exception:
        return None


def _ask_groq(content: str, source: str) -> str:
    prompt = (f"Summarize this YouTube video ({source}) in 4-5 natural spoken sentences. "
              f"Highlight the key points and main takeaway. No bullet points, no markdown.\n\n{content}")
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.5,
    }
    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Summary failed: {e}"
