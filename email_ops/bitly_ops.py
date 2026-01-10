"""
bitly_utils.py — URL Shortening via Bitly API
----------------------------------------------
Safely shortens Gmail URLs before sending them via WhatsApp notifications.
If Bitly is unavailable or the token is missing, the system falls back to the original link.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BITLY_ACCESS_TOKEN = os.getenv("BITLY_ACCESS_TOKEN")


def shorten_url(long_url: str) -> str:
    """
    Shorten a long Gmail URL using Bitly API.
    Falls back to original URL if Bitly is not configured or fails.
    """
    if not BITLY_ACCESS_TOKEN:
        print("[Bitly] ⚠️ No Bitly access token found. Using full Gmail link instead.")
        return long_url

    bitly_api = "https://api-ssl.bitly.com/v4/shorten"
    headers = {"Authorization": f"Bearer {BITLY_ACCESS_TOKEN}"}
    payload = {"long_url": long_url}

    try:
        print(f"[Bitly] 🔗 Shortening URL: {long_url}")
        response = requests.post(bitly_api, json=payload, headers=headers, timeout=8)
        response.raise_for_status()
        data = response.json()
        short_url = data.get("link")

        if short_url:
            print(f"[Bitly] ✅ Shortened URL: {short_url}")
            return short_url
        else:
            print("[Bitly] ⚠️ API returned no link field. Using full URL instead.")
            return long_url

    except requests.exceptions.RequestException as e:
        print(f"[Bitly] ❌ Failed to shorten URL ({e}). Using full Gmail link instead.")
        return long_url
