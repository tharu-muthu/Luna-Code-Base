import os
import time
import threading
import pygame
from config import Config


class AudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(Config.DEFAULT_VOLUME)

        self._lock = threading.Lock()

        self.is_playing = False
        self.is_paused = False
        self.current_category = None  # story / song / education
        self.last_index = None        # story/song number (1–10)
        self.current_file = None
        self.last_play_mode = None    # "specific" or "random"
        self.callback = None          # Function to call when playback ends

    def play(self, filepath, category=None, index=None, mode="specific", callback=None):
        """Plays an audio file and tracks its state."""
        if not os.path.exists(filepath):
            print(f"[AudioPlayer] File not found: {filepath}")
            return False

        self.stop()

        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            with self._lock:
                self.is_playing = True
                self.is_paused = False
                self.current_category = category
                self.last_index = index
                self.current_file = filepath
                self.last_play_mode = mode
                self.callback = callback
            return True
        except Exception as e:
            print(f"[AudioPlayer] Playback error: {e}")
            return False

    def play_feedback(self, name, wait=False):
        """Play feedback from feedback folder by name (without .mp3)."""
        path = os.path.join(Config.FEEDBACK_DIR, f"{name}.mp3")
        if os.path.exists(path):
            self.play(path)
            if wait:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
        else:
            print(f"[AudioPlayer] Missing feedback: {name}.mp3")

    def stop(self):
        """Stops any currently playing audio."""
        with self._lock:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            self.is_playing = False
            self.is_paused = False
            self.current_file = None
            self.callback = None

    def check_finished(self):
        """Check if playback ended naturally and run callback."""
        with self._lock:
            if self.is_paused:
                return False
            if self.is_playing and not pygame.mixer.music.get_busy():
                self.is_playing = False
                cb = self.callback
                self.callback = None
            else:
                return False

        # Run callback OUTSIDE the lock to avoid deadlocks
        if cb:
            cb()
        return True

    def set_volume(self, volume):
        """Set volume between 0.0 and 1.0"""
        volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(volume)

    def get_volume(self):
        """Get volume between 0.0 and 1.0"""
        return pygame.mixer.music.get_volume()

    def pause(self):
        """Pauses the current playback."""
        with self._lock:
            if self.is_playing and not self.is_paused:
                self.is_paused = True
                pygame.mixer.music.pause()

    def resume(self):
        """Resumes the paused playback."""
        with self._lock:
            if self.is_playing and self.is_paused:
                pygame.mixer.music.unpause()
                self.is_paused = False

    def increase_volume(self):
        current = pygame.mixer.music.get_volume()
        self.set_volume(current + Config.VOLUME_STEP)

    def decrease_volume(self):
        current = pygame.mixer.music.get_volume()
        self.set_volume(current - Config.VOLUME_STEP)

    def get_state_snapshot(self):
        """Thread-safe snapshot of current playback state.
        Use this in _handle_next/_handle_prev BEFORE calling stop()."""
        with self._lock:
            return {
                "category": self.current_category,
                "index": self.last_index,
                "mode": self.last_play_mode,
                "file": self.current_file,
                "playing": self.is_playing,
                "paused": self.is_paused,
            }
