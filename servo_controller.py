import time
import threading
import random
from contextlib import contextmanager

try:
    from board import SCL, SDA
    import busio
    from adafruit_pca9685 import PCA9685
    HAS_PCA = True
except ImportError:
    HAS_PCA = False


class ServoController:
    def __init__(self):
        if HAS_PCA:
            try:
                i2c = busio.I2C(SCL, SDA)
                self.pca = PCA9685(i2c)
                self.pca.frequency = 60
                self.is_simulated = False
            except Exception as e:
                print(f"[Servos] PCA9685 hardware creation failed ({e}). Entering Simulation Mode.")
                self.is_simulated = True
        else:
            print("[Servos] PCA9685 libraries not found. Entering Simulation Mode (dummy logging).")
            self.is_simulated = True

        self.SERVOMIN = 150
        self.SERVOMAX = 580

        self.left_hand = 0
        self.right_hand = 1
        self.neck = 2

        # Thread safety & tracking states
        self.lock = threading.Lock()
        self.current_neck_angle = 90
        self.is_animating = False
        self.idle_active = True
        self.running = True

        self.set_neutral()

        # Start idle head-turning background thread
        self.idle_thread = threading.Thread(target=self._idle_loop, daemon=True)
        self.idle_thread.start()

    def map_range(self, x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def angle_to_pulse(self, angle):
        return int(self.SERVOMIN + (angle / 180.0) * (self.SERVOMAX - self.SERVOMIN))

    @contextmanager
    def active_animation(self):
        """Context manager to safely manage active animations.
        It sets is_animating to True, returns the neck to 90 (neutral) first
        smoothly if it is currently turned left/right, yields to execute the
        animation, and then ensures servos are reset and is_animating is False.
        """
        self.is_animating = True
        
        # Smoothly return to 90 if not already there
        if self.current_neck_angle != 90:
            step = 1 if 90 > self.current_neck_angle else -1
            for angle in range(self.current_neck_angle, 90 + step, step):
                with self.lock:
                    if not self.is_simulated:
                        pulse = self.angle_to_pulse(angle)
                        self.pca.channels[self.neck].duty_cycle = pulse << 4
                self.current_neck_angle = angle
                time.sleep(0.015)
        
        try:
            yield
        finally:
            self.set_neutral()
            self.is_animating = False

    def set_servo_angle(self, channel, angle):
        with self.lock:
            if self.is_simulated:
                # Simulated: do not invoke I2C registers
                pass
            else:
                pulse = self.angle_to_pulse(angle)
                self.pca.channels[channel].duty_cycle = pulse << 4
            
            if channel == self.neck:
                self.current_neck_angle = angle

    def set_neutral(self):
        self.set_servo_angle(self.left_hand, 90)
        self.set_servo_angle(self.right_hand, 90)
        self.set_servo_angle(self.neck, 90)
        time.sleep(0.5)

    def perform_happy(self):
        with self.active_animation():
            for _ in range(2):
                for angle in range(90, 141, 2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    time.sleep(0.002) 
                    neck_angle = self.map_range(angle, 90, 150, 90, 105)
                    self.set_servo_angle(self.neck, neck_angle)
                    time.sleep(0.005)

                time.sleep(0.2)

                for angle in range(150, 49, -2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    neck_angle = self.map_range(angle, 150, 60, 120, 85)
                    time.sleep(0.002) 
                    self.set_servo_angle(self.neck, neck_angle)
                    time.sleep(0.005)

                time.sleep(0.1)

            self.set_neutral()


    def perform_angry(self):
        with self.active_animation():
            for _ in range(3):
                for angle in range(0, 91):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, 180 - angle)
                    time.sleep(0.001)
                for angle in range(90, -1, -1):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, 180 - angle)
                    time.sleep(0.001)

            self.neck_side_to_side(120, 60, 1)
            self.set_neutral()

    def perform_sad(self):
        with self.active_animation():
            for _ in range(3):
                for angle in range(90, 121):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    neck_map = self.map_range(angle, 90, 120, 90, 100)
                    self.set_servo_angle(self.neck, neck_map)
                    time.sleep(0.015)

                for angle in range(120, 89, -1):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    neck_map = self.map_range(angle, 120, 90, 100, 90)
                    self.set_servo_angle(self.neck, neck_map)
                    time.sleep(0.015)

            # self.neck_side_to_side(110, 70, 1)
            self.set_neutral()

    def neck_side_to_side(self, left, right, cycles):
        for _ in range(cycles):
            for angle in range(90, left + 1):
                self.set_servo_angle(self.neck, angle)
                time.sleep(0.01)
            for angle in range(left, right - 1, -1):
                self.set_servo_angle(self.neck, angle)
                time.sleep(0.01)
            for angle in range(right, 91):
                self.set_servo_angle(self.neck, angle)
                time.sleep(0.01)

    def wave(self, cycles=4):
        with self.active_animation():
            for _ in range(cycles):
                for angle in range(90, 59, -2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    time.sleep(0.02)
                for angle in range(60, 121, 2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    time.sleep(0.02)
                for angle in range(120, 89, -2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    time.sleep(0.02)
            self.set_neutral()

    def perform_excited(self):
        with self.active_animation():
            # Fast waving with quick neck nods
            for _ in range(3):
                for angle in range(100, 136, 3):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    # self.set_servo_angle(self.neck, 100)
                    time.sleep(0.02)
                for angle in range(135, 64, -3):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, angle)
                    # self.set_servo_angle(self.neck, 80)
                    time.sleep(0.02)
            self.set_neutral()

    def perform_love(self):
        with self.active_animation():
            # Gentle hug motion with slow neck tilts
            for _ in range(4):
                for angle in range(90, 60, -2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, 180 - angle)
                    # self.set_servo_angle(self.neck, 95)
                    time.sleep(0.03)
                for angle in range(60, 90, 2):
                    self.set_servo_angle(self.left_hand, angle)
                    self.set_servo_angle(self.right_hand, 180 - angle)
                    # self.set_servo_angle(self.neck, 85)
                    time.sleep(0.03)
            self.set_neutral()

    def move_neck_smoothly(self, target_angle, speed=0.03):
        """Move the neck smoothly to target_angle, aborting immediately if an animation starts."""
        step = 1 if target_angle > self.current_neck_angle else -1
        for angle in range(self.current_neck_angle, target_angle + step, step):
            if self.is_animating or not self.running:
                return False
            self.set_servo_angle(self.neck, angle)
            time.sleep(speed)
        return True

    def _idle_sleep(self, duration):
        """Sleeps for duration seconds, returning False if an animation starts."""
        start = time.monotonic()
        while time.monotonic() - start < duration:
            if self.is_animating or not self.running:
                return False
            time.sleep(0.1)
        return True

    def _idle_loop(self):
        """Background thread loop that periodically, smoothly turns the neck when idling.
        It looks to one side, waits 3 seconds, returns to neutral, looks to the other side,
        waits 3 seconds, returns to neutral, and then waits a random 30-90 seconds.
        """
        # Wait a few seconds initially after boot
        time.sleep(5)
        
        while self.running:
            if self.idle_active and not self.is_animating:
                # 1. Randomly choose which side to look first: left (115) or right (65)
                side_a = random.choice([65, 115])
                side_b = 65 if side_a == 115 else 115
                
                # Check is_animating before starting sequence
                if not self.is_animating:
                    # Move to side A smoothly
                    moved_a = self.move_neck_smoothly(side_a, speed=0.03)
                    
                    if moved_a and not self.is_animating:
                        # Hold side A for 3 seconds
                        if self._idle_sleep(3.0):
                            # Return to neutral (90) smoothly
                            returned_a = self.move_neck_smoothly(90, speed=0.03)
                            
                            if returned_a and not self.is_animating:
                                # Small pause at center (0.5s) before looking to other side
                                if self._idle_sleep(0.5):
                                    # Move to side B smoothly
                                    moved_b = self.move_neck_smoothly(side_b, speed=0.03)
                                    
                                    if moved_b and not self.is_animating:
                                        # Hold side B for 3 seconds
                                        if self._idle_sleep(3.0):
                                            # Return to neutral (90) smoothly
                                            self.move_neck_smoothly(90, speed=0.03)
                
                # Sleep a random interval from 30 to 90 seconds (per user feedback)
                # Sleep in small slices so we can wake up instantly when an animation starts
                wait_time = random.uniform(30, 90)
                self._idle_sleep(wait_time)
            else:
                time.sleep(0.5)
