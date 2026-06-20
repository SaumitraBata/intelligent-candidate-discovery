"""
Profile Quality Scorer & Anomaly Detector
Evaluates profile quality and flags suspicious or low-quality profiles.
"""

import re
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class QualityScorer:
    """Score profile quality and detect anomalies."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_completeness = config["quality"]["min_completeness_threshold"]
        self.anomaly_penalty = config["quality"]["anomaly_penalty"]

    def score(self, candidate_profile: Dict[str, Any]) -> float:
        """
        Score overall profile quality.
        
        Evaluates:
        1. Profile completeness
        2. Information consistency
        3. Description quality (length, substance)
        4. Credential credibility
        """
        scores = []

        # 1. Completeness (0.40 weight)
        completeness = candidate_profile.get("profile_completeness", 0)
        scores.append(("completeness", completeness, 0.40))

        # 2. Description quality (0.25 weight)
        desc_quality = self._score_description_quality(candidate_profile)
        scores.append(("description", desc_quality, 0.25))

        # 3. Skills quality (0.20 weight)
        skills_quality = self._score_skills_quality(candidate_profile)
        scores.append(("skills", skills_quality, 0.20))

        # 4. Consistency (0.15 weight)
        consistency = self._score_consistency(candidate_profile)
        scores.append(("consistency", consistency, 0.15))

        total = sum(s * w for _, s, w in scores)
        total_weight = sum(w for _, _, w in scores)

        return total / total_weight if total_weight > 0 else 0.3
    

    

    def detect_anomalies(self, candidate_profile):
        """Detect anomalies including title-description mismatches."""
        flags = []

        # ── Existing checks ─────────────────────────────────────────
        completeness = candidate_profile.get("profile_completeness", 0)
        if completeness < self.min_completeness:
            flags.append("very_sparse_profile")

        skills = candidate_profile.get("skills", [])
        if len(skills) > 50:
            flags.append("excessive_skill_claims")

        years = candidate_profile.get("experience_years", 0)
        if years > 45:
            flags.append("unrealistic_experience_claim")

        # ── HONEYPOT: Title-Description Mismatch ────────────────────
        # If candidate's job title doesn't match what the description describes
        # This is the #1 signal of honeypot candidates in this dataset
        career = candidate_profile.get("career_history", [])
        mismatch_count = 0
        
        for job in career:
            title = job.get("title", "").lower().strip()
            description = job.get("description", "").lower().strip()
            
            if not title or not description or len(description) < 30:
                continue

            # Extract role-defining nouns from title
            # E.g., "civil engineer" -> ["civil", "engineer"]
            title_words = set(w for w in title.split() if len(w) > 3)
            
            # Check if title words appear in the description
            # A genuine Civil Engineer job description should mention civil/engineering work
            title_in_desc = any(tw in description for tw in title_words if len(tw) > 4)
            
            # Check for clearly different role indicators in description
            role_indicators = [
                "marketing", "sales", "consulting", "business analyst",
                "product management", "accountant", "civil engineer",
                "mechanical engineer", "electrical engineer", "ml engineer",
                "software engineer", "data scientist", "designer",
                "hr", "human resources", "operations", "customer support",
            ]
            
            # Find which role the description actually describes
            described_roles = [r for r in role_indicators if r in description]
            title_role = next((r for r in role_indicators if r in title), None)
            
            # If description mentions a DIFFERENT role than the title claims
            if described_roles and title_role:
                if not any(r == title_role or title_role in r or r in title_role 
                        for r in described_roles):
                    mismatch_count += 1

        if mismatch_count >= 1:
            flags.append("title_description_mismatch")
        
        if mismatch_count >= 2:
            flags.append("severe_role_inconsistency")

        # ── HONEYPOT: Duplicate descriptions across jobs ────────────
        # Copy-paste descriptions indicate fake/generated profiles
        if len(career) >= 2:
            descriptions = [j.get("description", "") for j in career if j.get("description")]
            descriptions = [d for d in descriptions if len(d) > 50]
            if len(descriptions) >= 2:
                unique_descs = len(set(descriptions))
                if unique_descs < len(descriptions):
                    flags.append("duplicate_job_descriptions")

        # ── HONEYPOT: Advanced skills with very short tenure ────────
        # Claiming "advanced" in a skill used for only 2-6 months is suspicious
        skills_data = candidate_profile.get("skills_raw", [])
        advanced_short_tenure = 0
        if isinstance(skills_data, list) and skills_data and isinstance(skills_data[0], dict):
            for skill in skills_data:
                prof = skill.get("proficiency", "")
                duration = skill.get("duration_months", 0)
                if prof == "advanced" and 0 < duration < 8:
                    advanced_short_tenure += 1
        
        if advanced_short_tenure >= 3:
            flags.append("inflated_proficiency_claims")

        # ── HONEYPOT: Experience exceeds career timeline ────────────
        if career and years > 0:
            total_months = sum(j.get("duration_months", 0) for j in career)
            total_years = total_months / 12
            if total_years > 0 and years > total_years + 5:
                flags.append("experience_timeline_mismatch")

        # ── Other existing anomaly checks ───────────────────────────
        summary = candidate_profile.get("summary", "")
        if summary and self._is_keyword_stuffing(summary):
            flags.append("possible_keyword_stuffing")

        return flags
    




    def _is_keyword_stuffing(self, text: str) -> bool:
        """Detect keyword stuffing in text — works for any domain."""
        if not text or len(text) < 50:
            return False
        
        words = text.split()
        if len(words) < 20:
            return False
        
        # Check for excessive comma usage (often indicates keyword lists)
        comma_density = text.count(",") / len(words)
        if comma_density > 0.4:
            return True
        
        # Check for generic buzzword density
        buzzwords = {
            "innovative", "passionate", "expert", "guru", "ninja",
            "rockstar", "wizard", "leveraging", "synergize", "paradigm",
        }
        buzz_count = sum(1 for w in words if w.lower() in buzzwords)
        if buzz_count / len(words) > 0.10:
            return True
        
        return False
    




    def _score_description_quality(self, profile: Dict) -> float:
        """Score the quality of text descriptions."""
        summary = profile.get("summary", "")
        descriptions = profile.get("experience_descriptions", [])

        total_text = summary + " " + " ".join(str(d) for d in descriptions)

        if not total_text.strip():
            return 0.2

        word_count = len(total_text.split())

        # Ideal range: 50-500 words
        if word_count < 10:
            return 0.2
        elif word_count < 30:
            return 0.4
        elif word_count < 50:
            return 0.6
        elif word_count <= 500:
            return 0.9
        elif word_count <= 1000:
            return 0.85
        else:
            return 0.7  # Overly verbose

    def _score_skills_quality(self, profile: Dict) -> float:
        """Score the quality of listed skills."""
        skills = profile.get("skills", [])

        if not skills:
            return 0.2

        count = len(skills)

        # Ideal: 5-25 skills
        if count < 3:
            return 0.4
        elif count <= 25:
            return 0.8 + min(count / 25, 1.0) * 0.2
        elif count <= 40:
            return 0.8
        else:
            return 0.6  # Too many — may be padding

    def _score_consistency(self, profile: Dict) -> float:
        """Check for internal consistency."""
        score = 1.0

        # Check if experience years is consistent with listed companies
        years = profile.get("experience_years", 0)
        companies = profile.get("companies", [])
        if years > 0 and companies:
            # Rough check: ~2-5 years per company is normal
            expected_companies = max(1, years / 5)
            if len(companies) > years * 2:
                score -= 0.2  # Too many companies for stated experience

        return max(0.2, score)

    def _detect_keyword_stuffing(self, text: str) -> bool:
        """Detect potential keyword stuffing in text."""
        words = text.lower().split()
        if len(words) < 10:
            return False

        # Check for high proportion of tech buzzwords
        buzzwords = {"ai", "ml", "cloud", "agile", "devops", "blockchain",
                     "innovative", "passionate", "expert", "guru", "ninja",
                     "rockstar", "wizard"}

        buzz_count = sum(1 for w in words if w in buzzwords)
        if buzz_count / len(words) > 0.15:
            return True

        # Check for excessive comma-separated lists
        comma_count = text.count(",")
        if comma_count > len(words) * 0.3:
            return True

        return False

    def _is_generic_profile(self, text: str) -> bool:
        """Detect generic/template profiles."""
        generic_phrases = [
            "results-driven professional",
            "seeking new opportunities",
            "proven track record of success",
            "highly motivated individual",
            "passionate about technology",
            "team player with excellent",
            "looking for challenging role",
        ]

        text_lower = text.lower()
        matches = sum(1 for phrase in generic_phrases if phrase in text_lower)
        return matches >= 2