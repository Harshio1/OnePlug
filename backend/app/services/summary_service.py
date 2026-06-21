"""
Summary Generation Service — extractive summarisation for customer support transcripts.

Scores each sentence by: keyword relevance + position weight.
No external NLP library required. Designed for LLM swap-in later.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Domain keywords that increase a sentence's importance score
DOMAIN_KEYWORDS = {
    # Customer concern signals
    "problem", "issue", "error", "not working", "failed", "complaint",
    "delay", "refund", "cancel", "broken", "crash", "missing", "lost",
    # Resolution signals
    "resolved", "fixed", "working", "reset", "restarted", "completed",
    "charged", "charging", "started", "helped", "solved",
    # Action signals
    "will", "shall", "going to", "please", "need to", "require",
    "escalate", "callback", "follow up", "ticket", "raise",
    # EV domain
    "charger", "rfid", "station", "ev", "battery", "connector", "charging session",
    # Tanglish
    "charge aaguthu", "work aaguthu", "reset panrom", "help panrom",
}

SENTENCE_SPLITTER = re.compile(r'(?<=[.!?])\s+')


class SummaryService:
    """Generate a concise extractive summary of a customer support transcript."""

    MAX_SUMMARY_SENTENCES = 3

    def analyze(self, text: str, segments: List[dict] = None) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "summary": "No transcript content available to summarise.",
                "main_concern": "Unknown",
                "outcome": "Unknown",
                "action_needed": "Review transcript manually.",
            }

        sentences = self._split_sentences(text)
        if not sentences:
            return {
                "summary": text[:300],
                "main_concern": "Unknown",
                "outcome": "Unknown",
                "action_needed": "Review transcript manually.",
            }

        scored = self._score_sentences(sentences)
        top = sorted(scored, key=lambda x: x[1], reverse=True)[: self.MAX_SUMMARY_SENTENCES]
        # Preserve original order in summary
        top_idx = sorted([s[0] for s in top])
        summary_sentences = [sentences[i] for i in top_idx]
        summary = " ".join(summary_sentences).strip()

        main_concern = self._extract_main_concern(text)
        outcome = self._extract_outcome(text)
        action_needed = self._extract_action(text)

        logger.info(
            f"SummaryService: summary_len={len(summary)} | concern={main_concern} | outcome={outcome}"
        )

        return {
            "summary": summary,
            "main_concern": main_concern,
            "outcome": outcome,
            "action_needed": action_needed,
        }

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def _split_sentences(self, text: str) -> List[str]:
        raw = SENTENCE_SPLITTER.split(text.strip())
        return [s.strip() for s in raw if len(s.strip()) > 15]

    def _score_sentences(self, sentences: List[str]) -> List[tuple]:
        total = len(sentences)
        scored = []
        for idx, sentence in enumerate(sentences):
            lower = sentence.lower()
            kw_score = sum(1 for kw in DOMAIN_KEYWORDS if kw in lower)
            # Position weight: first and last sentences are more informative
            if idx == 0 or idx == total - 1:
                pos_weight = 1.5
            elif idx <= total * 0.25:
                pos_weight = 1.2
            else:
                pos_weight = 1.0
            length_bonus = min(len(sentence.split()) / 20, 1.0)
            score = (kw_score * pos_weight) + length_bonus
            scored.append((idx, score))
        return scored

    def _extract_main_concern(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["not delivered", "not arrived", "not received", "delivery"]):
            return "Delivery / Shipment Issue"
        if any(w in lower for w in ["refund", "money back", "chargeback"]):
            return "Refund Request"
        if any(w in lower for w in ["error", "not working", "won't work", "charge aagala", "work agala", "initiate agala"]):
            return "Technical / Charger Issue"
        if any(w in lower for w in ["no response", "ignored", "no one", "waited"]):
            return "Poor Support Experience"
        if any(w in lower for w in ["angry", "frustrated", "worst", "terrible"]):
            return "Angry / Escalation Risk"
        return "General Inquiry"

    def _extract_outcome(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["resolved", "fixed", "working now", "charging now", "charging start", "thank", "thanks"]):
            return "Issue Resolved"
        if any(w in lower for w in ["escalat", "manager", "supervisor", "ticket raised"]):
            return "Escalated to Higher Support"
        if any(w in lower for w in ["callback", "follow up", "will check", "will investigate"]):
            return "Pending Follow-up"
        return "Outcome Unclear"

    def _extract_action(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["refund", "money back"]):
            return "Process refund and notify customer."
        if any(w in lower for w in ["escalat", "manager"]):
            return "Escalate to senior support and monitor."
        if any(w in lower for w in ["ticket", "log", "raise"]):
            return "Follow up on open support ticket."
        if any(w in lower for w in ["resolved", "fixed", "working"]):
            return "Mark resolved. No action required."
        return "Review call and contact customer if needed."
