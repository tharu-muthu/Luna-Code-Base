import threading
import time
from emotion_timeline import EmotionTimeline


class EmotionManager(threading.Thread):
    def __init__(self, story_id, eyes, leds, servos):
        super().__init__()
        self.story_id = story_id
        self.eyes = eyes
        self.leds = leds
        self.servos = servos
        self.timeline = EmotionTimeline(story_id)
        self.timeline.start()
        self.running = True
        self.last_emotion = None

    def run(self):
        while self.running:
            current_emotion = self.timeline.get_current_emotion()

            if current_emotion and current_emotion != self.last_emotion:
                self._apply_emotion(current_emotion)
                self.last_emotion = current_emotion

            time.sleep(0.3)  # Smooth update rate

    def stop(self):
        self.running = False

    def pause(self):
        self.timeline.pause()

    def resume(self):
        self.timeline.resume()

    def _apply_emotion(self, emotion):
        print(f"[EmotionManager] Switching to emotion: {emotion}")
        # Display
        self.eyes.set_mood(emotion)
        self.eyes.auto_blink = False

        # LED
        led_method = getattr(self.leds, emotion, None)
        if callable(led_method):
            led_method()

        # Servo
        servo_method_map = {
            "happy": self.servos.perform_happy,
            "sad": self.servos.perform_sad,
            "angry": self.servos.perform_angry,
            "excited": self.servos.perform_excited,
            "love": self.servos.perform_love

        }
        if emotion in servo_method_map:
            threading.Thread(target=servo_method_map[emotion], daemon=True).start()
