"""
Translation Service — Tamil → English translation.

Primary:  googletrans (Google Translate, free, no API key required)
Fallback: Returns original text with a note if translation fails.

Architecture is designed for LLM swap-in (e.g. MarianMT, GPT-4) later.
"""
import sys
import logging
from typing import Optional

# Force UTF-8 to handle Tamil Unicode safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Translates Tamil text to natural English.

    Primary: deep-translator (Google Translate proxy, highly reliable)
    Fallback: Returns original text with a note if translation fails.
    """

    def __init__(self):
        self._translator = None
        self._available = False
        self._init()

    def _init(self):
        try:
            from deep_translator import GoogleTranslator
            self._translator = GoogleTranslator(source='ta', target='en')
            self._available = True
            logger.info("TranslationService: deep-translator ready.")
        except ImportError:
            logger.warning("TranslationService: deep-translator not installed. Run: pip install deep-translator")
        except Exception as exc:
            logger.warning(f"TranslationService: Init failed – {exc}")

    @property
    def is_available(self) -> bool:
        return self._available and self._translator is not None

    def translate_to_english(
        self,
        text: str,
        source_lang: str = "ta",
    ) -> Optional[str]:
        if not text or not text.strip():
            return None

        if not self.is_available:
            logger.warning("TranslationService: Translator not available. Returning None.")
            return None

        try:
            # deep-translator handles chunks automatically up to 5000 chars natively,
            # but we can do a quick check
            if len(text) > 4500:
                chunks = self._chunk_text(text, max_len=4500)
                translated_chunks = []
                for chunk in chunks:
                    translated_chunks.append(self._translator.translate(chunk))
                translated = " ".join(translated_chunks).strip()
            else:
                translated = self._translator.translate(text)

            logger.info(
                f"TranslationService: Translated {len(text)} chars "
                f"({source_lang}→en) → {len(translated)} chars."
            )
            return translated

        except Exception as exc:
            logger.error(f"TranslationService: Translation error – {exc}")
            return None

    def translate_segments_to_english(
        self,
        segments: list,
        source_lang: str = "ta",
    ) -> list:
        if not segments or not self.is_available:
            return []

        translated_segments = []
        for seg in segments:
            original_text = seg.get("text", "").strip()
            if not original_text:
                continue
            try:
                en_text = self._translator.translate(original_text)
            except Exception as exc:
                logger.warning(f"TranslationService: Segment translation failed – {exc}")
                en_text = original_text   # fall back to original

            translated_segments.append(
                {
                    "id": seg.get("id", len(translated_segments)),
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "text": en_text,
                }
            )

        logger.info(
            f"TranslationService: Translated {len(translated_segments)} segments ({source_lang}→en)."
        )
        return translated_segments

    @staticmethod
    def _chunk_text(text: str, max_len: int = 4500) -> list:
        """Split long text into sentence-aware chunks."""
        if len(text) <= max_len:
            return [text]

        sentences = text.replace("।", ".").split(".")
        chunks, current = [], ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            candidate = f"{current} {sentence}.".strip()
            if len(candidate) > max_len:
                if current:
                    chunks.append(current.strip())
                current = f"{sentence}."
            else:
                current = candidate

        if current.strip():
            chunks.append(current.strip())

        return chunks or [text[:max_len]]
