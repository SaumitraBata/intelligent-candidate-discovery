"""
Skill Matcher
Importance-weighted skill matching that prioritizes role-defining skills.
"""

import logging
from typing import Dict, List, Any, Set
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class SkillMatcher:
    """Advanced skill matching with importance weighting."""

    SYNONYM_GROUPS = [
        {"python", "python3", "python 3", "cpython"},
        {"javascript", "js", "ecmascript"},
        {"typescript", "ts"},
        {"react", "reactjs", "react.js"},
        {"angular", "angularjs", "angular.js"},
        {"vue", "vuejs", "vue.js"},
        {"node.js", "nodejs", "node"},
        {"c++", "cpp", "c plus plus"},
        {"c#", "csharp", "c sharp"},
        {"golang", "go"},
        {"postgresql", "postgres", "psql"},
        {"mongodb", "mongo"},
        {"kubernetes", "k8s"},
        {"amazon web services", "aws"},
        {"google cloud platform", "gcp", "google cloud"},
        {"microsoft azure", "azure"},
        {"machine learning", "ml"},
        {"deep learning", "dl"},
        {"natural language processing", "nlp"},
        {"artificial intelligence", "ai"},
        {"ci/cd", "cicd", "ci cd", "continuous integration", "continuous deployment"},
        {"docker", "containerization", "containers"},
        {"devops", "dev ops"},
        {"tensorflow", "tf"},
        {"scikit-learn", "sklearn", "scikit learn"},
        {"spring boot", "springboot", "spring-boot"},
        {"ruby on rails", "rails", "ror"},
        {"large language models", "llm", "llms"},
        {"retrieval augmented generation", "rag"},
        {"data engineering", "data eng"},
        {"business intelligence", "bi"},
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fuzzy_threshold = config["skill_matching"]["fuzzy_threshold"]
        self.use_synonyms = config["skill_matching"]["use_synonym_expansion"]

        self.synonym_map = {}
        if self.use_synonyms:
            for group in self.SYNONYM_GROUPS:
                canonical = min(group, key=len)
                for skill in group:
                    self.synonym_map[skill.lower()] = canonical.lower()

    def score(self, jd_requirements: Dict[str, Any],
              candidate_profile: Dict[str, Any]) -> float:
        """
        Importance-weighted skill scoring.
        Matches on critical skills count exponentially more than generic skill matches.
        """
        candidate_skills = set(s.lower() for s in candidate_profile.get("skills", []))
        if not candidate_skills:
            return 0.0

        canonical_candidate_skills = self._canonicalize(candidate_skills)

        must_have = jd_requirements.get("must_have_skills", [])
        nice_to_have = jd_requirements.get("nice_to_have_skills", [])
        soft_skills = jd_requirements.get("soft_skills", [])

        if not must_have and not nice_to_have and not soft_skills:
            return 0.5

        # Get importance scores from JD parser
        importance = jd_requirements.get("skill_importance", {})

        # ── TOP-N CRITICAL SKILLS GATE ──────────────────────────────
        # The top 5 must-have skills (by importance) are the ROLE-DEFINING skills
        # A candidate MUST match at least some of these to be relevant
        top_critical = must_have[:5] if len(must_have) >= 5 else must_have

        critical_matches = self._count_matches(
            top_critical, candidate_skills, canonical_candidate_skills
        )

        # Strict role-relevance gating
        if len(top_critical) >= 3:
            critical_ratio = critical_matches / len(top_critical)
            if critical_ratio == 0:
                # ZERO role-critical skills → candidate is fundamentally irrelevant
                return 0.05  # Near-zero, drops them out of top 100
            elif critical_ratio < 0.2:
                # Only matched 1 of 5+ critical skills → very weak fit
                role_multiplier = 0.25
            elif critical_ratio < 0.4:
                role_multiplier = 0.50
            elif critical_ratio < 0.6:
                role_multiplier = 0.75
            else:
                role_multiplier = 1.00
        else:
            role_multiplier = 1.0

        # ── IMPORTANCE-WEIGHTED MATCHING ────────────────────────────
        must_have_score = self._weighted_match(
            must_have, candidate_skills, canonical_candidate_skills, importance
        ) if must_have else 1.0

        nice_to_have_score = self._weighted_match(
            nice_to_have, candidate_skills, canonical_candidate_skills, importance
        ) if nice_to_have else 0.5

        soft_score = self._match_skill_set(
            soft_skills, candidate_skills, canonical_candidate_skills
        ) if soft_skills else 0.5

        # Heavy weight on must-haves
        total_weight = 0.0
        total_score = 0.0

        if must_have:
            total_score += 0.75 * must_have_score
            total_weight += 0.75
        if nice_to_have:
            total_score += 0.15 * nice_to_have_score
            total_weight += 0.15
        if soft_skills:
            total_score += 0.10 * soft_score
            total_weight += 0.10

        base_score = total_score / total_weight if total_weight > 0 else 0.5

        # Apply role-relevance multiplier
        return max(0.0, min(1.0, base_score * role_multiplier))

    def _count_matches(self, required_skills, candidate_skills, canonical_candidate):
        """Count exact + synonym + substring matches."""
        matches = 0
        for skill in required_skills:
            skill_lower = skill.lower()
            if skill_lower in candidate_skills:
                matches += 1
            elif any(skill_lower in cs or cs in skill_lower for cs in candidate_skills):
                matches += 1
            else:
                canonical = self.synonym_map.get(skill_lower, skill_lower)
                if canonical in canonical_candidate:
                    matches += 1
        return matches

    def _weighted_match(self, required_skills, candidate_skills,
                         canonical_candidate, importance_map):
        """
        Importance-weighted matching.
        High-importance skill matches contribute much more than low-importance ones.
        """
        if not required_skills:
            return 0.5

        total_weight = 0.0
        matched_weight = 0.0

        for skill in required_skills:
            skill_lower = skill.lower()
            # Importance from parser; if not available, default to 1.0
            # IMPORTANT: Square the importance to amplify difference
            raw_weight = importance_map.get(skill, 1.0) if importance_map else 1.0
            weight = max(1.0, raw_weight) ** 1.5  # Amplify importance differences
            total_weight += weight

            # Check for match (exact, substring, synonym, fuzzy)
            matched = False
            match_quality = 0.0

            if skill_lower in candidate_skills:
                match_quality = 1.0
                matched = True
            elif any(skill_lower in cs or cs in skill_lower for cs in candidate_skills):
                match_quality = 0.9
                matched = True
            else:
                canonical = self.synonym_map.get(skill_lower, skill_lower)
                if canonical in canonical_candidate:
                    match_quality = 1.0
                    matched = True
                else:
                    fuzzy_score = self._fuzzy_match(skill_lower, candidate_skills)
                    if fuzzy_score > 0:
                        match_quality = fuzzy_score
                        matched = True

            if matched:
                matched_weight += weight * match_quality

        return matched_weight / total_weight if total_weight > 0 else 0.5

    def _match_skill_set(self, required_skills, candidate_skills, canonical_candidate):
        """Simple unweighted matching (for soft skills)."""
        if not required_skills:
            return 0.5

        matched = 0
        total = len(required_skills)

        for req_skill in required_skills:
            req_lower = req_skill.lower()
            req_canonical = self.synonym_map.get(req_lower, req_lower)

            if req_lower in candidate_skills or req_canonical in canonical_candidate:
                matched += 1
                continue

            if any(req_lower in cs or cs in req_lower for cs in candidate_skills):
                matched += 0.9
                continue

            best_match = self._fuzzy_match(req_lower, candidate_skills)
            if best_match:
                matched += best_match

        return matched / total

    def _fuzzy_match(self, skill: str, candidates: Set[str]) -> float:
        if not candidates:
            return 0.0

        result = process.extractOne(
            skill, list(candidates),
            scorer=fuzz.token_sort_ratio,
            score_cutoff=self.fuzzy_threshold,
        )

        if result:
            match_str, match_score, _ = result
            return 0.5 + (match_score - self.fuzzy_threshold) / \
                   (100 - self.fuzzy_threshold) * 0.5

        return 0.0

    def _canonicalize(self, skills: Set[str]) -> Set[str]:
        canonical = set()
        for skill in skills:
            canonical.add(self.synonym_map.get(skill, skill))
        return canonical