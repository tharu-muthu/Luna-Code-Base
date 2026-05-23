# /home/tharu/luna/robot-siet-2/app.py
from flask import Flask, Response, request, send_from_directory
import subprocess, threading, re, sys
import RPi.GPIO as GPIO
from pathlib import Path

# --- make /home/tharu modules importable ---
sys.path.insert(0, "/home/tharu")

# robot modules
from audio_player import AudioPlayer
from command_handler import CommandHandler
from display import RoboEyes
from led_emotions import LEDController
from servo_controller import ServoController

# ---------------- Camera Setup ----------------
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
streaming_process = None  # Track the subprocess

def generate_frames():
    global streaming_process
    streaming_process = subprocess.Popen(
        ['libcamera-vid', '--codec', 'mjpeg', '--width', '640', '--height', '480',
         '--nopreview', '-o', '-', '-t', '0'],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    data = b""
    while True:
        if streaming_process.poll() is not None:
            break
        chunk = streaming_process.stdout.read(1024)
        if not chunk:
            continue
        data += chunk
        start = data.find(b'\xff\xd8')  # JPEG start
        end = data.find(b'\xff\xd9')    # JPEG end
        if start != -1 and end != -1 and end > start:
            frame = data[start:end+2]
            data = data[end+2:]
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# ---------------- Motor Setup (L298N direct control for /move) ----------------
# Motor A (left)
in1, in2, enA = 24, 23, 25
# Motor B (right)
in3, in4, enB = 17, 27, 22

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([in1, in2, enA, in3, in4, enB], GPIO.OUT)
pA = GPIO.PWM(enA, 1000); pB = GPIO.PWM(enB, 1000)
pA.start(50); pB.start(50)

def stop():      GPIO.output([in1, in2, in3, in4], GPIO.LOW)
def forward():   GPIO.output([in1, in3], GPIO.HIGH); GPIO.output([in2, in4], GPIO.LOW)
def backward():  GPIO.output([in2, in4], GPIO.HIGH); GPIO.output([in1, in3], GPIO.LOW)
def turn_left(): GPIO.output([in3], GPIO.HIGH);      GPIO.output([in1, in2, in4], GPIO.LOW)
def turn_right():GPIO.output([in1], GPIO.HIGH);      GPIO.output([in2, in3, in4], GPIO.LOW)

# ---------------- Robot objects (shared) ----------------
class _DummyMotors:
    def forward(self): pass
    def backward(self): pass
    def turn_left(self): pass
    def turn_right(self): pass

class _DummyDetector:
    def get_emotion(self): return None

audio  = AudioPlayer()
eyes   = RoboEyes()
leds   = LEDController()
servos = ServoController()

# startup neutral face/LED/servos
eyes.set_neutral(); leds.set_neutral(); servos.set_neutral()
eyes.start()

handler = CommandHandler(audio, eyes, leds, servos, _DummyMotors(), _DummyDetector())

def _bg(target, *args, **kwargs):
    threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

# ---------------- Static files ----------------
@app.route('/')
def index():         return send_from_directory(BASE_DIR, 'index.html')
@app.route('/style.css')
def style_css():     return send_from_directory(BASE_DIR, 'style.css')
@app.route('/script.js')
def script_js():     return send_from_directory(BASE_DIR, 'script.js')
@app.route('/background.jpg')
def bg_img():        return send_from_directory(BASE_DIR, 'background.jpg')

# ---------------- Camera routes ----------------
@app.route('/start', methods=['POST'])
def start_stream():  return ('', 204)

@app.route('/stop', methods=['POST'])
def stop_stream():
    global streaming_process
    if streaming_process:
        streaming_process.terminate()
        streaming_process = None
    return ('', 204)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ---------------- Movement ----------------
@app.route('/move', methods=['POST'])
def move_route():
    direction = request.form.get('direction')
    if   direction == 'forward':  forward()
    elif direction == 'backward': backward()
    elif direction == 'left':     turn_left()
    elif direction == 'right':    turn_right()
    else:                         stop()
    return ('', 204)

# ---------------- Volume ----------------
@app.route('/volume', methods=['POST'])
def volume():
    intensity = request.form.get('intensity', '')
    if intensity == 'increase':
        audio.increase_volume()
    elif intensity == 'decrease':
        audio.decrease_volume()
    return ('', 204)

# ---------------- Stories ----------------
@app.route('/play', methods=['POST'])
def play_story():
    name = request.form.get('story', '')   # e.g. 'story7'
    m = re.search(r'(\d+)', name)
    if m:
        num = int(m.group(1))
        _bg(handler._play_story, num, "specific")
    return ('', 204)

@app.route('/story/stop', methods=['POST'])
def stop_story():
    _bg(handler._handle_stop)
    return ('', 204)

@app.route('/story/next', methods=['POST'])
def next_story():
    _bg(handler._handle_next)
    return ('', 204)

# ---------------- Music ----------------
@app.route('/music', methods=['POST'])
def play_music():
    name = request.form.get('music', '')   # e.g. 'music3'
    m = re.search(r'(\d+)', name)
    if m:
        num = int(m.group(1))
        _bg(handler._play_song, num, "specific")
    return ('', 204)

@app.route('/music/stop', methods=['POST'])
def stop_music():
    _bg(handler._handle_stop)
    return ('', 204)

@app.route('/music/next', methods=['POST'])
def next_music():
    _bg(handler._handle_next)
    return ('', 204)

# ---------------- Education ----------------
@app.route('/education/play', methods=['POST'])
def education_play():
    type_ = request.form.get('type', '')   # alphabet | numbers | animals
    if type_ in ('alphabet', 'numbers', 'animals'):
        _bg(handler._play_educational, type_)
    return ('', 204)

@app.route('/education/stop', methods=['POST'])
def education_stop():
    _bg(handler._handle_stop)
    return ('', 204)

@app.route('/education/next', methods=['POST'])
def education_next():
    _bg(handler._handle_next)
    return ('', 204)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=9000)
    finally:
        try:
            leds.cleanup()
        except: pass
        GPIO.cleanup()
