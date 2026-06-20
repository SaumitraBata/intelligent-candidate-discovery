"""
Data Loader
Reads candidates.jsonl with smart caching.
- Detects new candidates and only processes those
- Skips already-processed candidates  
- Works on any system from fresh install
"""

import json
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from tqdm import tqdm

logger = logging.getLogger(__name__)


class CandidateDataLoader:
    """Loads candidate data with smart incremental caching."""

    SENTINEL_VALUES = {-1, "-1", None}

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dataset_dir = Path(config["paths"]["dataset_dir"])
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.profiles_cache = self.cache_dir / "processed_profiles.pkl"
        self.profiles_meta = self.cache_dir / "profiles_meta.json"

    # ──────────────────────────────────────────────────────────────────
    # FAST LOADER (skips JSONL when cache is valid)
    # ──────────────────────────────────────────────────────────────────

    def load_smart(self, use_sample: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        SMART loader — skips JSONL reading entirely when cache is valid.
        Only reads the raw file if cache is missing or stale.
        """
        if not (self.profiles_cache.exists() and self.profiles_meta.exists()):
            logger.info("  No cache — loading from JSONL...")
            raw = self.load_candidates(use_sample=use_sample)
            return self.smart_process(raw)

        try:
            with open(self.profiles_meta, "r") as f:
                meta = json.load(f)
            cached_count = meta.get("count", 0)

            path = self.dataset_dir / (
                self.config["paths"]["sample_candidates_file"] if use_sample
                else self.config["paths"]["candidates_file"]
            )

            if use_sample:
                raw = self.load_candidates(use_sample=True)
                return self.smart_process(raw)

            with open(path, "r", encoding="utf-8") as f:
                line_count = sum(1 for line in f if line.strip())

            if line_count == cached_count:
                logger.info(f"  Cache valid — {cached_count} profiles loaded from disk")
                with open(self.profiles_cache, "rb") as f:
                    return pickle.load(f)

            logger.info(
                f"  Cache size mismatch ({cached_count} cached vs {line_count} in file) — reloading"
            )
            raw = self.load_candidates(use_sample=use_sample)
            return self.smart_process(raw)

        except Exception as e:
            logger.warning(f"  Cache check failed: {e} — full reload")
            raw = self.load_candidates(use_sample=use_sample)
            return self.smart_process(raw)

    def load_candidates(self, use_sample: bool = False) -> List[Dict[str, Any]]:
        """Load all candidates from JSONL or sample JSON."""
        if use_sample:
            path = self.dataset_dir / self.config["paths"]["sample_candidates_file"]
            candidates = self._load_json_array(path)
        else:
            path = self.dataset_dir / self.config["paths"]["candidates_file"]
            candidates = self._load_jsonl(path)
        logger.info(f"  Loaded {len(candidates)} candidates from {path.name}")
        return candidates

    def smart_process(
        self, raw_candidates: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Smart processing with incremental cache."""
        current_ids = set(c.get("candidate_id") for c in raw_candidates if c.get("candidate_id"))
        current_hash = self._hash_id_set(current_ids)

        cached_profiles, cached_ids_hash = self._load_profile_cache()

        if cached_profiles and cached_ids_hash == current_hash:
            logger.info(f"  Cache valid — loaded {len(cached_profiles)} profiles instantly")
            return cached_profiles

        if cached_profiles:
            cached_ids = set(cached_profiles.keys())
            new_ids = current_ids - cached_ids
            removed_ids = cached_ids - current_ids

            if not new_ids and not removed_ids:
                logger.info("  Data content changed — full reprocess")
                return self._process_and_cache(raw_candidates, current_hash)

            logger.info(
                f"  Incremental update: {len(new_ids)} new, {len(removed_ids)} removed, "
                f"{len(cached_ids & current_ids)} unchanged"
            )

            for rid in removed_ids:
                cached_profiles.pop(rid, None)

            if new_ids:
                new_candidates = [c for c in raw_candidates if c.get("candidate_id") in new_ids]
                new_profiles = self._process_batch(new_candidates)
                cached_profiles.update(new_profiles)

            self._save_profile_cache(cached_profiles, current_hash)
            logger.info(f"  Updated cache — {len(cached_profiles)} total profiles")
            return cached_profiles

        logger.info("  No cache found — processing all candidates (one-time)")
        return self._process_and_cache(raw_candidates, current_hash)

    def process_all(self, raw_candidates):
        """Legacy alias — routes through smart_process."""
        return self.smart_process(raw_candidates)

    # ──────────────────────────────────────────────────────────────────
    # PROFILE EXTRACTION
    # ──────────────────────────────────────────────────────────────────

    def extract_profile_features(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and flatten all features from a raw candidate dict."""
        cid = candidate.get("candidate_id", "UNKNOWN")
        profile_raw = candidate.get("profile", {})
        career_history = candidate.get("career_history", [])
        education_list = candidate.get("education", [])
        skills_list = candidate.get("skills", [])
        certifications = candidate.get("certifications", [])
        languages = candidate.get("languages", [])
        redrob = candidate.get("redrob_signals", {})

        profile = {
            "candidate_id": cid,
            "name": profile_raw.get("anonymized_name", ""),
            "headline": profile_raw.get("headline", ""),
            "summary": profile_raw.get("summary", ""),
            "current_title": profile_raw.get("current_title", ""),
            "current_company": profile_raw.get("current_company", ""),
            "current_company_size": profile_raw.get("current_company_size", ""),
            "current_industry": profile_raw.get("current_industry", ""),
            "location": profile_raw.get("location", ""),
            "country": profile_raw.get("country", ""),
            "experience_years": float(profile_raw.get("years_of_experience", 0) or 0),
        }

        profile["skills"] = [
            s.get("name", "").lower().strip()
            for s in skills_list if s.get("name")
        ]
        profile["advanced_skills"] = [
            s.get("name", "").lower().strip()
            for s in skills_list
            if s.get("proficiency") in ("expert", "advanced")
        ]
        profile["skills_with_proficiency"] = {
            s.get("name", "").lower(): s.get("proficiency", "intermediate")
            for s in skills_list if s.get("name")
        }
        profile["skill_assessment_scores"] = redrob.get("skill_assessment_scores", {}) or {}
        profile["skill_count"] = len(profile["skills"])

        profile["career_history"] = career_history
        profile["companies"] = [j.get("company", "") for j in career_history if j.get("company")]
        profile["all_titles"] = [j.get("title", "") for j in career_history if j.get("title")]
        profile["all_company_sizes"] = [
            j.get("company_size", "") for j in career_history if j.get("company_size")
        ]

        current_job = next((j for j in career_history if j.get("is_current") is True), None)
        if current_job:
            profile["current_job_description"] = current_job.get("description", "")
            profile["current_industry"] = current_job.get("industry", profile["current_industry"])
        else:
            profile["current_job_description"] = ""

        profile["experience_descriptions"] = [
            j.get("description", "") for j in career_history if j.get("description")
        ]

        profile["education_list"] = education_list
        best_edu, best_tier, best_degree_rank = "", "unknown", 0
        degree_order = {
            "phd": 5, "doctorate": 5,
            "master": 4, "mba": 4, "m.tech": 4, "msc": 4, "m.s.": 4,
            "bachelor": 3, "b.tech": 3, "b.e.": 3, "b.sc": 3,
            "diploma": 2, "associate": 2,
            "high school": 1,
        }
        for edu in education_list:
            degree = edu.get("degree", "").lower()
            for deg_key, deg_rank in degree_order.items():
                if deg_key in degree and deg_rank > best_degree_rank:
                    best_degree_rank = deg_rank
                    best_edu = edu.get("degree", "")
                    best_tier = edu.get("tier", "unknown")
                    break

        profile["education"] = best_edu
        profile["education_tier"] = best_tier
        profile["education_fields"] = [
            e.get("field_of_study", "").lower() for e in education_list if e.get("field_of_study")
        ]

        profile["certifications"] = [c.get("name", "") for c in certifications if c.get("name")]
        profile["languages"] = [
            f"{l.get('language', '')} ({l.get('proficiency', '')})" for l in languages
        ]

        profile["redrob"] = self._extract_redrob_signals(redrob)
        profile["seniority_level"] = self._infer_seniority(profile)
        profile["profile_completeness"] = profile["redrob"]["profile_completeness_score"] / 100.0
        profile["company_prestige_score"] = self._calc_company_prestige(profile)
        # Keep raw skills data for anomaly detection
        profile["skills_raw"] = skills_list  # Original skill objects with proficiency + duration        

        return profile

    def _calc_company_prestige(self, profile: Dict) -> float:
        """Score 0-1 based on company size (validation signal)."""
        size_scores = {
            "1-10": 0.30,
            "11-50": 0.40,
            "51-200": 0.55,
            "201-500": 0.65,
            "501-1000": 0.72,
            "1001-5000": 0.80,
            "5001-10000": 0.88,
            "10001+": 0.95,
        }
        current_size = profile.get("current_company_size", "")
        current_score = size_scores.get(current_size, 0.50)
        past_scores = [size_scores.get(s, 0.5) for s in profile.get("all_company_sizes", [])]
        avg_past = sum(past_scores) / len(past_scores) if past_scores else 0.5
        return 0.65 * current_score + 0.35 * avg_past

    def _extract_redrob_signals(self, redrob: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and clean all redrob platform signals."""
        def safe_float(val, default=0.0, min_val=None, max_val=None):
            try:
                v = float(val)
                if min_val is not None: v = max(min_val, v)
                if max_val is not None: v = min(max_val, v)
                return v
            except (TypeError, ValueError):
                return default

        def safe_bool(val, default=False):
            if isinstance(val, bool): return val
            if isinstance(val, str): return val.lower() in ("true", "yes", "1")
            return default

        profile_completeness = safe_float(redrob.get("profile_completeness_score"), 50.0, 0, 100)
        open_to_work = safe_bool(redrob.get("open_to_work_flag"), False)
        response_rate = safe_float(redrob.get("recruiter_response_rate"), 0.0, 0, 1)
        avg_response_hours = safe_float(redrob.get("avg_response_time_hours"), 48.0, 0)
        notice_period = safe_float(redrob.get("notice_period_days"), 60.0, 0, 180)

        salary_raw = redrob.get("expected_salary_range_inr_lpa", {}) or {}
        salary_min = safe_float(salary_raw.get("min"), 0.0, 0)
        salary_max = safe_float(salary_raw.get("max"), 0.0, 0)
        if salary_min > salary_max and salary_max > 0:
            salary_min, salary_max = salary_max, salary_min

        work_mode = redrob.get("preferred_work_mode", "flexible")
        github_raw = redrob.get("github_activity_score", -1)
        github_score = safe_float(github_raw, -1)
        github_available = (github_score != -1)

        skill_assessments = redrob.get("skill_assessment_scores", {}) or {}
        skill_assessments = {
            k: safe_float(v, 0, 0, 100)
            for k, v in skill_assessments.items() if k and v is not None
        }

        verified_email = safe_bool(redrob.get("verified_email"), False)
        verified_phone = safe_bool(redrob.get("verified_phone"), False)
        linkedin_connected = safe_bool(redrob.get("linkedin_connected"), False)

        offer_rate_raw = redrob.get("offer_acceptance_rate", -1)
        offer_rate = safe_float(offer_rate_raw, -1)
        offer_rate_available = (offer_rate != -1)

        total_applications = safe_float(redrob.get("total_applications_on_platform"), 0, 0)
        interview_conversion = safe_float(redrob.get("interview_conversion_rate"), 0.0, 0, 1)
        ai_readiness_score = safe_float(redrob.get("ai_readiness_score"), 0.0, 0, 100)

        return {
            "profile_completeness_score": profile_completeness,
            "open_to_work_flag": open_to_work,
            "recruiter_response_rate": response_rate,
            "avg_response_time_hours": avg_response_hours,
            "notice_period_days": notice_period,
            "preferred_work_mode": work_mode,
            "salary_min_lpa": salary_min,
            "salary_max_lpa": salary_max,
            "salary_mid_lpa": (salary_min + salary_max) / 2 if salary_max > 0 else 0,
            "salary_data_valid": salary_max >= salary_min and salary_max > 0,
            "github_score": github_score,
            "github_available": github_available,
            "github_normalized": github_score / 100.0 if github_available else None,
            "skill_assessment_scores": skill_assessments,
            "skill_assessment_count": len(skill_assessments),
            "avg_skill_assessment": (
                sum(skill_assessments.values()) / len(skill_assessments)
                if skill_assessments else 0.0
            ),
            "verified_email": verified_email,
            "verified_phone": verified_phone,
            "linkedin_connected": linkedin_connected,
            "verification_count": sum([verified_email, verified_phone, linkedin_connected]),
            "offer_acceptance_rate": offer_rate,
            "offer_rate_available": offer_rate_available,
            "total_applications": total_applications,
            "interview_conversion_rate": interview_conversion,
            "last_active_str": redrob.get("last_active_on_platform"),
            "ai_readiness_score": ai_readiness_score,
        }

    def _infer_seniority(self, profile: Dict) -> str:
        """Infer seniority with company-size validation."""
        title = profile.get("current_title", "").lower()
        years = profile.get("experience_years", 0)
        company_size = profile.get("current_company_size", "")

        seniority_keywords = {
            "c-level": ["cto", "ceo", "cio", "cdo", "chief", "co-founder", "founder"],
            "vp": ["vice president", "vp of", "vp,"],
            "director": ["director"],
            "principal": ["principal", "staff engineer", "distinguished"],
            "lead": ["lead", "team lead", "tech lead", "engineering manager", "architect"],
            "senior": ["senior", "sr."],
            "mid": ["mid-level", "intermediate"],
            "junior": ["junior", "jr.", "associate", "graduate"],
            "intern": ["intern", "trainee"],
        }

        title_level = None
        for level, keywords in seniority_keywords.items():
            if any(kw in title for kw in keywords):
                title_level = level
                break

        # Adjust for company size
        if title_level == "c-level" and company_size in ("1-10",) and years < 5:
            return "senior" if years >= 3 else "mid"
        if title_level == "vp" and company_size in ("1-10", "11-50") and years < 8:
            return "lead"
        if title_level == "director" and company_size == "1-10" and years < 6:
            return "senior"

        if title_level:
            return title_level

        if years >= 15: return "principal"
        if years >= 10: return "lead"
        if years >= 6: return "senior"
        if years >= 3: return "mid"
        if years >= 1: return "junior"
        return "intern"

    # ──────────────────────────────────────────────────────────────────
    # CACHE
    # ──────────────────────────────────────────────────────────────────

    def _process_batch(self, candidates: List[Dict]) -> Dict[str, Dict[str, Any]]:
        profiles = {}
        errors = 0
        for candidate in tqdm(candidates, desc="Processing candidates"):
            try:
                cid = candidate.get("candidate_id", "UNKNOWN")
                profiles[cid] = self.extract_profile_features(candidate)
            except Exception as e:
                errors += 1
                logger.debug(f"  Error processing {candidate.get('candidate_id')}: {e}")
        if errors > 0:
            logger.warning(f"  {errors} candidates had processing errors")
        logger.info(f"  Processed {len(profiles)} candidate profiles")
        return profiles

    def _process_and_cache(
        self, raw_candidates: List[Dict], ids_hash: str
    ) -> Dict[str, Dict[str, Any]]:
        profiles = self._process_batch(raw_candidates)
        self._save_profile_cache(profiles, ids_hash)
        return profiles

    def _save_profile_cache(self, profiles: Dict, ids_hash: str):
        try:
            with open(self.profiles_cache, "wb") as f:
                pickle.dump(profiles, f, protocol=pickle.HIGHEST_PROTOCOL)
            meta = {
                "count": len(profiles),
                "ids_hash": ids_hash,
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.profiles_meta, "w") as f:
                json.dump(meta, f)
            logger.info(f"  Cached {len(profiles)} profiles for fast restart")
        except Exception as e:
            logger.warning(f"  Could not save cache: {e}")

    def _load_profile_cache(self) -> tuple:
        if not (self.profiles_cache.exists() and self.profiles_meta.exists()):
            return None, None
        try:
            with open(self.profiles_meta, "r") as f:
                meta = json.load(f)
            with open(self.profiles_cache, "rb") as f:
                profiles = pickle.load(f)
            return profiles, meta.get("ids_hash", "")
        except Exception as e:
            logger.warning(f"  Cache corrupted: {e}")
            return None, None

    def _hash_id_set(self, ids: set) -> str:
        sorted_ids = "|".join(sorted(ids))
        return hashlib.md5(sorted_ids.encode()).hexdigest()[:16]

    def _load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        candidates = []
        errors = 0
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        logger.info(f"  Reading {len(lines)} lines from {path.name}...")
        for line_num, line in enumerate(tqdm(lines, desc="Loading candidates"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                candidates.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors += 1
                logger.debug(f"  Line {line_num} parse error: {e}")
        if errors > 0:
            logger.warning(f"  {errors} lines failed to parse")
        return candidates

    def _load_json_array(self, path: Path) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array in {path.name}, got {type(data)}")
        return data