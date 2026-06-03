import threading
import time
import pygame

from voice_controller import VoiceController
from command_handler import CommandHandler
from emotion_manager import EmotionManager

from display import RoboEyes
from led_emotions import LEDController
from servo_controller import ServoController
from motor_controller import MotorController
from touch_sensor import TouchSensor

from audio_player import AudioPlayer
from emotion_detector import EmotionDetector
from config import Config

# NEW: import the web API factory
from web_api import create_app


def initialize_components():
    # Initialize hardware
    eyes = RoboEyes()
    leds = LEDController()
    servos = ServoController()
    motors = MotorController()
    audio = AudioPlayer()

    # Startup neutral mode
    eyes.set_neutral()
    leds.set_neutral()
    servos.set_neutral()

    # Start automatic eye updates
    eyes.auto_blink = True
    eyes.start()

    # Startup feedback (only at boot)
    audio.play_feedback("activated_now_listening_to_you", wait=True)

    # Core controllers
    emotion_detector = EmotionDetector(api_key=Config.GOOGLE_API_KEY)
    handler = CommandHandler(audio, eyes, leds, servos, motors, emotion_detector)
    voice = VoiceController(handler, audio)

    # Touch sensor thread
    touch_sensor = TouchSensor(leds, eyes, servos, handler)
    threading.Thread(target=touch_sensor.listen_for_touch, daemon=True).start()

    # RETURN EVERYTHING we need for the web server
    return voice, audio, handler, eyes, leds, servos, motors


def main():
    try:
        voice_controller, audio, handler, eyes, leds, servos, motors = initialize_components()

        # ---- Start Web API (same process, shared objects) ----
        app = create_app(handler, audio, eyes, leds, servos, motors)

        def run_web():
            try:
                app.run(
                    host="0.0.0.0",
                    port=9000,
                    use_reloader=False,  # prevents double-process / port conflict bug
                    threaded=True,
                    debug=False
                )
            except PermissionError:
                print("[WEB] ERROR - port 9000 requires root or is blocked.")
            except OSError as e:
                print(f"[WEB] ERROR - could not bind port 9000: {e}")
                print("[WEB] Fix: sudo fuser -k 9000/tcp  then restart.")
            except Exception as e:
                print(f"[WEB] Unexpected error: {e}")

        threading.Thread(target=run_web, name="flask-web", daemon=True).start()
        print("[WEB] Control UI starting on http://luna.local:9000 ...")


        # ---- Start voice loop (blocking) ----
        voice_controller.listen_forever()

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        try:
            eyes.stop()
        except:
            pass
        try:
            leds.cleanup()
        except:
            pass
        try:
            motors.stop()
        except:
            pass
        try:
            servos.set_neutral()
        except:
            pass
        pygame.quit()


if __name__ == "__main__":
    main()
