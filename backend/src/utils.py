"""
Utility functions for the Intelligent Candidate Discovery System.
"""

import logging
import os
import sys
import yaml
import numpy as np
from pathlib import Path
from typing import Dict, Any
import pandas as pd


def setup_logging(level=logging.INFO):
    """Configure logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration with built-in defaults.

    Supports environment variable overrides for portability across
    local/Docker/CI environments:
      - DATASET_DIR — overrides paths.dataset_dir
      - CANDIDATES_FILE — overrides paths.candidates_file
      - JD_FILE — overrides paths.jd_file
    """

    defaults = {
        "model": {
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "embedding_dimension": 384,
            "batch_size": 64,
        },
        "vector_store": {
            "backend": "qdrant",
        },
        "qdrant": {
            "mode": "local",
            "local_path": "./qdrant_data",
            "collection_name": "candidates",
        },
        "scoring_weights": {
            "semantic_fit": 0.30,
            "skill_match": 0.23,
            "redrob_signals": 0.20,
            "career_trajectory": 0.12,
            "experience_fit": 0.10,
            "profile_quality": 0.05,
        },
        "fusion": {
            "method": "weighted_geometric",
            "zero_handling": "epsilon",
            "epsilon": 0.001,
        },
        "skill_matching": {
            "fuzzy_threshold": 80,
            "use_synonym_expansion": True,
        },
        "behavioral": {
            "recency_decay_days": 180,
        },
        "career": {
            "seniority_levels": [
                "intern", "junior", "mid", "senior",
                "lead", "principal", "director", "vp", "c-level",
            ]
        },
        "quality": {
            "min_completeness_threshold": 0.3,
            "anomaly_penalty": 0.10,
        },
        "output": {
            "top_k": 100,
            "include_explanations": True,
            "format": "csv",
        },
        "challenge": {
            "use_sample_only": False,
            "max_reasoning_length": 150,
        },
    }

    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            user_config = yaml.safe_load(f) or {}
        config = _deep_merge(defaults, user_config)
    else:
        logging.getLogger(__name__).warning(
            f"Config file {config_path} not found — using defaults."
        )
        config = defaults

    # ── Environment variable overrides ──────────────────────────────
    # Allows the same config.yaml to work in local Python and Docker
    if "paths" not in config:
        config["paths"] = {}

    if "DATASET_DIR" in os.environ:
        config["paths"]["dataset_dir"] = os.environ["DATASET_DIR"]
        logging.getLogger(__name__).info(
            f"  Using DATASET_DIR from environment: {os.environ['DATASET_DIR']}"
        )

    if "CANDIDATES_FILE" in os.environ:
        config["paths"]["candidates_file"] = os.environ["CANDIDATES_FILE"]

    if "JD_FILE" in os.environ:
        config["paths"]["jd_file"] = os.environ["JD_FILE"]

    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts."""
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate candidate dataframe."""
    valid_count = sum(
        1
        for _, row in df.iterrows()
        if row.notna().sum() >= max(2, len(df.columns) * 0.2)
    )
    return {
        "total_profiles": len(df),
        "valid_profiles": valid_count,
        "completeness_ratio": valid_count / max(len(df), 1),
        "columns_found": list(df.columns),
    }


def normalize_text(text: str) -> str:
    """Normalize text."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.strip().split())


def safe_float(value, default=0.0) -> float:
    """Safely convert to float."""
    try:
        result = float(value)
        if np.isnan(result) or np.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def get_vector_store(config: Dict[str, Any]):
    """
    Factory function — returns correct vector store based on config.
    Makes it easy to switch between numpy and qdrant.
    """
    backend = config.get("vector_store", {}).get("backend", "qdrant")

    if backend == "qdrant":
        try:
            from src.vector_store.qdrant_store import QdrantStore
            return QdrantStore(config)
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"Qdrant failed ({e}) — falling back to numpy"
            )
            from src.embedding_store import EmbeddingStore
            return EmbeddingStore(config)
    else:
        from src.embedding_store import EmbeddingStore
        return EmbeddingStore(config)