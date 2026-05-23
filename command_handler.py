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

        self.number_map = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }

    # =========================
    # Core Command Dispatcher
    # =========================
    def handle(self, intent, slots):
        # print(f"[Command] Intent: {intent}, Slots: {slots}")

        # If sleeping, only allow the "wake" intent!
        if getattr(self, "sleeping", False):
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
            self.leds.stop_music()
            self.leds.set_neutral()
            self.eyes.set_mood("neutral")
            self.eyes.start()
            
            self.audio.play_feedback("playback_finished", wait=True)

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

        if type_ == "story":
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
        
        self.eyes.stop()
        self.eyes.edu_start()

        self.audio.play_feedback(feedback, wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        def on_finish():
            self.eyes.set_mood("neutral")
            self.eyes.start()
            self.eyes.edu_stop()
            self.audio.play_feedback("playback_finished", wait=True)

        # added to play the audio simultaneously
        threading.Thread(target=self.audio.play, args=(file,), kwargs={
            "category": "education", "mode": "random", "callback": on_finish
        }, daemon=True).start()

        # Set display only (neutral LEDs)
        if type_ == "alphabet":
            self.eyes.alphabet()
        elif type_ == "numbers":
            self.eyes.numbers()
        elif type_ == "animals":
            self.eyes.animals()


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
        if not self.audio.is_playing:
            print("[Stop] Nothing playing")
            return
        self.audio.stop()
        self._stop_timeline()
        self.leds.stop_music()
        self.eyes.edu_stop()
        self.eyes.stop()
        self.leds.set_neutral()
        self.servos.set_neutral()
        self.eyes.set_mood("neutral")
        self.eyes.set_neutral()
        self.eyes.start()
        self.audio.play_feedback("playback_stopped", wait=True)

    def _handle_next(self):
        if not self.audio.is_playing:
            print("[Next] Nothing playing")
            return

        last_type = self.audio.current_category
        last_index = self.audio.last_index
        last_mode = self.audio.last_play_mode

        self.audio.stop()
        self._stop_timeline()
        self.leds.stop_music()

        time.sleep(Config.FEEDBACK_DELAY)
        self.audio.play_feedback("playback_stopped", wait=True)
        time.sleep(Config.FEEDBACK_DELAY)
        self.audio.play_feedback("playback_switching", wait=True)
        time.sleep(Config.FEEDBACK_DELAY)

        if last_mode == "specific":
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
            elif last_type == "education":
                self._play_educational(random.choice(["alphabet", "numbers", "animals"]))

    def _handle_sleep(self):
        self.sleeping = True
        self.audio.stop()
        self._stop_timeline()
        self.eyes.stop()
        self.eyes.set_black()
        self.leds.turn_off()
        self.servos.set_neutral()
        self.audio.play_feedback("going_to_sleep", wait=True)

    def _handle_wake_up(self):
        if getattr(self, "sleeping", False):  # default False if not set yet
            self.eyes.set_neutral()
            self.leds.set_neutral()
            self.servos.set_neutral()
            self.eyes.start()  # restart auto-blink / drawing
            self.audio.play_feedback("waking_up", wait=True)
            self.sleeping = False


    def _on_playback_finish(self):
        self._stop_timeline()
        self.eyes.set_mood("neutral")
        self.leds.stop_music()
        self.eyes.start()
        self.leds.set_neutral()
        self.servos.set_neutral()
        self.audio.play_feedback("playback_finished", wait=True)

    # =========================
    # Emotion Detection
    # =========================
    def _handle_emotion_detection(self):
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
            self.timeline_thread.join()
        self.timeline_thread = None
