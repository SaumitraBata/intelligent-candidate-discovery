"""
Generate the official submission CSV.
Runs the full ranking pipeline directly (no HTTP, no timeouts).
"""

import csv
import logging
import os
import sys
import time
from pathlib import Path

# Auto-detect cached HuggingFace model for fast startup
hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
if hf_cache.exists() and any(hf_cache.iterdir()):
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

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


def generate_submission():
    """Run full ranking pipeline and write submission.csv."""
    setup_logging(logging.INFO)
    logger = logging.getLogger(__name__)
    start = time.time()

    logger.info("=" * 60)
    logger.info("  GENERATING OFFICIAL SUBMISSION CSV")
    logger.info("=" * 60)

    # ── Load config ─────────────────────────────────────────────────
    config = load_config("config.yaml")
    dataset_dir = Path(config["paths"]["dataset_dir"])
    jd_file = dataset_dir / config["paths"]["jd_file"]
    candidates_file = dataset_dir / config["paths"]["candidates_file"]

    # ── Read JD ─────────────────────────────────────────────────────
    logger.info(f"\n[1/6] Reading JD from {jd_file.name}...")
    jd_text = read_jd_docx(str(jd_file))
    logger.info(f"  JD length: {len(jd_text)} characters")
    logger.info(f"  Preview: {jd_text[:200]}...")

    # ── Load candidates ─────────────────────────────────────────────
    logger.info("\n[2/6] Loading candidates...")
    loader = CandidateDataLoader(config)
    profiles = loader.load_smart(use_sample=False)
    logger.info(f"  Loaded {len(profiles)} candidate profiles")

    # ── Load embedding model ────────────────────────────────────────
    logger.info("\n[3/6] Loading embedding model...")
    embedding_engine = EmbeddingEngine(config)

    # ── Load vector store ───────────────────────────────────────────
    logger.info("\n[4/6] Loading vector store...")
    store = get_vector_store(config)
    store.get_or_compute(
        candidate_profiles=profiles,
        embedding_engine=embedding_engine,
        data_file_path=str(candidates_file),
    )
    logger.info(f"  Vector store ready: {store.get_cache_info().get('candidate_count', '?')} vectors")

    # ── Initialize scorers ──────────────────────────────────────────
    logger.info("\n[5/6] Initializing scorers...")
    scorers = {
        "semantic":   SemanticScorer(config),
        "skill":      SkillMatcher(config),
        "redrob":     RedrobSignalsScorer(config),
        "career":     CareerScorer(config),
        "behavioral": BehavioralScorer(config),
        "experience": ExperienceScorer(config),
        "quality":    QualityScorer(config),
    }
    fusion = ScoreFusion(config)
    ranker = Ranker(config)
    explainer = Explainer(config)
    jd_parser = JDParser(config)

    # ── Parse JD and run ranking ────────────────────────────────────
    logger.info("\n[6/6] Running ranking pipeline...")
    rank_start = time.time()

    jd_req = jd_parser.parse(jd_text)
    logger.info(f"  JD requirements parsed: {len(jd_req.get('hard_skills', []))} skills, "
                f"seniority={jd_req.get('seniority_level')}")

    # Use enriched query for embedding
    jd_embedding = embedding_engine.embed_query(jd_text, jd_req)

    # Get similarities for all candidates via Qdrant
    raw_similarities = dict(
        store.search_similar(jd_embedding, top_k=len(profiles))
    )

    # Score all candidates
    logger.info("  Scoring all candidates across 7 dimensions...")
    all_scores = {}
    for cid, profile in profiles.items():
        raw_sim = raw_similarities.get(cid, 0.0)
        all_scores[cid] = {
            "semantic_fit":      scorers["semantic"]._rescale_similarity(raw_sim),
            "skill_match":       scorers["skill"].score(jd_req, profile),
            "redrob_signals":    scorers["redrob"].score(profile, jd_req),
            "career_trajectory": scorers["career"].score(jd_req, profile),
            "experience_fit":    scorers["experience"].score(jd_req, profile),
            "profile_quality":   scorers["quality"].score(profile),
            "anomaly_flags":     scorers["quality"].detect_anomalies(profile),
        }


    # Fuse scores
    logger.info("  Fusing scores...")
    fused = fusion.fuse(all_scores, jd_requirements=jd_req, profiles=profiles)

    # Round scores to 4 decimal places BEFORE ranking
    # This ensures tie-breaking matches what appears in the final CSV
    fused_rounded = {cid: round(score, 4) for cid, score in fused.items()}

    # Rank using rounded scores so ties align with CSV output
    logger.info("  Ranking candidates...")
    ranked = ranker.rank(fused_rounded, all_scores, profiles)[:100]




    logger.info(f"  Pipeline completed in {time.time() - rank_start:.1f}s")
    logger.info(f"  Top score: {ranked[0]['final_score']:.4f} ({ranked[0]['name']})")
    logger.info(f"  100th score: {ranked[-1]['final_score']:.4f} ({ranked[-1]['name']})")

    # ── Write submission CSV ────────────────────────────────────────
    output_path = Path("results/submission.csv")
    output_path.parent.mkdir(exist_ok=True)

    logger.info(f"\n  Writing submission to {output_path}...")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["candidate_id", "rank", "score", "reasoning"],
            quoting=csv.QUOTE_NONNUMERIC,
        )
        writer.writeheader()
        for i, candidate in enumerate(ranked, 1):
            cid = candidate["candidate_id"]
            profile = profiles[cid]
            scores = all_scores[cid]

            reasoning = explainer.explain(
                jd_req, profile, scores, candidate["final_score"]
            )

            writer.writerow({
                "candidate_id": cid,
                "rank": i,
                "score": round(candidate["final_score"], 4),
                "reasoning": reasoning,
            })

    # ── Done ────────────────────────────────────────────────────────
    total_time = time.time() - start
    logger.info("\n" + "=" * 60)
    logger.info(f"  SUCCESS — submission.csv created with 100 candidates")
    logger.info(f"  Output: {output_path.absolute()}")
    logger.info(f"  Total time: {total_time:.1f}s")
    logger.info("=" * 60)

    return output_path


if __name__ == "__main__":
    generate_submission()