import time

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

        self.set_neutral()

    def map_range(self, x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def angle_to_pulse(self, angle):
        return int(self.SERVOMIN + (angle / 180.0) * (self.SERVOMAX - self.SERVOMIN))

    def set_servo_angle(self, channel, angle):
        if self.is_simulated:
            # Simulated: do not invoke I2C registers
            pass
        else:
            pulse = self.angle_to_pulse(angle)
            self.pca.channels[channel].duty_cycle = pulse << 4

    def set_neutral(self):
        self.set_servo_angle(self.left_hand, 90)
        self.set_servo_angle(self.right_hand, 90)
        self.set_servo_angle(self.neck, 90)
        time.sleep(0.5)

    def perform_happy(self):
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
