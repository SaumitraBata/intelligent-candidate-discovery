"""
Ranker
Final ranking, deduplication, and candidate selection.
Implements hackathon-compliant tie-breaking (candidate_id ascending for equal scores).
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class Ranker:
    """Rank, deduplicate, and select top candidates."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def rank(self, fused_scores: Dict[str, float],
             detailed_scores: Dict[str, Dict[str, Any]],
             candidate_profiles: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Produce final ranked list of candidates.

        Sort order:
        1. By fused score (descending) — best candidates first
        2. By candidate_id (ascending) — deterministic tie-breaking
           (hackathon requirement: equal scores → IDs in alphabetical order)

        Steps:
        1. Sort by fused score (desc), then candidate_id (asc)
        2. Deduplicate by name (same person with multiple profiles)
        3. Return ranked list with metadata
        """
        # Two-key sort:
        # - Primary: -score (negative for descending order)
        # - Secondary: candidate_id (ascending, alphabetical)
        # Python's tuple comparison handles multi-key sort natively
        sorted_candidates = sorted(
            fused_scores.items(),
            key=lambda x: (-x[1], x[0]),
        )

        # Build ranked list with metadata + name-based deduplication
        ranked = []
        seen_names = set()

        for cid, score in sorted_candidates:
            profile = candidate_profiles.get(cid, {})

            # Deduplication by name (if available)
            # Prevents the same person appearing multiple times when they
            # have multiple profile entries with different IDs
            name = profile.get("name", "").strip().lower()
            if name and name in seen_names:
                logger.debug(f"  Skipping duplicate: {name} ({cid})")
                continue
            if name:
                seen_names.add(name)

            ranked.append({
                "candidate_id": cid,
                "final_score": score,
                "name": profile.get("name", ""),
                "current_title": profile.get("current_title", ""),
                "experience_years": profile.get("experience_years", 0),
                "seniority_level": profile.get("seniority_level", "unknown"),
                "skill_count": profile.get("skill_count", 0),
                "profile_completeness": profile.get("profile_completeness", 0),
            })

        logger.info(f"  Ranked {len(ranked)} candidates (after deduplication)")
        return ranked