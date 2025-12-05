#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import sys
import time
import queue
import wave
import threading
import tempfile
import logging
import platform
from dataclasses import dataclass, field
from typing import List, Optional

import speech_recognition as sr
import pyttsx3

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# Config
@dataclass
class Config:
    language_code: str = "ko-KR"
    llm_model: str = "gpt-4o-mini"
    whisper_model: str = "whisper-1"
    tts_voice: Optional[str] = None
    tts_rate: int = 200
    tts_volume: float = 1.0

    use_openai_stt: bool = False
    use_openai_tts: bool = False

    calibrate_seconds: float = 0.6
    pause_threshold: float = 0.6
    phrase_time_limit: Optional[float] = None

    max_history: int = 8
    log_level: str = "INFO"


# Logger
def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# TTS (pyttsx3 기본)
class TTSBase:
    def say(self, text: str):
        raise NotImplementedError

    def close(self):
        pass


class Pyttsx3TTS(TTSBase):
    def __init__(self, voice_id: Optional[str], rate: int, volume: float):
        self.engine = pyttsx3.init()
        if voice_id:
            self.engine.setProperty("voice", voice_id)
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

        self.queue = queue.Queue()
        self._stop = threading.Event()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                text = self.queue.get(timeout=0.1)
            except queue.Empty:
                try:
                    self.engine.iterate()
                except Exception:
                    pass
                continue

            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"TTS 실패: {e}")

    def say(self, text: str):
        self.queue.put(text)

    def close(self):
        self._stop.set()
        try:
            self.engine.stop()
        except Exception:
            pass


class OpenAITTS(TTSBase):
    def __init__(self, client, voice: str = "alloy", audio_format: str = "mp3"):
        self.client = client
        self.voice = voice
        self.audio_format = audio_format
        self.tempdir = tempfile.mkdtemp(prefix="voice_chatbot_tts_")

    def say(self, text: str):
        try:
            model_name = "gpt-4o-mini-tts"
            out_path = os.path.join(self.tempdir, f"tts_{int(time.time())}.{self.audio_format}")

            try:
                with self.client.audio.speech.with_streaming_response.create(
                    model=model_name,
                    voice=self.voice,
                    input=text,
                    format=self.audio_format,
                ) as resp:
                    resp.stream_to_file(out_path)
            except Exception:
                audio_resp = self.client.audio.speech.create(
                    model=model_name, voice=self.voice, input=text, format=self.audio_format
                )
                content = getattr(audio_resp, "content", None) or getattr(audio_resp, "audio", None)
                if isinstance(content, (bytes, bytearray)):
                    with open(out_path, "wb") as f:
                        f.write(content)

            if platform.system() == "Windows":
                os.startfile(out_path)
            elif platform.system() == "Darwin":
                os.system(f'open "{out_path}"')
            else:
                os.system(f'xdg-open "{out_path}"')

        except Exception as e:
            logging.error(f"OpenAI TTS 오류: {e}")


# STT
class STTBase:
    def recognize(self, audio: sr.AudioData) -> str:
        raise NotImplementedError


class GoogleSTT(STTBase):
    def __init__(self, language_code: str = "ko-KR"):
        self.language_code = language_code

    def recognize(self, audio: sr.AudioData) -> str:
        rec = sr.Recognizer()
        try:
            return rec.recognize_google(audio, language=self.language_code)
        except Exception:
            return ""


class OpenAIWhisperSTT(STTBase):
    def __init__(self, client, model: str = "whisper-1"):
        self.client = client
        self.model = model

    def recognize(self, audio: sr.AudioData) -> str:
        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                resp = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f
                )
            return getattr(resp, "text", "") or getattr(resp, "output_text", "")
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# LLM
class OpenAILLM:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
        self.messages = [
            {"role": "system", "content": "You are a helpful, concise voice assistant."}
        ]

    def ask(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        if len(self.messages) > 1 + 2 * 8:
            self.messages = [self.messages[0]] + self.messages[-16:]

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.5,
            )
            content = resp.choices[0].message.content
            self.messages.append({"role": "assistant", "content": content})
            return content
        except Exception:
            return "일시적으로 응답할 수 없습니다."


# Voice Assistant
class VoiceAssistant:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        setup_logging(cfg.log_level)

        api_key = os.getenv("OPENAI_API_KEY")
        if OpenAI is None:
            raise RuntimeError("openai SDK 임포트 실패.")
        self.client = OpenAI(api_key=api_key) if api_key else None

        if not self.client:
            raise RuntimeError("API KEY 필요.")

        self.llm = OpenAILLM(self.client, self.cfg.llm_model)

        if self.cfg.use_openai_stt:
            self.stt = OpenAIWhisperSTT(self.client, self.cfg.whisper_model)
        else:
            self.stt = GoogleSTT(self.cfg.language_code)

        if self.cfg.use_openai_tts:
            self.tts = OpenAITTS(self.client)
        else:
            self.tts = Pyttsx3TTS(self.cfg.tts_voice, self.cfg.tts_rate, self.cfg.tts_volume)

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.recognizer.pause_threshold = self.cfg.pause_threshold

        self.text_in_q = queue.Queue()
        self._stop = threading.Event()

        self.nlp_thread = threading.Thread(target=self._nlp_worker, daemon=True)
        self.nlp_thread.start()

    def _nlp_worker(self):
        while not self._stop.is_set():
            try:
                text = self.text_in_q.get(timeout=0.1)
            except queue.Empty:
                continue
            if not text:
                continue

            if text.strip().lower() in {"quit", "exit"} or any(k in text for k in ["종료", "그만", "끝내"]):
                self.tts.say("종료합니다.")
                self.stop()
                return

            reply = self.llm.ask(text)
            self.tts.say(reply)

    def start(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=self.cfg.calibrate_seconds)

        self.stop_listening = self.recognizer.listen_in_background(
            self.microphone, self._callback, phrase_time_limit=self.cfg.phrase_time_limit
        )

        try:
            while not self._stop.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def _callback(self, recognizer, audio):
        try:
            text = self.stt.recognize(audio).strip()
        except Exception:
            text = ""

        if text:
            self.text_in_q.put(text)

    def stop(self):
        if self._stop.is_set():
            return
        self._stop.set()

        try:
            self.stop_listening(wait_for_stop=False)
        except Exception:
            pass

        try:
            self.tts.close()
        except Exception:
            pass

        logging.info("종료됨.")


def main():
    cfg = Config()
    try:
        assistant = VoiceAssistant(cfg)
        assistant.start()
    except Exception as e:
        logging.error(f"실행 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
