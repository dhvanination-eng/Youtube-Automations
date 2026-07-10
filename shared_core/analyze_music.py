import os
import numpy as np
from pathlib import Path
from moviepy import AudioFileClip

def analyze_audio_file(file_path):
    """
    Analyzes an audio file using MoviePy and numpy.
    Returns a dict with audio features: rms_energy (volume), variance, tempo_hint.
    """
    try:
        clip = AudioFileClip(str(file_path))
        # Read sound array at 22050Hz, mono
        fps = 22050
        sound_array = clip.to_soundarray(fps=fps)
        if len(sound_array.shape) > 1:
            sound_array = sound_array.mean(axis=1) # Convert to mono
            
        # 1. Compute RMS energy (volume)
        rms = np.sqrt(np.mean(sound_array**2))
        
        # 2. Compute variance (dynamics)
        var = np.var(sound_array)
        
        # 3. Simple onset detection to estimate tempo (BPM hint)
        # Compute local energy in 100ms frames
        frame_len = int(fps * 0.1)
        hop_len = int(fps * 0.02)
        energies = []
        for i in range(0, len(sound_array) - frame_len, hop_len):
            frame = sound_array[i:i+frame_len]
            energies.append(np.sum(frame**2))
        energies = np.array(energies)
        
        # Compute first derivative of energy to find onsets
        diff = np.diff(energies)
        diff = np.maximum(diff, 0) # Half-wave rectify
        
        # Count peaks above threshold as beats
        threshold = np.mean(diff) + 1.2 * np.std(diff)
        peaks = np.where(diff > threshold)[0]
        
        duration = clip.duration
        # Estimate BPM based on peak density
        if duration > 0:
            bpm_estimate = (len(peaks) / duration) * 60
            # Normalize to reasonable range [60, 180]
            while bpm_estimate < 60 and bpm_estimate > 0:
                bpm_estimate *= 2
            while bpm_estimate > 180:
                bpm_estimate /= 2
        else:
            bpm_estimate = 120
            
        clip.close()
        return {
            "rms": float(rms),
            "variance": float(var),
            "bpm": float(bpm_estimate),
            "duration": float(duration)
        }
    except Exception as e:
        print(f"Error analyzing {file_path.name}: {e}")
        return None

def main():
    music_dir = Path("shared_core/music")
    if not music_dir.exists():
        print("Music directory not found.")
        return
        
    print("====================================================")
    print("       PROGRAMMATIC AUDIO FEATURE ANALYSIS          ")
    print("====================================================")
    
    for f in music_dir.glob("*.mp3"):
        features = analyze_audio_file(f)
        if features:
            print(f"\nFile: {f.name}")
            print(f"  Duration: {features['duration']:.2f}s")
            print(f"  RMS Volume (Energy): {features['rms']:.4f}")
            print(f"  Variance (Dynamics): {features['variance']:.4f}")
            print(f"  Estimated BPM: {features['bpm']:.1f}")

if __name__ == "__main__":
    main()
