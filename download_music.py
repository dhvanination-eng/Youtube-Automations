import os
import sys
import argparse
from pathlib import Path
import yt_dlp

def download_track(query_or_url, channel_name):
    project_root = Path(__file__).resolve().parent
    channel_dir = project_root / "5_second_video_channels" / channel_name
    
    if not channel_dir.exists():
        print(f"[Error] Channel directory '{channel_name}' does not exist.")
        return False
        
    music_dir = channel_dir / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[Music Downloader] Searching and downloading: {query_or_url}")
    
    # yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(music_dir / '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
        'no_warnings': False,
        'extract_audio': True,
    }
    
    # If it is not a direct URL, prepend ytsearch:
    if not query_or_url.startswith("http"):
        query_or_url = f"ytsearch1:{query_or_url}"
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query_or_url, download=True)
            if 'entries' in info:
                # Playlist or search results
                info = info['entries'][0]
            title = info.get('title', 'Downloaded_Track')
            print(f"\n[Music Downloader] SUCCESS! Saved '{title}.mp3' to {channel_name} music folder.")
            return True
    except Exception as e:
        print(f"[Music Downloader] Failed to download: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download music from YouTube to a channel's assets folder")
    parser.add_argument("query", type=str, help="Search query or YouTube URL")
    parser.add_argument("channel", type=str, help="Name of the target channel directory (e.g. history_explained)")
    args = parser.parse_args()
    
    download_track(args.query, args.channel)
