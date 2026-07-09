# Master System Documentation: 5-Second Loop Video Engine

This is a modular, zero-cost automated Python pipeline built to produce "5-Second Loop" retention-hacked YouTube Shorts. The code is designed to support both local execution and automated cloud runs on platforms like GitHub Actions.

---

## 1. Core Architecture & Folder Layout

All core libraries, scraping rules, and visual compositing codes are kept in `shared_core/` to prevent duplication. Channel directories only contain configuration files, logo files, and rendered assets.

```
YouTube_Automation/
│
├── api_keys.json.template          # Global API credentials template
├── api_keys.json                   # Centralized API key storage (local run config)
├── README.md                       # Master Pipeline Documentation
│
├── shared_core/                    # Central Shared Python Modules
│   ├── config.py                   # Global constants and path resolutions
│   ├── llm_engine.py               # Ollama / Gemini API client & Reddit scraper
│   ├── asset_hunter.py             # Pexels download & Pollinations AI card fetcher
│   └── visual_engine.py            # MoviePy compositor & html2image text renderer
│
└── 5_second_video_channels/        # Channel-Specific Configurations
    ├── channel_history/
    │   ├── config.json             # Visual themes and prompt guides
    │   ├── logo.png                # Circle avatar logo
    │   └── generation_history.json # Running execution logs
    │
    ├── channel_stoic/
    ├── history_explained/
    └── sports/
```

---

## 2. Product Psychology & Layout Design

The video layout is strictly optimized for high viewer-retention loops:

* **Solid Black Background**: The composite plays on a solid black backdrop canvas (no full-screen distracting videos behind text).
* **Profile Header (Top)**: If `logo.png` exists in the channel directory, it renders the avatar image (centered, height=140px, rounded to a circle) at `y=150`. If the logo is missing, the top section remains pure black.
* **Compact Text (Middle)**: The script text block is rendered with a clean sans-serif font (**Inter**) in sentence case. The text size is small (`font-size: 32px` inside a `950x380` box). It shifts vertically depending on logo presence (`y=400` if logo exists, `y=250` if logo is missing).
* **Highlights**: Shocking phrases are wrapped in `<yellow>` or `<red>` HTML tags to render custom brand highlight colors dynamically.
* **Visual Image Card (Bottom)**: Sourced from the Pollinations AI generator and preprocessed using Pillow to crop it into a `600x600` square with rounded corners (20px radius). It displays in the lower section (`y=950`) with **no border outline** ("white box" removed).
* **Retention Hack**: The text block is designed to take slightly longer to read than the 5.8-second video duration, forcing the viewer to watch the loop repeat.

---

## 3. Configuration & Sourcing

### Global API Key Storage
API keys are centralized in `api_keys.json` at the root of the project:
* `GEMINI_API_KEY`: Free key from Google AI Studio for prompt generation.
* `PEXELS_API_KEY`: Free key from Pexels to search and download background visual assets.

### Sourcing Scriptor
* **Reddit Scraper**: Pulls top trending facts from `r/todayilearned` JSON feed to feed the LLM.
* **Ollama Fallback**: Attempts local Ollama chat completion (`llama3`) if cloud endpoints are offline.
* **Manual Forced Script**: You can bypass LLM generation entirely for testing by writing a `"forced_script"` dictionary containing the exact script text and search query directly in your channel's `config.json`.

### Running Log Consolidation
* Execution history is recorded inside each channel's directory in a single cumulative file: `generation_history.json`. It appends the timestamps, script content, music track used, and output file paths chronologically into a running list.

---

## 4. How to Generate Video

To compile video for a channel (e.g. `history_explained`):
1. Navigate to the root directory.
2. Edit `api_keys.json` to insert your keys.
3. Run:
   ```bash
   python 5_second_video_channels/history_explained/run.py
   ```
4. Output file will be saved in `5_second_video_channels/history_explained/output/` and logged in `generation_history.json`.
