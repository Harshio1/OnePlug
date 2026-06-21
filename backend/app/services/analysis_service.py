"""
Analysis Orchestrator — runs all three AI analysis services sequentially
and returns a unified JSON analysis block for storage and frontend display.
"""
import logging
from typing import Dict, Any, List

from .sentiment_service import SentimentService
from .summary_service import SummaryService
from .issue_detection_service import IssueDetectionService

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Orchestrates summary, issue detection, and sentiment analysis.

    Usage
    -----
        service = AnalysisService()
        analysis = service.analyze(transcript_text, segments)

    Returns
    -------
    {
        "summary":           str,
        "main_concern":      str,
        "outcome":           str,
        "action_needed":     str,
        "issue_detected":    bool,
        "issue_type":        str | None,
        "severity":          str | None,   # High / Medium / Low
        "all_issues":        list,
        "sentiment":         str,          # Positive / Neutral / Negative
        "sentiment_score":   float,
        "analysed":          True,
    }
    """

    def __init__(self):
        self.sentiment_svc = SentimentService()
        self.issue_svc = IssueDetectionService()
        self.summary_svc = SummaryService()
        logger.info("AnalysisService: All sub-services initialised.")

    def analyze(self, transcript_text: str, segments: List[dict] = None) -> Dict[str, Any]:
        """Run full AI analysis pipeline on transcript text."""
        logger.info(
            f"AnalysisService: Starting analysis | "
            f"text_len={len(transcript_text)} | segments={len(segments or [])}"
        )

        # Run all three analysis passes
        sentiment_result = self.sentiment_svc.analyze(transcript_text)
        issue_result = self.issue_svc.analyze(transcript_text)
        summary_result = self.summary_svc.analyze(transcript_text, segments)

        analysis = {
            # Summary block
            "summary": summary_result["summary"],
            "main_concern": summary_result["main_concern"],
            "outcome": summary_result["outcome"],
            "action_needed": summary_result["action_needed"],
            # Issue block
            "issue_detected": issue_result["issue_detected"],
            "issue_type": issue_result["issue_type"],
            "severity": issue_result["severity"],
            "all_issues": issue_result["all_issues"],
            # Sentiment block
            "sentiment": sentiment_result["sentiment"],
            "sentiment_score": sentiment_result["sentiment_score"],
            # Meta
            "analysed": True,
        }

        logger.info(
            f"AnalysisService: Complete | "
            f"sentiment={analysis['sentiment']} | "
            f"issue={analysis['issue_type']} | "
            f"severity={analysis['severity']}"
        )
        return analysis
