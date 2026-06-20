"""
Explainer — Human-friendly reasoning generator.
No tech jargon. Reads like an HR person wrote it.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Explainer:
    """Generate human-friendly reasoning text."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_len = config.get("challenge", {}).get("max_reasoning_length", 150)

    def explain(self, jd_requirements, candidate_profile, scores, final_score):
        """Generate short human-friendly reasoning."""
        parts = []

        title = candidate_profile.get("current_title", "")
        years = candidate_profile.get("experience_years", 0)
        company = candidate_profile.get("current_company", "")

        if title and company:
            parts.append(f"{title} at {company} with {years:.0f} years of experience")
        elif title:
            parts.append(f"{title} with {years:.0f} years")

        jd_skills = set(s.lower() for s in (
            jd_requirements.get("hard_skills", []) +
            jd_requirements.get("must_have_skills", [])
        ))
        candidate_skills = set(s.lower() for s in candidate_profile.get("skills", []))
        if jd_skills:
            matched = sum(
                1 for js in jd_skills
                if any(js in cs or cs in js for cs in candidate_skills)
            )
            if matched == len(jd_skills):
                parts.append(f"has all {matched} required skills")
            elif matched >= len(jd_skills) * 0.7:
                parts.append(f"has {matched} of {len(jd_skills)} required skills")
            else:
                parts.append(f"matches {matched} of {len(jd_skills)} skills")

        redrob = candidate_profile.get("redrob", {})
        if redrob.get("open_to_work_flag"):
            parts.append("actively looking for new role")

        notice = redrob.get("notice_period_days", -1)
        if 0 <= notice <= 15:
            parts.append("can start immediately")
        elif 0 < notice <= 30:
            parts.append(f"available in {notice:.0f} days")

        rate = redrob.get("recruiter_response_rate", 0)
        if rate >= 0.7:
            parts.append("responds quickly to recruiters")

        github = redrob.get("github_score", -1)
        if github >= 70:
            parts.append("active on GitHub")

        reasoning = ". ".join(filter(None, parts)) + "."

        if len(reasoning) > self.max_len:
            reasoning = reasoning[: self.max_len - 3] + "..."

        return reasoning

    def explain_detailed(self, jd_requirements, candidate_profile, scores, final_score):
        """Longer human-friendly explanation for detail view."""
        parts = []

        if final_score >= 0.80:
            parts.append("Excellent match for this role.")
        elif final_score >= 0.65:
            parts.append("Strong candidate for this position.")
        elif final_score >= 0.45:
            parts.append("Potential match worth reviewing.")
        else:
            parts.append("Weak match for this role.")

        sem = scores.get("semantic_fit", 0)
        if sem >= 0.80:
            parts.append("Their background closely aligns with the role.")
        elif sem >= 0.60:
            parts.append("Good overall alignment with the role.")
        elif sem >= 0.40:
            parts.append("Some alignment with the role.")

        jd_skills = list(jd_requirements.get("hard_skills", []))
        c_skills = candidate_profile.get("skills", [])
        if jd_skills:
            matched = [
                s for s in jd_skills
                if any(s.lower() in cs.lower() or cs.lower() in s.lower()
                       for cs in c_skills)
            ]
            missing = [s for s in jd_skills if s not in matched]
            if matched:
                parts.append(f"Has {len(matched)} of {len(jd_skills)} needed skills.")
            if missing and len(missing) <= 3:
                parts.append(f"Missing: {', '.join(missing)}.")

        years = candidate_profile.get("experience_years", 0)
        exp_range = jd_requirements.get("experience_range", (0, 99))
        if exp_range[1] < 99:
            if exp_range[0] <= years <= exp_range[1]:
                parts.append(f"Experience level ({years:.0f} years) fits perfectly.")
            elif years < exp_range[0]:
                parts.append(f"Less experience than needed ({years:.0f} vs {exp_range[0]} years).")
            else:
                parts.append(f"More experience than needed ({years:.0f} years).")

        redrob = candidate_profile.get("redrob", {})
        if redrob.get("open_to_work_flag"):
            parts.append("Actively looking for opportunities.")

        notice = redrob.get("notice_period_days", -1)
        if 0 <= notice <= 15:
            parts.append(f"Can start almost immediately ({notice:.0f} days).")
        elif notice <= 45:
            parts.append(f"Available within {notice:.0f} days.")

        anomalies = scores.get("anomaly_flags", [])
        flag_descriptions = {
            "very_sparse_profile": "Profile lacks detail.",
            "experience_seniority_mismatch": "Title and experience don't match.",
            "excessive_skill_claims": "Unusually many skills listed.",
            "possible_keyword_stuffing": "Profile may have keyword stuffing.",
            "generic_template_profile": "Profile reads like a template.",
            "unrealistic_experience_claim": "Experience claim seems unrealistic.",
        }
        for flag in anomalies:
            desc = flag_descriptions.get(flag, flag.replace("_", " "))
            parts.append(f"Note: {desc}")

        return " ".join(parts)