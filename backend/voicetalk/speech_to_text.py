import sounddevice as sd
import numpy as np
import queue
import faster_whisper
import time
from difflib import SequenceMatcher

# Load Faster Whisper model
model_size = "small"
model = faster_whisper.WhisperModel(model_size, device="cpu")

samplerate = 16000
block_size = 1024
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Callback for audio input stream"""
    if status:
        print(f"Audio status: {status}")
    audio_queue.put(indata.copy())

def record_and_transcribe(duration=5):
    """Record audio for specified duration and return transcription"""
    print("🎤 Listening...")
    buffer = []
    
    try:
        with sd.InputStream(samplerate=samplerate, channels=1, callback=audio_callback, blocksize=block_size):
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    data = audio_queue.get(timeout=0.1)
                    buffer.extend(data[:, 0])
                except queue.Empty:
                    continue
        
        if not buffer:
            return ""
        
        audio_chunk = np.array(buffer, dtype=np.float32)
        
        # Transcribe
        segments, _ = model.transcribe(
            audio_chunk,
            beam_size=5,
            language="en",
            task="transcribe",
            vad_filter=True
        )
        
        transcription = " ".join(segment.text.strip() for segment in segments)
        return transcription.strip()
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def detect_wakeword(transcription, wakewords, similarity_threshold=0.7):
    """Detect wakeword with fuzzy matching"""
    transcription = transcription.lower().strip()
    
    # Direct substring matching
    for wakeword in wakewords:
        if wakeword.lower() in transcription:
            return True, wakeword
    
    # Word-by-word similarity matching
    transcription_words = transcription.split()
    for wakeword in wakewords:
        wakeword_words = wakeword.lower().split()
        
        for i in range(len(transcription_words) - len(wakeword_words) + 1):
            sequence = ' '.join(transcription_words[i:i+len(wakeword_words)])
            if similarity(sequence, wakeword.lower()) >= similarity_threshold:
                return True, wakeword
    
    return False, None

def listen_for_wakeword():
    """Listen continuously for wakeword"""
    wakewords = [
        "hey jarvis", "jarvis", "hey j", "jarvis wake up",
        "hello jarvis", "hi jarvis", "yo jarvis",
        "hey javis", "hey jarvin", "jarvas"
    ]
    
    print(f"🟢 Listening for wakewords...")
    buffer = []
    chunk_duration = 3
    
    with sd.InputStream(samplerate=samplerate, channels=1, callback=audio_callback, blocksize=block_size):
        while True:
            try:
                data = audio_queue.get(timeout=0.1)
                buffer.extend(data[:, 0])
                
                if len(buffer) >= samplerate * chunk_duration:
                    audio_chunk = np.array(buffer, dtype=np.float32)
                    
                    # Keep overlap for continuous detection
                    overlap_samples = int(samplerate * 0.5)
                    buffer = buffer[-overlap_samples:] if len(buffer) > overlap_samples else []
                    
                    # Transcribe
                    segments, _ = model.transcribe(
                        audio_chunk,
                        beam_size=5,
                        language="en",
                        task="transcribe",
                        vad_filter=True
                    )
                    
                    transcription = " ".join(segment.text.strip() for segment in segments)
                    
                    if transcription.strip():
                        print(f"🎤 Heard: '{transcription}'")
                        
                        detected, matched_wakeword = detect_wakeword(transcription, wakewords)
                        
                        if detected:
                            print(f"🟢 Wakeword detected: '{matched_wakeword}'")
                            return True
                            
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                print("\n🔴 Stopping wakeword detection...")
                return False
            except Exception as e:
                print(f"⚠️ Wakeword detection error: {e}")
                time.sleep(1)
                continue

