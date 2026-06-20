"""
Score Fusion — Updated for Challenge Dataset
Includes redrob_signals as a scored dimension.
"""

import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ScoreFusion:
    """Fuse multiple scoring signals including redrob platform signals."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.weights = config["scoring_weights"]
        self.method = config["fusion"]["method"]
        self.epsilon = config["fusion"]["epsilon"]
        self.anomaly_penalty = config["quality"]["anomaly_penalty"]

    def fuse(self, all_scores, jd_requirements=None, profiles=None):
        """
        Fuse all scoring dimensions with generic penalty application.

        Penalties applied:
        1. Negative requirement match — only if JD explicitly excluded something
        2. Honeypot detection — universal structural anomaly checks (35% per flag)
        3. Standard anomaly flags — existing quality checks
        """
        fused = {}

        # Extract JD's negative requirements (if any)
        neg_req = jd_requirements.get("negative_requirements", {}) if jd_requirements else {}
        excluded_keywords = neg_req.get("excluded_keywords", [])
        excluded_in_parens = neg_req.get("excluded_in_parens", [])
        exclusion_strength = neg_req.get("exclusion_strength", 0.0)

        # Combine all excluded terms
        all_excluded = set()
        for kw in excluded_keywords + excluded_in_parens:
            if len(kw) >= 3:
                all_excluded.add(kw.lower().strip())

        # Define honeypot flags — these signal fake/inflated profiles
        honeypot_flags = {
            "title_description_mismatch",
            "severe_role_inconsistency",
            "duplicate_job_descriptions",
            "inflated_proficiency_claims",
            "experience_timeline_mismatch",
            "experience_career_mismatch",
            "inflated_expertise_claims",
            "uniform_expert_claims",
            "uniform_proficiency_pattern",
            "uniform_tenure_pattern",
            "zero_engagement_pattern",
            "skill_experience_mismatch",
        }

        for cid, scores in all_scores.items():
            dimension_scores = {
                "semantic_fit": scores.get("semantic_fit", 0),
                "skill_match": scores.get("skill_match", 0),
                "redrob_signals": scores.get("redrob_signals", 0),
                "career_trajectory": scores.get("career_trajectory", 0),
                "experience_fit": scores.get("experience_fit", 0),
                "profile_quality": scores.get("profile_quality", 0),
            }

            if self.method == "weighted_geometric":
                raw_score = self._weighted_geometric_mean(dimension_scores)
            else:
                raw_score = self._weighted_arithmetic_mean(dimension_scores)

            # ── PENALTY 1: Negative requirements (only if JD has them) ──
            if profiles and cid in profiles and all_excluded and exclusion_strength > 0:
                profile = profiles[cid]
                penalty_multiplier = self._calc_negative_penalty(
                    profile, all_excluded, exclusion_strength
                )
                raw_score *= penalty_multiplier

            # ── PENALTY 2: Honeypot detection (universal) ──────────────
            # Heavier penalty: each honeypot flag reduces score by 35%
            # Floor of 0.10 to prevent score from going completely to zero
            anomalies = scores.get("anomaly_flags", [])
            honeypot_count = sum(1 for f in anomalies if f in honeypot_flags)
            if honeypot_count > 0:
                honeypot_penalty = max(0.10, 1.0 - (honeypot_count * 0.35))
                raw_score *= honeypot_penalty

            # ── PENALTY 3: Standard anomaly flags ──────────────────────
            other_anomalies = [f for f in anomalies if f not in honeypot_flags]
            standard_penalty = len(other_anomalies) * self.anomaly_penalty

            final_score = max(0.0, raw_score - standard_penalty)
            fused[cid] = final_score

        return fused

    def _calc_negative_penalty(self, profile, excluded_terms, strength):
        """
        Calculate penalty for negative requirement matches.
        The penalty intensity scales with how strongly the JD expressed exclusions.
        """
        # Build searchable text from profile
        searchable = " ".join([
            profile.get("current_title", "").lower(),
            profile.get("current_company", "").lower(),
            " ".join(profile.get("companies", [])).lower(),
            " ".join(profile.get("all_titles", [])).lower(),
            profile.get("current_industry", "").lower(),
        ])

        if not searchable.strip():
            return 1.0  # No data to penalize

        # Count how many excluded terms appear in this candidate's profile
        matches = sum(1 for term in excluded_terms if term in searchable)

        if matches == 0:
            return 1.0  # No exclusions matched, full score

        # Penalty scales with: (a) number of matches, (b) JD exclusion strength
        # If JD weakly signals exclusion (strength 0.2), small penalty
        # If JD strongly signals exclusion (strength 1.0), large penalty
        base_penalty = min(0.8, matches * 0.20)  # Cap at 80% reduction
        effective_penalty = base_penalty * strength

        return max(0.15, 1.0 - effective_penalty)

    def _weighted_arithmetic_mean(self, scores: Dict[str, float]) -> float:
        total, total_weight = 0.0, 0.0
        for dim, score in scores.items():
            weight = self.weights.get(dim, 0)
            total += score * weight
            total_weight += weight
        return total / total_weight if total_weight > 0 else 0

    def _weighted_geometric_mean(self, scores: Dict[str, float]) -> float:
        log_sum, total_weight = 0.0, 0.0
        for dim, score in scores.items():
            weight = self.weights.get(dim, 0)
            if weight <= 0:
                continue
            safe_score = max(score, self.epsilon)
            log_sum += weight * math.log(safe_score)
            total_weight += weight
        if total_weight <= 0:
            return 0
        return math.exp(log_sum / total_weight)