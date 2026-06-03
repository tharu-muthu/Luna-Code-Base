import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables (.env parser)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()


class Config:
    BASE_DIR = BASE_DIR

    # Media and feedback paths
    MEDIA_DIR = os.path.join(BASE_DIR, "media")
    STORIES_DIR = os.path.join(MEDIA_DIR, "stories")
    SONGS_DIR = os.path.join(MEDIA_DIR, "songs")
    EDUCATION_DIR = os.path.join(MEDIA_DIR, "education")
    FEEDBACK_DIR = os.path.join(BASE_DIR, "feedback")
    IMAGE_DIR = os.path.join(BASE_DIR, "images")
    ANIMAL_IMAGE_DIR = os.path.join(IMAGE_DIR, "animals")

    # Audio configuration
    DEFAULT_VOLUME = 0.6            # 0.0 to 1.0
    VOLUME_STEP = 0.1

    # Delays and durations
    FEEDBACK_DELAY = 0.5
    COMMAND_LISTEN_DURATION = 3
    TOUCH_COOLDOWN = 5
    MOTOR_RUN_DURATION = 3

    # API Keys (loaded dynamically with safe fallbacks)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDZ-qp3bV0WS5BywXjL84pYVqyH5TlbZiI")
    PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "HaA1GFy3+aa2hMf4z9tIJCV1WTZnUwyhchdcoJ38UXjDUXBaz03dzw==")

    # Porcupine + Rhino engine paths
    WAKE_WORD_PATH = os.path.join(BASE_DIR, "hey-luna_en_raspberry-pi_v3_0_0.ppn")
    RHINO_CONTEXT_PATH = os.path.join(BASE_DIR, "robot_commands_en_raspberry-pi_v3_0_0.rhn")
    RHINO_MODEL_PATH = os.path.join(BASE_DIR, "lib", "raspberry-pi", "rhino_params.pv")
    RHINO_LIB_PATH = os.path.join(BASE_DIR, "lib", "raspberry-pi", "arm11", "libpv_rhino.so")
