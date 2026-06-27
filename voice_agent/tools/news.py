"""
tools/news.py — Fetch news headlines from free RSS feeds. No API key needed.
"""
import requests
import re


FEEDS = {
    "world":  "https://feeds.bbci.co.uk/news/world/rss.xml",
    "india":  "https://feeds.bbci.co.uk/news/world/south_asia/rss.xml",
    "tech":   "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "sports": "https://feeds.bbci.co.uk/sport/rss.xml",
    "cricket":"https://feeds.bbci.co.uk/sport/cricket/rss.xml",
}
DEFAULT_FEED = "world"


def get_news(query: str = "", count: int = 5) -> str:
    """Fetch and return top headlines based on topic."""
    q = query.lower()

    topic = DEFAULT_FEED
    for key in FEEDS:
        if key in q:
            topic = key
            break

    # India news if "india" mentioned
    if "india" in q or "indian" in q:
        topic = "india"
    if "cricket" in q or "ipl" in q:
        topic = "cricket"
    if "tech" in q or "technology" in q or "ai" in q:
        topic = "tech"
    if "sport" in q or "football" in q:
        topic = "sports"

    url = FEEDS.get(topic, FEEDS[DEFAULT_FEED])

    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        # Extract CDATA titles
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", resp.text)
        if not titles:
            # Fallback: plain title tags
            titles = re.findall(r"<title>(.*?)</title>", resp.text)

        # Skip the feed's own title (first item)
        headlines = [t.strip() for t in titles[1:count+1] if t.strip()]

        if not headlines:
            return "Couldn't fetch news right now. Check your internet."

        topic_label = topic.title()
        result = f"Top {topic_label} headlines: "
        result += ". ".join(f"{i+1}. {h}" for i, h in enumerate(headlines)) + "."
        return result

    except requests.exceptions.ConnectionError:
        return "Can't reach the news right now — check your internet."
    except Exception as e:
        return f"News fetch failed: {e}"
