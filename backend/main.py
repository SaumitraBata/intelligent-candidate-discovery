"""
Intelligent Candidate Discovery — FastAPI Backend

Features:
  - BGE-small embeddings (semantic search)
  - Qdrant vector store (scales to millions)
  - 7-signal scoring with company prestige validation
  - Smart incremental caching (only processes new candidates)
  - Config-driven architecture (works on any system)
"""

import os
from pathlib import Path

# Auto-detect if HuggingFace model is cached locally
hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
if hf_cache.exists() and any(hf_cache.iterdir()):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

import csv
import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import aiofiles
import uvicorn
from fastapi import (
    FastAPI, File, Form, HTTPException, UploadFile,
    WebSocket, WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import CandidateDataLoader
from src.embedding_engine import EmbeddingEngine
from src.explainer import Explainer
from src.jd_parser import JDParser
from src.jd_reader import read_jd_docx
from src.ranker import Ranker
from src.scoring.behavioral_scorer import BehavioralScorer
from src.scoring.career_scorer import CareerScorer
from src.scoring.experience_scorer import ExperienceScorer
from src.scoring.quality_scorer import QualityScorer
from src.scoring.redrob_scorer import RedrobSignalsScorer
from src.scoring.score_fusion import ScoreFusion
from src.scoring.semantic_scorer import SemanticScorer
from src.scoring.skill_matcher import SkillMatcher
from src.utils import load_config, setup_logging, get_vector_store

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

CONFIG = load_config("config.yaml")
DATASET_DIR = Path(CONFIG["paths"]["dataset_dir"])
UPLOAD_DIR = Path("uploads")
EXPORT_DIR = Path("exports")
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)
PIPELINE: Dict[str, Any] = {}


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self.active[session_id] = ws

    def disconnect(self, session_id: str):
        self.active.pop(session_id, None)

    async def send(self, session_id: str, data: dict):
        ws = self.active.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.disconnect(session_id)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    logger.info("=" * 60)
    logger.info("  INTELLIGENT CANDIDATE DISCOVERY")
    logger.info("=" * 60)
    start = time.time()

    # 1. Load candidates (smart cache)
    logger.info("\n  [1/4] Loading candidates...")
    loader = CandidateDataLoader(CONFIG)
    candidates_file = DATASET_DIR / CONFIG["paths"]["candidates_file"]
    use_sample = CONFIG.get("challenge", {}).get("use_sample_only", False)
    PIPELINE["candidate_profiles"] = loader.load_smart(use_sample=use_sample)
    logger.info(f"  Ready with {len(PIPELINE['candidate_profiles'])} candidate profiles")

    # 2. Load embedding model
    logger.info("\n  [2/4] Loading embedding model...")
    PIPELINE["embedding_engine"] = EmbeddingEngine(CONFIG)

    # 3. Vector store
    logger.info("\n  [3/4] Initialising vector store...")
    store = get_vector_store(CONFIG)
    PIPELINE["candidate_embeddings"] = store.get_or_compute(
        candidate_profiles=PIPELINE["candidate_profiles"],
        embedding_engine=PIPELINE["embedding_engine"],
        data_file_path=str(candidates_file),
    )
    PIPELINE["vector_store"] = store
    logger.info(
        f"  Vector store ready: "
        f"{store.get_cache_info().get('candidate_count', '?')} vectors"
    )

    # 4. Scorers
    logger.info("\n  [4/4] Initialising scorers...")
    PIPELINE["scorers"] = {
        "semantic":   SemanticScorer(CONFIG),
        "skill":      SkillMatcher(CONFIG),
        "redrob":     RedrobSignalsScorer(CONFIG),
        "career":     CareerScorer(CONFIG),
        "behavioral": BehavioralScorer(CONFIG),
        "experience": ExperienceScorer(CONFIG),
        "quality":    QualityScorer(CONFIG),
    }
    PIPELINE["fusion"] = ScoreFusion(CONFIG)
    PIPELINE["ranker"] = Ranker(CONFIG)
    PIPELINE["explainer"] = Explainer(CONFIG)
    PIPELINE["jd_parser"] = JDParser(CONFIG)

    logger.info(f"\n  Ready in {time.time() - start:.1f}s")
    logger.info("  http://localhost:8000")

    yield

    logger.info("  Shutting down...")
    PIPELINE.clear()


app = FastAPI(
    title="Intelligent Candidate Discovery",
    description="Enterprise-grade candidate ranking system",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 20
    filters: Optional[Dict[str, Any]] = None


class JDTextRequest(BaseModel):
    jd_text: str
    top_k: int = 100
    filters: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


@app.get("/api/health")
async def health():
    store_info = {}
    if "vector_store" in PIPELINE:
        store_info = PIPELINE["vector_store"].get_cache_info()
    return {
        "status": "ok",
        "candidates_loaded": len(PIPELINE.get("candidate_profiles", {})),
        "model": CONFIG["model"]["embedding_model"],
        "vector_backend": CONFIG.get("vector_store", {}).get("backend"),
        "store_info": store_info,
    }


@app.get("/api/cache-info")
async def cache_info():
    store = PIPELINE.get("vector_store")
    if not store:
        raise HTTPException(503, "Store not ready")
    return store.get_cache_info()


@app.delete("/api/cache")
async def clear_cache():
    store = PIPELINE.get("vector_store")
    if not store:
        raise HTTPException(503, "Store not ready")
    store.clear_cache()
    return {"message": "Cache cleared. Restart server to recompute."}


@app.get("/api/stats")
async def stats():
    profiles = PIPELINE.get("candidate_profiles", {})
    if not profiles:
        return {"error": "No data"}
    all_p = list(profiles.values())
    exp_vals = [p.get("experience_years", 0) for p in all_p]
    countries: Dict[str, int] = {}
    seniority: Dict[str, int] = {}
    for p in all_p:
        c = p.get("country", "Unknown")
        countries[c] = countries.get(c, 0) + 1
        s = p.get("seniority_level", "unknown")
        seniority[s] = seniority.get(s, 0) + 1
    return {
        "total_candidates": len(profiles),
        "open_to_work": sum(
            1 for p in all_p
            if p.get("redrob", {}).get("open_to_work_flag")
        ),
        "avg_experience_years": round(
            sum(exp_vals) / max(len(exp_vals), 1), 1
        ),
        "experience_distribution": {
            "0-2 yrs":  sum(1 for e in exp_vals if e <= 2),
            "3-5 yrs":  sum(1 for e in exp_vals if 3 <= e <= 5),
            "6-10 yrs": sum(1 for e in exp_vals if 6 <= e <= 10),
            "10+ yrs":  sum(1 for e in exp_vals if e > 10),
        },
        "top_countries": dict(
            sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]
        ),
        "seniority_distribution": seniority,
        "vector_backend": CONFIG.get("vector_store", {}).get("backend"),
        "embedding_model": CONFIG["model"]["embedding_model"],
    }


@app.post("/api/search")
async def search(request: QueryRequest):
    """Search by plain-English query."""
    _check_ready()
    if not request.query.strip():
        raise HTTPException(400, "Query cannot be empty")
    try:
        t = time.time()
        jd_req = PIPELINE["jd_parser"].parse(request.query)

        jd_emb = PIPELINE["embedding_engine"].embed_query(request.query, jd_req)

        scores = _score_all(jd_emb, jd_req, request.filters)
        fused = PIPELINE["fusion"].fuse(
                scores,
                jd_requirements=jd_req,
                profiles=PIPELINE["candidate_profiles"],
                )
        ranked = PIPELINE["ranker"].rank(
            fused, scores, PIPELINE["candidate_profiles"]
        )[: request.top_k]
        results = _build_results(ranked, scores, jd_req)
        return {
            "query": request.query,
            "total_searched": len(PIPELINE["candidate_profiles"]),
            "returned": len(results),
            "time_seconds": round(time.time() - t, 3),
            "jd_requirements": {
                "hard_skills":      jd_req["hard_skills"],
                "soft_skills":      jd_req["soft_skills"],
                "experience_range": jd_req["experience_range"],
                "seniority_level":  jd_req["seniority_level"],
            },
            "candidates": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@app.post("/api/rank")
async def rank(request: JDTextRequest):
    """Rank all candidates against a full JD text."""
    _check_ready()
    sid = request.session_id or str(uuid.uuid4())
    try:
        t = time.time()
        await _progress(sid, "parsing_jd", 10, "Parsing JD...")
        jd_req = PIPELINE["jd_parser"].parse(request.jd_text)

        await _progress(sid, "embedding", 25, "Embedding JD...")
        jd_emb = PIPELINE["embedding_engine"].embed_jd(
            request.jd_text, jd_req
        )

        await _progress(sid, "scoring", 50, "Scoring candidates...")
        scores = _score_all(jd_emb, jd_req, request.filters)

        await _progress(sid, "ranking", 75, "Ranking...")
        fused = PIPELINE["fusion"].fuse(
                scores,
                jd_requirements=jd_req,
                profiles=PIPELINE["candidate_profiles"],
                )
        ranked = PIPELINE["ranker"].rank(
            fused, scores, PIPELINE["candidate_profiles"]
        )[: request.top_k]

        await _progress(sid, "explaining", 90, "Building results...")
        results = _build_results(ranked, scores, jd_req)

        await _progress(sid, "complete", 100, "Done!")

        return {
            "session_id": sid,
            "total_searched": len(PIPELINE["candidate_profiles"]),
            "returned": len(results),
            "time_seconds": round(time.time() - t, 3),
            "jd_requirements": {
                "hard_skills":      jd_req["hard_skills"],
                "soft_skills":      jd_req["soft_skills"],
                "experience_range": jd_req["experience_range"],
                "seniority_level":  jd_req["seniority_level"],
                "education":        jd_req["education"],
                "industry_domain":  jd_req["industry_domain"],
            },
            "candidates": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rank error: {e}", exc_info=True)
        await _progress(sid, "error", 0, str(e))
        raise HTTPException(500, str(e))


@app.post("/api/upload-jd")
async def upload_jd(
    file: UploadFile = File(...),
    top_k: int = Form(100),
    session_id: str = Form(None),
):
    _check_ready()
    sid = session_id or str(uuid.uuid4())
    if not file.filename.endswith((".docx", ".txt")):
        raise HTTPException(400, "Only .docx and .txt supported")

    fpath = UPLOAD_DIR / f"{sid}_{file.filename}"
    async with aiofiles.open(fpath, "wb") as f:
        await f.write(await file.read())

    try:
        if file.filename.endswith(".docx"):
            jd_text = read_jd_docx(str(fpath))
        else:
            async with aiofiles.open(fpath, "r", encoding="utf-8") as f:
                jd_text = await f.read()
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {e}")

    result = await rank(
        JDTextRequest(jd_text=jd_text, top_k=top_k, session_id=sid)
    )
    result["uploaded_filename"] = file.filename
    result["jd_preview"] = jd_text[:500] + (
        "..." if len(jd_text) > 500 else ""
    )
    return result


@app.post("/api/export")
async def export(candidates: List[Dict[str, Any]]):
    eid = str(uuid.uuid4())[:8]
    path = EXPORT_DIR / f"submission_{eid}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["candidate_id", "rank", "score", "reasoning"],
            quoting=csv.QUOTE_NONNUMERIC,
        )
        w.writeheader()
        for row in candidates:
            w.writerow({
                "candidate_id": row["candidate_id"],
                "rank":         row["rank"],
                "score":        row["final_score"],
                "reasoning":    row.get("reasoning", ""),
            })
    return FileResponse(
        str(path),
        filename=f"submission_{eid}.csv",
        media_type="text/csv",
    )


@app.get("/api/candidate/{candidate_id}")
async def candidate_detail(candidate_id: str):
    profiles = PIPELINE.get("candidate_profiles", {})
    if candidate_id not in profiles:
        raise HTTPException(404, "Candidate not found")
    return _sanitize(profiles[candidate_id])


@app.websocket("/ws/{session_id}")
async def ws(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)


def _check_ready():
    if not PIPELINE or "scorers" not in PIPELINE:
        raise HTTPException(503, "Pipeline not ready")


def _score_all(jd_embedding, jd_requirements, filters=None):
    """Score all candidates using vector search + rule-based scorers."""
    scorers = PIPELINE["scorers"]
    store = PIPELINE["vector_store"]
    profiles = PIPELINE["candidate_profiles"]

    qdrant_filters = _extract_qdrant_filters(filters or {})

    raw_similarities = dict(
        store.search_similar(
            jd_embedding,
            top_k=len(profiles),
            filters=qdrant_filters if qdrant_filters else None,
        )
    )

    all_scores: Dict[str, Dict] = {}
    for cid, profile in profiles.items():
        raw_sim = raw_similarities.get(cid, 0.0)
        all_scores[cid] = {
            "semantic_fit":      scorers["semantic"]._rescale_similarity(raw_sim),
            "skill_match":       scorers["skill"].score(jd_requirements, profile),
            "redrob_signals":    scorers["redrob"].score(profile, jd_requirements),
            "career_trajectory": scorers["career"].score(jd_requirements, profile),
            "experience_fit":    scorers["experience"].score(jd_requirements, profile),
            "profile_quality":   scorers["quality"].score(profile),
            "anomaly_flags":     scorers["quality"].detect_anomalies(profile),
        }

    if filters:
        all_scores = _post_filter(all_scores, profiles, filters)
    return all_scores


def _extract_qdrant_filters(filters):
    qdrant_filters = {}
    if filters.get("min_experience"):
        qdrant_filters["min_experience"] = filters["min_experience"]
    if filters.get("max_experience"):
        qdrant_filters["max_experience"] = filters["max_experience"]
    if filters.get("open_to_work_only"):
        qdrant_filters["open_to_work_only"] = True
    if filters.get("max_notice_period"):
        qdrant_filters["max_notice_period"] = filters["max_notice_period"]
    return qdrant_filters


def _post_filter(all_scores, profiles, filters):
    filtered = {}
    for cid, scores in all_scores.items():
        profile = profiles.get(cid, {})
        if filters.get("required_skills"):
            c_skills = {s.lower() for s in profile.get("skills", [])}
            required = [s.lower() for s in filters["required_skills"]]
            if not any(rs in c_skills for rs in required):
                continue
        if filters.get("location"):
            loc = profile.get("location", "").lower()
            country = profile.get("country", "").lower()
            floc = filters["location"].lower()
            if floc not in loc and floc not in country:
                continue
        if filters.get("seniority_levels"):
            if profile.get("seniority_level") not in filters["seniority_levels"]:
                continue
        filtered[cid] = scores
    return filtered


def _build_results(ranked, all_scores, jd_req):
    profiles = PIPELINE["candidate_profiles"]
    explainer = PIPELINE["explainer"]
    results = []

    for i, candidate in enumerate(ranked):
        cid = candidate["candidate_id"]
        profile = profiles[cid]
        scores = all_scores[cid]
        redrob = profile.get("redrob", {})

        results.append({
            "rank":             i + 1,
            "candidate_id":     cid,
            "name":             profile.get("name", ""),
            "current_title":    profile.get("current_title", ""),
            "current_company":  profile.get("current_company", ""),
            "location":         profile.get("location", ""),
            "country":          profile.get("country", ""),
            "experience_years": profile.get("experience_years", 0),
            "seniority_level":  profile.get("seniority_level", ""),
            "skills":           profile.get("skills", [])[:15],
            "education":        profile.get("education", ""),
            "education_tier":   profile.get("education_tier", "unknown"),
            "final_score":      round(candidate["final_score"], 4),
            "score_breakdown": {
                "semantic_fit":      round(scores.get("semantic_fit", 0), 3),
                "skill_match":       round(scores.get("skill_match", 0), 3),
                "redrob_signals":    round(scores.get("redrob_signals", 0), 3),
                "career_trajectory": round(scores.get("career_trajectory", 0), 3),
                "experience_fit":    round(scores.get("experience_fit", 0), 3),
                "profile_quality":   round(scores.get("profile_quality", 0), 3),
            },
            "redrob_highlights": {
                "open_to_work":         redrob.get("open_to_work_flag", False),
                "response_rate":        round(redrob.get("recruiter_response_rate", 0), 2),
                "notice_period_days":   redrob.get("notice_period_days", 0),
                "github_score":         redrob.get("github_score", -1),
                "verified":             redrob.get("verification_count", 0) >= 2,
                "skill_assessments":    redrob.get("skill_assessment_scores", {}),
                "profile_completeness": redrob.get("profile_completeness_score", 0),
            },
            "anomaly_flags": scores.get("anomaly_flags", []),
            "reasoning": explainer.explain(
                jd_req, profile, scores, candidate["final_score"]
            ),
            "detailed_reasoning": explainer.explain_detailed(
                jd_req, profile, scores, candidate["final_score"]
            ),
        })

    return results


def _sanitize(profile):
    return {
        "candidate_id":            profile.get("candidate_id"),
        "name":                    profile.get("name"),
        "headline":                profile.get("headline"),
        "summary":                 profile.get("summary"),
        "current_title":           profile.get("current_title"),
        "current_company":         profile.get("current_company"),
        "location":                profile.get("location"),
        "country":                 profile.get("country"),
        "experience_years":        profile.get("experience_years"),
        "seniority_level":         profile.get("seniority_level"),
        "skills":                  profile.get("skills"),
        "skills_with_proficiency": profile.get("skills_with_proficiency"),
        "education":               profile.get("education"),
        "education_tier":          profile.get("education_tier"),
        "education_fields":        profile.get("education_fields"),
        "certifications":          profile.get("certifications"),
        "companies":               profile.get("companies"),
        "all_titles":              profile.get("all_titles"),
        "career_history":          profile.get("career_history"),
        "redrob":                  profile.get("redrob"),
    }


async def _progress(sid, stage, pct, msg):
    await manager.send(sid, {"stage": stage, "percent": pct, "message": msg})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )