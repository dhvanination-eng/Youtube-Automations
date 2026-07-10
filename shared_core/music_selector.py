import os
import random
import requests
from pathlib import Path
from shared_core.config import GEMINI_API_KEY

MUSIC_DIR = Path(__file__).resolve().parent / "music"

MUSIC_CATEGORIES = {
    "tech_upbeat": "tech_upbeat.mp3",
    "ambient_storytelling": "ambient_storytelling.mp3",
    "rivalry_dramatic": "rivalry_dramatic.mp3",
    "tension_crime": "tension_crime.mp3",
    "satisfying_upbeat": "satisfying_upbeat.mp3",
    "mystery_intellectual": "mystery_intellectual.mp3",
    "epic_majestic": "epic_majestic.mp3",
    "space_futuristic": "space_futuristic.mp3",
    "inspire_dramatic": "inspire_dramatic.mp3",
    "dark_suspense": "dark_suspense.mp3",
    "epic_historical": "epic_historical.mp3",
    "action_heavy": "action_heavy.mp3",
    "disaster_grand": "disaster_grand.mp3"
}

def classify_music_via_gemini(script_text):
    """
    Uses Gemini API to classify the script text into a matching music category.
    """
    if not GEMINI_API_KEY:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""You are an audio director selecting background music for a short documentary script.
Analyze the following script text:
"{script_text}"

Classify it into EXACTLY one of the following categories based on its theme, emotion, and pace:
- tech_upbeat (tech trivia, Google, internet, quick business tricks)
- ambient_storytelling (quiet documentary, neutral narration, deep thoughts)
- rivalry_dramatic (clashes, battles, business rivalry, revenge, success against odds)
- tension_crime (suspense, illegal, heist, money schemes, escape)
- satisfying_upbeat (satisfying actions, visual beauty, symmetry, relaxing lofi vibe)
- mystery_intellectual (riddles, puzzles, secrets, signature, hidden codes)
- epic_majestic (deep emotional wonder, sunset, Jean-Claude Van Damme epic split, nostalgia)
- space_futuristic (planets, cosmos, alien, futuristic science, universe)
- inspire_dramatic (inspiration, turning point, startup choices, flappy bird maker)
- dark_suspense (danger, swamp diver, horror elements, ghost story, zero visibility)
- epic_historical (ancient kingdoms, Roman emperors, bowing, legends, old battles)
- action_heavy (demolition, heavy machinery, high speed, physical impact)
- disaster_grand (engineering failures, natural disasters, Niagara Falls shutting down, immense power)

Respond with ONLY the exact category name from the list above (e.g., 'tech_upbeat'). Do not write any other words or punctuation."""

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
            category = result["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
            if category in MUSIC_CATEGORIES:
                print(f"[Music Selector AI] AI classified script as category: {category}")
                return category
    except Exception as e:
        print(f"[Music Selector AI Warning] AI classification failed: {e}")
        
    return None

def classify_music_via_rules(script_text):
    """
    A rule-based thinking system that checks for key terms to select a music category.
    """
    text = script_text.lower()
    
    # 1. Space / futuristic
    if any(w in text for w in ["space", "planet", "alien", "universe", "cosmos", "galaxy", "orbit", "astronaut"]):
        return "space_futuristic"
        
    # 2. Dark / suspense
    if any(w in text for w in ["diver", "swamp", "visibility", "rescue", "ghost", "dark", "horror", "dangerous", "water"]):
        return "dark_suspense"
        
    # 3. Disaster / grand scale
    if any(w in text for w in ["niagara", "falls", "disaster", "engineering", "shut down", "collapsed", "flood"]):
        return "disaster_grand"
        
    # 4. Tension / crime
    if any(w in text for w in ["illegal", "crime", "heist", "prison", "escape", "flee", "police", "arrest", "steal"]):
        return "tension_crime"
        
    # 5. Tech / business upbeat
    if any(w in text for w in ["google", "ads", "adsense", "clicks", "tech", "computer", "internet", "website"]):
        return "tech_upbeat"
        
    # 6. Epic historical
    if any(w in text for w in ["rome", "roman", "emperor", "kingdom", "empire", "ancient", "bc", "medieval", "bowed"]):
        return "epic_historical"
        
    # 7. Epic majestic
    if any(w in text for w in ["mercedes", "brakes", "volvo", "trucks", "split", "van damme", "sunrise", "highway"]):
        return "epic_majestic"
        
    # 8. Rivalry dramatic
    if any(w in text for w in ["disney", "fired", "dreamworks", "rivalry", "clash", "lawsuit", "battle"]):
        return "rivalry_dramatic"
        
    # 9. Inspire dramatic
    if any(w in text for w in ["walked away", "million", "flappy bird", "creator", "abandoned", "quit"]):
        return "inspire_dramatic"
        
    # 10. Action heavy
    if any(w in text for w in ["demolish", "demolition", "bottom", "crush", "dynamite", "explosion"]):
        return "action_heavy"
        
    # 11. Satisfying upbeat
    if any(w in text for w in ["satisfying", "cgi", "sunday", "morning", "beauty", "aesthetic", "smooth"]):
        return "satisfying_upbeat"
        
    # 12. Mystery intellectual
    if any(w in text for w in ["signature", "sign", "code", "riddle", "mystery", "puzzle", "secret"]):
        return "mystery_intellectual"
        
    return None

def select_music_for_fact(script_text):
    """
    Selects background music matching the fact text.
    Pivots from AI -> Rule-based thinking -> Randomness.
    """
    # Step 1: Try AI classification
    category = classify_music_via_gemini(script_text)
    
    # Step 2: Fallback to rule-based thinking system
    if not category:
        print("[Music Selector] AI unavailable or failed. Pivoting to Rule-Based Thinking System...")
        category = classify_music_via_rules(script_text)
        if category:
            print(f"[Music Selector Rules] Rule-based system matched category: {category}")
            
    # Step 3: Fallback to complete randomness
    if not category:
        print("[Music Selector] No rule matched. Pivoting to Randomness...")
        category = random.choice(list(MUSIC_CATEGORIES.keys()))
        print(f"[Music Selector Random] Randomly selected category: {category}")
        
    filename = MUSIC_CATEGORIES[category]
    music_path = MUSIC_DIR / filename
    
    if music_path.exists():
        return str(music_path)
    else:
        # Emergency backup: if file doesn't exist, search the folder for any mp3
        all_songs = list(MUSIC_DIR.glob("*.mp3"))
        if all_songs:
            return str(random.choice(all_songs))
            
    return None
