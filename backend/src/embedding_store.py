"""
Embedding Store
Saves and loads candidate embeddings to/from disk.
So we NEVER recompute them unless candidates change.

No vector database needed.
Just numpy files saved on disk — instant load.
"""

import logging
import os
import json
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EmbeddingStore:
    """
    Persistent embedding storage using numpy files.
    
    Files saved:
    cache/
    ├── candidate_embeddings.npy      ← all embeddings (matrix)
    ├── candidate_ids.json            ← ordered list of IDs
    ├── metadata.json                 ← model name, date, count
    └── data_hash.txt                 ← hash of candidates.jsonl
    
    Logic:
    - First run  → compute and save
    - Next runs  → load from disk instantly
    - Data changes → detect via hash → recompute automatically
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

        self.embeddings_path = self.cache_dir / "candidate_embeddings.npy"
        self.ids_path = self.cache_dir / "candidate_ids.json"
        self.metadata_path = self.cache_dir / "metadata.json"
        self.hash_path = self.cache_dir / "data_hash.txt"

        self.model_name = config["model"]["embedding_model"]

        # In-memory cache (loaded once per session)
        self._embeddings: Optional[np.ndarray] = None
        self._ids: Optional[list] = None

    # ─────────────────────────────────────────────────────────────────
    # PUBLIC METHODS
    # ─────────────────────────────────────────────────────────────────

    def get_or_compute(
        self,
        candidate_profiles: Dict[str, Any],
        embedding_engine,
        data_file_path: str = None,
    ) -> Dict[str, np.ndarray]:
        """
        Main method — returns embeddings dict.
        
        Either loads from disk cache OR computes fresh.
        Automatically detects if data has changed.

        Args:
            candidate_profiles : processed candidate profiles dict
            embedding_engine   : EmbeddingEngine instance
            data_file_path     : path to candidates.jsonl (for hash check)

        Returns:
            Dict mapping candidate_id -> embedding vector
        """
        # Check if valid cache exists
        if self._cache_is_valid(candidate_profiles, data_file_path):
            logger.info("  ✅ Loading embeddings from disk cache...")
            return self._load_from_disk()
        else:
            logger.info("  🔄 Computing fresh embeddings (first run or data changed)...")
            embeddings = self._compute_and_save(
                candidate_profiles, embedding_engine, data_file_path
            )
            return embeddings

    def is_cached(self) -> bool:
        """Check if a valid cache exists on disk."""
        return (
            self.embeddings_path.exists()
            and self.ids_path.exists()
            and self.metadata_path.exists()
        )

    def clear_cache(self):
        """Delete all cached embeddings."""
        for path in [self.embeddings_path, self.ids_path,
                     self.metadata_path, self.hash_path]:
            if path.exists():
                path.unlink()
        self._embeddings = None
        self._ids = None
        logger.info("  🗑️  Embedding cache cleared")

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache."""
        if not self.is_cached():
            return {"cached": False}

        metadata = self._load_metadata()
        size_mb = self.embeddings_path.stat().st_size / (1024 * 1024)

        return {
            "cached": True,
            "candidate_count": metadata.get("candidate_count", 0),
            "model_name": metadata.get("model_name", ""),
            "computed_at": metadata.get("computed_at", ""),
            "embedding_dimension": metadata.get("embedding_dimension", 0),
            "cache_size_mb": round(size_mb, 2),
        }

    # ─────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ─────────────────────────────────────────────────────────────────

    def _cache_is_valid(
        self,
        candidate_profiles: Dict,
        data_file_path: str = None,
    ) -> bool:
        """
        Check if cache exists and is still valid.
        
        Cache is INVALID if:
        1. Cache files dont exist
        2. Model name changed (different embedding model)
        3. Number of candidates changed
        4. Data file hash changed (file was updated)
        """
        if not self.is_cached():
            logger.info("  No cache found on disk")
            return False

        metadata = self._load_metadata()

        # Check model name matches
        if metadata.get("model_name") != self.model_name:
            logger.info(
                f"  Model changed: {metadata.get('model_name')} → {self.model_name}"
            )
            return False

        # Check candidate count matches
        if metadata.get("candidate_count") != len(candidate_profiles):
            logger.info(
                f"  Candidate count changed: "
                f"{metadata.get('candidate_count')} → {len(candidate_profiles)}"
            )
            return False

        # Check file hash if path provided
        if data_file_path and self.hash_path.exists():
            current_hash = self._compute_file_hash(data_file_path)
            saved_hash = self.hash_path.read_text().strip()
            if current_hash != saved_hash:
                logger.info("  Data file has changed — recomputing embeddings")
                return False

        logger.info(
            f"  Cache valid: {metadata.get('candidate_count')} candidates, "
            f"model={metadata.get('model_name')}"
        )
        return True

    def _compute_and_save(
        self,
        candidate_profiles: Dict,
        embedding_engine,
        data_file_path: str = None,
    ) -> Dict[str, np.ndarray]:
        """Compute embeddings and save to disk."""
        from datetime import datetime

        # Compute using embedding engine
        logger.info(f"  Computing embeddings for {len(candidate_profiles)} candidates...")
        embeddings_dict = embedding_engine.embed_candidates(candidate_profiles)

        # Convert to ordered arrays for efficient storage
        ids = list(embeddings_dict.keys())
        matrix = np.array([embeddings_dict[cid] for cid in ids], dtype=np.float32)

        # Save to disk
        logger.info("  Saving embeddings to disk cache...")
        np.save(str(self.embeddings_path), matrix)

        with open(self.ids_path, "w") as f:
            json.dump(ids, f)

        # Save metadata
        metadata = {
            "model_name": self.model_name,
            "candidate_count": len(ids),
            "embedding_dimension": matrix.shape[1],
            "computed_at": datetime.now().isoformat(),
            "matrix_shape": list(matrix.shape),
        }
        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Save data file hash
        if data_file_path and Path(data_file_path).exists():
            file_hash = self._compute_file_hash(data_file_path)
            self.hash_path.write_text(file_hash)

        size_mb = self.embeddings_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"  ✅ Saved {len(ids)} embeddings to disk "
            f"({size_mb:.1f} MB) "
            f"[shape: {matrix.shape}]"
        )

        # Store in memory too
        self._embeddings = matrix
        self._ids = ids

        return embeddings_dict

    def _load_from_disk(self) -> Dict[str, np.ndarray]:
        """Load embeddings from disk into memory."""
        # Load matrix
        logger.info("  Loading embedding matrix from disk...")
        matrix = np.load(str(self.embeddings_path))

        # Load IDs
        with open(self.ids_path, "r") as f:
            ids = json.load(f)

        metadata = self._load_metadata()
        size_mb = self.embeddings_path.stat().st_size / (1024 * 1024)

        logger.info(
            f"  ✅ Loaded {len(ids)} embeddings from cache "
            f"({size_mb:.1f} MB) "
            f"[dim={metadata.get('embedding_dimension')}] "
            f"[computed: {metadata.get('computed_at', 'unknown')[:10]}]"
        )

        # Store in memory
        self._embeddings = matrix
        self._ids = ids

        # Convert back to dict
        return {cid: matrix[i] for i, cid in enumerate(ids)}

    def _load_metadata(self) -> Dict:
        """Load metadata from disk."""
        try:
            with open(self.metadata_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute MD5 hash of a file to detect changes."""
        hasher = hashlib.md5()
        path = Path(file_path)

        if not path.exists():
            return ""

        # For large files, only hash first + last 1MB (fast but reliable enough)
        file_size = path.stat().st_size
        with open(path, "rb") as f:
            if file_size <= 2 * 1024 * 1024:
                # Small file: hash everything
                hasher.update(f.read())
            else:
                # Large file: hash first 1MB + last 1MB + file size
                hasher.update(f.read(1024 * 1024))
                f.seek(-1024 * 1024, 2)
                hasher.update(f.read())
                hasher.update(str(file_size).encode())

        return hasher.hexdigest()

    # ─────────────────────────────────────────────────────────────────
    # FAST SEARCH METHODS (use in-memory matrix)
    # ─────────────────────────────────────────────────────────────────

    def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 100,
    ) -> list:
        """
        Fast similarity search using matrix operations.
        
        Instead of comparing one by one (slow loop),
        we do ONE matrix multiplication to get ALL similarities at once.
        
        This is why we store embeddings as a matrix, not individual files.
        
        Args:
            query_embedding : 1D numpy array (the JD embedding)
            top_k           : number of top candidates to return
            
        Returns:
            List of (candidate_id, similarity_score) tuples, sorted desc
        """
        if self._embeddings is None or self._ids is None:
            raise RuntimeError("Embeddings not loaded. Call get_or_compute() first.")

        # ONE matrix multiplication = ALL similarities at once
        # Shape: (5000,) — one score per candidate
        similarities = np.dot(self._embeddings, query_embedding)

        # Get top-k indices (fast numpy operation)
        if top_k >= len(similarities):
            top_indices = np.argsort(similarities)[::-1]
        else:
            # argpartition is faster than full sort for large arrays
            top_indices = np.argpartition(similarities, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        return [
            (self._ids[i], float(similarities[i]))
            for i in top_indices
        ]