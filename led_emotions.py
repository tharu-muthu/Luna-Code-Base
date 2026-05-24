try:
    import RPi.GPIO as GPIO
except ImportError:
    print("[LED] RPi.GPIO not found. Entering Simulation Mode (dummy logging).")
    
    class DummyPWM:
        def __init__(self, pin, frequency):
            self.pin = pin
            self.frequency = frequency
        def start(self, duty_cycle):
            pass
        def ChangeDutyCycle(self, duty_cycle):
            pass
        def stop(self):
            pass

    class DummyGPIO:
        BCM = "BCM"
        OUT = "OUT"
        LOW = 0
        HIGH = 1
        PUD_DOWN = "PUD_DOWN"
        
        def setmode(self, mode): pass
        def setwarnings(self, state): pass
        def setup(self, pins, direction, pull_up_down=None): pass
        def output(self, pin, value): pass
        def input(self, pin): return 0
        def PWM(self, pin, frequency):
            return DummyPWM(pin, frequency)
        def cleanup(self): pass

    GPIO = DummyGPIO()

import time
import threading

class LEDController:
    def __init__(self):
        self.RED_PIN = 7
        self.GREEN_PIN = 9
        self.BLUE_PIN = 16

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.RED_PIN, GPIO.OUT)
        GPIO.setup(self.GREEN_PIN, GPIO.OUT)
        GPIO.setup(self.BLUE_PIN, GPIO.OUT)

        self.red_pwm = GPIO.PWM(self.RED_PIN, 100)
        self.green_pwm = GPIO.PWM(self.GREEN_PIN, 100)
        self.blue_pwm = GPIO.PWM(self.BLUE_PIN, 100)

        self.red_pwm.start(0)
        self.green_pwm.start(0)
        self.blue_pwm.start(0)

        self.music_playing = False
        self.music_thread = None

    def set_color(self, r, g, b):
        self.red_pwm.ChangeDutyCycle(r)
        self.green_pwm.ChangeDutyCycle(g)
        self.blue_pwm.ChangeDutyCycle(b)

    def fade_to(self, r_target, g_target, b_target, steps=50, delay=0.02):
        for i in range(steps + 1):
            # Early exit if music was stopped mid-fade
            if not self.music_playing and self.music_thread is not None:
                return
            r = int(r_target * i / steps)
            g = int(g_target * i / steps)
            b = int(b_target * i / steps)
            self.set_color(r, g, b)
            time.sleep(delay)

    def happy(self): self.fade_to(0, 100, 0)
    def sad(self): self.fade_to(0, 0, 100)
    def angry(self): self.fade_to(100, 0, 0)
    def excited(self): self.fade_to(100, 100, 0)
    def love(self): self.fade_to(100, 0, 100)
    def set_neutral(self): self.fade_to(0, 50, 100)
    def turn_off(self): self.set_color(0, 0, 0)

    def music(self):
        self.music_playing = True

        def music_loop():
            while self.music_playing:
                self.fade_to(100, 0, 0)
                if not self.music_playing: break
                time.sleep(0.3)
                self.fade_to(0, 100, 0)
                if not self.music_playing: break
                time.sleep(0.3)
                self.fade_to(0, 0, 100)
                if not self.music_playing: break
                time.sleep(0.3)
                self.fade_to(100, 100, 0)
                if not self.music_playing: break
                time.sleep(0.3)
                self.fade_to(100, 0, 100)
                if not self.music_playing: break
                time.sleep(0.3)
                self.fade_to(0, 50, 100)
                if not self.music_playing: break
                time.sleep(0.3)

        # FIX: Set daemon=True so thread doesn't block process exit
        self.music_thread = threading.Thread(target=music_loop, daemon=True)
        self.music_thread.start()

    def stop_music(self):
        self.music_playing = False
        if self.music_thread:
            # fade_to now checks music_playing, so join won't hang long
            self.music_thread.join(timeout=2.0)
            self.music_thread = None
        self.turn_off()

    def cleanup(self):
        self.stop_music()
        self.red_pwm.stop()
        self.green_pwm.stop()
        self.blue_pwm.stop()
        GPIO.cleanup()
