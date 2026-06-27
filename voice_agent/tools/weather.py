"""
tools/weather.py — Weather via wttr.in (free, no API key needed).

"What's the weather in Lucknow"
"Weather today"
"Will it rain tomorrow"
"Weather forecast"
"""

import requests
import re

DEFAULT_CITY = "Lucknow"  # Praful's home city


def get_weather(query: str = "") -> str:
    """Fetch current weather and short forecast. Defaults to Lucknow."""
    city = _extract_city(query) or DEFAULT_CITY

    try:
        # wttr.in returns structured JSON
        resp = requests.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=10,
            headers={"User-Agent": "voice-agent/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()

        current = data["current_condition"][0]
        weather_desc = current["weatherDesc"][0]["value"]
        temp_c       = current["temp_C"]
        feels_like   = current["FeelsLikeC"]
        humidity     = current["humidity"]
        wind_kmph    = current["windspeedKmph"]

        # Today and tomorrow forecast
        days = data.get("weather", [])
        today    = days[0] if len(days) > 0 else None
        tomorrow = days[1] if len(days) > 1 else None

        result = (
            f"Weather in {city}: {weather_desc}. "
            f"{temp_c}°C, feels like {feels_like}°C. "
            f"Humidity {humidity}%, wind {wind_kmph} km/h."
        )

        if today:
            max_c = today["maxtempC"]
            min_c = today["mintempC"]
            result += f" Today's high is {max_c}°C, low {min_c}°C."

        if tomorrow:
            t_desc = tomorrow["hourly"][4]["weatherDesc"][0]["value"]
            t_max  = tomorrow["maxtempC"]
            result += f" Tomorrow: {t_desc}, up to {t_max}°C."

        return result

    except requests.exceptions.ConnectionError:
        return "Can't reach weather service — check your internet."
    except Exception as e:
        return f"Couldn't fetch weather: {e}"


def _extract_city(text: str) -> str:
    """Try to pull a city name from the query."""
    t = text.lower()
    for kw in ["weather in ", "weather for ", "weather at ", "in ", "for "]:
        idx = t.find(kw)
        if idx != -1:
            city = text[idx + len(kw):].strip(" ?.!")
            if city and len(city) > 1 and city.lower() not in ("today", "tomorrow", "now"):
                return city
    return ""
