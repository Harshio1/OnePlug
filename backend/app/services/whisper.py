import os
import sys
import time
import logging
from typing import Dict, Any, List

import static_ffmpeg

# ── Suppress tqdm progress bar to avoid Windows stderr crash ──────────
os.environ["TQDM_DISABLE"] = "1"

logger = logging.getLogger(__name__)


class WhisperService:
    """
    Local transcription service using faster-whisper with large-v3 model.

    Why faster-whisper + large-v3:
    - large-v3 is OpenAI's best Whisper model — dramatically better accuracy
      for Tamil proper nouns, numbers, and technical terms vs small model.
    - faster-whisper runs large-v3 with INT8 quantization: ~3 GB RAM
      vs ~10 GB for the standard large-v3 in openai-whisper.
    - 4x faster inference than openai-whisper on CPU.
    - Supports task="translate" (Tamil -> English directly).

    Fallback chain: large-v3 → medium → small (all via faster-whisper INT8)
    """

    def __init__(self):
        # ── ffmpeg ────────────────────────────────────────────────────────
        try:
            static_ffmpeg.add_paths()
            logger.info("WhisperService: ffmpeg ready.")
        except Exception as fe:
            logger.warning(f"WhisperService: static-ffmpeg warning: {fe}")

        self.model = None
        self.loaded_model_name = None
        self.is_demo_mode = False
        self.tried_loading = False

    def _load_model_if_needed(self):
        if self.tried_loading:
            return
        self.tried_loading = True
        try:
            from faster_whisper import WhisperModel

            # Try models from best to smallest until one loads
            for model_name, compute in [
                ("large-v3", "int8"),
                ("medium",   "int8"),
                ("small",    "int8"),
            ]:
                try:
                    logger.info(f"WhisperService: Loading faster-whisper '{model_name}' (compute={compute})...")
                    self.model = WhisperModel(
                        model_name,
                        device="cpu",
                        compute_type=compute,
                        # Download to a local cache inside the project
                        download_root=os.path.join(
                            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "model_cache"
                        ),
                    )
                    self.loaded_model_name = model_name
                    self.is_demo_mode = False
                    logger.info(f"WhisperService: '{model_name}' loaded successfully.")
                    break
                except Exception as exc:
                    logger.error(f"WhisperService: '{model_name}' load failed: {exc}")

        except ImportError:
            logger.error("WhisperService: faster-whisper not installed. Run: pip install faster-whisper")
            self.is_demo_mode = True

        if self.model is None:
            self.is_demo_mode = True
            logger.error("WhisperService: No model loaded — running in demo/mock mode.")

    # ─────────────────────────────────────────────────────────────────────
    def transcribe_audio(
        self,
        file_path: str,
        language_hint: str = None,
        prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Transcribe audio and translate to English using faster-whisper.
        Returns the full pipeline response schema.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        self._load_model_if_needed()

        if self.is_demo_mode or self.model is None:
            logger.warning("WhisperService: model unavailable — mock fallback active.")
            return self._generate_mock_transcript(file_path, language_hint or "en")

        try:
            return self._run_transcription(file_path, language_hint, prompt)
        except Exception as exc:
            import traceback
            with open("whisper_error.log", "a") as f:
                f.write(f"Transcription error on {file_path}: {exc}\n")
                traceback.print_exc(file=f)
            logger.error(f"WhisperService: Transcription error: {exc}", exc_info=True)
            return self._generate_mock_transcript(file_path, language_hint or "en")

    # ─────────────────────────────────────────────────────────────────────
    def _run_transcription(
        self,
        file_path: str,
        language_hint: str = None,
        prompt: str = None,
    ) -> Dict[str, Any]:

        logger.info(
            f"WhisperService: Starting transcription | "
            f"file={os.path.basename(file_path)} | "
            f"model={self.loaded_model_name} | task=transcribe"
        )

        t0 = time.time()

        # ── faster-whisper transcribe ─────────────────────────────────────
        # task="translate" → translates source language to English transcript directly
        # vad_filter=False → do NOT filter segments (Tamil has high no_speech_prob
        #                     which would silence the entire audio with VAD on)
        # beam_size=5      → better accuracy than greedy (beam_size=1)
        # best_of=5        → sample 5 candidates and pick best (improves accuracy)
        # temperature=0    → deterministic, no randomness
        segments_iter, info = self.model.transcribe(
            file_path,
            task="translate",
            language=language_hint if language_hint else None,  # None = auto-detect
            beam_size=5,
            best_of=5,
            temperature=0,
            vad_filter=False,
            without_timestamps=False,
            word_timestamps=False,
            initial_prompt=prompt if prompt else "OnePlug EV charging network. Customer calls about charging stations, RFID cards, mobile app. EV car models: Tata Nexon EV, Tata Tiago EV, MG ZS EV, BYD Atto 3, Mahindra XUV400. Common complaints: payment failed, OTP delay, charger error 402, session stopped, wallet refund."
        )

        detected_lang = info.language
        lang_prob     = round(info.language_probability, 4)
        duration      = round(info.duration, 2)

        # Consume the generator — this is where actual inference runs
        segments: List[Dict[str, Any]] = []
        full_text_parts = []

        for seg in segments_iter:
            seg_dict = {
                "id":               seg.id,
                "start":            round(seg.start, 2),
                "end":              round(seg.end, 2),
                "text":             seg.text.strip(),
                "avg_logprob":      round(seg.avg_logprob, 4),
                "compression_ratio": round(seg.compression_ratio, 4),
                "no_speech_prob":   round(seg.no_speech_prob, 4),
            }
            segments.append(seg_dict)
            if seg.text.strip():
                full_text_parts.append(seg.text.strip())

        elapsed   = round(time.time() - t0, 2)
        full_text = " ".join(full_text_parts)
        word_count = len(full_text.split())

        logger.info(
            f"WhisperService: Done | elapsed={elapsed}s | "
            f"lang={detected_lang} (p={lang_prob}) | "
            f"duration={duration}s | segments={len(segments)} | words={word_count}"
        )

        return {
            "text":              full_text,
            "transcript":        full_text,
            "detected_language": detected_lang,
            "language":          detected_lang,
            "confidence":        lang_prob,
            "duration":          duration,
            "words_count":       word_count,
            "segment_count":     len(segments),
            "segments":          segments,
            "api_used":          f"faster-whisper/{self.loaded_model_name}",
        }

    # ─────────────────────────────────────────────────────────────────────
    def _generate_mock_transcript(self, file_path: str, language: str) -> Dict[str, Any]:
        return {
            "text":              "Demo mode: No Whisper model loaded.",
            "transcript":        "Demo mode: No Whisper model loaded.",
            "detected_language": language,
            "language":          language,
            "confidence":        0.0,
            "duration":          0.0,
            "words_count":       0,
            "segment_count":     0,
            "segments":          [],
            "api_used":          "demo_mock",
        }
