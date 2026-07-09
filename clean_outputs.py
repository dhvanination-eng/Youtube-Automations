import os
import shutil
from pathlib import Path

def clean_outputs():
    project_root = Path(__file__).resolve().parent
    channels_dir = project_root / "5_second_video_channels"
    
    if not channels_dir.exists():
        print("[Cleaner] Channels directory not found.")
        return
        
    for channel_path in channels_dir.iterdir():
        if channel_path.is_dir():
            output_dir = channel_path / "output"
            temp_dir = channel_path / "temp"
            
            # Clean output directory
            if output_dir.exists():
                print(f"[Cleaner] Cleaning output directory for channel: {channel_path.name}")
                for item in output_dir.iterdir():
                    if item.is_file() and item.suffix.lower() == ".mp4":
                        try:
                            item.unlink()
                            print(f"  Deleted: {item.name}")
                        except Exception as e:
                            print(f"  Failed to delete {item.name}: {e}")
            
            # Clean temp directory
            if temp_dir.exists():
                print(f"[Cleaner] Cleaning temp directory for channel: {channel_path.name}")
                try:
                    shutil.rmtree(temp_dir)
                    print("  Deleted temp directory")
                except Exception as e:
                    print(f"  Failed to delete temp directory: {e}")

if __name__ == "__main__":
    clean_outputs()
