"""
tools/web_search.py — Free web search via DuckDuckGo (no API key needed).

Uses the duckduckgo-search package to get real results.
Install: pip install duckduckgo-search
"""

from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 4) -> str:
    """
    Search the web and return a short summary of results.
    Returns a plain string ready to be sent back to the LLM.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"I searched for '{query}' but found nothing useful."

        lines = [f"Search results for: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body  = r.get("body", "")
            lines.append(f"{i}. {title}: {body}")

        return "\n".join(lines)

    except Exception as e:
        return f"Web search failed: {e}"
