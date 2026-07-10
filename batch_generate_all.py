import subprocess
import sys
from pathlib import Path

# List of channels to process
CHANNELS = [
    "channel_stoic",
    "sports",
    "channel_paradox",
    "channel_mystery",
    "channel_wealth",
    "channel_nostalgia",
    "channel_survival",
    "channel_mythology"
]

def main():
    print("==================================================")
    print("      STARTING BATCH GENERATION FOR ALL CHANNELS  ")
    print("==================================================")
    
    for channel in CHANNELS:
        print(f"\n[Batch Runner] Generating 35 scripts for: {channel}...")
        try:
            # Execute batch_generate.py with git push disabled during loop to prevent push storms
            res = subprocess.run(
                [sys.executable, "batch_generate.py", channel, "--count", "35", "--no-git-push"],
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                print(f"[Batch Runner] Successfully generated and pooled scripts for {channel}.")
                # Print last few lines of output
                lines = res.stdout.strip().split("\n")
                for line in lines[-3:]:
                    print(f"  {line}")
            else:
                print(f"[Batch Runner Error] Failed to generate for {channel}:")
                print(res.stderr)
        except Exception as e:
            print(f"[Batch Runner Error] Exception occurred for {channel}: {e}")

    # After all are generated, run a single git commit and push to sync everything cleanly
    print("\n[Batch Runner] Synchronizing pool files to GitHub...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        # Check if there are changes
        status_res = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if status_res.returncode != 0:
            subprocess.run(["git", "commit", "-m", "update(pool): batch generate 35 scripts for all 8 channels"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("[Batch Runner] Successfully pushed all pool files to GitHub!")
        else:
            print("[Batch Runner] No changes to commit.")
    except Exception as e:
        print(f"[Batch Runner Warning] Git synchronization failed: {e}")

if __name__ == "__main__":
    main()
