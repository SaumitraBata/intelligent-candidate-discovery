"""
Candidate Profiler
Transforms raw candidate data into rich, structured profiles.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.utils import normalize_text, safe_float

logger = logging.getLogger(__name__)


class CandidateProfiler:
    """Extract and enrich candidate profile features."""

    # Column name mapping — handles various naming conventions
    COLUMN_ALIASES = {
        "candidate_id": ["candidate_id", "id", "candidateid", "cand_id", "profile_id", "user_id"],
        "name": ["name", "full_name", "fullname", "candidate_name"],
        "current_title": ["current_title", "title", "job_title", "position", "designation",
                          "current_role", "role"],
        "summary": ["summary", "bio", "about", "profile_summary", "description",
                     "headline", "professional_summary", "about_me"],
        "skills": ["skills", "skill_set", "skillset", "technologies", "tech_stack",
                    "competencies", "key_skills", "technical_skills"],
        "experience_years": ["experience_years", "years_of_experience", "total_experience",
                             "yoe", "experience", "exp_years", "years_experience",
                             "total_years_experience"],
        "education": ["education", "degree", "qualification", "academic",
                      "education_level", "highest_education"],
        "location": ["location", "city", "country", "region", "address"],
        "certifications": ["certifications", "certificates", "certs"],
        "last_active": ["last_active", "last_activity", "last_login", "last_seen",
                        "activity_date", "last_updated", "updated_at"],
        "profile_views": ["profile_views", "views", "view_count"],
        "applications": ["applications", "applied_count", "jobs_applied",
                         "application_count"],
        "companies": ["companies", "previous_companies", "company", "employer",
                      "organization", "organisations", "current_company"],
        "industry": ["industry", "domain", "sector", "field"],
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def profile_all(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        """Profile all candidates from a DataFrame."""
        # Resolve column mappings
        column_map = self._resolve_columns(df)
        logger.debug(f"  Column mapping: {column_map}")

        profiles = {}
        for idx, row in df.iterrows():
            cid = self._get_value(row, column_map, "candidate_id", default=f"candidate_{idx}")
            cid = str(cid)

            profile = self._extract_profile(row, column_map, cid)
            profiles[cid] = profile

        logger.info(f"  Profiled {len(profiles)} candidates")
        return profiles

    def _resolve_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Map canonical field names to actual DataFrame column names."""
        column_map = {}
        df_cols_lower = {c.lower().strip(): c for c in df.columns}

        for canonical, aliases in self.COLUMN_ALIASES.items():
            mapped = None
            for alias in aliases:
                if alias.lower() in df_cols_lower:
                    mapped = df_cols_lower[alias.lower()]
                    break
            column_map[canonical] = mapped

        # Also capture any unmapped columns for later use
        mapped_cols = set(v for v in column_map.values() if v is not None)
        column_map["_extra_columns"] = [c for c in df.columns if c not in mapped_cols]

        return column_map

    def _get_value(self, row, column_map, field, default=None):
        """Safely get a value from a row using the column map."""
        col = column_map.get(field)
        if col is None:
            return default
        val = row.get(col, default)
        if pd.isna(val):
            return default
        return val

    def _extract_profile(self, row, column_map: Dict, cid: str) -> Dict[str, Any]:
        """Extract a complete profile from a single row."""
        profile = {
            "candidate_id": cid,
            "name": self._get_value(row, column_map, "name", ""),
            "current_title": normalize_text(
                str(self._get_value(row, column_map, "current_title", ""))
            ),
            "summary": normalize_text(
                str(self._get_value(row, column_map, "summary", ""))
            ),
            "skills": self._parse_skills(
                self._get_value(row, column_map, "skills", "")
            ),
            "experience_years": self._parse_experience_years(
                self._get_value(row, column_map, "experience_years", 0)
            ),
            "education": normalize_text(
                str(self._get_value(row, column_map, "education", ""))
            ),
            "location": str(self._get_value(row, column_map, "location", "")),
            "certifications": self._parse_list_field(
                self._get_value(row, column_map, "certifications", "")
            ),
            "companies": self._parse_list_field(
                self._get_value(row, column_map, "companies", "")
            ),
            "industry": str(self._get_value(row, column_map, "industry", "")),
        }

        # Behavioral signals
        profile["last_active"] = self._parse_date(
            self._get_value(row, column_map, "last_active")
        )
        profile["profile_views"] = safe_float(
            self._get_value(row, column_map, "profile_views", 0)
        )
        profile["applications"] = safe_float(
            self._get_value(row, column_map, "applications", 0)
        )

        # Extract experience descriptions from any extra text columns
        profile["experience_descriptions"] = self._extract_experience_descriptions(
            row, column_map
        )

        # Derived features
        profile["seniority_level"] = self._infer_seniority(profile)
        profile["profile_completeness"] = self._calculate_completeness(profile)
        profile["skill_count"] = len(profile["skills"])

        return profile

    def _parse_skills(self, raw_skills) -> List[str]:
        """Parse skills from various formats."""
        if not raw_skills or (isinstance(raw_skills, float) and np.isnan(raw_skills)):
            return []

        raw_skills = str(raw_skills)

        # Handle list-like strings: "[skill1, skill2]" or "skill1; skill2"
        raw_skills = raw_skills.strip("[](){}")
        raw_skills = raw_skills.replace("'", "").replace('"', "")

        # Split on common delimiters
        skills = re.split(r"[,;|/\n]+", raw_skills)
        skills = [s.strip().lower() for s in skills if s.strip() and len(s.strip()) > 1]

        return list(set(skills))

    def _parse_experience_years(self, raw) -> float:
        """Parse years of experience from various formats."""
        if raw is None:
            return 0.0

        val = safe_float(raw, -1)
        if val >= 0:
            return min(val, 50)  # Cap at 50 years

        # Try to extract from string
        text = str(raw)
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            return min(float(match.group(1)), 50)

        return 0.0

    def _parse_date(self, raw) -> Optional[datetime]:
        """Parse date from various formats."""
        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            return None

        if isinstance(raw, datetime):
            return raw

        if isinstance(raw, pd.Timestamp):
            return raw.to_pydatetime()

        date_formats = [
            "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y",
        ]

        raw_str = str(raw).strip()
        for fmt in date_formats:
            try:
                return datetime.strptime(raw_str, fmt)
            except ValueError:
                continue

        # Try pandas parsing
        try:
            return pd.to_datetime(raw_str).to_pydatetime()
        except Exception:
            return None

    def _parse_list_field(self, raw) -> List[str]:
        """Parse a list-like field."""
        if not raw or (isinstance(raw, float) and np.isnan(raw)):
            return []

        raw = str(raw).strip("[](){}")
        raw = raw.replace("'", "").replace('"', "")
        items = re.split(r"[,;|/\n]+", raw)
        return [i.strip() for i in items if i.strip()]

    def _extract_experience_descriptions(self, row, column_map) -> List[str]:
        """Extract any experience description text from extra columns."""
        descriptions = []
        extra_cols = column_map.get("_extra_columns", [])

        for col in extra_cols:
            val = row.get(col)
            if val and isinstance(val, str) and len(val) > 30:
                descriptions.append(val)

        # Also use summary if available
        summary = self._get_value(row, column_map, "summary", "")
        if summary and isinstance(summary, str) and len(summary) > 20:
            descriptions.insert(0, summary)

        return descriptions

    def _infer_seniority(self, profile: Dict) -> str:
        """Infer seniority level from title and experience."""
        title = profile.get("current_title", "").lower()
        years = profile.get("experience_years", 0)

        # Title-based detection
        seniority_keywords = {
            "c-level": ["cto", "ceo", "cio", "cdo", "chief", "co-founder", "founder"],
            "vp": ["vice president", "vp"],
            "director": ["director"],
            "principal": ["principal", "staff", "distinguished"],
            "lead": ["lead", "team lead", "tech lead", "architect"],
            "senior": ["senior", "sr.", "sr "],
            "mid": ["mid", "intermediate"],
            "junior": ["junior", "jr.", "jr ", "associate"],
            "intern": ["intern", "trainee", "apprentice"],
        }

        for level, keywords in seniority_keywords.items():
            if any(kw in title for kw in keywords):
                return level

        # Fall back to experience-based
        if years >= 15:
            return "principal"
        elif years >= 10:
            return "lead"
        elif years >= 6:
            return "senior"
        elif years >= 3:
            return "mid"
        elif years >= 1:
            return "junior"
        else:
            return "intern"

    def _calculate_completeness(self, profile: Dict) -> float:
        """Calculate profile completeness score (0-1)."""
        fields_weights = {
            "current_title": 0.15,
            "summary": 0.15,
            "skills": 0.20,
            "experience_years": 0.15,
            "education": 0.10,
            "companies": 0.10,
            "certifications": 0.05,
            "location": 0.05,
            "industry": 0.05,
        }

        score = 0.0
        for field, weight in fields_weights.items():
            val = profile.get(field)
            if val:
                if isinstance(val, list) and len(val) > 0:
                    score += weight
                elif isinstance(val, str) and len(val.strip()) > 0:
                    score += weight
                elif isinstance(val, (int, float)) and val > 0:
                    score += weight

        return min(score, 1.0)