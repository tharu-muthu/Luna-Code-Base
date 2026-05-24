import os
import random
import threading
import time

from config import Config
from emotion_timeline import EmotionTimeline
from emotion_manager import EmotionManager


class CommandHandler:
    def __init__(self, audio, eyes, leds, servos, motors, emotion_detector):
        self.audio = audio
        self.eyes = eyes
        self.leds = leds
        self.servos = servos
        self.motors = motors
        self.detector = emotion_detector
        self.timeline_thread = None
        self.sleeping = False

        # Track current educational subtype for next/prev
        self._current_edu_type = None
        self._edu_display_thread = None

        self.number_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }

        # Ordered list for educational next/prev cycling
        self._edu_types = ["alphabet", "numbers", "animals"]

    # =========================
    # Core Command Dispatcher
    # =========================
    def handle(self, intent, slots):
        # If sleeping, only allow the "wake" intent!
        if self.sleeping:
            if intent == "wake":
                self._handle_wake_up()
            return

        # Volume control
        if intent == "volume":
            intensity = slots.get("intensity", "")
            if intensity == "increase":
                self.audio.increase_volume()
            elif intensity == "decrease":
                self.audio.decrease_volume()
            return

        # Sleep mode
        if intent == "sleep":
            self._handle_sleep()
            return
        # Wake Up
        if intent == "wake":
            self._handle_wake_up()
            return

        # Stop
        if intent == "stop":
            self._handle_stop()
            return

        # Next
        if intent == "next":
            self._handle_next()
            return

        # Previous
        if intent in ("prev", "previous"):
            self._handle_prev()
            return

        # Pause
        if intent == "pause":
            self._handle_pause()
            return

        # Resume
        if intent == "resume":
            self._handle_resume()
            return

        # Navigation
        if intent == "navigation":
            self._handle_navigation(slots.get("side", ""))
            return

        # Emotion detection
        if intent == "checkEmotion":
            self._handle_emotion_detection()
            return

        # Specific story
        if intent == "playStory":
            
            num = self.number_map.get(slots.get("storyNum", "").lower(), None)
            if num:
                self._play_story(num, mode="specific")
            return

        # Specific song
        if intent == "playSong":
            num = self.number_map.get(slots.get("songNum", "").lower(), None)
            if num:
                self._play_song(num, mode="specific")
            return

        # General playback (random)
        if intent == "genaralPlay":
            type_ = slots.get("type", "")
            if type_ in ["song", "story"]:
                self._play_random(type_)
            elif type_ in ["alphabet", "numbers", "animals"]:
                self._play_educational(type_)

    # =========================
    # Playback Functions
    # =========================
    def _play_story(self, number, mode="specific"):
        story_file = os.path.join(Config.STORIES_DIR, f"story_{number}.mp3")
        feedback = f"playing_story_{number}"
        if not os.path.exists(story_file):
            print(f"[Story] Not found: {story_file}")
            return

        self.audio.play_feedback(feedback, wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        # Timeline + playback
        def on_finish():
            self._stop_timeline()
            self.eyes.set_mood("neutral")
            self.eyes.start()
            self.leds.set_neutral()
            self.servos.set_neutral()
            self.audio.play_feedback("playback_finished", wait=True)

        # Start timeline thread
        self._start_emotion_timeline(number)

        self.audio.play(
            story_file,
            category="story",
            index=number,
            mode=mode,
            callback=on_finish
        )

    def _play_song(self, number, mode="specific"):
        song_file = os.path.join(Config.SONGS_DIR, f"song_{number}.mp3")
        feedback = f"playing_song_{number}"
        if not os.path.exists(song_file):
            print(f"[Song] Not found: {song_file}")
            return
        
        self.eyes.stop()

        self.audio.play_feedback(feedback, wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        self.eyes.music(Config.MOTOR_RUN_DURATION)
        self.leds.music()

        def on_finish():
            self._on_playback_finish()

        self.audio.play(
            song_file,
            category="song",
            index=number,
            mode=mode,
            callback=on_finish
        )

    def _play_random(self, type_):
        folder = Config.STORIES_DIR if type_ == "story" else Config.SONGS_DIR
        prefix = "story_" if type_ == "story" else "song_"
        feedback = "playing_a_story" if type_ == "story" else "playing_a_song"

        files = [f for f in os.listdir(folder) if f.startswith(prefix)]
        if not files:
            print(f"[Random {type_}] No files found.")
            return
        self.eyes.stop()

        selected = random.choice(files)
        number = int(selected.split("_")[-1].split(".")[0])
        path = os.path.join(folder, selected)

        self.audio.play_feedback(feedback, wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        if type_ == "story":
            self.eyes.start()
            self._start_emotion_timeline(number)
            self.audio.play(path, category="story", index=number, mode="random", callback=self._on_playback_finish)
        else:
            self.eyes.music(Config.MOTOR_RUN_DURATION)
            self.leds.music()
            self.audio.play(path, category="song", index=number, mode="random", callback=self._on_playback_finish)

    def _play_educational(self, type_):
        file = os.path.join(Config.EDUCATION_DIR, f"{type_}.mp3")
        feedback = f"playing_{type_}"
        

        if not os.path.exists(file):
            print(f"[Edu] Not found: {file}")
            return
        
        # Stop any currently running educational display thread cleanly
        self.eyes.edu_stop()
        # Wait for old display thread to exit
        if self._edu_display_thread and self._edu_display_thread.is_alive():
            self._edu_display_thread.join(timeout=1.0)
        self._edu_display_thread = None

        self.eyes.stop()
        self.eyes.edu_start()
        self.leds.set_neutral() # Restore active friendly LEDs!

        # Track the educational subtype for next/prev cycling
        self._current_edu_type = type_

        self.audio.play_feedback(feedback, wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        def on_finish():
            """Called when audio playback ends naturally."""
            self.eyes.edu_stop()
            # Wait for display thread to exit before restarting eye loop
            if self._edu_display_thread and self._edu_display_thread.is_alive():
                self._edu_display_thread.join(timeout=2.0)
            self._edu_display_thread = None
            self.eyes.set_mood("neutral")
            self.eyes.start()
            self.audio.play_feedback("playback_finished", wait=True)

        # Start audio in a daemon thread
        threading.Thread(target=self.audio.play, args=(file,), kwargs={
            "category": "education", "mode": "specific", "callback": on_finish
        }, daemon=True).start()

        # Start display loop in a separate daemon thread (NOT blocking the caller)
        display_func = {
            "alphabet": self.eyes.alphabet,
            "numbers": self.eyes.numbers,
            "animals": self.eyes.animals,
        }.get(type_)

        if display_func:
            self._edu_display_thread = threading.Thread(target=display_func, daemon=True)
            self._edu_display_thread.start()


    # =========================
    # Navigation
    # =========================
    def execute_movement(self, direction, speak=True):
        motor_map = {
            "forward": self.motors.forward,
            "backward": self.motors.backward,
            "left": self.motors.turn_left,
            "right": self.motors.turn_right
        }

        if direction not in motor_map:
            return

        if speak:
            sound_map = {
                "forward": "coming_fowrd",
                "backward": "going_backward",
                "left": "turning_left",
                "right": "turning_right"
            }
            if direction in sound_map:
                self.audio.play_feedback(sound_map[direction], wait=True)
                time.sleep(Config.FEEDBACK_DELAY)

        # 1 wave cycle takes 1.2s. MOTOR_RUN_DURATION is 3.0s.
        # Trigger exactly 2 cycles (2.4s total wave duration) to align with wheels
        cycles = int(Config.MOTOR_RUN_DURATION / 1.2)

        threading.Thread(target=motor_map[direction], daemon=True).start()
        threading.Thread(target=self.servos.wave, args=(cycles,), daemon=True).start()

    def _handle_navigation(self, direction):
        self.execute_movement(direction, speak=True)

    # =========================
    # Stop, Next, Sleep
    # =========================
    def _handle_stop(self):
        if not self.audio.is_playing and not self.audio.is_paused:
            print("[Stop] Nothing playing")
            return

        self.audio.stop()
        self._stop_timeline()
        self.leds.stop_music()

        # Stop educational display and wait for its thread to exit
        self.eyes.edu_stop()
        if self._edu_display_thread and self._edu_display_thread.is_alive():
            self._edu_display_thread.join(timeout=2.0)
        self._edu_display_thread = None

        self.eyes.stop()
        self.leds.set_neutral()
        self.servos.set_neutral()
        self.eyes.set_mood("neutral")
        self.eyes.set_neutral()
        self.eyes.start()
        self.audio.play_feedback("playback_stopped", wait=True)

    def _handle_next(self):
        # Take a thread-safe snapshot BEFORE stopping anything
        state = self.audio.get_state_snapshot()
        if not state["playing"] and not state["paused"]:
            print("[Next] Nothing playing")
            return

        last_type = state["category"]
        last_index = state["index"]
        last_mode = state["mode"]

        self.audio.stop()
        self._stop_timeline()
        self.leds.stop_music()

        # Stop educational display and wait for its thread to exit
        self.eyes.edu_stop()
        if self._edu_display_thread and self._edu_display_thread.is_alive():
            self._edu_display_thread.join(timeout=2.0)
        self._edu_display_thread = None

        self.leds.set_neutral()

        time.sleep(Config.FEEDBACK_DELAY)
        self.audio.play_feedback("playback_stopped", wait=True)
        time.sleep(Config.FEEDBACK_DELAY)
        self.audio.play_feedback("playback_switching", wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        if last_type == "education":
            # Cycle to next educational type in order
            if self._current_edu_type and self._current_edu_type in self._edu_types:
                idx = self._edu_types.index(self._current_edu_type)
                next_type = self._edu_types[(idx + 1) % len(self._edu_types)]
            else:
                next_type = random.choice(self._edu_types)
            self._play_educational(next_type)

        elif last_mode == "specific":
            next_index = last_index + 1
            if last_type == "story":
                path = os.path.join(Config.STORIES_DIR, f"story_{next_index}.mp3")
                if os.path.exists(path):
                    self._play_story(next_index, mode="specific")
                else:
                    self.audio.play_feedback("no_file_to_switch", wait=True)
            elif last_type == "song":
                path = os.path.join(Config.SONGS_DIR, f"song_{next_index}.mp3")
                if os.path.exists(path):
                    self._play_song(next_index, mode="specific")
                else:
                    self.audio.play_feedback("no_file_to_switch", wait=True)

        elif last_mode == "random":
            if last_type in ["story", "song"]:
                self._play_random(last_type)

    def _handle_prev(self):
        # Take a thread-safe snapshot BEFORE stopping anything
        state = self.audio.get_state_snapshot()
        if not state["playing"] and not state["paused"]:
            print("[Prev] Nothing playing")
            return

        last_type = state["category"]
        last_index = state["index"]
        last_mode = state["mode"]

        self.audio.stop()
        self._stop_timeline()
        self.leds.stop_music()

        # Stop educational display and wait for its thread to exit
        self.eyes.edu_stop()
        if self._edu_display_thread and self._edu_display_thread.is_alive():
            self._edu_display_thread.join(timeout=2.0)
        self._edu_display_thread = None

        self.leds.set_neutral()

        time.sleep(Config.FEEDBACK_DELAY)
        self.audio.play_feedback("playback_stopped", wait=True)
        time.sleep(Config.FEEDBACK_DELAY)
        self.audio.play_feedback("playback_switching", wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        if last_type == "education":
            # Cycle to previous educational type in order
            if self._current_edu_type and self._current_edu_type in self._edu_types:
                idx = self._edu_types.index(self._current_edu_type)
                prev_type = self._edu_types[(idx - 1) % len(self._edu_types)]
            else:
                prev_type = random.choice(self._edu_types)
            self._play_educational(prev_type)

        elif last_mode == "specific":
            prev_index = last_index - 1
            if prev_index < 1:
                self.audio.play_feedback("no_file_to_switch", wait=True)
                return
            if last_type == "story":
                path = os.path.join(Config.STORIES_DIR, f"story_{prev_index}.mp3")
                if os.path.exists(path):
                    self._play_story(prev_index, mode="specific")
                else:
                    self.audio.play_feedback("no_file_to_switch", wait=True)
            elif last_type == "song":
                path = os.path.join(Config.SONGS_DIR, f"song_{prev_index}.mp3")
                if os.path.exists(path):
                    self._play_song(prev_index, mode="specific")
                else:
                    self.audio.play_feedback("no_file_to_switch", wait=True)

        elif last_mode == "random":
            if last_type in ["story", "song"]:
                self._play_random(last_type)

    def _handle_pause(self):
        self._handle_pause_internal()

    def _handle_pause_internal(self):
        self.audio.pause()
        if self.timeline_thread:
            self.timeline_thread.pause()
        if hasattr(self.eyes, "pause"):
            self.eyes.pause()

    def _handle_resume(self):
        self._handle_resume_internal()

    def _handle_resume_internal(self):
        self.audio.resume()
        if self.timeline_thread:
            self.timeline_thread.resume()
        if hasattr(self.eyes, "resume"):
            self.eyes.resume()

    def _handle_sleep(self):
        self.sleeping = True
        self.audio.stop()
        self._stop_timeline()
        self.eyes.edu_stop()
        if self._edu_display_thread and self._edu_display_thread.is_alive():
            self._edu_display_thread.join(timeout=2.0)
        self._edu_display_thread = None
        self.eyes.stop()
        self.eyes.set_black()
        self.leds.turn_off()
        self.servos.set_neutral()
        self.audio.play_feedback("going_to_sleep", wait=True)

    def _handle_wake_up(self):
        if self.sleeping:
            self.eyes.set_neutral()
            self.leds.set_neutral()
            self.servos.set_neutral()
            self.eyes.start()  # restart auto-blink / drawing
            self.audio.play_feedback("waking_up", wait=True)
            self.sleeping = False


    def _on_playback_finish(self):
        """Unified callback for when any playback finishes naturally."""
        self._stop_timeline()
        self.leds.stop_music()
        self.eyes.set_mood("neutral")
        self.eyes.start()
        self.leds.set_neutral()
        self.servos.set_neutral()
        self.audio.play_feedback("playback_finished", wait=True)

    # =========================
    # Emotion Detection
    # =========================
    def _handle_emotion_detection(self):
        # Stop streaming if active to prevent camera resource busy conflict
        if hasattr(self, "check_and_stop_stream"):
            was_streaming = self.check_and_stop_stream()
            if was_streaming:
                print("[Emotion] Web video stream paused for photo capture.")
                time.sleep(1.0) # Wait for camera hardware resources to be fully released

        self.audio.play_feedback("E_detection", wait=True)
        emotion = self.detector.get_emotion()
        print(f"[Facial Emotion] {emotion}")

        if emotion == "Joy":
            self.audio.play_feedback("joy", wait=True)
            time.sleep(Config.FEEDBACK_DELAY)
            self._play_random("story")
        elif emotion == "Sorrow":
            self.audio.play_feedback("sorrow", wait=True)
            time.sleep(Config.FEEDBACK_DELAY)
            self._play_random("song")
        elif emotion == "Anger":
            self.audio.play_feedback("anger", wait=True)
            time.sleep(Config.FEEDBACK_DELAY)
            self.audio.play(os.path.join(Config.SONGS_DIR, "rude.mp3"))
        elif emotion == "Surprise":
            self.audio.play_feedback("surprised", wait=True)
        else:
            self.audio.play_feedback("no_face_detected", wait=True)

    # =========================
    # Emotion Timeline Thread
    # =========================
    def _start_emotion_timeline(self, story_id):
        self._stop_timeline()
        self.timeline_thread = EmotionManager(story_id, self.eyes, self.leds, self.servos)
        self.timeline_thread.start()

    def _stop_timeline(self):
        if self.timeline_thread and self.timeline_thread.is_alive():
            self.timeline_thread.stop()
            self.timeline_thread.join(timeout=2.0)
        self.timeline_thread = None
