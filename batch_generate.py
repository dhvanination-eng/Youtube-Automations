import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

# Fix python import path resolution
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared_core.llm_engine import generate_batch_via_gemini, validate_script, SYSTEM_PROMPT

def git_commit_and_push(file_paths, commit_message):
    """Adds, commits, and pushes specified files to the git repository."""
    try:
        # Verify git status
        res = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
        if res.returncode != 0:
            print("[Git Sync Warning] Not inside a Git repository. Skipping commit/push.")
            return

        for path in file_paths:
            subprocess.run(["git", "add", str(path)], check=True)

        # Check if there are changes staged for commit
        status_res = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if status_res.returncode == 0:
            print("[Git Sync] No changes staged. Skipping commit.")
            return

        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print(f"[Git Sync] Staged files committed: '{commit_message}'")

        # Push to remote
        print("[Git Sync] Pushing changes to remote repository...")
        push_res = subprocess.run(["git", "push"], capture_output=True, text=True)
        if push_res.returncode == 0:
            print("[Git Sync] Successfully pushed to remote!")
        else:
            print(f"[Git Sync Warning] Failed to push to remote: {push_res.stderr.strip()}")
    except Exception as e:
        print(f"[Git Sync Warning] Git operation encountered an error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Batch generate scripts for a specific channel using Gemini.")
    parser.add_argument("channel", type=str, help="Name of the channel folder (e.g. channel_stoic)")
    parser.add_argument("--count", type=int, default=100, help="Number of scripts to generate (default: 100)")
    parser.add_argument("--git-push", action="store_true", default=True, help="Push changes to GitHub (default: True)")
    parser.add_argument("--no-git-push", dest="git_push", action="store_false")
    args = parser.parse_args()

    channel_name = args.channel
    channel_dir = PROJECT_ROOT / "5_second_video_channels" / channel_name

    if not channel_dir.exists() or not channel_dir.is_dir():
        print(f"[Error] Channel directory '{channel_dir}' does not exist.")
        sys.exit(1)

    print(f"[Batch Generator] Initiating script generation for: {channel_name}")
    print(f"[Batch Generator] Target count: {args.count} scripts")

    # Load custom prompt if exists
    prompt_path = channel_dir / "prompt.txt"
    system_prompt = SYSTEM_PROMPT
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as pf:
            system_prompt = pf.read().strip()
        print(f"[Batch Generator] Loaded custom system prompt from prompt.txt")

    # Load previously generated script blocks to avoid duplicates
    existing_facts = []

    # 1. From generation history
    history_path = channel_dir / "generation_history.json"
    if history_path.exists():
        try:
            with open(history_path, "r") as hf:
                history_data = json.load(hf)
                for entry in history_data:
                    text = entry.get("script", {}).get("text_block")
                    if text:
                        existing_facts.append(text)
            print(f"[Batch Generator] Loaded {len(existing_facts)} previously used facts from history.")
        except Exception as e:
            print(f"[Batch Generator Warning] Failed to parse history log: {e}")

    # 2. From existing script pool (unconsumed queue)
    pool_path = channel_dir / "script_pool.json"
    existing_pool = []
    if pool_path.exists():
        try:
            with open(pool_path, "r") as pf:
                existing_pool = json.load(pf)
                for entry in existing_pool:
                    text = entry.get("text_block")
                    if text:
                        existing_facts.append(text)
            print(f"[Batch Generator] Loaded {len(existing_pool)} unconsumed facts from pool.")
        except Exception as e:
            print(f"[Batch Generator Warning] Failed to parse script pool: {e}")

    # Generate scripts batch
    try:
        new_scripts = generate_batch_via_gemini(system_prompt, existing_facts, count=args.count)
    except Exception as e:
        print(f"[Error] Batch generation failed: {e}")
        sys.exit(1)

    # Validate and filter
    valid_scripts = []
    for script in new_scripts:
        if validate_script(script):
            valid_scripts.append(script)
        else:
            print(f"[Batch Generator Warning] Skipping invalid script format: {script}")

    print(f"[Batch Generator] Generated {len(new_scripts)} raw scripts; {len(valid_scripts)} validated successfully.")

    if not valid_scripts:
        print("[Batch Generator] No valid scripts generated. Exiting.")
        sys.exit(0)

    # Append to existing pool
    combined_pool = existing_pool + valid_scripts
    with open(pool_path, "w") as pf:
        json.dump(combined_pool, pf, indent=2)

    print(f"[Batch Generator] Script pool successfully updated at: {pool_path}")
    print(f"[Batch Generator] Pool now contains {len(combined_pool)} unconsumed scripts.")

    # Git Sync
    if args.git_push:
        git_commit_and_push(
            file_paths=[pool_path],
            commit_message=f"update(pool): batch generated {len(valid_scripts)} scripts for {channel_name}"
        )

if __name__ == "__main__":
    main()
