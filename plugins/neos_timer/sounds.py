# plugins/neos_timer/sounds.py
"""
Sound generation for timer alerts.
Generates beep, bell, and alarm tones programmatically (no external files needed).
"""

import wave
import struct
import math
import tempfile
import os
import logging
import threading
import subprocess

logger = logging.getLogger(__name__)

SAMPLE_RATE = 8000


def generate_tone(frequency: float, duration: float, volume: float = 0.5) -> bytes:
    """Generate a sine wave tone as WAV data."""
    samples = int(duration * SAMPLE_RATE)
    buffer = []
    
    for i in range(samples):
        t = i / SAMPLE_RATE
        value = int(32767 * volume * math.sin(2 * math.pi * frequency * t))
        buffer.append(struct.pack('<h', value))
    
    return b''.join(buffer)


def generate_beep(duration: float = 0.3, frequency: float = 1000) -> bytes:
    """Generate a simple beep tone."""
    return generate_tone(frequency, duration, 0.7)


def generate_bell(duration: float = 1.0) -> bytes:
    """Generate a bell-like tone with harmonics."""
    samples = int(duration * SAMPLE_RATE)
    buffer = []
    
    for i in range(samples):
        t = i / SAMPLE_RATE
        freq = 800 + 200 * math.exp(-t * 3)
        value = int(32767 * 0.6 * math.sin(2 * math.pi * freq * t) * 
                   (1 + 0.3 * math.sin(2 * math.pi * 2 * t)))
        buffer.append(struct.pack('<h', value))
    
    return b''.join(buffer)


def generate_alarm(duration: float = 1.0) -> bytes:
    """Generate an alarm tone with pulsing effect."""
    samples = int(duration * SAMPLE_RATE)
    buffer = []
    
    for i in range(samples):
        t = i / SAMPLE_RATE
        pulse = (math.sin(2 * math.pi * 4 * t) + 1) / 2
        freq = 600 + 400 * pulse
        value = int(32767 * 0.8 * math.sin(2 * math.pi * freq * t))
        buffer.append(struct.pack('<h', value))
    
    return b''.join(buffer)


def create_wav_file(wav_data: bytes) -> str:
    """Create a temporary WAV file."""
    with wave.open(tempfile.mktemp(suffix='.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(wav_data)
    return w


def get_sound_data(sound_type: str, duration: float = None) -> bytes:
    """Get sound data for a given sound type."""
    if sound_type == "beep":
        return generate_beep(duration or 0.3)
    elif sound_type == "bell":
        return generate_bell(duration or 1.0)
    elif sound_type == "alarm":
        return generate_alarm(duration or 1.0)
    else:
        return generate_beep(0.3)


def play_sound(sound_type: str = "beep", repeat: int = 1, interval: float = 3.0) -> bool:
    """Play a sound with optional repeat."""
    try:
        sound_data = get_sound_data(sound_type)
        
        def play_loop():
            for i in range(repeat):
                try:
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                        f.write(sound_data)
                        temp_file = f.name
                    
                    subprocess.run(['aplay', '-q', temp_file], check=True)
                    os.unlink(temp_file)
                    
                    if i < repeat - 1:
                        threading.Event().wait(interval)
                except Exception as e:
                    logger.error(f"Play iteration {i} failed: {e}")
        
        thread = threading.Thread(target=play_loop, daemon=True)
        thread.start()
        return True
        
    except Exception as e:
        logger.error(f"Failed to play sound: {e}")
        return False


def play_sound_blocking(sound_type: str = "beep", repeat: int = 1, interval: float = 3.0) -> bool:
    """Play a sound synchronously (blocking)."""
    try:
        sound_data = get_sound_data(sound_type)
        
        for i in range(repeat):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(sound_data)
                temp_file = f.name
            
            subprocess.run(['aplay', '-q', temp_file], check=True)
            os.unlink(temp_file)
            
            if i < repeat - 1:
                threading.Event().wait(interval)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to play sound: {e}")
        return False
