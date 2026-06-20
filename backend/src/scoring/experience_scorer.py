"""
Experience Fit Scorer
Evaluates how well candidate experience matches JD requirements.
"""

import math
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ExperienceScorer:
    """Score candidates on experience fit."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def score(self, jd_requirements: Dict[str, Any],
              candidate_profile: Dict[str, Any]) -> float:
        """
        Score experience fit using a Gaussian penalty around the ideal range.
        
        Perfect score for candidates within the required range.
        Gaussian decay for those outside the range.
        Slightly asymmetric: over-experience penalized less than under-experience.
        """
        exp_range = jd_requirements.get("experience_range", (0, 99))
        min_years, max_years = exp_range
        candidate_years = candidate_profile.get("experience_years", 0)

        if min_years == 0 and max_years >= 99:
            return 0.7  # No experience requirement specified

        # Within range: perfect score
        if min_years <= candidate_years <= max_years:
            # Bonus for being in the (middle of range)
            range_size = max(max_years - min_years, 1)
            mid_point = min_years + range_size / 2
            distance_from_mid = abs(candidate_years - mid_point) / range_size
            return 0.9 + 0.1 * (1 - distance_from_mid)

        # Below minimum
        if candidate_years < min_years:
            deficit = min_years - candidate_years
            # Gaussian penalty — steeper for under-experience
            sigma = max(min_years * 0.4, 1.5)
            penalty = math.exp(-(deficit ** 2) / (2 * sigma ** 2))
            return penalty * 0.85  # Cap at 0.85 even with minimal deficit

        # Above maximum
        if candidate_years > max_years:
            surplus = candidate_years - max_years
            # Gentler penalty for over-experience
            sigma = max(max_years * 0.5, 3.0)
            penalty = math.exp(-(surplus ** 2) / (2 * sigma ** 2))
            return penalty * 0.9  # More lenient than under-experience

        return 0.5  # Shouldn't reach here