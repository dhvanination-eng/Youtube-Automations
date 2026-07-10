import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Fix python import path resolution: ensure PROJECT_ROOT is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared_core.llm_engine import generate_history_script
from shared_core.asset_hunter import generate_history_visual, fetch_local_music
from shared_core.visual_engine import process_visual_card, render_text_overlay, create_video_composite
from shared_core.distributor import YouTubeDistributor
from shared_core.config import SHARED_CORE_DIR

def main():
    parser = argparse.ArgumentParser(description="Run YouTube Shorts Generation Pipeline for a specific channel")
    parser.add_argument("channel", type=str, help="Name of the channel folder (e.g. history_explained)")
    parser.add_argument("--upload", action="store_true", help="Upload the rendered video to YouTube using Data API")
    args = parser.parse_args()

    channel_name = args.channel
    channel_dir = PROJECT_ROOT / "5_second_video_channels" / channel_name

    if not channel_dir.exists() or not channel_dir.is_dir():
        print(f"[Error] Channel directory '{channel_dir}' does not exist.")
        sys.exit(1)

    print("====================================================")
    print(f"      Starting YouTube Shorts Generation Pipeline   ")
    print(f"      Channel: {channel_name}                       ")
    print("====================================================")

    # 1. Resolve channel directory paths
    config_path = channel_dir / "config.json"
    prompt_path = channel_dir / "prompt.txt"
    assets_dir = channel_dir / "assets"
    music_dir = assets_dir / "music"
    output_dir = channel_dir / "output"
    temp_dir = channel_dir / "temp"

    # Create directories if they do not exist
    for directory in [assets_dir, music_dir, output_dir, temp_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    # 2. Load configurations
    if not config_path.exists():
        print(f"[Error] Config file not found at {config_path}. Exiting.")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = json.load(f)

    print(f"[Run Pipeline] Loaded configuration for: {config.get('channel_name', channel_name)}")

    # Check for channel logo
    logo_filename = config.get("logo_filename", "logo.png")
    logo_path = channel_dir / logo_filename
    if not logo_path.exists():
        # Fallback to check inside assets/
        logo_path = assets_dir / logo_filename

    logo_str = str(logo_path) if logo_path.exists() else None
    if logo_str:
        print(f"[Run Pipeline] Found channel logo: {logo_str}")
    else:
        print("[Run Pipeline] No channel logo found (skipping logo overlay).")

    # Load custom system prompt
    system_prompt = None
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        print(f"[Run Pipeline] Loaded custom system prompt from prompt.txt ({len(system_prompt)} chars).")
    else:
        print("[Run Pipeline] No custom prompt.txt found. Using default system prompt.")

    # 3. Generate script via LLM or use forced override
    if "forced_script" in config:
        print("[Run Pipeline] Using FORCED script override from configuration...")
        script_data = config["forced_script"]
    else:
        use_reddit = config.get("use_reddit", True)
        fallback_facts = config.get("fallback_facts", None)
        script_data = generate_history_script(
            system_prompt=system_prompt, 
            use_reddit=use_reddit,
            fallback_facts=fallback_facts
        )

    text_block = script_data.get("text_block")

    print("\n----------------------------------------------------")
    print(f"Generated Script Text:\n{text_block}")
    print("----------------------------------------------------\n")

    # 4. Resolve temporary and output paths
    temp_visual_path = temp_dir / "temp_visual_raw.jpg"
    temp_processed_visual_path_local = temp_dir / "temp_visual_card.png"
    temp_text_overlay_path = temp_dir / "temp_text_overlay.png"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"short_{timestamp}.mp4"
    final_output_path = output_dir / output_filename

    try:
        # 5. Fetch and preprocess AI visual card (only if enabled)
        show_visual_card = config.get("show_visual_card", True)
        temp_processed_visual_path = None
        if show_visual_card:
            print("[Run Pipeline] Step 1: Sourcing AI image visual card...")
            img_success = generate_history_visual(text_block, str(temp_visual_path))
            if not img_success:
                raise RuntimeError("Failed to generate AI visual card.")

            card_success = process_visual_card(str(temp_visual_path), str(temp_processed_visual_path_local))
            if not card_success:
                raise RuntimeError("Failed to preprocess visual card image.")
            temp_processed_visual_path = str(temp_processed_visual_path_local)
        else:
            print("[Run Pipeline] Step 1: AI visual card overlay is disabled in config. Skipping.")

        # 6. Render Text Overlay via html2image
        print("[Run Pipeline] Step 2: Rendering transparent HTML/CSS text overlay...")
        theme_config = config.get("theme", {})
        text_success = render_text_overlay(
            text_block, 
            str(temp_text_overlay_path), 
            theme_config=theme_config
        )
        if not text_success:
            raise RuntimeError("Failed to render text HTML to image overlay.")

        # 7. Sourcing background audio beat
        print("[Run Pipeline] Step 3: Sourcing background audio beats...")
        from shared_core.music_selector import select_music_for_fact
        music_path = select_music_for_fact(script_data["text_block"])
        if not music_path:
            music_path = fetch_local_music(str(assets_dir))

        # 8. Composite everything using MoviePy
        print("[Run Pipeline] Step 4: Compositing and rendering video...")
        composite_success = create_video_composite(
            text_overlay_path=str(temp_text_overlay_path),
            visual_card_path=temp_processed_visual_path,
            output_video_path=str(final_output_path),
            logo_path=logo_str,
            music_path=music_path
        )

        if composite_success:
            print("\n====================================================")
            print(f" SUCCESS: Render completed! File saved at:")
            print(f" {final_output_path.resolve()}")
            print("====================================================")

            # Log script execution to cumulative history file in channel folder
            history_path = channel_dir / "generation_history.json"
            history_list = []
            if history_path.exists():
                try:
                    with open(history_path, "r") as hf:
                        history_list = json.load(hf)
                except Exception as e:
                    print(f"[Run Pipeline] Warning: Failed to parse existing log history: {e}")

            # 8b. Upload to YouTube if requested
            video_id = None
            if args.upload:
                print("\n[Run Pipeline] Stage 5: Authenticating and uploading to YouTube...")
                distributor = YouTubeDistributor(secrets_dir=channel_dir)
                if distributor.authenticate():
                    # Parse custom description/tags from config if present
                    meta_config = config.get("youtube_metadata", {})
                    default_desc = f"Subscribe to {config.get('channel_name', 'our channel')} for more daily retention-hacked loops! #shorts"
                    description = meta_config.get("description", default_desc)
                    tags = meta_config.get("tags", ["shorts", channel_name])
                    category_id = meta_config.get("categoryId", "22")
                    
                    # Construct clean title from config/script
                    title = f"{config.get('channel_name', 'Short')} fact"
                    if "forced_script" in config:
                        # Grab the first query keyword or a short preview
                        title = f"{config.get('channel_name')} - {config['forced_script'].get('yt_search_query', 'Fact')}"
                    
                    video_id = distributor.upload_video(
                        video_path=str(final_output_path),
                        title=title,
                        description=description,
                        tags=tags,
                        category_id=category_id
                    )

            log_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "script": script_data,
                "music_used": Path(music_path).name if music_path else "None",
                "output_video": str(final_output_path.resolve()),
                "youtube_video_id": video_id
            }
            history_list.append(log_data)

            with open(history_path, "w") as hf:
                json.dump(history_list, hf, indent=2)
            print(f"[Run Pipeline] Cumulative running log updated: {history_path}")

    except Exception as e:
        print(f"\n[Error] Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # 9. Clean up temporary files
        print("[Run Pipeline] Cleaning up temporary rendering assets...")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print("[Run Pipeline] Temp directory successfully removed.")

if __name__ == "__main__":
    main()
