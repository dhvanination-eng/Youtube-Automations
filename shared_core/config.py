import os
import json
from pathlib import Path

# Paths
SHARED_CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SHARED_CORE_DIR.parent
CHANNELS_DIR = PROJECT_ROOT / "5_second_video_channels"

# Video dimensions & properties (Optimized for YouTube Shorts 9:16)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
TARGET_DURATION = 5.8  # Retention-hack loops: strictly 5.0 to 6.0 seconds
DARKEN_FACTOR = 0.5    # Darken background by 50% for high contrast text readability

# Load centralized keys from api_keys.json if present
root_keys = {}
possible_keys_paths = [
    SHARED_CORE_DIR / "api_keys.json",
    PROJECT_ROOT / "api_keys.json"
]
for path in possible_keys_paths:
    if path.exists():
        try:
            with open(path, "r") as kf:
                root_keys = json.load(kf)
            break
        except Exception as e:
            print(f"[Config Warning] Failed to parse api_keys.json at {path}: {e}")

# Resolve API keys: environment variables override local json files
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", root_keys.get("PEXELS_API_KEY", ""))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", root_keys.get("GEMINI_API_KEY", ""))

# Clean placeholder template strings
if PEXELS_API_KEY.startswith("YOUR_"):
    PEXELS_API_KEY = ""
if GEMINI_API_KEY.startswith("YOUR_"):
    GEMINI_API_KEY = ""

# Ollama Local Configuration (For local test environments)
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
