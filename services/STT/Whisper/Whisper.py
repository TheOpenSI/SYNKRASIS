# =======================================================================================
# Speech to text service using OpenAI Whisper, runs locally on CPU (no GPU needed).
# The model is downloaded from Hugging Face on first use, whisper models are not gated
# so no HUGGING_FACE_TOKEN is required.
# On macOS, the terminal needs Microphone and Input Monitoring/Accessibility
# permissions (System Settings > Privacy & Security) for recording and key detection.
# Usage:
#     - listen() -> Optional[str] : hold the push-to-talk key (default space) and speak,
#                                   release to stop, returns the transcribed text
#     - cleanup():
# =======================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import numpy as np
import sounddevice as sd
from pynput import keyboard
from transformers import pipeline
from typing import Optional

from services.Base import ServiceBase
from utils.output_message_format.output_colour import print_info, print_error, print_success


class Whisper(ServiceBase):
    def __init__(self,
                 model_name: str = "openai/whisper-base",
                 sample_rate: int = 16000,
                 push_to_talk_key: str = "space"):
        """
        Creates a Whisper speech to text service
        Args:
            model_name (str): The HF repository of the whisper model. Defaults to whisper-base
                which is small enough to run on CPU. Other options: openai/whisper-tiny,
                openai/whisper-small.
            sample_rate (int): Recording sample rate, whisper expects 16000. Defaults to 16000.
            push_to_talk_key (str): The key to hold while talking, must be a special key name
                from pynput (e.g. "space", "shift_r", "ctrl_r"). Defaults to "space".
        """
        super().__init__()
        self.model_name = model_name
        self.sample_rate = sample_rate
        self.push_to_talk_key_name = push_to_talk_key
        self.push_to_talk_key = getattr(keyboard.Key, push_to_talk_key)
        self.transcriber = pipeline("automatic-speech-recognition", model=self.model_name)
        print_success(f"Whisper model {self.model_name} loaded.")


    def _record_push_to_talk(self) -> Optional[np.ndarray]:
        """
        Record audio from the microphone while the push-to-talk key is held down.
        Returns:
            Optional[np.ndarray]: The recorded audio as a float32 array, None if nothing recorded.
        """
        frames = []
        is_recording = {"active": False}  # dict so the callbacks can modify it

        def audio_callback(indata, frame_count, time_info, status):
            if is_recording["active"]:
                frames.append(indata.copy())

        def on_press(key):
            if key == self.push_to_talk_key and not is_recording["active"]:
                is_recording["active"] = True
                print_info("Recording... release the key to stop.")

        def on_release(key):
            if key == self.push_to_talk_key and is_recording["active"]:
                return False  # stops the keyboard listener

        print_info(f"Hold [{self.push_to_talk_key_name}] and speak...")
        with sd.InputStream(samplerate=self.sample_rate,
                            channels=1,
                            dtype="float32",
                            callback=audio_callback):
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()

        if not frames:
            return None
        return np.concatenate(frames).flatten()


    def listen(self) -> Optional[str]:
        """
        Record with push-to-talk and transcribe the audio using whisper.
        Returns:
            Optional[str]: The transcribed text, None if nothing was recorded.
        """
        audio = self._record_push_to_talk()
        if audio is None or len(audio) == 0:
            print_error("No audio recorded.")
            return None

        result = self.transcriber({"array": audio, "sampling_rate": self.sample_rate})
        text = result["text"].strip()
        if not text:
            print_error("Could not transcribe any speech.")
            return None

        return text


    def cleanup(self):
        """
        Release the whisper model
        """
        if self.transcriber is not None:
            del self.transcriber
            self.transcriber = None
        print_success("Whisper resources cleaned up.")
