"""
Issue Detection Service — pattern-based issue flagging for EV customer support calls.

Detects issue types, assigns severity, and is easily extensible.
"""
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Issue pattern definitions ────────────────────────────────────────────────
# Each entry: (issue_type, severity, keyword_patterns)
ISSUE_PATTERNS: List[tuple] = [
    (
        "Escalation Risk",
        "High",
        [
            r"\bescalat", r"\bmanager\b", r"\bsupervisor\b", r"\blegal\b",
            r"\blawsuit\b", r"\bconsumer court\b", r"\bpolice\b",
            r"\bcomplaint\b.*\bfile\b", r"\bformal complaint\b",
        ],
    ),
    (
        "Angry / Frustrated Customer",
        "High",
        [
            r"\bangry\b", r"\bfurious\b", r"\boutrageous\b", r"\bterrible\b",
            r"\bworst\b", r"\bhorrible\b", r"\bunacceptable\b", r"\bfraud\b",
            r"\bcheated\b", r"\bscam\b", r"\bliar\b", r"\bstupid\b",
            r"very (angry|upset|frustrated|disappointed)",
            r"(this is|that is) ridiculous",
        ],
    ),
    (
        "Refund Request",
        "High",
        [
            r"\brefund\b", r"\bmoney back\b", r"\bcancel.*order\b",
            r"\bchargeback\b", r"\bdispute\b", r"\breturn.*amount\b",
            r"\bpayment.*back\b", r"\breturn my money\b",
        ],
    ),
    (
        "Delivery Delay",
        "Medium",
        [
            r"\bnot delivered\b", r"\bnot arrived\b", r"\bdelivery.*delay\b",
            r"\bdelayed\b", r"\blate delivery\b", r"\bstill waiting\b",
            r"\bnot received\b", r"\bshipment\b", r"\bpackage.*missing\b",
            r"\border.*not.*come\b", r"\bwhere is my\b",
        ],
    ),
    (
        "Technical Issue",
        "Medium",
        [
            r"\berror\b", r"\berror code\b", r"\bnot working\b",
            r"\bwon.t (start|work|charge|connect|initiate)\b",
            r"\bcharger.*fail\b", r"\bcharging.*fail\b",
            r"\bno power\b", r"\bblank screen\b", r"\bscreen.*off\b",
            r"\brfid.*not\b", r"\bapp.*crash\b", r"\bapp.*not\b",
            r"\bstation.*down\b", r"\bcharger.*down\b",
            r"\bwork agala\b", r"\bcharge aagala\b", r"\binitiate agala\b",
        ],
    ),
    (
        "Poor Support Experience",
        "Medium",
        [
            r"\bno response\b", r"\bnever replied\b", r"\bno one.*help\b",
            r"\bwaited.*long\b", r"\blong.*wait\b", r"\bhours on hold\b",
            r"\bignored\b", r"\bghosted\b", r"\bunavailable\b",
            r"\bno one.*answer\b", r"\bkeep.*transfer\b",
            r"\bhelp panala\b", r"\brespond agala\b",
        ],
    ),
]


class IssueDetectionService:
    """Detect customer support issues and assign severity levels."""

    def analyze(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "issue_detected": False,
                "issue_type": None,
                "severity": None,
                "all_issues": [],
                "issue_reason": "Empty transcript.",
            }

        lower = text.lower()
        matched: List[Dict] = []

        for issue_type, severity, patterns in ISSUE_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, lower):
                    # Avoid duplicate issue types
                    if not any(m["issue_type"] == issue_type for m in matched):
                        matched.append({"issue_type": issue_type, "severity": severity})
                    break   # one pattern match per issue type is enough

        if not matched:
            logger.info("IssueDetectionService: No issues detected.")
            return {
                "issue_detected": False,
                "issue_type": None,
                "severity": None,
                "all_issues": [],
                "issue_reason": "No flagged issues detected in transcript.",
            }

        # Sort by severity: High → Medium → Low
        severity_rank = {"High": 0, "Medium": 1, "Low": 2}
        matched.sort(key=lambda x: severity_rank.get(x["severity"], 9))

        primary = matched[0]
        reason = f"Detected {len(matched)} issue(s): {', '.join(m['issue_type'] for m in matched)}."
        logger.info(f"IssueDetectionService: {reason}")

        return {
            "issue_detected": True,
            "issue_type": primary["issue_type"],
            "severity": primary["severity"],
            "all_issues": matched,
            "issue_reason": reason,
        }
