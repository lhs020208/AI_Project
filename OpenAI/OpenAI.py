
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
voice_chatbot.py
----------------
"OpenAI API와 Python을 활용한 실시간 음성 비서 챗봇" 예시 구현.

요구사항
- STT: SpeechRecognition(기본, Google Speech Recognition) → 실패/옵션시 OpenAI Whisper API로 대체
- LLM: OpenAI GPT 계열 (기본: gpt-4o-mini)
- TTS: pyttsx3(오프라인, 기본) → 옵션으로 OpenAI TTS API 사용 가능
- 실시간 파이프라인: 마이크 입력 → 텍스트 → LLM → 음성 출력
- PyAudio, SpeechRecognition, gTTS/pyttsx3, openai 등 통합

설치(이미 완료했다고 하셨음):
    pip install openai SpeechRecognition gTTS pyttsx3 pyaudio

환경변수:
    set OPENAI_API_KEY=sk-...   (Windows CMD)
    export OPENAI_API_KEY=sk-... (macOS/Linux)

실행:
    python voice_chatbot.py

종료:
    Ctrl+C 또는 음성으로 "종료", "quit", "exit" 라고 말하기.
"""

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

# --- 외부 라이브러리 ---
import speech_recognition as sr
import pyttsx3

# OpenAI 최신 Python SDK (2024~) 방식
# https://platform.openai.com/docs (모델명/엔드포인트는 시기에 따라 달라질 수 있음)
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # 런타임에서 친절히 에러 메시지 출력

# =====================
# 설정
# =====================
@dataclass
class Config:
    # 언어 설정 (Google STT 언어코드)
    language_code: str = "ko-KR"  # 필요시 "en-US"
    # 모델 설정
    llm_model: str = "gpt-4o-mini"  # 텍스트 응답 생성용
    whisper_model: str = "whisper-1"  # OpenAI STT (옵션)
    tts_voice: Optional[str] = None  # pyttsx3 음성 id (None이면 기본)
    tts_rate: int = 200  # pyttsx3 말하기 속도 (wpm)
    tts_volume: float = 1.0  # 0.0 ~ 1.0
    # 엔진 선택
    use_openai_stt: bool = False   # True면 OpenAI Whisper API 사용 (기본 False: Google SR)
    use_openai_tts: bool = False   # True면 OpenAI TTS 사용 (기본 False: pyttsx3)
    # 음성 인식 민감도/반응성
    calibrate_seconds: float = 0.6  # 주변 잡음 보정 시간
    pause_threshold: float = 0.6    # 말 멈춤 감지 (짧을수록 빠른 끊김)
    phrase_time_limit: Optional[float] = None  # None: 자동, 값 설정 시 최대 발화 길이(초)
    # 파이프라인
    max_history: int = 8  # LLM 대화 히스토리 유지 턴 수
    # 로그
    log_level: str = "INFO"


# =====================
# 유틸: 로거
# =====================
def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# =====================
# 음성 합성 (TTS)
# =====================
class TTSBase:
    def say(self, text: str):
        raise NotImplementedError

    def close(self):
        pass


class Pyttsx3TTS(TTSBase):
    def __init__(self, voice_id: Optional[str], rate: int, volume: float):
        self.engine = pyttsx3.init()
        try:
            if voice_id:
                self.engine.setProperty("voice", voice_id)
            self.engine.setProperty("rate", rate)
            self.engine.setProperty("volume", volume)
        except Exception as e:
            logging.warning(f"pyttsx3 초기화 중 경고: {e}")

        # 별도 스레드에서 runAndWait 이벤트 루프 구동
        self.queue = queue.Queue()
        self._stop = threading.Event()
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                text = self.queue.get(timeout=0.1)
            except queue.Empty:
                # 엔진 이벤트를 지속 처리
                try:
                    self.engine.iterate()
                except Exception:
                    pass
                continue

            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"TTS 재생 실패: {e}")

    def say(self, text: str):
        self.queue.put(text)

    def close(self):
        self._stop.set()
        try:
            self.engine.stop()
        except Exception:
            pass


class OpenAITTS(TTSBase):
    """
    OpenAI TTS 사용 (옵션). 생성된 오디오를 파일로 저장 후 재생.
    pyttsx3가 기본이라 이 클래스는 선택적으로만 사용.
    """
    def __init__(self, client, voice: str = "alloy", audio_format: str = "mp3"):
        self.client = client
        self.voice = voice
        self.audio_format = audio_format
        # PyAudio로 직접 mp3 재생은 어려우므로, OS 기본 플레이어 호출 or 단순 파일 저장 안내
        self.tempdir = tempfile.mkdtemp(prefix="voice_chatbot_tts_")

    def say(self, text: str):
        try:
            # 최신 SDK 기준 예시: client.audio.speech.create(...)
            # 주의: 모델/파라미터는 시기에 따라 변경될 수 있음.
            # 모델 예: "gpt-4o-mini-tts"
            model_name = "gpt-4o-mini-tts"
            out_path = os.path.join(self.tempdir, f"tts_{int(time.time())}.{self.audio_format}")

            # 스트리밍 저장 (가능한 경우)
            try:
                with self.client.audio.speech.with_streaming_response.create(
                    model=model_name,
                    voice=self.voice,
                    input=text,
                    format=self.audio_format,
                ) as resp:
                    resp.stream_to_file(out_path)
            except Exception:
                # 비스트리밍 방식
                audio_resp = self.client.audio.speech.create(
                    model=model_name, voice=self.voice, input=text, format=self.audio_format
                )
                # bytes로 올 수 있음
                content = getattr(audio_resp, "content", None)
                if content is None and hasattr(audio_resp, "audio"):
                    content = audio_resp.audio
                if isinstance(content, (bytes, bytearray)):
                    with open(out_path, "wb") as f:
                        f.write(content)
                else:
                    # 안전장치: 객체가 파일-like인 경우
                    with open(out_path, "wb") as f:
                        f.write(audio_resp.read())

            logging.info(f"[OpenAI TTS] 생성됨: {out_path}")
            # OS 기본 플레이어로 열기 (차단적일 수 있음)
            try:
                if platform.system() == "Windows":
                    os.startfile(out_path)  # type: ignore[attr-defined]
                elif platform.system() == "Darwin":
                    os.system(f'open "{out_path}"')
                else:
                    os.system(f'xdg-open "{out_path}"')
            except Exception as e:
                logging.warning(f"자동 재생 실패 (파일만 저장): {e}")
        except Exception as e:
            logging.error(f"OpenAI TTS 오류: {e}")


# =====================
# 음성 인식 (STT)
# =====================
class STTBase:
    def recognize(self, audio: sr.AudioData) -> str:
        raise NotImplementedError


class GoogleSTT(STTBase):
    def __init__(self, language_code: str = "ko-KR"):
        self.language_code = language_code

    def recognize(self, audio: sr.AudioData) -> str:
        # SpeechRecognition의 Google Web Speech API
        rec = sr.Recognizer()
        try:
            text = rec.recognize_google(audio, language=self.language_code)
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logging.error(f"Google STT RequestError: {e}")
            raise


class OpenAIWhisperSTT(STTBase):
    def __init__(self, client, model: str = "whisper-1"):
        self.client = client
        self.model = model

    def recognize(self, audio: sr.AudioData) -> str:
        # AudioData → WAV 바이트로 추출 → Whisper 업로드
        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp.flush()
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                resp = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f
                )
            # 최신 SDK에서는 resp.text 또는 resp.output_text 등 형태가 가능
            # 안전하게 둘 다 시도
            text = getattr(resp, "text", None) or getattr(resp, "output_text", "") or ""
            return text
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# =====================
# LLM (OpenAI GPT)
# =====================
class OpenAILLM:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
        self.messages: List[dict] = [
            {"role": "system", "content": "You are a helpful, concise voice assistant. Reply briefly."}
        ]

    def ask(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        # 히스토리 길이 제한
        if len(self.messages) > 1 + 2 * 8:
            # system 1개 + (user, assistant) x 8 정도
            self.messages = [self.messages[0]] + self.messages[-16:]

        try:
            # 보수적으로 여전히 널리 쓰이는 chat.completions API 사용
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=0.5,
            )
            content = resp.choices[0].message.content
            # 히스토리에 assistant 응답 추가
            self.messages.append({"role": "assistant", "content": content})
            return content
        except Exception as e:
            logging.error(f"OpenAI LLM 오류: {e}")
            return "죄송해요. 잠시 응답을 생성할 수 없었습니다."


# =====================
# 음성 비서 본체
# =====================
class VoiceAssistant:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        setup_logging(cfg.log_level)

        # OpenAI 클라이언트
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.warning("환경변수 OPENAI_API_KEY가 설정되지 않았습니다. (LLM/TTS/Whisper 사용 시 필요)")
        if OpenAI is None:
            raise RuntimeError("openai Python SDK 임포트 실패. 'pip install openai' 후 다시 실행하세요.")
        self.client = OpenAI(api_key=api_key) if api_key else None

        # LLM
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY가 없어 LLM을 사용할 수 없습니다.")
        self.llm = OpenAILLM(self.client, self.cfg.llm_model)

        # STT
        if self.cfg.use_openai_stt:
            if not self.client:
                raise RuntimeError("OPENAI Whisper 사용을 위해 OPENAI_API_KEY가 필요합니다.")
            self.stt: STTBase = OpenAIWhisperSTT(self.client, self.cfg.whisper_model)
            logging.info("STT: OpenAI Whisper 사용")
        else:
            self.stt = GoogleSTT(self.cfg.language_code)
            logging.info("STT: Google Speech Recognition 사용")

        # TTS
        if self.cfg.use_openai_tts:
            if not self.client:
                raise RuntimeError("OPENAI TTS 사용을 위해 OPENAI_API_KEY가 필요합니다.")
            self.tts: TTSBase = OpenAITTS(self.client, voice="alloy", audio_format="mp3")
            logging.info("TTS: OpenAI TTS 사용 (파일 저장 후 OS 플레이어로 재생)")
        else:
            self.tts = Pyttsx3TTS(self.cfg.tts_voice, self.cfg.tts_rate, self.cfg.tts_volume)
            logging.info("TTS: pyttsx3(오프라인) 사용")

        # SR 구성요소
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()  # 디폴트 마이크
        self.recognizer.pause_threshold = self.cfg.pause_threshold

        # 파이프라인 큐
        self.text_in_q: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()

        # 워커 스레드
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

            logging.info(f"[USER] {text}")
            if text.strip().lower() in {"quit", "exit"} or any(k in text for k in ["종료", "그만", "끝내"]):
                self.tts.say("종료할게요.")
                self.stop()
                return

            # LLM 호출
            reply = self.llm.ask(text)
            logging.info(f"[ASSISTANT] {reply}")
            # 음성 출력
            self.tts.say(reply)

    def start(self):
        logging.info("마이크 초기화 중... 주변 잡음을 측정합니다.")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=self.cfg.calibrate_seconds)

        logging.info("듣는 중입니다. 말씀하세요. (Ctrl+C로 종료)")
        # 백그라운드 콜백 사용 → 실시간/논블로킹
        self.stop_listening = self.recognizer.listen_in_background(
            self.microphone, self._callback, phrase_time_limit=self.cfg.phrase_time_limit
        )

        try:
            while not self._stop.is_set():
                time.sleep(0.1)
        except KeyboardInterrupt:
            logging.info("사용자 인터럽트로 종료합니다.")
            self.stop()

    def _callback(self, recognizer: sr.Recognizer, audio: sr.AudioData):
        # 콜백: 오디오 조각을 받으면 STT → 텍스트 큐
        try:
            text = self.stt.recognize(audio).strip()
        except Exception as e:
            logging.error(f"STT 실패: {e}")
            # Whisper로 폴백 시도 (Google 실패 케이스 대비)
            if not self.cfg.use_openai_stt and self.client is not None:
                try:
                    logging.info("STT 폴백: OpenAI Whisper 시도")
                    text = OpenAIWhisperSTT(self.client, self.cfg.whisper_model).recognize(audio).strip()
                except Exception as e2:
                    logging.error(f"STT 폴백 실패: {e2}")
                    text = ""
            else:
                text = ""

        if text:
            self.text_in_q.put(text)
        else:
            logging.debug("인식된 텍스트 없음(무시).")

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
        logging.info("종료되었습니다.")


def main():
    cfg = Config(
        language_code="ko-KR",
        llm_model="gpt-4o-mini",
        whisper_model="whisper-1",
        tts_voice=None,        # 필요 시 pyttsx3의 voice id 지정
        tts_rate=200,
        tts_volume=1.0,
        use_openai_stt=False,  # True면 Whisper 사용
        use_openai_tts=False,  # True면 OpenAI TTS 사용(파일 재생)
        calibrate_seconds=0.6,
        pause_threshold=0.6,
        phrase_time_limit=None,
        max_history=8,
        log_level="INFO",
    )

    try:
        assistant = VoiceAssistant(cfg)
        assistant.start()
    except Exception as e:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
        logging.error(f"실행 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
