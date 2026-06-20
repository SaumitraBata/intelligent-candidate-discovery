"""
This is the KEY new scorer that leverages all the platform signals:
Redrob Signals Scorer
The KEY differentiator — scores candidates based on platform behavioral signals.

These signals are unique to the Redrob platform and go far beyond resume content:
- Profile completeness (how invested is the candidate?)
- Open to work flag (are they actively seeking?)
- Recruiter response rate (how reliable/engaged are they?)
- GitHub activity (real technical contribution proof)
- Skill assessments (verified skill scores, not self-reported)
- Notice period (how quickly can they start?)
- Verification status (email, phone, LinkedIn)
- Offer acceptance history
"""

import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RedrobSignalsScorer:
    """
    Score candidates based on Redrob platform behavioral signals.
    
    Weight breakdown within this scorer:
    - Open to work flag:          20% (most direct availability signal)
    - Recruiter response rate:    15% (reliability & engagement)
    - Profile completeness:       15% (investment & professionalism)
    - GitHub activity:            12% (verified technical proof)
    - Skill assessments:          12% (verified skill scores)
    - Notice period:              10% (time-to-hire signal)
    - Verification status:         8% (trust/authenticity)
    - Offer acceptance rate:       8% (hiring success probability)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rc = config.get("redrob", {})
        
        # Weights
        self.w_open_to_work = self.rc.get("open_to_work_weight", 0.20)
        self.w_response_rate = self.rc.get("response_rate_weight", 0.15)
        self.w_completeness = self.rc.get("profile_completeness_weight", 0.15)
        self.w_github = self.rc.get("github_activity_weight", 0.12)
        self.w_skill_assess = self.rc.get("skill_assessment_weight", 0.12)
        self.w_notice = self.rc.get("notice_period_weight", 0.10)
        self.w_verification = self.rc.get("verification_weight", 0.08)
        self.w_offer = self.rc.get("salary_fit_weight", 0.08)
        
        # Thresholds
        self.notice_ideal_max = self.rc.get("notice_period_ideal_max", 30)
        self.notice_acceptable = self.rc.get("notice_period_acceptable", 60)
    
    def score(self, candidate_profile: Dict[str, Any],
              jd_requirements: Optional[Dict[str, Any]] = None) -> float:
        """
        Compute the comprehensive Redrob signals score.
        
        Args:
            candidate_profile: Processed candidate profile with redrob key
            jd_requirements: Optional JD requirements for context-aware scoring
        
        Returns:
            Float score 0.0 - 1.0
        """
        redrob = candidate_profile.get("redrob", {})
        
        if not redrob:
            return 0.4  # No signals — neutral-low
        
        # Compute individual signal scores
        open_score = self._score_open_to_work(redrob)
        response_score = self._score_response_rate(redrob)
        completeness_score = self._score_profile_completeness(redrob)
        github_score = self._score_github_activity(
            redrob, candidate_profile.get("skills", [])
        )
        skill_assess_score = self._score_skill_assessments(
            redrob, jd_requirements
        )
        notice_score = self._score_notice_period(redrob)
        verification_score = self._score_verification(redrob)
        offer_score = self._score_offer_history(redrob)
        
        # Weighted combination
        final = (
            self.w_open_to_work * open_score +
            self.w_response_rate * response_score +
            self.w_completeness * completeness_score +
            self.w_github * github_score +
            self.w_skill_assess * skill_assess_score +
            self.w_notice * notice_score +
            self.w_verification * verification_score +
            self.w_offer * offer_score
        )
        
        return max(0.0, min(1.0, final))
    
    def score_breakdown(self, candidate_profile: Dict[str, Any],
                         jd_requirements: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """Return full score breakdown for explanation purposes."""
        redrob = candidate_profile.get("redrob", {})
        
        return {
            "open_to_work": self._score_open_to_work(redrob),
            "response_rate": self._score_response_rate(redrob),
            "profile_completeness": self._score_profile_completeness(redrob),
            "github_activity": self._score_github_activity(
                redrob, candidate_profile.get("skills", [])
            ),
            "skill_assessments": self._score_skill_assessments(redrob, jd_requirements),
            "notice_period": self._score_notice_period(redrob),
            "verification": self._score_verification(redrob),
            "offer_history": self._score_offer_history(redrob),
        }
    
    # ─────────────────────────────────────────────────────────────────────
    # Individual Signal Scorers
    # ─────────────────────────────────────────────────────────────────────
    
    def _score_open_to_work(self, redrob: Dict) -> float:
        """
        Open-to-work flag is the most direct availability signal.
        
        True  = actively seeking = highly valuable = 1.0
        False = not actively looking = 0.3 (may still be persuadable)
        """
        open_flag = redrob.get("open_to_work_flag", False)
        return 1.0 if open_flag else 0.35
    
    def _score_response_rate(self, redrob: Dict) -> float:
        """
        Recruiter response rate measures how reliably a candidate responds
        to recruiter outreach. High rate = trustworthy, engaged candidate.
        
        Also factors in average response time (faster = better).
        """
        response_rate = redrob.get("recruiter_response_rate", 0.0)
        avg_hours = redrob.get("avg_response_time_hours", 48.0)
        
        # Response rate score (0-1, direct)
        rate_score = response_rate
        
        # Response time score (faster is better, capped at 72 hours)
        # 0 hours = 1.0, 24 hours = 0.7, 48 hours = 0.4, 72+ hours = 0.1
        time_score = max(0.1, 1.0 - (avg_hours / 72.0) * 0.9)
        
        return 0.70 * rate_score + 0.30 * time_score
    
    def _score_profile_completeness(self, redrob: Dict) -> float:
        """
        Profile completeness score (0-100 from platform).
        Higher completeness = more invested candidate = more reliable data.
        """
        completeness = redrob.get("profile_completeness_score", 50.0)
        
        # Normalize to 0-1 with a slight curve (reward high completeness more)
        normalized = (completeness / 100.0) ** 0.85
        return normalized
    
    def _score_github_activity(self, redrob: Dict,
                                candidate_skills: list) -> float:
        """
        GitHub activity score proves real technical engagement.
        
        Rules:
        - Score of -1 = no GitHub linked
        - For tech roles: no GitHub is a mild negative signal
        - For non-tech roles: no GitHub is neutral
        - High score (>70) = strong technical proof
        """
        github_score = redrob.get("github_score", -1)
        github_available = redrob.get("github_available", False)
        
        if not github_available:
            # No GitHub — check if they're a tech candidate
            tech_skills = {"python", "java", "javascript", "go", "rust", "c++",
                          "react", "node.js", "django", "machine learning"}
            has_tech_skills = any(s in tech_skills for s in candidate_skills)
            
            if has_tech_skills:
                return 0.35  # Tech candidate with no GitHub — slight concern
            else:
                return 0.55  # Non-tech — neutral
        
        # GitHub score available (0-100)
        normalized = github_score / 100.0
        
        # Bonus curve: 80+ GitHub score is really strong
        if normalized >= 0.80:
            return min(1.0, normalized * 1.1)
        
        return normalized
    
    def _score_skill_assessments(self, redrob: Dict,
                                   jd_requirements: Optional[Dict] = None) -> float:
        """
        Skill assessment scores are VERIFIED scores (not self-reported).
        These are taken on the Redrob platform.
        
        Logic:
        - If assessments exist, use their average
        - If JD requirements known, weight relevant skill assessments higher
        - If no assessments, neutral score
        """
        skill_assessments = redrob.get("skill_assessment_scores", {}) or {}
        
        if not skill_assessments:
            return 0.45  # No assessments — neutral
        
        # If we have JD requirements, weight relevant skills higher
        if jd_requirements:
            jd_skills = set(
                s.lower() for s in (
                    jd_requirements.get("hard_skills", []) +
                    jd_requirements.get("must_have_skills", [])
                )
            )
            
            relevant_scores = []
            other_scores = []
            
            for skill, score in skill_assessments.items():
                skill_lower = skill.lower()
                is_relevant = any(
                    js in skill_lower or skill_lower in js
                    for js in jd_skills
                )
                
                if is_relevant:
                    relevant_scores.append(score / 100.0)
                else:
                    other_scores.append(score / 100.0)
            
            if relevant_scores and other_scores:
                return 0.70 * (sum(relevant_scores) / len(relevant_scores)) + \
                       0.30 * (sum(other_scores) / len(other_scores))
            elif relevant_scores:
                return sum(relevant_scores) / len(relevant_scores)
            else:
                return sum(other_scores) / len(other_scores)
        
        # Flat average
        avg = redrob.get("avg_skill_assessment", 0.0)
        return avg / 100.0
    
    def _score_notice_period(self, redrob: Dict) -> float:
        """
        Notice period in days — shorter is more desirable from recruiter POV.
        
        0 days (immediate):   1.0
        ≤30 days (1 month):   0.90
        ≤60 days (2 months):  0.70
        ≤90 days (3 months):  0.50
        >90 days:             Linear decay down to 0.15
        """
        notice = redrob.get("notice_period_days", 60.0)
        
        if notice <= 0:
            return 1.0
        elif notice <= 15:
            return 0.95
        elif notice <= self.notice_ideal_max:
            return 0.85
        elif notice <= self.notice_acceptable:
            return 0.65
        elif notice <= 90:
            return 0.45
        else:
            # Linear decay from 90 to 180 days
            excess = min(notice - 90, 90)
            return max(0.15, 0.45 - (excess / 90) * 0.30)
    
    def _score_verification(self, redrob: Dict) -> float:
        """
        Verification status indicates trust and authenticity.
        
        Verified email + phone + LinkedIn = full trust
        """
        email = redrob.get("verified_email", False)
        phone = redrob.get("verified_phone", False)
        linkedin = redrob.get("linkedin_connected", False)
        
        # Count verifications
        count = sum([email, phone, linkedin])
        
        if count == 3:
            return 1.0
        elif count == 2:
            return 0.80
        elif count == 1:
            return 0.55
        else:
            return 0.25  # No verifications — low trust
    
    def _score_offer_history(self, redrob: Dict) -> float:
        """
        Offer acceptance rate and hiring history.
        
        High acceptance rate = reliable, not a window shopper.
        -1 = no offer history (neutral — first time on platform)
        """
        offer_rate = redrob.get("offer_acceptance_rate", -1)
        offer_available = redrob.get("offer_rate_available", False)
        
        if not offer_available:
            return 0.55  # No history — neutral
        
        # Rate 0-1: higher is better
        # Very low rate (< 0.2) is concerning (either very picky or ghosting)
        if offer_rate >= 0.7:
            return 0.95
        elif offer_rate >= 0.5:
            return 0.80
        elif offer_rate >= 0.3:
            return 0.60
        elif offer_rate >= 0.1:
            return 0.40
        else:
            return 0.20  # Very low acceptance rate
    
    def get_reasoning_snippet(self, candidate_profile: Dict[str, Any]) -> str:
        """
        Generate a short reasoning snippet about redrob signals
        for the submission CSV reasoning column.
        """
        redrob = candidate_profile.get("redrob", {})
        parts = []
        
        if redrob.get("open_to_work_flag"):
            parts.append("actively seeking")
        
        rate = redrob.get("recruiter_response_rate", 0)
        if rate > 0:
            parts.append(f"response rate {rate:.2f}")
        
        github = redrob.get("github_score", -1)
        if github != -1:
            parts.append(f"GitHub score {github:.0f}")
        
        notice = redrob.get("notice_period_days", -1)
        if notice >= 0:
            parts.append(f"notice {notice:.0f}d")
        
        assessments = redrob.get("skill_assessment_scores", {})
        if assessments:
            avg = sum(assessments.values()) / len(assessments)
            parts.append(f"{len(assessments)} assessments (avg {avg:.0f})")
        
        return "; ".join(parts) if parts else "platform signals available"