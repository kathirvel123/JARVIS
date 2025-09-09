import torch
from kokoro import KPipeline
import soundfile as sf
import numpy as np
import sounddevice as sd

device = "cuda" if torch.cuda.is_available() else "cpu"
pipeline = KPipeline(lang_code='a', device=device)

def speak(text, voice="af_heart", speed=1):
    """Convert text to speech and play it"""
    try:
        print(f"🔊 Speaking: {text}")
        generator = pipeline(text, voice=voice, speed=speed, split_pattern=r'\n+')
        audio_data = []
        
        for *_, audio in generator:
            audio_data.append(audio)
        
        if audio_data:
            final_audio = np.concatenate(audio_data)
            sd.play(final_audio, 24000)
            sd.wait()  # Wait until playback finishes
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        print(f"📢 {text}")  # Fallback to text output