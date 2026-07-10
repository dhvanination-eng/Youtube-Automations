import os
import re
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
# pyrefly: ignore [missing-import]
from html2image import Html2Image
import importlib
# Cross-version MoviePy imports (supporting 1.x and 2.x)
try:
    # Try MoviePy 2.x imports first
    from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip
    import moviepy.video.fx as vfx
    import moviepy.audio.fx as afx
except ImportError:
    try:
        # Fallback to MoviePy 1.x
        editor = importlib.import_module("moviepy.editor")
        VideoFileClip = editor.VideoFileClip
        ImageClip = editor.ImageClip
        CompositeVideoClip = editor.CompositeVideoClip
        AudioFileClip = editor.AudioFileClip
        vfx = importlib.import_module("moviepy.video.fx.all")
        afx = importlib.import_module("moviepy.audio.fx.all")
    except ImportError:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.video.VideoClip import ImageClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        import moviepy.video.fx as vfx
        import moviepy.audio.fx as afx


from shared_core.config import VIDEO_WIDTH, VIDEO_HEIGHT, TARGET_DURATION

def process_visual_card(image_path, output_path, target_size=(600, 600), corner_radius=20):
    """
    Pillow image preprocessing: crops/resizes image to a square card,
    rounds corners, and saves it WITHOUT any borders drawn (clean card).
    """
    print(f"[Visual Engine] Preprocessing history visual card from {image_path}...")
    img = Image.open(image_path).convert("RGBA")
    
    # 1. Square fit crop
    img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
    
    # 2. Rounded corner mask
    mask = Image.new("L", target_size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0) + target_size, radius=corner_radius, fill=255)
    
    # 3. Create rounded image canvas
    rounded_img = Image.new("RGBA", target_size, (0, 0, 0, 0))
    rounded_img.paste(img, (0, 0), mask=mask)
    
    # 4. Save as PNG to preserve transparent rounded bounds
    rounded_img.save(output_path, "PNG")
    print(f"[Visual Engine] Processed visual card successfully saved to {output_path}")
    return True

def parse_highlight_tags(text, font_theme=None):
    """
    Parses highlight tags (<yellow> and <red>) and converts them to styled HTML span tags.
    """
    yellow_color = "#FFDE00"
    red_color = "#FF2E2E"
    
    if font_theme:
        yellow_color = font_theme.get("yellow_color", yellow_color)
        red_color = font_theme.get("red_color", red_color)
        
    text = text.replace("<yellow>", f'<span class="highlight-yellow">')
    text = text.replace("</yellow>", '</span>')
    text = text.replace("<red>", f'<span class="highlight-red">')
    text = text.replace("</red>", '</span>')
    return text

def render_text_overlay(text, output_path, theme_config=None):
    """
    Uses html2image to render the formatted script block into a transparent
    compact 950x380 PNG overlay (keeping text clean, centered, and small).
    """
    theme = theme_config or {}
    font_name = theme.get("font_name", "Inter")
    font_url = theme.get("font_url", "https://fonts.googleapis.com/css2?family=Inter:wght@700;800;900&display=swap")
    
    parsed_text = parse_highlight_tags(text, theme)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      @import url('{font_url}');
      body {{
        margin: 0;
        padding: 0;
        background: transparent;
        width: 950px;
        height: 380px;
        display: flex;
        justify-content: center;
        align-items: center;
        font-family: '{font_name}', sans-serif;
        overflow: hidden;
      }}
      .container {{
        width: 900px;
        text-align: center;
        color: white;
        font-size: 34px;
        font-weight: 800;
        line-height: 1.45;
        letter-spacing: 0.2px;
        word-wrap: break-word;
      }}
      .highlight-yellow {{
        color: {theme.get("yellow_color", "#FFDE00")};
        font-weight: 900;
      }}
      .highlight-red {{
        color: {theme.get("red_color", "#FF2E2E")};
        font-weight: 900;
      }}
    </style>
    </head>
    <body>
      <div class="container">
        {parsed_text}
      </div>
    </body>
    </html>
    """
    
    print("[Visual Engine] Generating HTML text overlay screenshot...")
    hti = Html2Image(custom_flags=['--no-sandbox', '--disable-gpu', '--headless', '--hide-scrollbars', '--default-background-color=00000000'])
    
    output_dir = os.path.dirname(output_path)
    output_name = os.path.basename(output_path)
    
    hti.output_path = output_dir
    hti.screenshot(html_str=html_content, save_as=output_name, size=(950, 380))
    print(f"[Visual Engine] Text overlay saved to {output_path}")
    return True

from shared_core.config import DARKEN_FACTOR

def create_video_composite(
    text_overlay_path,
    visual_card_path,
    output_video_path,
    bg_video_path=None,
    logo_path=None,
    music_path=None
):
    """
    Composites the vertical Short:
    - Background Video (if provided, scaled/cropped/darkened) or Black Canvas.
    - Logo (if exists) scaled to full width at y=0.
    - Compact text centered in middle.
    - Rounded visual card centered in lower half, y=1000.
    """
    print("[Visual Engine] Compositing assets onto solid background...")
    duration = TARGET_DURATION
    
    bg_clip = None
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            print(f"[Visual Engine] Loading background video: {bg_video_path}")
            # Load and mute background video
            raw_bg = VideoFileClip(bg_video_path).without_audio()
            
            # Loop/subclip background video to match duration
            if raw_bg.duration < duration:
                # If too short, loop it
                raw_bg = raw_bg.loop(duration=duration)
            else:
                raw_bg = raw_bg.subclip(0, duration)
                
            # Resize and crop to vertical 1080x1920
            # Scale video so it fills the 1080x1920 canvas
            w, h = raw_bg.size
            scale_factor = max(VIDEO_WIDTH / w, VIDEO_HEIGHT / h)
            new_w, new_h = int(w * scale_factor), int(h * scale_factor)
            
            try:
                resized_bg = raw_bg.resized(new_size=(new_w, new_h))
            except AttributeError:
                resized_bg = raw_bg.resize(newsize=(new_w, new_h))
                
            # Center crop to 1080x1920
            x1 = (new_w - VIDEO_WIDTH) // 2
            y1 = (new_h - VIDEO_HEIGHT) // 2
            
            try:
                bg_clip = resized_bg.cropped(x1=x1, y1=y1, width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
            except AttributeError:
                bg_clip = resized_bg.crop(x1=x1, y1=y1, width=VIDEO_WIDTH, height=VIDEO_HEIGHT)
                
            # Darken the background video so text stands out
            try:
                bg_clip = bg_clip.with_effects([vfx.MultiplyColor(DARKEN_FACTOR)])
            except (AttributeError, NameError):
                try:
                    bg_clip = bg_clip.fx(vfx.multiply_color, DARKEN_FACTOR)
                except Exception:
                    # Fallback fl_image filter
                    bg_clip = bg_clip.fl_image(lambda img: (img * DARKEN_FACTOR).astype('uint8'))
                    
        except Exception as e:
            print(f"[Visual Engine Warning] Failed to process background video: {e}. Falling back to black background...")
            bg_clip = None

    if bg_clip is None:
        # Create a temporary black canvas image using PIL to serve as the background clip
        black_bg_temp = Path(output_video_path).parent / "temp_pitch_black.png"
        black_img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
        black_img.save(black_bg_temp)
        
        try:
            bg_clip = ImageClip(str(black_bg_temp)).with_duration(duration)
        except AttributeError:
            bg_clip = ImageClip(str(black_bg_temp)).set_duration(duration)
            
    clips = [bg_clip]
    
    # Track positions dynamically depending on whether a logo exists
    text_y_pos = 370  # Default higher up if no logo is present
    
    # 2. Position Channel Logo/Banner (scaled to full width of the video at the top)
    if logo_path and os.path.exists(logo_path):
        print(f"[Visual Engine] Placing channel banner logo: {logo_path}")
        try:
            logo_clip = ImageClip(logo_path).with_duration(duration)
        except AttributeError:
            logo_clip = ImageClip(logo_path).set_duration(duration)
            
        logo_clip = logo_clip.resized(width=int(VIDEO_WIDTH * 0.8))  # Scale to 80% of video width
        
        # Center horizontally, position at y=40
        try:
            logo_clip = logo_clip.with_position(("center", 40))
        except AttributeError:
            logo_clip = logo_clip.set_position(("center", 40))
            
        clips.append(logo_clip)
        text_y_pos = 520  # Shift text down below the banner

    # 3. Position compact Text overlay (centered vertically or shifted under logo)
    try:
        text_clip = ImageClip(text_overlay_path).with_duration(duration)
    except AttributeError:
        text_clip = ImageClip(text_overlay_path).set_duration(duration)
        
    try:
        text_clip = text_clip.with_position(("center", text_y_pos))
    except AttributeError:
        text_clip = text_clip.set_position(("center", text_y_pos))
        
    clips.append(text_clip)

    # 4. Position square visual card (centered in lower half, y=1000)
    if visual_card_path and os.path.exists(visual_card_path):
        print(f"[Visual Engine] Overlaying rounded visual card: {visual_card_path}")
        try:
            visual_clip = ImageClip(visual_card_path).with_duration(duration)
        except AttributeError:
            visual_clip = ImageClip(visual_card_path).set_duration(duration)
            
        try:
            visual_clip = visual_clip.with_position(("center", 1000))
        except AttributeError:
            visual_clip = visual_clip.set_position(("center", 1000))
            
        clips.append(visual_clip)

    # 5. Composite layers
    video = CompositeVideoClip(clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    
    # 6. Background music
    if music_path and os.path.exists(music_path):
        print(f"[Visual Engine] Mixing audio track: {music_path}")
        audio = AudioFileClip(music_path)
        
        try:
            audio = audio.subclipped(0, duration)
        except AttributeError:
            audio = audio.subclip(0, duration)
            
        try:
            audio = audio.with_effects([afx.AudioFadeOut(1.0)])
        except Exception:
            try:
                audio = audio.fx(afx.audio_fadeout, 1.0)
            except Exception:
                pass
                
        try:
            video = video.with_audio(audio)
        except AttributeError:
            video = video.set_audio(audio)

    # 7. Write final video
    print(f"[Visual Engine] Encoding and exporting video to {output_video_path}...")
    try:
        video.write_videofile(
            output_video_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            preset="medium",
            threads=4
        )
    finally:
        video.close()
        bg_clip.close()
        # Clean up temporary black background image file
        if os.path.exists(black_bg_temp):
            os.remove(black_bg_temp)
            
    print(f"[Visual Engine] Video render completed successfully! Output: {output_video_path}")
    return True
