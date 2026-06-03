# /home/tharu/luna/web_api.py
from flask import Flask, Response, request, send_from_directory
from pathlib import Path
import subprocess, threading, re

# Where your site files live
SITE_DIR = Path("/home/tharu/luna/robot-site-2")

def create_app(handler, audio, eyes, leds, servos, motors):
    app = Flask(__name__)
    streaming_process = {"p": None}  # use dict to mutate in closures

    # ---------- Helpers ----------
    def check_and_stop_stream():
        p = streaming_process.get("p", None)
        if p:
            try:
                p.terminate()
                p.wait(timeout=1.0)
            except:
                pass
            streaming_process["p"] = None
            return True
        return False

    handler.check_and_stop_stream = check_and_stop_stream

    def bg(target, *args, **kwargs):
        threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    def generate_frames():
        # MJPEG stream from libcamera-vid
        streaming_process["p"] = subprocess.Popen(
            ['libcamera-vid', '--codec', 'mjpeg', '--width', '640', '--height', '480',
             '--nopreview', '-o', '-', '-t', '0'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        buf = b""
        try:
            while True:
                if streaming_process["p"].poll() is not None:
                    break
                chunk = streaming_process["p"].stdout.read(1024)
                if not chunk:
                    continue
                buf += chunk
                s = buf.find(b'\xff\xd8'); e = buf.find(b'\xff\xd9')
                if s != -1 and e != -1 and e > s:
                    frame = buf[s:e+2]; buf = buf[e+2:]
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        finally:
            # Always terminate camera process when client disconnects
            p = streaming_process.get("p")
            if p:
                try:
                    p.terminate()
                    p.wait(timeout=2.0)
                except:
                    pass
                streaming_process["p"] = None

    # ---------- Static files ----------
    @app.route('/')
    def index():          return send_from_directory(SITE_DIR, 'index.html')
    @app.route('/style.css')
    def style_css():      return send_from_directory(SITE_DIR, 'style.css')
    @app.route('/script.js')
    def script_js():      return send_from_directory(SITE_DIR, 'script.js')
    @app.route('/background.jpg')
    def background_img(): return send_from_directory(SITE_DIR, 'background.jpg')

    # ---------- Camera ----------
    @app.route('/start', methods=['POST'])
    def start_stream():   return ('', 204)  # page will start pulling /video_feed

    @app.route('/stop', methods=['POST'])
    def stop_stream():
        p = streaming_process["p"]
        if p: p.terminate(); streaming_process["p"] = None
        return ('', 204)

    @app.route('/video_feed')
    def video_feed():
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    # ---------- Movement ----------
    @app.route('/move', methods=['POST'])
    def move():
        direction = request.form.get('direction', '')
        if   direction == 'forward':  motors.forward()
        elif direction == 'backward': motors.backward()
        elif direction == 'left':     motors.turn_left()
        elif direction == 'right':    motors.turn_right()
        else:                         motors.stop()
        return ('', 204)

    # ---------- Volume ----------
    @app.route('/volume', methods=['GET', 'POST'])
    def volume():
        if request.method == 'POST':
            intensity = request.form.get('intensity', '')
            if intensity == 'increase': audio.increase_volume()
            elif intensity == 'decrease': audio.decrease_volume()
        return {"volume": round(audio.get_volume() * 100)}

    # ---------- Pause / Resume ----------
    @app.route('/pause', methods=['POST'])
    def pause_playback():
        handler._handle_pause()
        return {"status": "paused"}

    @app.route('/resume', methods=['POST'])
    def resume_playback():
        handler._handle_resume()
        return {"status": "playing"}

    # ---------- Status Sync ----------
    @app.route('/status', methods=['GET'])
    def get_status():
        category = audio.current_category
        track_name = "Nothing playing"
        
        if audio.is_playing or audio.is_paused:
            if category == "story":
                track_name = f"Story {audio.last_index}" if audio.last_index else "Story"
            elif category == "song":
                track_name = f"Music {audio.last_index}" if audio.last_index else "Music"
            elif category == "education":
                if audio.current_file:
                    filename = Path(audio.current_file).name # e.g. 'alphabet.mp3'
                    edu_name = filename.split('.')[0] # 'alphabet'
                    track_name = edu_name.capitalize() # 'Alphabet'
                else:
                    track_name = "Education"
        else:
            track_name = "Stopped"

        return {
            "playing": audio.is_playing,
            "paused": audio.is_paused,
            "category": category,
            "track": track_name,
            "volume": round(audio.get_volume() * 100)
        }

    # ---------- Stories ----------
    @app.route('/play', methods=['POST'])
    def play_story():
        name = request.form.get('story', '')  # e.g. 'story7'
        m = re.search(r'(\d+)', name)
        if m: bg(handler._play_story, int(m.group(1)), "specific")
        return ('', 204)

    @app.route('/story/stop', methods=['POST'])
    def stop_story():
        bg(handler._handle_stop)
        return ('', 204)

    @app.route('/story/next', methods=['POST'])
    def next_story():
        bg(handler._handle_next)
        return ('', 204)

    @app.route('/story/prev', methods=['POST'])
    def prev_story():
        bg(handler._handle_prev)
        return ('', 204)

    # ---------- Music ----------
    @app.route('/music', methods=['POST'])
    def play_music():
        name = request.form.get('music', '')  # e.g. 'music3'
        m = re.search(r'(\d+)', name)
        if m: bg(handler._play_song, int(m.group(1)), "specific")
        return ('', 204)

    @app.route('/music/stop', methods=['POST'])
    def stop_music():
        bg(handler._handle_stop)
        return ('', 204)

    @app.route('/music/next', methods=['POST'])
    def next_music():
        bg(handler._handle_next)
        return ('', 204)

    @app.route('/music/prev', methods=['POST'])
    def prev_music():
        bg(handler._handle_prev)
        return ('', 204)

    # ---------- Education ----------
    @app.route('/education/play', methods=['POST'])
    def edu_play():
        t = request.form.get('type', '')  # 'alphabet' | 'numbers' | 'animals'
        if t in ('alphabet','numbers','animals'):
            bg(handler._play_educational, t)
        return ('', 204)

    @app.route('/education/stop', methods=['POST'])
    def edu_stop():
        bg(handler._handle_stop)
        return ('', 204)

    @app.route('/education/next', methods=['POST'])
    def edu_next():
        bg(handler._handle_next)
        return ('', 204)

    @app.route('/education/prev', methods=['POST'])
    def edu_prev():
        bg(handler._handle_prev)
        return ('', 204)

    return app