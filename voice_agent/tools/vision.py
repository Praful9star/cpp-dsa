"""
tools/vision.py — Camera vision using Groq's vision model.

Takes a photo with termux-camera, sends to Groq llama-3.2-11b-vision,
returns a natural language description.

"What do you see?"
"Read this text" (point at something written)
"What food is this?"
"Describe what's in front of me"
"Read the whiteboard"
"""

import subprocess
import base64
import os
import time
import requests
import config

PHOTO_PATH = "/data/data/com.termux/files/home/.buddy_vision.jpg"
GROQ_VISION_URL = "https://api.groq.com/openai/v1/chat/completions"
VISION_MODEL    = "meta-llama/llama-4-scout-17b-16e-instruct"  # Groq vision model


def look_and_describe(query: str = "") -> str:
    """Take a photo and describe what's in it."""

    # Take photo with termux-camera
    capture_result = _capture_photo()
    if not capture_result:
        return "Couldn't take a photo. Make sure Termux:API has camera permission."

    # Read and encode as base64
    try:
        with open(PHOTO_PATH, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"Couldn't read the photo: {e}"

    # Build the question
    if not query or query.strip().lower() in ["what do you see", "describe", "look"]:
        prompt = ("Describe what you see in this image naturally and conversationally, "
                  "like a friend describing it out loud. Keep it under 4 sentences.")
    elif any(k in query.lower() for k in ["read", "text", "write", "says", "written"]):
        prompt = "Read and transcribe all the text visible in this image."
    elif any(k in query.lower() for k in ["food", "eat", "dish", "meal"]):
        prompt = "What food or dish is in this image? Describe it briefly."
    elif any(k in query.lower() for k in ["person", "who", "face"]):
        prompt = "Describe the person or people in this image without identifying them."
    else:
        prompt = f"Look at this image and answer: {query}"

    # Call Groq vision
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }},
            ],
        }],
        "max_tokens": 300,
        "temperature": 0.5,
    }

    try:
        resp = requests.post(GROQ_VISION_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as e:
        status = resp.status_code if resp else 0
        if status == 404 or status == 400:
            # Model name changed — fall back gracefully
            return _vision_fallback(image_data, prompt)
        return f"Vision API error {status}."
    except Exception as e:
        return f"Vision failed: {e}"


def _capture_photo() -> bool:
    """Capture a photo using termux-camera-photo."""
    try:
        # Remove old photo
        if os.path.exists(PHOTO_PATH):
            os.remove(PHOTO_PATH)

        result = subprocess.run(
            ["termux-camera-photo", "-c", "0", PHOTO_PATH],
            capture_output=True, text=True, timeout=15,
        )
        time.sleep(1)  # give camera time to save
        return os.path.exists(PHOTO_PATH)

    except FileNotFoundError:
        return False
    except Exception:
        return False


def _vision_fallback(image_data: str, prompt: str) -> str:
    """Try alternate Groq vision model names if primary fails."""
    fallback_models = [
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
    ]
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    for model in fallback_models:
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                ]}],
                "max_tokens": 300,
            }
            resp = requests.post(GROQ_VISION_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return "Vision model isn't available right now. Try again later."
