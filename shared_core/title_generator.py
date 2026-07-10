import os
import re
import requests
from shared_core.config import GEMINI_API_KEY

def generate_video_title(script_text, yt_search_query=None, fallback_title=None):
    """
    Generates a simple, human-understandable video title summarizing the script text.
    Pivots: AI -> Fallback Config Title -> Algorithmic Summary -> Default query capitalize.
    """
    # 1. Try AI Generation
    if GEMINI_API_KEY:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""You are a content director writing an engaging, simple, and clean title for a short video.
The video script content is:
"{script_text}"

Rules:
1. Write a very simple, human-understandable title summarizing the actual event in the video.
2. The title must be strictly between 3 and 6 words.
3. Do not use quotes, hashtags, punctuation, or clickbaity all-caps (e.g., write "Google's $12 Mistake" instead of "YOU WON'T BELIEVE WHAT GOOGLE DID!").
4. Return ONLY the plain text title. No other explanation."""

        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                title = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Strip wrapping quotes if any
                title = re.sub(r'^["\']|["\']$', '', title)
                if 5 < len(title) < 60:
                    print(f"[Title Generator] Generated AI title: {title}")
                    return title
        except Exception as e:
            print(f"[Title Generator Warning] AI title generation failed: {e}")

    # 2. Fallback to predefined title in fallback config
    if fallback_title:
        print(f"[Title Generator] Sourced predefined title: {fallback_title}")
        return fallback_title

    # 3. Algorithmic fallback using query text
    if yt_search_query:
        # Clean up search query by removing fluff words like drone, loop, vertical, background, test
        fluff_words = ["drone", "loop", "vertical", "background", "shot", "footage", "aesthetic", "4k", "hd", "test", "close", "up", "zoom"]
        words = yt_search_query.split()
        cleaned_words = [w for w in words if w.lower() not in fluff_words]
        # Capitalize and join
        algo_title = " ".join(cleaned_words).title()
        if len(algo_title) > 5:
            print(f"[Title Generator] Generated algorithmic title: {algo_title}")
            return algo_title

    return "Amazing Fact"
