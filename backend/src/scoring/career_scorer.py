"""
Career Trajectory Scorer
Smart scoring with role-family awareness.
Cross-family roles (Civil Engineer for AI role) get heavily penalized.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CareerScorer:
    """Score candidates with role-family awareness."""

    SENIORITY_LEVELS = {
        "intern": 0, "trainee": 0, "apprentice": 0,
        "junior": 1, "associate": 1, "entry": 1,
        "mid": 2, "intermediate": 2,
        "senior": 3, "sr": 3,
        "lead": 4, "team lead": 4, "tech lead": 4,
        "principal": 5, "staff": 5,
        "director": 6, "head": 6,
        "vp": 7, "vice president": 7,
        "c-level": 8, "cto": 8, "ceo": 8, "cio": 8,
    }

    COMPANY_SIZE_PRESTIGE = {
        "1-10": 0.35,
        "11-50": 0.45,
        "51-200": 0.60,
        "201-500": 0.70,
        "501-1000": 0.78,
        "1001-5000": 0.85,
        "5001-10000": 0.92,
        "10001+": 1.00,
    }

    # Role families — candidates in wrong family get penalized hard
    ROLE_FAMILIES = {
        "engineering_ai_data": [
            "software engineer", "software developer", "developer", "programmer",
            "ml engineer", "ai engineer", "machine learning", "data scientist",
            "data engineer", "data analyst", "ai specialist", "nlp engineer",
            "computer vision", "deep learning", "research engineer",
            "applied scientist", "research scientist", "ai research",
            "ml ops", "mlops", "analytics engineer",
            "backend", "frontend", "fullstack", "full stack", "full-stack",
            "devops", "site reliability", "platform engineer", "cloud engineer",
            "infrastructure", "security engineer", "mobile developer",
            "ios developer", "android developer", "qa engineer", "sdet",
            "test engineer", "automation engineer",
            "tech lead", "engineering manager", "principal engineer",
            "staff engineer", "architect", "solutions architect",
            "cto", "vp engineering", "engineering director",
        ],
        "product_design": [
            "product manager", "product owner", "product designer",
            "ux designer", "ui designer", "ux researcher",
            "design lead", "head of design",
        ],
        "business_ops": [
            "operations manager", "business analyst", "business operations",
            "consultant", "strategy", "ceo", "coo", "founder",
        ],
        "hr_people": [
            "hr manager", "hr executive", "human resources",
            "recruiter", "talent acquisition", "people operations",
            "hr business partner", "hrbp",
        ],
        "sales_marketing": [
            "sales executive", "sales manager", "account executive",
            "business development", "marketing manager", "digital marketing",
            "content marketing", "growth", "marketing executive",
            "smm", "social media", "brand manager",
        ],
        "finance_accounting": [
            "accountant", "finance manager", "financial analyst",
            "chartered accountant", "cfo", "auditor",
        ],
        "physical_engineering": [
            "civil engineer", "mechanical engineer", "electrical engineer",
            "electronics engineer", "chemical engineer", "structural engineer",
            "industrial engineer", "automobile engineer",
        ],
        "creative": [
            "graphic designer", "content writer", "copywriter",
            "video editor", "animator", "illustrator",
        ],
        "support": [
            "customer support", "customer service", "technical support",
            "help desk", "support specialist",
        ],
        "project_mgmt": [
            "project manager", "program manager", "tpm",
            "scrum master", "agile coach",
        ],
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config



    def score(self, jd_requirements, candidate_profile):
        """Generic career scoring without hardcoded role families."""
        scores = []

        seniority_score = self._score_seniority_alignment(jd_requirements, candidate_profile)
        scores.append(("seniority", seniority_score, 0.30))

        prestige_score = self._score_company_prestige(candidate_profile)
        scores.append(("prestige", prestige_score, 0.20))

        growth_score = self._score_growth_velocity(candidate_profile)
        scores.append(("growth", growth_score, 0.20))

        domain_score = self._score_domain_relevance(jd_requirements, candidate_profile)
        scores.append(("domain", domain_score, 0.15))

        title_score = self._score_title_relevance(jd_requirements, candidate_profile)
        scores.append(("title", title_score, 0.15))

        total = sum(s * w for _, s, w in scores)
        total_weight = sum(w for _, _, w in scores)
        return total / total_weight if total_weight > 0 else 0.5



    def _score_role_family(self, jd_req, profile):
        """
        Heavy penalty for cross-family matches.
        Civil Engineer applying for AI Engineer = score 0.10
        """
        candidate_title = profile.get("current_title", "").lower()
        if not candidate_title:
            return 0.3

        # Determine JD's target families from role_keywords + raw_text
        jd_text = (
            jd_req.get("raw_text", "").lower() + " " +
            " ".join(jd_req.get("role_keywords", [])) + " " +
            " ".join(jd_req.get("domain_concepts", []))
        ).lower()

        jd_families = set()
        for family, keywords in self.ROLE_FAMILIES.items():
            for kw in keywords:
                if kw in jd_text:
                    jd_families.add(family)
                    break

        # Determine candidate's family from title
        candidate_family = None
        best_match_len = 0
        for family, keywords in self.ROLE_FAMILIES.items():
            for kw in keywords:
                if kw in candidate_title:
                    if len(kw) > best_match_len:
                        candidate_family = family
                        best_match_len = len(kw)

        # If no JD family detected, neutral score
        if not jd_families:
            return 0.6

        # If no candidate family detected, slight penalty
        if not candidate_family:
            return 0.4

        # Perfect match
        if candidate_family in jd_families:
            return 1.0

        # Adjacent families (semi-compatible)
        compatible_pairs = [
            ("engineering_ai_data", "product_design"),
            ("engineering_ai_data", "project_mgmt"),
            ("product_design", "business_ops"),
            ("sales_marketing", "business_ops"),
        ]
        for f1, f2 in compatible_pairs:
            if (candidate_family == f1 and f2 in jd_families) or \
               (candidate_family == f2 and f1 in jd_families):
                return 0.45

        # Cross-family — heavy penalty
        return 0.10

    def _score_seniority_alignment(self, jd_req, profile):
        jd_seniority = jd_req.get("seniority_level", "mid")
        candidate_seniority = profile.get("seniority_level", "mid")

        jd_level = self.SENIORITY_LEVELS.get(jd_seniority, 2)
        cand_level = self.SENIORITY_LEVELS.get(candidate_seniority, 2)

        company_size = profile.get("current_company_size", "")
        years = profile.get("experience_years", 0)

        if cand_level >= 6 and company_size == "1-10" and years < 5:
            cand_level = max(2, cand_level - 2)
        elif cand_level >= 4 and company_size == "1-10" and years < 3:
            cand_level = max(2, cand_level - 1)

        diff = abs(jd_level - cand_level)

        if diff == 0: return 1.0
        elif diff == 1:
            return 0.85 if cand_level > jd_level else 0.75
        elif diff == 2: return 0.45
        else: return max(0.1, 1.0 - diff * 0.20)

    def _score_company_prestige(self, profile):
        if "company_prestige_score" in profile:
            return profile["company_prestige_score"]

        current_size = profile.get("current_company_size", "")
        current_score = self.COMPANY_SIZE_PRESTIGE.get(current_size, 0.50)

        past_sizes = profile.get("all_company_sizes", [])
        if past_sizes:
            past_scores = [self.COMPANY_SIZE_PRESTIGE.get(s, 0.5) for s in past_sizes]
            avg_past = sum(past_scores) / len(past_scores)
        else:
            avg_past = 0.5

        return 0.65 * current_score + 0.35 * avg_past

    def _score_growth_velocity(self, profile):
        years = profile.get("experience_years", 0)
        seniority = profile.get("seniority_level", "mid")
        level = self.SENIORITY_LEVELS.get(seniority, 2)

        if years <= 0: return 0.5

        if years < 2: expected = 1
        elif years < 5: expected = 2
        elif years < 8: expected = 3
        elif years < 12: expected = 4
        elif years < 16: expected = 5
        else: expected = 6

        if level >= expected + 1: return 0.95
        elif level >= expected: return 0.80
        elif level >= expected - 1: return 0.60
        else: return 0.40

    def _score_domain_relevance(self, jd_req, profile):
        jd_domains = set(d.lower() for d in jd_req.get("industry_domain", []))
        candidate_industry = profile.get("current_industry", "").lower()

        if not jd_domains: return 0.7
        if not candidate_industry: return 0.5

        for domain in jd_domains:
            if domain in candidate_industry or candidate_industry in domain:
                return 1.0

        domain_keywords = set()
        for d in jd_domains:
            domain_keywords.update(d.split("_"))
            domain_keywords.update(d.split())

        industry_keywords = set(candidate_industry.replace("_", " ").split())
        overlap = domain_keywords & industry_keywords
        return 0.7 if overlap else 0.3

    def _score_title_relevance(self, jd_req, profile):
        candidate_title = profile.get("current_title", "").lower()
        if not candidate_title:
            return 0.4

        jd_text = jd_req.get("raw_text", "").lower()
        title_words = set(re.findall(r'\b\w+\b', candidate_title))
        jd_words = set(re.findall(r'\b\w+\b', jd_text))

        stop_words = {"the", "a", "an", "and", "or", "of", "in", "at", "to", "for",
                      "is", "are", "was", "were", "be", "been"}
        title_words -= stop_words
        jd_words -= stop_words

        if not title_words:
            return 0.4

        overlap = title_words & jd_words
        overlap_ratio = len(overlap) / len(title_words)
        return min(1.0, 0.3 + overlap_ratio * 0.7)