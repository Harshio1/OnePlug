"""
Sentiment Analysis Service — lightweight keyword-based NLP.

Supports English, Tamil (romanised/Tanglish), and mixed transcripts.
Architecture is designed to be drop-in replaced by an LLM call later.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ── Word banks ──────────────────────────────────────────────────────────────

POSITIVE_WORDS = {
    # English
    "thank", "thanks", "thankyou", "great", "excellent", "perfect", "good",
    "happy", "satisfied", "resolved", "fixed", "working", "helped", "helpful",
    "appreciate", "wonderful", "fantastic", "awesome", "brilliant", "solved",
    "quick", "fast", "efficient", "professional", "smooth", "easy",
    # Tanglish / Tamil-English
    "super", "nandri", "romba nandri", "sari", "okay", "ok", "achu",
    "nanba", "correct", "start achu", "work aaguthu", "charging aaguthu",
}

NEGATIVE_WORDS = {
    # English
    "angry", "frustrated", "upset", "annoyed", "disappointed", "terrible",
    "horrible", "awful", "useless", "worst", "bad", "wrong", "broken",
    "failed", "error", "issue", "problem", "complaint", "unacceptable",
    "delay", "delayed", "late", "missing", "lost", "stolen", "refund",
    "not working", "doesn't work", "wont work", "not fixed", "unresolved",
    "escalate", "manager", "legal", "lawsuit", "cheated", "fraud",
    "no response", "ignored", "ghosted", "never replied",
    # Tanglish / Tamil-English
    "varalai", "work agala", "work aagala", "initiate agala", "charge aagala",
    "problem iruku", "error varuthu", "respond agala", "panala",
    "late achu", "kandupudikala", "theriyala", "help panala",
}

NEUTRAL_WORDS = {
    "check", "looking", "trying", "waiting", "hold", "moment",
    "one second", "let me", "i will", "we will", "please",
}


class SentimentService:
    """Classify transcript sentiment as Positive / Neutral / Negative."""

    def analyze(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"sentiment": "Neutral", "sentiment_score": 0.0, "sentiment_reason": "Empty transcript."}

        lower = text.lower()
        words = set(lower.split())

        pos_hits = [w for w in POSITIVE_WORDS if w in lower]
        neg_hits = [w for w in NEGATIVE_WORDS if w in lower]

        pos_score = len(pos_hits)
        neg_score = len(neg_hits)

        total = pos_score + neg_score or 1
        score = round((pos_score - neg_score) / total, 3)   # -1 … +1

        if score > 0.1:
            sentiment = "Positive"
        elif score < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        reason = f"Detected {pos_score} positive signal(s) and {neg_score} negative signal(s)."
        logger.info(f"SentimentService: {sentiment} (score={score}) | {reason}")

        return {
            "sentiment": sentiment,
            "sentiment_score": score,
            "sentiment_reason": reason,
        }
