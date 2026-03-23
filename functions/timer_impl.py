# functions/timer_impl.py
"""
Timer implementation for NEOS.
Provides timer and notification functionality.
"""

import logging
import threading
import time
import uuid
import subprocess
import tempfile
import os
import wave
import struct
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

SAMPLE_RATE = 8000

_config = {
    "default_sound": True,
    "default_sound_type": "beep",
    "default_repeat": 3,
    "default_repeat_interval": 3,
    "default_desktop": True,
    "default_phone": False,
    "ntfy_topic": "NEOS-Timer",
    "ntfy_enabled": True,
}

_timers: Dict[str, Any] = {}
_timer_lock = threading.Lock()
_active_alerts: Dict[str, bool] = {}


def generate_tone(frequency: float, duration: float, volume: float = 0.5) -> bytes:
    """Generate a sine wave tone as WAV data."""
    samples = int(duration * SAMPLE_RATE)
    buffer = []
    for i in range(samples):
        t = i / SAMPLE_RATE
        value = int(32767 * volume * math.sin(2 * math.pi * frequency * t))
        buffer.append(struct.pack('<h', value))
    return b''.join(buffer)


def get_sound_data(sound_type: str, duration: float = None) -> bytes:
    """Get sound data for a given sound type."""
    if sound_type == "beep":
        return generate_tone(1000, duration or 0.3, 0.7)
    elif sound_type == "bell":
        duration = duration or 1.0
        samples = int(duration * SAMPLE_RATE)
        buffer = []
        for i in range(samples):
            t = i / SAMPLE_RATE
            freq = 800 + 200 * math.exp(-t * 3)
            value = int(32767 * 0.6 * math.sin(2 * math.pi * freq * t))
            buffer.append(struct.pack('<h', value))
        return b''.join(buffer)
    elif sound_type == "alarm":
        duration = duration or 1.0
        samples = int(duration * SAMPLE_RATE)
        buffer = []
        for i in range(samples):
            t = i / SAMPLE_RATE
            pulse = (math.sin(2 * math.pi * 4 * t) + 1) / 2
            freq = 600 + 400 * pulse
            value = int(32767 * 0.8 * math.sin(2 * math.pi * freq * t))
            buffer.append(struct.pack('<h', value))
        return b''.join(buffer)
    else:
        return generate_tone(1000, 0.3, 0.7)


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
                        time.sleep(interval)
                except Exception as e:
                    logger.error(f"Play iteration {i} failed: {e}")
        
        thread = threading.Thread(target=play_loop, daemon=True)
        thread.start()
        return True
    except Exception as e:
        logger.error(f"Failed to play sound: {e}")
        return False


class Timer:
    """A countdown timer."""
    
    def __init__(self, name: str, minutes: int, message: str = None, **options):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.minutes = minutes
        self.message = message or f"{name} timer complete"
        self.sound = options.get("sound", _config.get("default_sound", True))
        self.sound_type = options.get("sound_type", _config.get("default_sound_type", "beep"))
        self.repeat = options.get("repeat", _config.get("default_repeat", 3))
        self.repeat_interval = options.get("repeat_interval", _config.get("default_repeat_interval", 3))
        self.desktop = options.get("desktop", _config.get("default_desktop", True))
        self.phone = options.get("phone", _config.get("default_phone", False))
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(minutes=minutes)
        self.cancelled = False
        self.dismissed = False
        self._thread = None
    
    def remaining_seconds(self) -> float:
        if self.cancelled or self.dismissed:
            return 0
        delta = self.end_time - datetime.now()
        return max(0, delta.total_seconds())
    
    def remaining_formatted(self) -> str:
        secs = self.remaining_seconds()
        if secs == 0:
            return "complete"
        mins = int(secs // 60)
        secs = int(secs % 60)
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"
    
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        secs = self.remaining_seconds()
        if secs > 0:
            time.sleep(secs)
        if not self.cancelled and not self.dismissed:
            self._trigger_alert()
    
    def _trigger_alert(self):
        logger.info(f"Timer '{self.name}' complete!")
        _active_alerts[self.name] = True
        
        if self.sound:
            play_sound(self.sound_type, self.repeat, self.repeat_interval)
        
        if self.desktop:
            try:
                subprocess.run([
                    'notify-send', '-u', 'critical', '-t', '0',
                    f"Timer: {self.name}",
                    self.message
                ], check=False)
            except Exception as e:
                logger.error(f"Desktop notification failed: {e}")
        
        if self.phone and _config.get("ntfy_enabled"):
            _send_ntfy_notification(self.name, self.message)
    
    def cancel(self):
        self.cancelled = True
        if self.name in _active_alerts:
            del _active_alerts[self.name]
    
    def dismiss(self):
        self.dismissed = True
        if self.name in _active_alerts:
            del _active_alerts[self.name]


def _send_ntfy_notification(title: str, message: str, priority: str = "normal"):
    """Send notification via ntfy."""
    try:
        import requests
        topic = _config.get("ntfy_topic", "NEOS-Timer")
        priority_map = {"low": 0, "normal": 1, "high": 4}
        priority_val = priority_map.get(priority, 1)
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=f"{title}: {message}".encode(),
            headers={
                "Title": title,
                "Priority": str(priority_val),
                "Tags": "alarm,clock"
            },
            timeout=10
        )
    except Exception as e:
        logger.error(f"ntfy notification failed: {e}")


def set_timer(name: str, minutes: int, message: str = None, **options) -> tuple:
    """Set a new timer or update existing one."""
    if not name:
        return "Timer name is required", False
    if minutes <= 0:
        return "Minutes must be positive", False
    
    with _timer_lock:
        if name in _timers:
            _timers[name].cancel()
        timer = Timer(name, minutes, message, **options)
        _timers[name] = timer
        timer.start()
    
    return f"Timer '{name}' set for {minutes} minute(s)", True


def cancel_timer(name: str) -> tuple:
    """Cancel a timer."""
    if not name:
        return "Timer name is required", False
    with _timer_lock:
        if name in _timers:
            _timers[name].cancel()
            del _timers[name]
            return f"Timer '{name}' cancelled", True
    return f"Timer '{name}' not found", False


def list_timers() -> tuple:
    """List all active timers."""
    with _timer_lock:
        if not _timers:
            return "No active timers", True
        lines = ["Active Timers:", ""]
        for name, timer in _timers.items():
            remaining = timer.remaining_formatted()
            lines.append(f"• {name}: {remaining} remaining")
        return "\n".join(lines), True


def dismiss_timer(name: str) -> tuple:
    """Dismiss an active timer alert."""
    if not name:
        return "Timer name is required", False
    with _timer_lock:
        if name in _timers:
            _timers[name].dismiss()
            if name in _active_alerts:
                del _active_alerts[name]
            return f"Timer '{name}' dismissed", True
    return f"Timer '{name}' not found", False


def send_notification(title: str, message: str, sound: bool = True, 
                     sound_type: str = "beep", desktop: bool = True,
                     phone: bool = False, priority: str = "normal") -> tuple:
    """Send a notification."""
    if sound:
        play_sound(sound_type, 1, 0)
    
    if desktop:
        try:
            subprocess.run([
                'notify-send', '-u', 'normal', '-t', '5000',
                title, message
            ], check=False)
        except Exception as e:
            logger.error(f"Desktop notification failed: {e}")
    
    if phone and _config.get("ntfy_enabled"):
        _send_ntfy_notification(title, message, priority)
    
    return f"Notification sent: {title}", True
