"""
Universal Candidate Data Converter
Converts any supported format into challenge JSONL format.

Supports:
  CSV (.csv)
  JSON (.json) — both arrays and nested objects
  JSONL (.jsonl)
  Excel (.xlsx, .xls)
  TSV (.tsv)

Smart column mapping:
  Auto-detects common field names (e.g., "Full Name", "name", "candidate_name")
  Handles missing fields gracefully with sensible defaults
  Reports unmapped columns so you can review

How to Use:

Convert a CSV:
python convert_to_jsonl.py --input my_candidates.csv

Convert Excel:
python convert_to_jsonl.py --input candidates.xlsx --output new_data.jsonl

Convert JSON (from LinkedIn export, ATS export, etc.):
python convert_to_jsonl.py --input linkedin_export.json

Convert with custom starting ID (to append to existing dataset):
# If you already have 100,000 candidates and want to add more:
python convert_to_jsonl.py --input new_batch.csv --start-id 100001

"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# SMART COLUMN MAPPING
# ══════════════════════════════════════════════════════════════════════

COLUMN_ALIASES = {
    "name": [
        "name", "full_name", "fullname", "candidate_name", "person_name",
        "applicant_name", "first_name", "anonymized_name",
    ],
    "headline": [
        "headline", "tagline", "professional_headline", "linkedin_headline",
        "bio", "tag_line",
    ],
    "summary": [
        "summary", "about", "bio", "description", "profile_summary",
        "about_me", "introduction", "overview",
    ],
    "current_title": [
        "current_title", "title", "job_title", "position", "designation",
        "current_role", "role", "current_position", "job_role",
    ],
    "current_company": [
        "current_company", "company", "employer", "organization",
        "company_name", "current_employer", "workplace", "current_organization",
    ],
    "current_company_size": [
        "company_size", "current_company_size", "employees", "team_size",
        "organization_size", "company_employees",
    ],
    "current_industry": [
        "industry", "current_industry", "sector", "domain", "field",
        "company_industry",
    ],
    "location": [
        "location", "city", "address", "current_location", "based_in",
        "where", "place",
    ],
    "country": [
        "country", "nation", "country_name", "residence_country",
    ],
    "years_of_experience": [
        "years_of_experience", "experience_years", "years_exp", "yoe",
        "total_experience", "exp_years", "experience", "years",
    ],
    "skills": [
        "skills", "skill_set", "skillset", "technologies", "tech_stack",
        "competencies", "key_skills", "technical_skills", "expertise",
    ],
    "education": [
        "education", "degree", "qualification", "academic_background",
        "highest_education", "education_level",
    ],
    "education_institution": [
        "institution", "school", "university", "college", "alma_mater",
    ],
    "education_field": [
        "field_of_study", "major", "specialization", "stream", "branch",
    ],
    "certifications": [
        "certifications", "certificates", "certs", "credentials",
    ],
    "languages": [
        "languages", "spoken_languages", "language_skills",
    ],
    "open_to_work": [
        "open_to_work", "open_for_work", "looking_for_job", "is_available",
        "actively_looking", "available", "seeking_job",
    ],
    "notice_period_days": [
        "notice_period", "notice_period_days", "notice", "availability_days",
        "joining_time", "notice_days",
    ],
    "salary_min": [
        "salary_min", "min_salary", "expected_salary_min", "salary_from",
        "min_compensation",
    ],
    "salary_max": [
        "salary_max", "max_salary", "expected_salary_max", "salary_to",
        "max_compensation",
    ],
    "preferred_work_mode": [
        "work_mode", "preferred_work_mode", "work_preference",
        "remote_preference", "work_type",
    ],
    "github": [
        "github", "github_url", "github_profile", "github_link",
        "github_username", "github_score", "github_activity",
    ],
    "linkedin": [
        "linkedin", "linkedin_url", "linkedin_profile", "linkedin_link",
    ],
    "email": [
        "email", "email_address", "contact_email", "mail",
    ],
    "phone": [
        "phone", "phone_number", "mobile", "contact_number", "telephone",
    ],
    "verified_email": [
        "verified_email", "email_verified", "is_email_verified",
    ],
    "verified_phone": [
        "verified_phone", "phone_verified", "is_phone_verified",
    ],
    "career_history": [
        "career_history", "work_history", "experience_history",
        "previous_jobs", "employment_history", "work_experience",
    ],
    "candidate_id": [
        "candidate_id", "id", "candidateid", "person_id", "applicant_id",
        "user_id", "profile_id",
    ],
}


# ══════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def safe_str(val, default: str = "") -> str:
    """Convert anything to string safely."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val).strip()


def safe_float(val, default: float = 0.0) -> float:
    """Convert anything to float safely."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    try:
        # Handle strings like "5 years", "$50000", "5.5 yrs"
        if isinstance(val, str):
            cleaned = re.sub(r"[^\d.\-]", "", val)
            return float(cleaned) if cleaned else default
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default: int = 0) -> int:
    """Convert anything to int safely."""
    return int(safe_float(val, default))


def safe_bool(val, default: bool = False) -> bool:
    """Convert anything to bool safely."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.lower().strip() in (
            "true", "yes", "1", "y", "t", "open", "available", "active"
        )
    return default


def normalize_company_size(val) -> str:
    """Normalize company size to challenge enum."""
    valid_sizes = [
        "1-10", "11-50", "51-200", "201-500",
        "501-1000", "1001-5000", "5001-10000", "10001+",
    ]
    s = safe_str(val).lower().replace(" ", "").replace(",", "")

    if s in [v.lower() for v in valid_sizes]:
        for v in valid_sizes:
            if s == v.lower():
                return v

    # Try to parse numeric
    num = safe_int(val, -1)
    if num > 0:
        if num <= 10: return "1-10"
        if num <= 50: return "11-50"
        if num <= 200: return "51-200"
        if num <= 500: return "201-500"
        if num <= 1000: return "501-1000"
        if num <= 5000: return "1001-5000"
        if num <= 10000: return "5001-10000"
        return "10001+"

    # Common keyword mapping
    keywords = {
        "startup": "11-50", "small": "51-200", "medium": "201-500",
        "large": "1001-5000", "enterprise": "10001+", "mnc": "10001+",
        "fortune": "10001+",
    }
    for kw, size in keywords.items():
        if kw in s:
            return size

    return "51-200"  # Sensible default


def normalize_work_mode(val) -> str:
    """Normalize work mode to challenge enum."""
    s = safe_str(val).lower()
    if "remote" in s: return "remote"
    if "hybrid" in s: return "hybrid"
    if "onsite" in s or "office" in s or "in-person" in s: return "onsite"
    return "flexible"


def parse_skills(val) -> List[Dict[str, Any]]:
    """Parse skills from any format into structured list."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []

    skills_list = []

    # Already a list of dicts
    if isinstance(val, list):
        for item in val:
            if isinstance(item, dict):
                skills_list.append({
                    "name": safe_str(item.get("name", item.get("skill", ""))),
                    "proficiency": safe_str(item.get("proficiency", "intermediate")).lower(),
                    "endorsements": safe_int(item.get("endorsements", 0)),
                    "duration_months": safe_int(item.get("duration_months", 12)),
                })
            elif isinstance(item, str):
                skills_list.append(_build_skill(item))
        return [s for s in skills_list if s.get("name")]

    # String — split by delimiters
    text = safe_str(val)
    if not text:
        return []

    # Try to parse as JSON list first
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            return parse_skills(parsed)
        except json.JSONDecodeError:
            pass

    # Split by common delimiters
    text = text.strip("[]{}()")
    parts = re.split(r"[,;|/\n\t]+", text)
    return [_build_skill(p.strip().strip("\"'")) for p in parts if p.strip()]


def _build_skill(name: str) -> Dict[str, Any]:
    """Build a single skill dict."""
    return {
        "name": name,
        "proficiency": "intermediate",
        "endorsements": 0,
        "duration_months": 12,
    }


def parse_career_history(val) -> List[Dict[str, Any]]:
    """Parse career history from various formats."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []

    if isinstance(val, list):
        history = []
        for job in val:
            if isinstance(job, dict):
                history.append({
                    "company": safe_str(job.get("company", "")),
                    "title": safe_str(job.get("title", "")),
                    "start_date": safe_str(job.get("start_date", "")),
                    "end_date": safe_str(job.get("end_date", "")),
                    "duration_months": safe_int(job.get("duration_months", 0)),
                    "is_current": safe_bool(job.get("is_current", False)),
                    "industry": safe_str(job.get("industry", "")),
                    "company_size": normalize_company_size(job.get("company_size", "")),
                    "description": safe_str(job.get("description", "")),
                })
        return history
    return []


def parse_education(val) -> List[Dict[str, Any]]:
    """Parse education from various formats."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []

    if isinstance(val, list):
        education = []
        for edu in val:
            if isinstance(edu, dict):
                education.append({
                    "institution": safe_str(edu.get("institution", "")),
                    "degree": safe_str(edu.get("degree", "")),
                    "field_of_study": safe_str(edu.get("field_of_study", "")),
                    "start_year": safe_int(edu.get("start_year", 0)),
                    "end_year": safe_int(edu.get("end_year", 0)),
                    "grade": safe_str(edu.get("grade", "")),
                    "tier": safe_str(edu.get("tier", "unknown")).lower(),
                })
        return education

    # Single string → single education entry
    text = safe_str(val)
    if text:
        return [{
            "institution": "",
            "degree": text,
            "field_of_study": "",
            "start_year": 0,
            "end_year": 0,
            "grade": "",
            "tier": "unknown",
        }]
    return []


def parse_list_field(val) -> List[str]:
    """Parse a list field (certifications, languages)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return [safe_str(item) for item in val if item]
    text = safe_str(val).strip("[]{}()")
    parts = re.split(r"[,;|/\n]+", text)
    return [p.strip().strip("\"'") for p in parts if p.strip()]


# ══════════════════════════════════════════════════════════════════════
# COLUMN RESOLUTION
# ══════════════════════════════════════════════════════════════════════

def resolve_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """Map canonical field names to actual column names in source data."""
    column_map = {}
    cols_lower = {str(c).lower().strip(): str(c) for c in columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        mapped = None
        for alias in aliases:
            if alias.lower() in cols_lower:
                mapped = cols_lower[alias.lower()]
                break
        column_map[canonical] = mapped

    return column_map


def get_field(row, column_map: Dict, field: str, default=None):
    """Safely extract a field from a row using the column map."""
    col = column_map.get(field)
    if col is None:
        return default

    # Pandas Series or dict-like
    try:
        val = row[col] if hasattr(row, "__getitem__") else getattr(row, col, default)
        if isinstance(val, float) and pd.isna(val):
            return default
        return val
    except (KeyError, AttributeError):
        return default


# ══════════════════════════════════════════════════════════════════════
# FILE LOADERS
# ══════════════════════════════════════════════════════════════════════

def load_source(file_path: Path) -> pd.DataFrame:
    """Load any supported file format into a DataFrame."""
    ext = file_path.suffix.lower()
    logger.info(f"  Detected format: {ext}")

    if ext == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8")
    elif ext == ".tsv":
        df = pd.read_csv(file_path, sep="\t", encoding="utf-8")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Handle different JSON shapes
        if isinstance(data, list):
            df = pd.json_normalize(data, max_level=1)
        elif isinstance(data, dict):
            # If it has a key with the list (e.g., {"candidates": [...]})
            for key in ("candidates", "data", "results", "records", "profiles"):
                if key in data and isinstance(data[key], list):
                    df = pd.json_normalize(data[key], max_level=1)
                    break
            else:
                df = pd.json_normalize([data], max_level=1)
        else:
            raise ValueError(f"Unsupported JSON structure: {type(data)}")
    elif ext == ".jsonl":
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        df = pd.json_normalize(records, max_level=1)
    else:
        raise ValueError(
            f"Unsupported file format: {ext}\n"
            f"Supported: .csv, .tsv, .xlsx, .xls, .json, .jsonl"
        )

    logger.info(f"  Loaded {len(df)} rows with {len(df.columns)} columns")
    return df


# ══════════════════════════════════════════════════════════════════════
# MAIN CONVERSION
# ══════════════════════════════════════════════════════════════════════

def build_candidate(row, column_map: Dict, idx: int, start_id: int) -> Dict[str, Any]:
    """Build a single candidate record from a row."""

    # Use existing ID if present, else generate one
    existing_id = get_field(row, column_map, "candidate_id")
    if existing_id:
        cid = safe_str(existing_id)
        if not cid.startswith("CAND_"):
            cid = f"CAND_{int(safe_float(cid, idx)):07d}"
    else:
        cid = f"CAND_{start_id + idx:07d}"

    # ── Build profile ─────────────────────────────────────────────────
    profile = {
        "anonymized_name": safe_str(get_field(row, column_map, "name")),
        "headline": safe_str(get_field(row, column_map, "headline")),
        "summary": safe_str(get_field(row, column_map, "summary")),
        "current_title": safe_str(get_field(row, column_map, "current_title")),
        "current_company": safe_str(get_field(row, column_map, "current_company")),
        "current_company_size": normalize_company_size(
            get_field(row, column_map, "current_company_size")
        ),
        "current_industry": safe_str(get_field(row, column_map, "current_industry")),
        "location": safe_str(get_field(row, column_map, "location")),
        "country": safe_str(get_field(row, column_map, "country"), "India"),
        "years_of_experience": min(50.0, safe_float(
            get_field(row, column_map, "years_of_experience")
        )),
    }

    # ── Build skills, education, history ──────────────────────────────
    skills = parse_skills(get_field(row, column_map, "skills"))
    career = parse_career_history(get_field(row, column_map, "career_history"))
    education = parse_education(get_field(row, column_map, "education"))
    certs = parse_list_field(get_field(row, column_map, "certifications"))
    languages = parse_list_field(get_field(row, column_map, "languages"))

    # ── Build Redrob signals ──────────────────────────────────────────
    github_val = get_field(row, column_map, "github")
    if github_val is None or safe_str(github_val) == "":
        github_score = -1.0
    elif isinstance(github_val, (int, float)):
        github_score = float(github_val)
    else:
        # If it's a URL/username, assume default score
        github_score = 50.0 if safe_str(github_val) else -1.0

    redrob = {
        "profile_completeness_score": _calc_completeness(profile, skills, education),
        "open_to_work_flag": safe_bool(get_field(row, column_map, "open_to_work")),
        "recruiter_response_rate": 0.5,
        "avg_response_time_hours": 48.0,
        "notice_period_days": min(180, safe_int(
            get_field(row, column_map, "notice_period_days"), 60
        )),
        "expected_salary_range_inr_lpa": {
            "min": safe_float(get_field(row, column_map, "salary_min")),
            "max": safe_float(get_field(row, column_map, "salary_max")),
        },
        "preferred_work_mode": normalize_work_mode(
            get_field(row, column_map, "preferred_work_mode")
        ),
        "github_activity_score": github_score,
        "offer_acceptance_rate": -1.0,
        "verified_email": safe_bool(get_field(row, column_map, "verified_email")),
        "verified_phone": safe_bool(get_field(row, column_map, "verified_phone")),
        "linkedin_connected": bool(safe_str(get_field(row, column_map, "linkedin"))),
        "skill_assessment_scores": {},
        "total_applications_on_platform": 0,
        "interview_conversion_rate": 0.0,
        "last_active_on_platform": datetime.now().strftime("%Y-%m-%d"),
        "ai_readiness_score": 50.0,
    }

    return {
        "candidate_id": cid,
        "profile": profile,
        "career_history": career,
        "education": education,
        "skills": skills,
        "certifications": [{"name": c, "issuer": "", "year": 0} for c in certs],
        "languages": [
            {"language": l, "proficiency": "professional"} for l in languages
        ],
        "redrob_signals": redrob,
    }


def _calc_completeness(profile: Dict, skills: List, education: List) -> float:
    """Estimate profile completeness based on filled fields."""
    score = 0.0
    weights = {
        "current_title": 15, "current_company": 10, "summary": 15,
        "headline": 10, "location": 10, "years_of_experience": 10,
    }
    for field, weight in weights.items():
        val = profile.get(field)
        if val and (not isinstance(val, (int, float)) or val > 0):
            score += weight
    if skills: score += 15
    if education: score += 15
    return min(100.0, score)


def convert(input_path: Path, output_path: Path, start_id: int = 1) -> int:
    """Main conversion entry point."""
    logger.info(f"  Loading source: {input_path.name}")
    df = load_source(input_path)

    logger.info("  Detecting columns...")
    column_map = resolve_columns(df.columns.tolist())

    # Report what was mapped
    mapped_count = sum(1 for v in column_map.values() if v is not None)
    logger.info(f"  Mapped {mapped_count}/{len(COLUMN_ALIASES)} fields:")
    for canonical, source in column_map.items():
        if source:
            logger.info(f"     {canonical:25s} ← {source}")

    # Warn about unmapped important fields
    important = ["name", "current_title", "skills"]
    missing = [f for f in important if not column_map.get(f)]
    if missing:
        logger.warning(f"  Missing important fields: {missing}")
        logger.warning(f"  Available columns: {list(df.columns)}")

    # Convert
    logger.info(f"  Converting {len(df)} candidates...")
    written = 0
    errors = 0

    with open(output_path, "w", encoding="utf-8") as out:
        for idx, row in df.iterrows():
            try:
                candidate = build_candidate(row, column_map, idx, start_id)
                out.write(json.dumps(candidate, ensure_ascii=False) + "\n")
                written += 1
            except Exception as e:
                errors += 1
                logger.debug(f"  Row {idx} error: {e}")

    if errors > 0:
        logger.warning(f"  {errors} rows had errors and were skipped")

    logger.info(f"  Wrote {written} candidates to {output_path.name}")
    return written


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Convert any candidate data format to challenge JSONL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_to_jsonl.py --input candidates.csv
  python convert_to_jsonl.py --input data.xlsx --output my_candidates.jsonl
  python convert_to_jsonl.py --input linkedin_export.json --start-id 100001
""",
    )
    parser.add_argument("--input", "-i", required=True, help="Source file path")
    parser.add_argument(
        "--output", "-o", default="candidates.jsonl",
        help="Output JSONL path (default: candidates.jsonl)"
    )
    parser.add_argument(
        "--start-id", type=int, default=1,
        help="Starting ID number for generated candidate_ids (default: 1)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"  Input file not found: {input_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("  UNIVERSAL CANDIDATE CONVERTER")
    logger.info("=" * 60)

    try:
        count = convert(input_path, output_path, args.start_id)
        logger.info("=" * 60)
        logger.info(f"  SUCCESS — {count} candidates written")
        logger.info(f"  Output: {output_path.absolute()}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"  Conversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()