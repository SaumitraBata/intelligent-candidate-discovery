"""
Behavioral Scorer — Updated for Challenge Dataset
Uses platform activity signals from redrob_signals.
"""

import math
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BehavioralScorer:
    """Score candidates based on behavioral signals from the dataset."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.recency_half_life = config["behavioral"]["recency_decay_days"]

    def score(self, candidate_profile: Dict[str, Any]) -> float:
        """
        Behavioral scoring using platform activity signals.
        Uses last_active date and application history from redrob signals.
        """
        redrob = candidate_profile.get("redrob", {})
        
        # Activity recency
        recency_score = self._score_recency(redrob)
        
        # Application activity (engagement proxy)
        app_score = self._score_application_activity(redrob)
        
        # Interview conversion (quality of applications)
        conversion_score = self._score_interview_conversion(redrob)
        
        # Weighted
        return (
            0.40 * recency_score +
            0.35 * app_score +
            0.25 * conversion_score
        )

    def _score_recency(self, redrob: Dict) -> float:
        """Score based on last active date."""
        last_active_str = redrob.get("last_active_str")
        
        if not last_active_str:
            return 0.4  # Unknown
        
        try:
            # Try parsing different date formats
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%Y/%m/%d"]:
                try:
                    last_active = datetime.strptime(str(last_active_str)[:10], "%Y-%m-%d")
                    break
                except ValueError:
                    continue
            else:
                return 0.4
            
            days_since = (datetime.now() - last_active).days
            days_since = max(0, days_since)
            
            # Exponential decay
            return max(0.05, math.exp(-0.693 * days_since / self.recency_half_life))
        
        except Exception:
            return 0.4

    def _score_application_activity(self, redrob: Dict) -> float:
        """Score based on application activity on platform."""
        total_apps = redrob.get("total_applications", 0)
        
        if total_apps <= 0:
            return 0.35
        elif total_apps <= 3:
            return 0.55
        elif total_apps <= 10:
            return 0.75
        elif total_apps <= 20:
            return 0.85
        elif total_apps <= 40:
            return 0.80  # Slight spray-and-pray concern
        else:
            return 0.65

    def _score_interview_conversion(self, redrob: Dict) -> float:
        """Score interview conversion rate — quality over quantity."""
        rate = redrob.get("interview_conversion_rate", 0.0)
        
        if rate <= 0:
            return 0.40
        elif rate >= 0.6:
            return 1.0
        elif rate >= 0.4:
            return 0.80
        elif rate >= 0.2:
            return 0.60
        else:
            return 0.40