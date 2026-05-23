try:
    import RPi.GPIO as GPIO
except ImportError:
    print("[Touch] RPi.GPIO not found. Entering Simulation Mode (dummy logging).")
    
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
        IN = "IN"
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
from config import Config


class TouchSensor:
    def __init__(self, leds, eyes, servos, handler=None):
        self.leds = leds
        self.eyes = eyes
        self.servos = servos
        self.handler = handler
        self.touch_pin = 4  # GPIO 4 (Physical Pin 7)
        self.cooldown = Config.TOUCH_COOLDOWN
        self.last_touch_time = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.touch_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def listen_for_touch(self):
        print("[TouchSensor] Ready on GPIO 4...")
        while True:
            if GPIO.input(self.touch_pin) == GPIO.HIGH:
                # Ignore touch if the robot is sleeping!
                if getattr(self.handler, "sleeping", False):
                    time.sleep(0.5)
                    continue

                now = time.time()
                if now - self.last_touch_time >= self.cooldown:
                    self.last_touch_time = now
                    print("[TouchSensor] Touch detected!")

                    # Start the reaction in a thread
                    threading.Thread(target=self._handle_touch, daemon=True).start()

            time.sleep(0.1)

    def _handle_touch(self):
        # Disable blinking
        self.eyes.auto_blink = False
        self.eyes.set_mood("love")
        self.leds.love()


        threading.Thread(target=self.servos.perform_love, daemon=True).start()
        duration = 5.0  # adjust as needed

        # Keep drawing love mood for 2.5 seconds
        start_time = time.time()
        while time.time() - start_time < duration:
            self.eyes.update()
            time.sleep(0.05)

        self.eyes.set_mood("neutral")
        self.leds.set_neutral()

        # to take the eye back to normal
        for _ in range(20):  # show neutral for 1 second
            self.eyes.update()
            time.sleep(0.05)

        # Re-enable blinking
        self.eyes.auto_blink = True
