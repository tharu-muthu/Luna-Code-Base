import queue
import time
import collections
import numpy as np
import sounddevice as sd
from pvporcupine import create as create_porcupine
from pvrhino import Rhino

from config import Config


class VoiceController:
    def __init__(self, command_handler, audio_player):
        self.command_handler = command_handler
        self.audio = audio_player

        self.input_sample_rate = 44100
        self.target_sample_rate = 16000

        # FIX: Use deque instead of np.concatenate to avoid O(n²) copying
        self._raw_buffer = collections.deque()
        self._raw_buffer_len = 0

        self.command_mode = False
        self.last_wake_time = 0

        self.audio_queue = queue.Queue()

        # Activation state
        self.first_activation = True
        self.is_sleeping = False

        # Pre-compute resampling indices once (never change)
        self._input_samples_needed = int(512 * (self.input_sample_rate / self.target_sample_rate))
        self._resample_indices = np.linspace(0, self._input_samples_needed, 512).astype(np.float64)
        self._source_indices = np.arange(self._input_samples_needed, dtype=np.float64)

        # Initialize Porcupine (wake word)
        self.porcupine = create_porcupine(
            access_key=Config.PICOVOICE_ACCESS_KEY,
            keyword_paths=[Config.WAKE_WORD_PATH]
        )

        # Initialize Rhino (command recognizer)
        self.rhino = Rhino(
            access_key=Config.PICOVOICE_ACCESS_KEY,
            context_path=Config.RHINO_CONTEXT_PATH,
            model_path=Config.RHINO_MODEL_PATH,
            library_path=Config.RHINO_LIB_PATH
        )

    def _get_input_device_index(self):
        for i, dev in enumerate(sd.query_devices()):
            if "USB" in dev['name'] and dev['max_input_channels'] > 0:
                print(f"[Voice] Using USB mic: {dev['name']}")
                return i
        raise RuntimeError("No USB microphone found")

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Voice] Audio status: {status}")

        # Append samples to deque (O(1) per call, avoids np.concatenate copying)
        samples = indata[:, 0].copy()
        self._raw_buffer.append(samples)
        self._raw_buffer_len += len(samples)

        while self._raw_buffer_len >= self._input_samples_needed:
            # Collect enough samples from the deque
            collected = []
            remaining = self._input_samples_needed
            while remaining > 0:
                front = self._raw_buffer[0]
                if len(front) <= remaining:
                    collected.append(self._raw_buffer.popleft())
                    remaining -= len(front)
                else:
                    # Split: take what we need, leave the rest
                    collected.append(front[:remaining])
                    self._raw_buffer[0] = front[remaining:]
                    remaining = 0

            chunk = np.concatenate(collected)
            self._raw_buffer_len -= self._input_samples_needed

            # Resample using pre-computed indices
            resampled = np.interp(
                self._resample_indices,
                self._source_indices,
                chunk
            ).astype(np.int16)

            self.audio_queue.put(resampled)

    def listen_forever(self):
        print("[VoiceController] Say 'Hey Luna' to wake...")

        with sd.InputStream(
            callback=self.audio_callback,
            channels=1,
            samplerate=self.input_sample_rate,
            blocksize=512,
            dtype='int16',
            device=self._get_input_device_index()
        ):
            while True:
                self.audio.check_finished()

                # Command mode timeout
                if self.command_mode and (time.time() - self.last_wake_time > Config.COMMAND_LISTEN_DURATION):
                    print("[INFO] Command listening period ended.")
                    self.command_mode = False

                data = self.audio_queue.get()
                pcm = np.frombuffer(data, dtype=np.int16)

                # Wake word detection
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    print("🎤 Wake word detected: 'Hey Luna'")
                    self.command_mode = True
                    self.last_wake_time = time.time()

                    if self.is_sleeping:
                        self.audio.play_feedback("activated_now_listening_to_you", wait=True)
                        self.is_sleeping = False
                        self.first_activation = False
                        
                    # commented out cz this plays activated now listnening to u twice

                    # elif self.first_activation:
                    #     self.audio.play_feedback("activated_now_listening_to_you", wait=True)
                    #     self.first_activation = False

                    continue

                # Command detection
                if self.command_mode:
                    finalized = self.rhino.process(pcm)
                    if finalized:
                        inference = self.rhino.get_inference()
                        if inference.is_understood:
                            print(f"[Command] Intent: {inference.intent}, Slots: {inference.slots}")
                            self.command_handler.handle(inference.intent, inference.slots)
                            self.command_mode = False

    def cleanup(self):
        self.porcupine.delete()
        self.rhino.delete()
