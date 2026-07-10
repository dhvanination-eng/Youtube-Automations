import os
import random
import requests
from pathlib import Path
from shared_core.config import PEXELS_API_KEY

# Fallback background video URLs in case Pexels API fails or key is missing
FALLBACK_BACKGROUND_URLS = [
    "https://github.com/intel-iot-devkit/sample-videos/raw/master/classroom.mp4",
    "https://github.com/intel-iot-devkit/sample-videos/raw/master/person-bicycle-car-detection.mp4"
]

def search_pexels_video(query, output_path, channel_assets_dir=None):
    """
    Searches for a background video. 
    First checks if a local video is available in channel_assets_dir/videos/.
    If not, queries Pexels API, and finally falls back to a remote URL download.
    """
    import shutil
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Step 1: Check for local videos in channel assets
    if channel_assets_dir:
        local_videos_dir = Path(channel_assets_dir) / "videos"
        if local_videos_dir.exists() and local_videos_dir.is_dir():
            local_vids = [f for f in local_videos_dir.glob("*") if f.suffix.lower() in [".mp4", ".mov", ".avi"]]
            if local_vids:
                selected_vid = random.choice(local_vids)
                print(f"[Asset Hunter] Sourced local background video: {selected_vid.name}")
                try:
                    shutil.copy(str(selected_vid), output_path)
                    return True
                except Exception as e:
                    print(f"[Asset Hunter Warning] Failed to copy local video: {e}. Falling back to Pexels...")

    # Step 2: Query Pexels API
    if PEXELS_API_KEY:
        try:
            print(f"[Asset Hunter] Searching Pexels for vertical videos of '{query}'...")
            url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&per_page=5&orientation=portrait"
            headers = {"Authorization": PEXELS_API_KEY}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                if videos:
                    # Select the first video and find an appropriate link
                    video = videos[0]
                    video_files = video.get("video_files", [])
                    
                    # Sort files by width to get a vertical HD link (width around 1080 is ideal)
                    best_link = None
                    for vf in sorted(video_files, key=lambda x: abs(x.get("width", 0) - 1080)):
                        if vf.get("link"):
                            best_link = vf["link"]
                            break
                            
                    if best_link:
                        print(f"[Asset Hunter] Downloading Pexels video: {best_link[:80]}...")
                        vid_resp = requests.get(best_link, timeout=30)
                        if vid_resp.status_code == 200:
                            with open(output_path, "wb") as f:
                                f.write(vid_resp.content)
                            print(f"[Asset Hunter] Saved Pexels video to {output_path}")
                            return True
        except Exception as e:
            print(f"[Asset Hunter] Pexels API search failed: {e}")
            
    # Step 3: Fallback download
    print("[Asset Hunter] Using fallback background video loop...")
    fallback_url = random.choice(FALLBACK_BACKGROUND_URLS)
    try:
        vid_resp = requests.get(fallback_url, timeout=30)
        if vid_resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(vid_resp.content)
            print(f"[Asset Hunter] Saved fallback video to {output_path}")
            return True
    except Exception as e:
        print(f"[Asset Hunter] Failed to download fallback video: {e}")
        
    return False

def generate_fallback_card(output_path):
    """
    Generates a high-quality, stylized dark-theme card with a gold border using PIL
    to serve as a foolproof local fallback visual when APIs fail.
    """
    from PIL import Image, ImageDraw
    print("[Asset Hunter] Creating stylized PIL placeholder card as visual fallback...")
    
    # 600x600 dark charcoal canvas
    card = Image.new("RGBA", (600, 600), (25, 25, 25, 255))
    draw = ImageDraw.Draw(card)
    
    # Draw double gold borders for vintage aesthetic
    gold_color = (212, 175, 55, 255)
    # Outer gold border
    draw.rectangle([25, 25, 575, 575], outline=gold_color, width=4)
    # Inner gold border
    draw.rectangle([35, 35, 565, 565], outline=gold_color, width=2)
    
    # Draw an abstract historical hourglass graphic in the center
    # Hourglass top bulb
    draw.polygon([(250, 180), (350, 180), (300, 250)], fill=(212, 175, 55, 180))
    # Hourglass bottom bulb
    draw.polygon([(300, 250), (250, 320), (350, 320)], fill=(212, 175, 55, 180))
    # Hourglass top/bottom plates
    draw.line([(240, 170), (360, 170)], fill=gold_color, width=8)
    draw.line([(240, 330), (360, 330)], fill=gold_color, width=8)
    
    # Draw decorative antique stars in corners
    for cx, cy in [(80, 80), (520, 80), (80, 520), (520, 520)]:
        draw.line([(cx-10, cy), (cx+10, cy)], fill=gold_color, width=2)
        draw.line([(cx, cy-10), (cx, cy+10)], fill=gold_color, width=2)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Save as JPEG
    card.convert("RGB").save(output_path, "JPEG")
    print(f"[Asset Hunter] Saved fallback placeholder card to {output_path}")
    return True

def generate_history_visual(fact_text, output_path):
    """
    Downloads an AI image explaining the fact using Pollinations.ai (free & no-key).
    We form a descriptive prompt from the fact contents and retry with timeout.
    """
    clean_fact = fact_text.replace("<yellow>", "").replace("</yellow>", "").replace("<red>", "").replace("</red>", "")
    
    image_prompt = (
        f"A striking museum display showcase of {clean_fact}. "
        f"Aesthetic historical archaeological artifact, extreme detail, "
        f"photorealistic museum lighting, depth of field, 4k resolution"
    )
    
    if len(image_prompt) > 400:
        image_prompt = image_prompt[:400]
        
    seed = random.randint(1, 999999)
    url = f"https://image.pollinations.ai/p/{requests.utils.quote(image_prompt)}?width=600&height=600&seed={seed}&nologo=true"
    
    # Try requesting with retries
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"[Asset Hunter] Generating Pollinations AI visual (Attempt {attempt}/{max_retries})...")
        try:
            # 45 seconds timeout per attempt
            response = requests.get(url, timeout=45)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                print(f"[Asset Hunter] AI visual successfully saved to {output_path}")
                return True
        except Exception as e:
            print(f"[Asset Hunter] Attempt {attempt} failed: {e}")
            
    # If all attempts fail, trigger local Pillow fallback card generator
    return generate_fallback_card(output_path)

def fetch_local_music(channel_assets_dir):
    """
    Searches the channel assets directory for any background music files (.mp3, .wav).
    Returns a random file path or None if no files are found.
    """
    music_dir = Path(channel_assets_dir) / "music"
    if not music_dir.exists():
        return None
        
    music_files = [f for f in music_dir.glob("*") if f.suffix.lower() in [".mp3", ".wav"]]
    if music_files:
        selected_music = random.choice(music_files)
        print(f"[Asset Hunter] Selected background beat: {selected_music.name}")
        return str(selected_music)
        
    return None

if __name__ == "__main__":
    # Quick visual download test
    test_path = "scratch_test_image.jpg"
    generate_history_visual("an ancient Roman golden coin discovered in Pompeii", test_path)
    if os.path.exists(test_path):
        print("Success! Test image downloaded.")
        os.remove(test_path)
