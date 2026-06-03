import time
import random
import math
import threading
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import board
    import digitalio
    from adafruit_rgb_display import ili9341
    HAS_DISPLAY = True
except ImportError:
    HAS_DISPLAY = False

from config import Config

# Display dimensions for landscape mode
WIDTH = 320
HEIGHT = 240

# Mood color definitions
MOOD_COLORS = {
    "happy": (46, 204, 113),     # Soft Emerald Green
    "sad": (52, 152, 219),       # Beautiful Sky Blue
    "angry": (231, 76, 60),      # Premium Coral/Crimson
    "love": (255, 105, 180),     # Sweet Rose Pink
    "neutral": (0, 210, 255),    # Vibrant Cyber Teal
    "excited": (155, 89, 182)    # Premium Amethyst Purple
}

class RoboEyes:
    def __init__(self):
        self.width = WIDTH
        self.height = HEIGHT
        self.image = Image.new("RGB", (self.width, self.height), "black")
        self.draw_obj = ImageDraw.Draw(self.image)

        if HAS_DISPLAY:
            try:
                # Setup ILI9341 display inside the class
                cs_pin = digitalio.DigitalInOut(board.D5)
                dc_pin = digitalio.DigitalInOut(board.D6)
                reset_pin = digitalio.DigitalInOut(board.D13)
                spi = board.SPI()

                self.disp = ili9341.ILI9341(
                    spi,
                    cs=cs_pin,
                    dc=dc_pin,
                    rst=reset_pin,
                    width=WIDTH,
                    height=HEIGHT,
                    rotation=180
                )
                self.is_simulated = False
            except Exception as e:
                print(f"[Display] SPI display hardware initialization failed ({e}). Running in headless Simulation Mode.")
                self.is_simulated = True
                self.disp = None
        else:
            print("[Display] Display libraries (board/digitalio/adafruit_rgb_display) not found. Running in headless Simulation Mode.")
            self.is_simulated = True
            self.disp = None

        self.eye_w = 110
        self.eye_h = 110
        self.eye_spacing = 30
        self.eye_radius = 18

        total_eye_width = 2 * self.eye_w + self.eye_spacing
        start_x = (self.width - total_eye_width) // 2
        y_pos = (self.height - self.eye_h) // 2
        self.left_eye_pos = (start_x, y_pos)
        self.right_eye_pos = (start_x + self.eye_w + self.eye_spacing, y_pos)

        self.mood = "neutral"
        self.blinking = False
        self.auto_blink = False

        self.blink_direction = 0
        self.blink_progress = 0.0
        self.blink_speed_close = 0.08
        self.blink_speed_open = 0.12
        self.blink_hold_time = 0.03
        self.blink_hold_timer = 0

        self.last_blink = time.monotonic()
        self.next_blink_time = time.monotonic() + random.uniform(8, 16)

        self.frame_interval = 0.03
        self.last_frame = 0

        self.vertical_offset = 0
        self.scale_factor = 1.0
        self.animation_phase = 0.0

        self.eye_x_offset = 0.0
        self.eye_y_offset = 0.0
        self.target_eye_x_offset = 0.0
        self.target_eye_y_offset = 0.0
        self.next_neutral_shift_time = time.monotonic() + random.uniform(3, 7)
        self.neutral_shift_start_time = 0
        self.neutral_shift_duration = 0.6
        # New configuration for smoother idle look and auto blink
        self.idle_interval = 30  # minimum seconds between idle moves
        self.idle_variation = 60  # additional random seconds (total 30-90)
        self.blink_interval = 5   # base seconds between blinks
        self.blink_variation = 4  # random extra seconds
        self.last_idle_move = time.monotonic()
        self.next_idle_time = self.last_idle_move + self.idle_interval + random.uniform(0, self.idle_variation)
        # Thread lock for safe offset updates
        self.lock = threading.Lock()


        # Thread control flags
        self.running = False
        self.run = False
        self.update_thread = None

        # Educational pause state — initialized here instead of only in edu_start()
        self.is_paused = False
        self.paused_time = None
        self.accumulated_paused = 0.0

        # Cache the font once to avoid repeated disk reads on Pi Zero 2W
        self._cached_font = None
        try:
            self._cached_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 160
            )
        except OSError:
            self._cached_font = ImageFont.load_default()

        # Cache animal images to avoid repeated disk reads
        self._animal_image_cache = {}

    def set_mood(self, mood):
        self.mood = mood


    def blink(self):
        if not self.blinking:
            self.blinking = True
            self.blink_direction = 1
            self.blink_progress = 0.0
            self.blink_speed_close = random.uniform(0.06, 0.09)
            self.blink_speed_open = random.uniform(0.09, 0.13)

    def toggle_auto_blink(self):
        self.auto_blink = not self.auto_blink

    def mood_color(self):
        return MOOD_COLORS.get(self.mood, (0, 0, 255))

    def draw(self):
        self.image.paste((0, 0, 0), [0, 0, self.width, self.height])
        self._draw_eye(self.draw_obj, self.left_eye_pos, True)
        self._draw_eye(self.draw_obj, self.right_eye_pos, False)
        if not self.is_simulated and self.disp is not None:
            self.disp.image(self.image)

    def _draw_heart(self, draw, cx, cy, size, fill_color):
        scale = 0.05
        points = []
        for t in range(0, 360, 5):
            angle = math.radians(t)
            x = size * 16 * (math.sin(angle) ** 3)
            y = -size * (13 * math.cos(angle) - 5 * math.cos(2 * angle) - 2 * math.cos(3 * angle) - math.cos(4 * angle))
            points.append((cx + int(x * scale), cy + int(y * scale)))
        draw.polygon(points, fill=fill_color)

    def _draw_star(self, draw, cx, cy, size, fill_color):
        points = []
        for i in range(5):
            angle_outer = math.radians(i * 72 - 90)
            angle_inner = math.radians(i * 72 + 36 - 90)
            points.append((cx + size * math.cos(angle_outer), cy + size * math.sin(angle_outer)))
            points.append((cx + size * 0.5 * math.cos(angle_inner), cy + size * 0.5 * math.sin(angle_inner)))
        draw.polygon(points, fill=fill_color)

    def _draw_eye(self, draw, pos, is_left):
        x, y = pos
        y += self.vertical_offset

        scale = self.scale_factor
        eye_w = int(self.eye_w * scale)
        eye_h = int(self.eye_h * scale)
        eye_x = x + (self.eye_w - eye_w) // 2
        eye_y = y + (self.eye_h - eye_h) // 2

        b, g, r = self.mood_color()
        color = (r, g, b)

        # Smooth glide offset (updated in update())
        # Entire solid eye capsules glide around in neutral, sad, and angry moods!
        offset_x = int(self.eye_x_offset) if self.mood in ("neutral", "sad", "angry") else 0
        offset_y = int(self.eye_y_offset) if self.mood in ("neutral", "sad", "angry") else 0

        # Shifted center
        cx = eye_x + eye_w // 2 + offset_x
        cy = eye_y + eye_h // 2 + offset_y
        size = min(eye_w, eye_h) // 2

        # 1. Draw base eye moods (all drawn centering at shifted cx, cy)
        if self.mood == "love":
            self._draw_heart(draw, cx, cy, size + 10, color)
        elif self.mood == "excited":
            self._draw_star(draw, cx, cy, size, color)
        elif self.mood == "happy":
            self._draw_happy_eye(draw, cx, cy, size, color)
        elif self.mood == "sad":
            self._draw_sad_eye(draw, cx, cy, eye_w, eye_h, is_left, color)
        elif self.mood == "angry":
            self._draw_angry_eye(draw, cx, cy, eye_w, eye_h, is_left, color)
        else: # neutral / default
            # Solid main capsule
            draw.rounded_rectangle(
                (cx - eye_w // 2, cy - eye_h // 2, cx + eye_w // 2, cy + eye_h // 2),
                radius=self.eye_radius,
                fill=color
            )

        # 2. Overlay Dual-Eyelid Curved Blinking (drawn over the shifted eye shapes!)
        if self.blinking:
            if self.blink_progress >= 0.95:
                # Fully closed: draw a beautiful horizontal glowing slit line
                draw.rectangle(
                    (cx - eye_w // 2 - 10, cy - eye_h // 2 - 10, cx + eye_w // 2 + 10, cy + eye_h // 2 + 10),
                    fill="black"
                )
                slit_w = eye_w - 20
                draw.rounded_rectangle(
                    (cx - slit_w // 2, cy - 2, cx + slit_w // 2, cy + 2),
                    radius=2,
                    fill=color
                )
            else:
                # Upper Eyelid: curves down from top to meet center+4
                upper_bottom_y = (cy - eye_h // 2) + int((eye_h // 2 + 4) * self.blink_progress)
                draw.ellipse(
                    (cx - eye_w // 2 - 15, upper_bottom_y - eye_h, cx + eye_w // 2 + 15, upper_bottom_y),
                    fill="black"
                )
                # Lower Eyelid: curves up from bottom to meet center-4
                lower_top_y = (cy + eye_h // 2) - int((eye_h // 2 + 4) * self.blink_progress)
                draw.ellipse(
                    (cx - eye_w // 2 - 15, lower_top_y, cx + eye_w // 2 + 15, lower_top_y + eye_h),
                    fill="black"
                )

    def _draw_sad_eye(self, draw, cx, cy, eye_w, eye_h, is_left, color):
        # Draw beautiful solid eye base
        draw.rounded_rectangle(
            (cx - eye_w // 2, cy - eye_h // 2, cx + eye_w // 2, cy + eye_h // 2),
            radius=self.eye_radius,
            fill=color
        )
        
        # Cut top-outer corners smoothly to make a worried, drooping sad brow circle
        if is_left:
            # Cut top-left
            draw.ellipse((cx - int(eye_w * 1.15), cy - int(eye_h * 1.0), cx + int(eye_w * 0.15), cy - int(eye_h * 0.1)), fill="black")
        else:
            # Cut top-right
            draw.ellipse((cx - int(eye_w * 0.15), cy - int(eye_h * 1.0), cx + int(eye_w * 1.15), cy - int(eye_h * 0.1)), fill="black")

    def _draw_angry_eye(self, draw, cx, cy, eye_w, eye_h, is_left, color):
        # Draw beautiful solid eye base
        draw.rounded_rectangle(
            (cx - eye_w // 2, cy - eye_h // 2, cx + eye_w // 2, cy + eye_h // 2),
            radius=self.eye_radius,
            fill=color
        )

        # Cut top-inner corners smoothly to make a fierce, sloping angry brow circle
        if is_left:
            # Cut top-right
            draw.ellipse((cx - int(eye_w * 0.15), cy - int(eye_h * 1.0), cx + int(eye_w * 1.15), cy - int(eye_h * 0.1)), fill="black")
        else:
            # Cut top-left
            draw.ellipse((cx - int(eye_w * 1.15), cy - int(eye_h * 1.0), cx + int(eye_w * 0.15), cy - int(eye_h * 0.1)), fill="black")

    def _idle_look(self, now):
        """Handle smooth random eye movement when idle.
        Uses self.idle_interval/variation to schedule next move.
        Random target offsets are within +/-30px X and +/-15px Y.
        Offsets are applied via target_eye_x_offset / target_eye_y_offset.
        """
        with self.lock:
            if now >= self.next_idle_time:
                # Choose new random target offsets
                self.target_eye_x_offset = random.randint(-30, 30)
                self.target_eye_y_offset = random.randint(-15, 15)
                self.last_idle_move = now
                self.next_idle_time = now + self.idle_interval + random.uniform(0, self.idle_variation)

    def _auto_blink(self, now):
        """Smooth auto‑blink using sinusoidal easing.
        Blink cycle consists of closing and opening phases with configurable durations.
        """
        # Parameters for blink phases (seconds)
        close_duration = 0.15
        open_duration = 0.12
        total_duration = close_duration + open_duration
        if not hasattr(self, "_blink_cycle_start"):
            self._blink_cycle_start = None
        if self.auto_blink and not self.blinking and now >= self.next_blink_time:
            # Start a new blink cycle
            self.blinking = True
            self._blink_cycle_start = now
            self.blink_direction = 1  # 1 for closing, -1 for opening
            self.blink_progress = 0.0
        if self.blinking:
            elapsed = now - self._blink_cycle_start
            if elapsed <= close_duration:
                # Closing phase
                t = elapsed / close_duration
                # Sinusoidal ease-in
                self.blink_progress = 0.5 * (1 - math.cos(math.pi * t))
            elif elapsed <= total_duration:
                # Opening phase
                t = (elapsed - close_duration) / open_duration
                # Sinusoidal ease-out
                self.blink_progress = 1.0 - 0.5 * (1 - math.cos(math.pi * t))
            else:
                # Blink finished
                self.blinking = False
                self.blink_direction = 0
                self.blink_progress = 0.0
                self._blink_cycle_start = None
                self.next_blink_time = now + self.blink_interval + random.uniform(0, self.blink_variation)

    def update(self):
        now = time.monotonic()
        dt = now - self.last_frame
        self.last_frame = now

        self.animation_phase += dt

        if self.mood == "happy":
            self.vertical_offset = int(math.sin(self.animation_phase * 3) * 5)
            self.scale_factor = 1.0
        elif self.mood == "sad":
            amplitude = 3
            base_offset = 8
            self.vertical_offset = base_offset + int(amplitude * math.sin(self.animation_phase * 1.5))
            self.scale_factor = 1.0
        elif self.mood in ("angry", "love", "excited"):
            self.vertical_offset = 0
            self.scale_factor = 1.0 + 0.05 * math.sin(self.animation_phase * 4)
        else:
            self.vertical_offset = 0
            self.scale_factor = 1.0

        # Idle look handling (smooth random eye movement)
        self._idle_look(now)

        # Smooth organic glides (lerp) toward targets
        lerp_speed = 0.12
        self.eye_x_offset += (self.target_eye_x_offset - self.eye_x_offset) * lerp_speed
        self.eye_y_offset += (self.target_eye_y_offset - self.eye_y_offset) * lerp_speed

        # Auto‑blink handling with smooth easing
        self._auto_blink(now)

        self.draw()

    def set_neutral(self):
        self.set_mood("neutral")
        # FIX: Always ENABLE auto_blink, don't toggle (was toggling before,
        # so every other call would disable blinking)
        self.auto_blink = True
        self.update()

    def set_black(self):
        """Turn off the display and stop eye animations (sleep mode)."""
        self.blinking = False
        self.auto_blink = False
        self.image.paste((0, 0, 0), [0, 0, self.width, self.height])
        if not self.is_simulated and self.disp is not None:
            self.disp.image(self.image)

    def display_number(self, num):
        image = Image.new("RGB", (self.width, self.height), "black")
        draw = ImageDraw.Draw(image)
        font = self._cached_font
        text = str(num)
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (self.width - w) // 2
        y = (self.height - h) // 2 - 30
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
        if not self.is_simulated and self.disp is not None:
            self.disp.image(image)

    def numbers(self):
        # (number, timestamp in seconds)
        timeline = [
            (1, 8),
            (2, 10),
            (3, 13),
            (4, 16),
            (5, 18),
            (6, 21),
            (7, 23),
            (8, 26),
            (9, 29),
            (10, 31)
        ]

        start_time = time.time()

        for num, target_time in timeline:
            # Wait until target time is reached
            while self.get_elapsed_time(start_time) < target_time:
                time.sleep(0.05)
                if not self.run:
                    return
            if not self.run:
                return
            self.display_number(num)


    def countdown_numbers(self, delay=1):
        for num in range(10, 0, -1):
            self.display_number(num)
            time.sleep(delay)

    def display_letter(self, letter):
        image = Image.new("RGB", (self.width, self.height), "black")
        draw = ImageDraw.Draw(image)
        font = self._cached_font
        bbox = draw.textbbox((0, 0), letter, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (self.width - w) // 2
        y = (self.height - h) // 2 - 30
        draw.text((x, y), letter, font=font, fill=(255, 255, 255))
        if not self.is_simulated and self.disp is not None:
            self.disp.image(image)

    def alphabet(self):
        timeline = {
            'A': 7, 'B': 9, 'C': 11, 'D': 13, 'E': 15, 'F': 19,
            'G': 21, 'H': 24, 'I': 26, 'J': 29, 'K': 31, 'L': 34,
            'M': 36, 'N': 39, 'O': 41, 'P': 44, 'Q': 46, 'R': 49,
            'S': 51, 'T': 54, 'U': 56, 'V': 59, 'W': 62, 'X': 64,
            'Y': 66, 'Z': 69
        }

        start_time = time.time()

        for letter, target_sec in timeline.items():
            while self.get_elapsed_time(start_time) < target_sec:
                time.sleep(0.05)
                if not self.run:
                    return
            if not self.run:
                return
            self.display_letter(letter)


    def display_animal(self, name, delay=0):
        """Display an animal image. Uses cache to avoid repeated disk reads."""
        try:
            # Use absolute path via Config
            img_path = os.path.join(Config.ANIMAL_IMAGE_DIR, f"{name}.png")

            # Check cache first
            if name in self._animal_image_cache:
                background = self._animal_image_cache[name]
            else:
                image = Image.open(img_path).convert("RGB")
                image = ImageOps.fit(image, (239, 239), method=Image.LANCZOS)
                background = Image.new("RGB", (self.width, self.height), "black")
                x = (self.width - 239) // 2
                y = (self.height - 239) // 2
                background.paste(image, (x, y))
                self._animal_image_cache[name] = background

            if not self.is_simulated and self.disp is not None:
                self.disp.image(background)
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            print(f"Error loading/displaying animal '{name}': {e}")

    def animals(self):
        # Timeline: animal name + time offset in seconds
        timeline = [
            ("dog", 0),
            ("cat", 12),
            ("cow", 19),
            ("bird", 27),
            ("pig", 38),
            ("horse", 45),
            ("wolf", 52),
            ("snake", 60),
            ("frog", 70),
            ("whale", 77),
            ("owl", 85),
            ("sheep", 93),
            ("chicken", 103),
            ("bee", 111),
            ("monkey", 120),
            ("lion", 127),
        ]

        start_time = time.time()

        for animal, target_offset in timeline:
            # Wait until it's the correct time to display
            while self.get_elapsed_time(start_time) < target_offset:
                time.sleep(0.05)
                if not self.run:
                    return
            if not self.run:
                return
            self.display_animal(animal)


    def music(self, duration):
        self.display_animal(name="Music_Symbol", delay=0)


    def start(self):
        """Start continuous updating in a background thread."""
        if not self.running:
            self.running = True
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()

    def stop(self):
        """Stop the background update loop."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
            self.update_thread = None

    def _update_loop(self):
        """Internal method that runs in a thread, continuously calling update()."""
        while self.running:
            self.update()
            time.sleep(self.frame_interval)

    def edu_start(self):
        self.run = True
        self.is_paused = False
        self.paused_time = None
        self.accumulated_paused = 0.0

    def edu_stop(self):
        """Signal the educational display loop to exit.
        Does NOT restart the eye loop - the caller is responsible for that."""
        self.run = False

    def pause(self):
        if not self.is_paused:
            self.is_paused = True
            self.paused_time = time.time()

    def resume(self):
        if self.is_paused:
            self.accumulated_paused += time.time() - self.paused_time
            self.is_paused = False
            self.paused_time = None

    def get_elapsed_time(self, start_time):
        if self.is_paused:
            return self.paused_time - start_time - self.accumulated_paused
        else:
            return time.time() - start_time - self.accumulated_paused