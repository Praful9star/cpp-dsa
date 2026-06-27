"""
tools/web_search.py — Free web search via DuckDuckGo HTML endpoint.

Uses only the 'requests' package (already installed). No API key, no Rust,
no extra dependencies.
"""

import re
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    )
}


def web_search(query: str, max_results: int = 4) -> str:
    """
    Search DuckDuckGo and return a plain-text summary of the top results.
    """
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": "", "kl": "in-en"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        html = resp.text

        # Extract result snippets with simple regex — no BeautifulSoup needed
        # DDG HTML results look like: class="result__snippet">...text...</a>
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )

        # Clean HTML tags from extracted text
        def strip_tags(text):
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

        results = []
        for title, snippet in zip(titles[:max_results], snippets[:max_results]):
            t = strip_tags(title)
            s = strip_tags(snippet)
            if t or s:
                results.append(f"• {t}: {s}")

        if not results:
            return f"I searched for '{query}' but couldn't find useful results."

        return f"Search results for '{query}':\n" + "\n".join(results)

    except requests.exceptions.ConnectionError:
        return "Can't reach the internet for search right now."
    except Exception as e:
        return f"Web search failed: {e}"
