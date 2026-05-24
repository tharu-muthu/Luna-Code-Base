import os
import requests
import base64
import subprocess
import time
from PIL import Image
from config import Config


class EmotionDetector:
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.GOOGLE_API_KEY
        self.api_url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"

        self.image_path = "captured.jpg"
        self.compressed_path = "compressed.jpg"

        self.likelihood_score = {
            "UNKNOWN": 0,
            "VERY_UNLIKELY": 0,
            "UNLIKELY": 1,
            "POSSIBLE": 2,
            "LIKELY": 3,
            "VERY_LIKELY": 4
        }

        self.conflicts = [("Joy", "Sorrow"), ("Anger", "Surprise")]

    def get_emotion(self):
        self._capture_image()
        self._compress_image()

        with open(self.compressed_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": encoded},
                "features": [{"type": "FACE_DETECTION"}]
            }]
        }

        try:
            response = requests.post(self.api_url, json=payload)
            data = response.json()
            faces = data["responses"][0].get("faceAnnotations")

            if not faces:
                return "NoFace"

            emotions = {
                "Joy": faces[0].get("joyLikelihood", "UNKNOWN"),
                "Sorrow": faces[0].get("sorrowLikelihood", "UNKNOWN"),
                "Anger": faces[0].get("angerLikelihood", "UNKNOWN"),
                "Surprise": faces[0].get("surpriseLikelihood", "UNKNOWN")
            }

            scored = {
                k: self.likelihood_score[v]
                for k, v in emotions.items()
                if self.likelihood_score[v] >= 2  # Only POSSIBLE or higher
            }

            # Handle conflicts
            for e1, e2 in self.conflicts:
                if e1 in scored and e2 in scored:
                    if scored[e1] > scored[e2]:
                        del scored[e2]
                    else:
                        del scored[e1]

            return max(scored, key=scored.get) if scored else "Neutral"

        except Exception as e:
            print(f"[EmotionDetector] Error: {e}")
            return "NoFace"

    def _capture_image(self):
        subprocess.run([
            "libcamera-jpeg", "-o", self.image_path,
            "-t", "1000", "--width", "640", "--height", "480", "--quality", "95"
        ], check=True)
        time.sleep(1)

    def _compress_image(self):
        img = Image.open(self.image_path)
        img = img.resize((640, 480))
        img.save(self.compressed_path, format="JPEG", optimize=True, quality=70)
