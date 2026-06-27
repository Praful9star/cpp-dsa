"""
tools/translate.py — Free translation via MyMemory API. No key needed.

"Translate hello to Hindi"
"How do you say thank you in French"
"Translate: main theek hoon — to English"
"""
import requests
import re

LANG_MAP = {
    "hindi":      "hi",
    "english":    "en",
    "french":     "fr",
    "spanish":    "es",
    "german":     "de",
    "japanese":   "ja",
    "chinese":    "zh",
    "arabic":     "ar",
    "portuguese": "pt",
    "russian":    "ru",
    "italian":    "it",
    "korean":     "ko",
    "urdu":       "ur",
    "punjabi":    "pa",
    "bengali":    "bn",
    "tamil":      "ta",
    "telugu":     "te",
    "marathi":    "mr",
    "gujarati":   "gu",
}


def translate(query: str) -> str:
    """Detect text and target language from query, translate, return result."""
    t = query.lower()

    # Detect target language
    target_lang = "hi"  # default to Hindi
    target_name = "Hindi"
    for lang_name, code in LANG_MAP.items():
        if lang_name in t:
            target_lang = code
            target_name = lang_name.title()
            break

    # Extract text to translate
    text_to_translate = _extract_text(query)
    if not text_to_translate:
        return "What would you like me to translate? Say 'translate [text] to [language]'."

    # Detect source (assume English unless it's clearly not)
    source_lang = "en"
    if target_lang == "en":
        source_lang = "auto"

    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q":       text_to_translate,
                "langpair": f"{source_lang}|{target_lang}",
            },
            timeout=10,
        )
        data = resp.json()
        translation = data["responseData"]["translatedText"]

        if not translation or translation == text_to_translate:
            return f"Couldn't translate that. Try again with clearer phrasing."

        return f"'{text_to_translate}' in {target_name} is: {translation}"

    except requests.exceptions.ConnectionError:
        return "Can't reach translation service — check your internet."
    except Exception as e:
        return f"Translation failed: {e}"


def _extract_text(query: str) -> str:
    """Pull out the actual text to translate from the spoken query."""
    q = query

    # "translate X to Y" → X
    m = re.search(r"translate[:\s]+(.+?)\s+to\s+\w+", q, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # "how do you say X in Y"
    m = re.search(r"say\s+(.+?)\s+in\s+\w+", q, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # "what is X in Y"
    m = re.search(r"what is\s+(.+?)\s+in\s+\w+", q, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # After "translate:" or "translate "
    m = re.search(r"translate[:\s]+(.+)", q, re.IGNORECASE)
    if m:
        # Remove trailing language name
        text = m.group(1).strip()
        for lang in LANG_MAP:
            text = re.sub(rf"\s+to\s+{lang}\s*$", "", text, flags=re.IGNORECASE)
        return text.strip()

    return ""
