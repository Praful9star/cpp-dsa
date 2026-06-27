"""
tools/briefing.py — Morning/evening briefing: weather + news + reminders + quote + streak.
"""
import datetime
import requests
from tools.weather   import get_weather
from tools.reminders import list_reminders

QUOTES = [
    "Code is like humor. When you have to explain it, it's bad. — Cory House",
    "First, solve the problem. Then, write the code. — John Johnson",
    "The best error message is the one that never shows up. — Thomas Fuchs",
    "Programs must be written for people to read, and only incidentally for machines. — Abelson",
    "Simplicity is the soul of efficiency. — Austin Freeman",
    "The most dangerous phrase is 'we've always done it this way'. — Grace Hopper",
    "Before software can be reusable it first has to be usable. — Ralph Johnson",
    "Make it work, make it right, make it fast. — Kent Beck",
    "Talk is cheap. Show me the code. — Linus Torvalds",
    "Any fool can write code that a computer can understand. Good programmers write code humans can understand.",
    "Your most unhappy customers are your greatest source of learning. — Bill Gates",
    "The function of good software is to make the complex appear simple. — Grady Booch",
]

def get_news_headlines(count: int = 4) -> list[str]:
    """Fetch top headlines from BBC RSS — no API key needed."""
    try:
        resp = requests.get(
            "https://feeds.bbci.co.uk/news/rss.xml",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        import re
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", resp.text)
        # Skip first (it's the feed title itself)
        return [t for t in titles[1:count+1] if t]
    except Exception:
        return []

def morning_briefing() -> str:
    now  = datetime.datetime.now()
    hour = now.hour

    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    parts = [f"{greeting}, Praful!"]

    # Weather
    try:
        weather = get_weather("Lucknow")
        parts.append(weather)
    except Exception:
        pass

    # News
    headlines = get_news_headlines(3)
    if headlines:
        parts.append("Here's what's happening in the world:")
        for h in headlines:
            parts.append(f"— {h}.")

    # Reminders
    reminders = list_reminders()
    if "No active" not in reminders:
        parts.append(f"Reminder check: {reminders}")

    # Countdown to CU
    cu_date = datetime.date(2025, 7, 1)
    today   = datetime.date.today()
    delta   = (cu_date - today).days
    if delta > 0:
        parts.append(f"By the way, Chandigarh University is in {delta} days. Time to prep!")
    elif delta == 0:
        parts.append("Today's the day — Chandigarh University! Let's go Praful!")

    # Quote
    import random
    parts.append(f"Quote for today: {random.choice(QUOTES)}")

    return " ".join(parts)
