import os
import re
import json
import random
import requests
from shared_core.config import GEMINI_API_KEY, OLLAMA_API_URL, OLLAMA_MODEL

# Fallback facts database in case API calls fail or rate-limits occur
FALLBACK_FACTS = [
    {
        "yt_search_query": "mercedes safety truck semi braking road test",
        "text_block": "A 20-ton semi truck <red>just outbraked your car.</red> Mercedes engineers <yellow>made it stop from 93 mph in seconds</yellow> — no swerve, no skid, no drama. <red>Sensors react faster than any driver could.</red> Picture your car's brakes doing that at highway speed, <yellow>fully loaded, without losing control.</yellow> That's the future rolling toward <red>every road on Earth.</red>"
    },
    {
        "yt_search_query": "roman empire coliseum drone shot",
        "text_block": "The ancient Romans used to clean and whiten their teeth using <yellow>human urine</yellow>. It was so valuable that they even established a <red>urine tax</red> on the public collections."
    },
    {
        "yt_search_query": "voyager spacecraft deep space",
        "text_block": "The computers on the <yellow>Voyager 1 spacecraft</yellow> possess only sixty-nine kilobytes of memory. That is hundreds of thousands of times less capacity than a <red>standard car key fob</red> today."
    },
    {
        "yt_search_query": "oxford university old library",
        "text_block": "Oxford University is actually older than the <yellow>Aztec Empire</yellow>. The school began teaching in ten ninety-six, whereas the Aztec civilization was founded in <red>fourteen twenty-eight</red>."
    }
]

SYSTEM_PROMPT = """You are an expert YouTube Shorts scriptwriter for a "History Explained" channel. Your goal is to write a single, mind-bending historical fact, paradox, or engineering marvel (strictly between 30 and 45 words).

CRITICAL RULES:
1. You must output ONLY a valid JSON object. Do not include markdown code block formatting (like ```json ... ```).
2. Wrap exactly 2 or 3 shocking phrases or important keywords in `<red>` or `<yellow>` HTML tags (e.g. `<yellow>first moon landing</yellow>` or `<red>Great Pyramids of Giza</red>`) so our video renderer can highlight them.
3. Provide a `yt_search_query` to find highly relevant, aesthetic royalty-free background footage (e.g., historical timelapses, drone shots, or archival footage).
4. The script word count must be strictly between 30 and 45 words (excluding the HTML tags themselves).
5. Provide a highly descriptive `image_prompt` for a text-free visual card illustrating the fact. The prompt must describe a photorealistic, high-detail, artistic image, and explicitly state that it must not contain any text, writing, labels, or letters.

Required JSON structure:
{
  "yt_search_query": "relevant background video search terms",
  "text_block": "The complete fact script text with highlight tags...",
  "image_prompt": "highly detailed image generation prompt, photorealistic, no text, no letters, artistic lighting, 4k"
}"""

def clean_html_tags(text):
    """Strips HTML tags to count words accurately."""
    return re.sub(r'<[^>]+>', '', text)

def count_words(text):
    """Counts the words in a text after removing tags."""
    return len(clean_html_tags(text).split())

def parse_json_robustly(text):
    """Clean and parse JSON from API response, resolving common formatting issues."""
    text = text.strip()
    # Remove markdown code block formatting
    if text.startswith("```"):
        match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
            
    try:
        return json.loads(text)
    except Exception as e:
        # Extract JSON content between first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
        raise e


def fetch_reddit_til():
    """
    Fetches the top trending titles from Reddit's r/todayilearned.
    Used to seed the LLM with viral historical fact concepts.
    """
    url = "https://www.reddit.com/r/todayilearned/hot.json?limit=10"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            facts = []
            for post in posts:
                title = post.get("data", {}).get("title", "")
                # Clean prefix TIL or TIL that
                title_clean = re.sub(r'^(TIL|today i learned|today ilearned)\s+(that|about)?\s*', '', title, flags=re.IGNORECASE).strip()
                if title_clean:
                    facts.append(title_clean)
            return facts
    except Exception as e:
        print(f"[Reddit Scraper] Failed to fetch facts: {e}")
    return []

def generate_script_via_gemini(system_prompt, seed_concept=None):
    """Calls the Google Gemini API to generate the JSON script."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")
        
    prompt = system_prompt
    if seed_concept:
        prompt += f"\n\nHere is a raw historical seed fact you must adapt into the retention-hacked format: {seed_concept}"
    else:
        prompt += "\n\nGenerate a brand new mind-bending historical fact."

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    last_error = None
    # Try gemini-3-flash-preview first (has strong caching), fallback to newer/older models
    for model in ["gemini-3-flash-preview", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            response = requests.post(url, json=payload, timeout=30)

            response.raise_for_status()
            result = response.json()
            text_content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return parse_json_robustly(text_content)
        except Exception as e:
            last_error = e
            print(f"[LLM Engine] Failed to generate script using {model}: {e}")
            continue
            
    if last_error:
        raise last_error


def generate_script_via_ollama(system_prompt, seed_concept=None):
    """Calls the local Ollama API to generate the JSON script."""
    url = f"{OLLAMA_API_URL}/api/generate"
    
    prompt = system_prompt
    if seed_concept:
        prompt += f"\n\nHere is a raw historical seed fact you must adapt into the retention-hacked format: {seed_concept}"
    else:
        prompt += "\n\nGenerate a brand new mind-bending historical fact."

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    
    text_content = result["response"].strip()
    return parse_json_robustly(text_content)

def generate_history_script(system_prompt=None, use_reddit=False, fallback_facts=None):
    """
    Main entrypoint to generate a script.
    Checks Gemini API first, falls back to Ollama, and finally falls back to static facts.
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT
    if fallback_facts is None:
        fallback_facts = FALLBACK_FACTS

    seed_concept = None
    if use_reddit:
        reddit_facts = fetch_reddit_til()
        if reddit_facts:
            seed_concept = random.choice(reddit_facts)
            print(f"[LLM Engine] Found Reddit seed: {seed_concept[:60]}...")
            
    # Try Gemini
    if GEMINI_API_KEY:
        try:
            print("[LLM Engine] Attempting Cloud Gemini API generation...")
            script = generate_script_via_gemini(system_prompt, seed_concept)
            if validate_script(script):
                return script
        except Exception as e:
            print(f"[LLM Engine] Gemini generation failed: {e}")
            
    # Try Ollama (Local)
    try:
        print(f"[LLM Engine] Attempting Local Ollama API generation using model '{OLLAMA_MODEL}'...")
        script = generate_script_via_ollama(system_prompt, seed_concept)
        if validate_script(script):
            return script
    except Exception as e:
        print(f"[LLM Engine] Ollama generation failed: {e}")

    # Final Fallback
    print("[LLM Engine] All API endpoints failed. Returning pre-configured fallback script.")
    return random.choice(fallback_facts)

def validate_script(script):
    """Validates structure and constraints of the generated JSON script."""
    if not isinstance(script, dict):
        return False
    if "yt_search_query" not in script or "text_block" not in script or "image_prompt" not in script:
        print(f"[LLM Engine] Validation failed: Missing keys in script {script}")
        return False
        
    word_count = count_words(script["text_block"])
    print(f"[LLM Engine] Generated script text: '{script['text_block']}' ({word_count} words)")
    
    if word_count < 25 or word_count > 50:
        print(f"[LLM Engine] Word count ({word_count}) is outside target range (25-50 words). Rejecting script.")
        return False
        
    # Check for highlight tags
    if "<yellow>" not in script["text_block"] and "<red>" not in script["text_block"]:
        print("[LLM Engine] Script contains no highlight tags. Rejecting script.")
        return False
        
    return True

def generate_batch_via_gemini(system_prompt, existing_facts, count=100):
    """
    Generates a batch of unique history scripts using Gemini, preventing duplicate concepts.
    """
    import time
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")

    generated_scripts = []
    chunk_size = 25
    remaining = count

    while remaining > 0:
        current_request_count = min(chunk_size, remaining)
        print(f"[LLM Engine] Requesting chunk of {current_request_count} scripts from Gemini (remaining: {remaining - current_request_count})...")
        
        # Combine system prompt with exclusion context
        exclusion_text = ""
        all_existing = existing_facts + [s.get("text_block", "") for s in generated_scripts]
        if all_existing:
            # Show only the last 150 facts to keep context clean but informative
            recent_facts = all_existing[-150:]
            exclusion_text = "\n\nCRITICAL: DO NOT generate facts about any of the following topics or reuse these concepts:\n"
            for fact in recent_facts:
                exclusion_text += f"- {fact[:120]}\n"
        
        prompt = system_prompt + exclusion_text
        prompt += f"\n\nGenerate exactly {current_request_count} unique, mind-bending historical fact scripts following the instructions above."
        prompt += "\nReturn a valid JSON array of objects, where each object has exactly the keys 'yt_search_query' and 'text_block'."

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        success = False
        last_error = None
        # Try gemini-3-flash-preview first (has strong caching), fallback to newer/older models
        for model in ["gemini-3-flash-preview", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                result = response.json()
                text_content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                scripts_chunk = parse_json_robustly(text_content)
                if isinstance(scripts_chunk, list):
                    generated_scripts.extend(scripts_chunk)
                    remaining -= len(scripts_chunk)
                    success = True
                    break
                elif isinstance(scripts_chunk, dict) and "scripts" in scripts_chunk:
                    s_list = scripts_chunk["scripts"]
                    if isinstance(s_list, list):
                        generated_scripts.extend(s_list)
                        remaining -= len(s_list)
                        success = True
                        break
            except Exception as e:
                last_error = e
                print(f"[LLM Engine] Failed chunk generation using {model}: {e}")
                continue
                
        if not success:
            print(f"[LLM Engine] Failed to get valid chunk from Gemini. Stopping batch generation.")
            if last_error:
                raise last_error
            break
            
        if remaining > 0:
            print("[LLM Engine] Sleeping for 10 seconds to respect API rate limits...")
            time.sleep(10)
            
    return generated_scripts

if __name__ == "__main__":
    # Test execution
    print("Generating sample script...")
    sample = generate_history_script(use_reddit=True)
    print(json.dumps(sample, indent=2))
