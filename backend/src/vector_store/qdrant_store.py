"""
Qdrant Vector Store — Optimized for 100,000+ candidates
Key features:
- Checkpoint saving (resume if interrupted)
- Batch encode + immediate upload (never lose progress)
- Progress tracking
- Fast search after first run
"""

import logging
import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class QdrantStore:
    """
    Local Qdrant vector store optimized for large datasets.
    Handles 100,000+ candidates efficiently.
    Saves progress — safe to interrupt and resume.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dimension   = config["model"]["embedding_dimension"]
        self.model_name  = config["model"]["embedding_model"]

        qdrant_cfg = config.get("qdrant", {})
        self.local_path      = qdrant_cfg.get("local_path", "./qdrant_data")
        self.collection_name = qdrant_cfg.get("collection_name", "candidates")

        # Checkpoint file — tracks how many are already uploaded
        self.checkpoint_path = Path(self.local_path) / "upload_checkpoint.json"
        self.meta_path       = Path(self.local_path) / "store_metadata.json"

        self._client = None
        self._setup_client()

    # ──────────────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────────────

    def _setup_client(self):
        """Connect to local Qdrant."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import (
                Distance, VectorParams, HnswConfigDiff
            )

            Path(self.local_path).mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=self.local_path)
            logger.info(f"  Qdrant: Connected (local: {self.local_path})")

            existing = [
                c.name
                for c in self._client.get_collections().collections
            ]

            if self.collection_name not in existing:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE,
                        hnsw_config=HnswConfigDiff(
                            m=16,
                            ef_construct=100,
                        ),
                    ),
                )
                logger.info(
                    f"  Qdrant: Created collection '{self.collection_name}'"
                )
            else:
                count = self._client.count(self.collection_name).count
                logger.info(
                    f"  Qdrant: Collection exists — {count} vectors stored"
                )

        except ImportError:
            raise ImportError(
                "Run: pip install qdrant-client==1.9.1"
            )

    # ──────────────────────────────────────────────────────────────────
    # Main Entry Point
    # ──────────────────────────────────────────────────────────────────

    def get_or_compute(
        self,
        candidate_profiles: Dict[str, Any],
        embedding_engine,
        data_file_path: str = None,
    ) -> Dict[str, Any]:
        """
        Smart compute with checkpoint resume.

        First run  : encodes + uploads all candidates (slow, once only)
        Next runs  : detects already stored, skips computation instantly
        If crashed : resumes from last checkpoint automatically
        """
        total_expected = len(candidate_profiles)
        existing_count = self._client.count(self.collection_name).count

        # Check if model changed
        metadata = self._load_metadata()
        model_changed = metadata.get("model_name") != self.model_name

        if model_changed and existing_count > 0:
            logger.info(
                "  Qdrant: Embedding model changed — "
                "clearing and recomputing all vectors"
            )
            self._clear_collection()
            self._clear_checkpoint()
            existing_count = 0

        # All done — nothing to compute
        if existing_count >= total_expected:
            logger.info(
                f"  Qdrant: All {existing_count} candidates already "
                f"embedded — skipping computation"
            )
            self._save_metadata(total_expected)
            return {cid: True for cid in candidate_profiles.keys()}

        # Resume from checkpoint
        checkpoint = self._load_checkpoint()
        already_uploaded_ids = set(checkpoint.get("uploaded_ids", []))

        if already_uploaded_ids:
            logger.info(
                f"  Qdrant: Resuming from checkpoint — "
                f"{len(already_uploaded_ids)} already uploaded, "
                f"{total_expected - len(already_uploaded_ids)} remaining"
            )
        else:
            logger.info(
                f"  Qdrant: First run — encoding {total_expected} candidates"
            )
            logger.info(
                f"  ⏱  Estimated time: "
                f"{self._estimate_time(total_expected)}"
            )
            logger.info(
                "  💾 Progress saved every 1000 candidates — "
                "safe to interrupt and resume"
            )

        # Compute and upload in streaming batches
        self._encode_and_upload_streaming(
            candidate_profiles=candidate_profiles,
            embedding_engine=embedding_engine,
            already_uploaded_ids=already_uploaded_ids,
        )

        self._save_metadata(total_expected)
        self._clear_checkpoint()  # Clean up checkpoint on success

        final_count = self._client.count(self.collection_name).count
        logger.info(
            f"  Qdrant: Complete — {final_count} vectors stored"
        )

        return {cid: True for cid in candidate_profiles.keys()}

    # ──────────────────────────────────────────────────────────────────
    # Streaming Encode + Upload
    # ──────────────────────────────────────────────────────────────────

    def _encode_and_upload_streaming(
        self,
        candidate_profiles: Dict[str, Any],
        embedding_engine,
        already_uploaded_ids: set,
        encode_batch_size: int = 256,
        upload_batch_size: int = 200,
        checkpoint_every: int = 1000,
    ):
        """
        Encode and upload in streaming batches.

        Key design:
        - Encode 256 candidates at a time (fits in RAM)
        - Upload immediately after encoding
        - Save checkpoint every 1000 uploads
        - If interrupted: restart resumes from checkpoint

        encode_batch_size: how many to encode at once (RAM dependent)
        upload_batch_size: how many to upload to Qdrant at once
        checkpoint_every:  save progress every N candidates
        """
        from qdrant_client.models import PointStruct
        from tqdm import tqdm

        # Filter out already uploaded
        all_cids = [
            cid for cid in candidate_profiles.keys()
            if cid not in already_uploaded_ids
        ]

        total_remaining = len(all_cids)
        uploaded_ids    = list(already_uploaded_ids)
        points_buffer   = []
        processed       = 0

        logger.info(
            f"  Encoding and uploading {total_remaining} candidates..."
        )

        with tqdm(
            total=total_remaining,
            desc="  Embedding + Uploading",
            unit="candidates",
        ) as pbar:

            for batch_start in range(0, total_remaining, encode_batch_size):
                batch_cids = all_cids[
                    batch_start: batch_start + encode_batch_size
                ]

                # ── Encode this batch ──────────────────────────────────
                batch_profiles = {
                    cid: candidate_profiles[cid] for cid in batch_cids
                }
                batch_texts = [
                    embedding_engine._build_candidate_text(profile)
                    for profile in batch_profiles.values()
                ]

                batch_embeddings = embedding_engine.model.encode(
                    batch_texts,
                    batch_size=64,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )

                # ── Build Qdrant points ────────────────────────────────
                for i, cid in enumerate(batch_cids):
                    profile   = candidate_profiles[cid]
                    embedding = batch_embeddings[i]

                    points_buffer.append(
                        PointStruct(
                            id=self._id_to_int(cid),
                            vector=embedding.tolist(),
                            payload=self._build_payload(cid, profile),
                        )
                    )

                    uploaded_ids.append(cid)
                    processed += 1

                    # ── Upload buffer when full ────────────────────────
                    if len(points_buffer) >= upload_batch_size:
                        self._client.upsert(
                            collection_name=self.collection_name,
                            points=points_buffer,
                        )
                        points_buffer = []

                    # ── Save checkpoint periodically ───────────────────
                    if processed % checkpoint_every == 0:
                        # Upload remaining buffer first
                        if points_buffer:
                            self._client.upsert(
                                collection_name=self.collection_name,
                                points=points_buffer,
                            )
                            points_buffer = []

                        self._save_checkpoint(uploaded_ids)
                        stored = self._client.count(
                            self.collection_name
                        ).count
                        logger.info(
                            f"  💾 Checkpoint saved: "
                            f"{processed}/{total_remaining} processed, "
                            f"{stored} stored in Qdrant"
                        )

                pbar.update(len(batch_cids))

        # Upload any remaining points
        if points_buffer:
            self._client.upsert(
                collection_name=self.collection_name,
                points=points_buffer,
            )

    # ──────────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────────

    def search_similar(
        self,
        query_embedding: np.ndarray,
        top_k: int = 100,
        filters: Dict[str, Any] = None,
    ) -> List[tuple]:
        """
        Fast vector similarity search.
        Compatible with both qdrant-client 1.7+ (query_points) and older (search).
        """
        qdrant_filter = (
            self._build_filter(filters) if filters else None
        )

        # Try new API first (qdrant-client >= 1.7.x)
        try:
            result = self._client.query_points(
                collection_name=self.collection_name,
                query=query_embedding.tolist(),
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            # New API returns QueryResponse object with .points attribute
            points = result.points
        except AttributeError:
            # Fallback to old API (qdrant-client < 1.7)
            points = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
            )

        return [
            (p.payload["candidate_id"], float(p.score))
            for p in points
        ]

    # ──────────────────────────────────────────────────────────────────
    # Real-time Operations (Enterprise Features)
    # ──────────────────────────────────────────────────────────────────

    def add_candidate(
        self,
        candidate_id: str,
        embedding: np.ndarray,
        profile: Dict[str, Any],
    ):
        """Add a single new candidate instantly."""
        from qdrant_client.models import PointStruct

        self._client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=self._id_to_int(candidate_id),
                    vector=embedding.tolist(),
                    payload=self._build_payload(candidate_id, profile),
                )
            ],
        )

    def delete_candidate(self, candidate_id: str):
        """Remove a candidate from the index."""
        from qdrant_client.models import PointIdsList

        self._client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(
                points=[self._id_to_int(candidate_id)]
            ),
        )

    def get_cache_info(self) -> Dict[str, Any]:
        """Cache info for API endpoint."""
        try:
            count    = self._client.count(self.collection_name).count
            metadata = self._load_metadata()
            checkpoint = self._load_checkpoint()
            uploaded_so_far = len(checkpoint.get("uploaded_ids", []))

            return {
                "cached":              count > 0,
                "candidate_count":     count,
                "model_name":          metadata.get("model_name", self.model_name),
                "computed_at":         metadata.get("computed_at", "unknown"),
                "embedding_dimension": self.dimension,
                "backend":             "qdrant",
                "storage_path":        self.local_path,
                "in_progress":         uploaded_so_far > 0 and uploaded_so_far < count,
            }
        except Exception:
            return {"cached": False, "backend": "qdrant"}

    def clear_cache(self):
        """Clear all vectors and checkpoints."""
        self._clear_collection()
        self._clear_checkpoint()
        if self.meta_path.exists():
            self.meta_path.unlink()
        logger.info("  Qdrant: Cache cleared")

    # ──────────────────────────────────────────────────────────────────
    # Private Helpers
    # ──────────────────────────────────────────────────────────────────

    def _build_payload(
        self,
        candidate_id: str,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build searchable payload metadata."""
        redrob = profile.get("redrob", {})
        return {
            "candidate_id":       candidate_id,
            "experience_years":   float(profile.get("experience_years", 0) or 0),
            "seniority_level":    str(profile.get("seniority_level", "") or ""),
            "location":           str(profile.get("location", "") or ""),
            "country":            str(profile.get("country", "") or ""),
            "current_title":      str(profile.get("current_title", "") or ""),
            "open_to_work":       bool(redrob.get("open_to_work_flag", False)),
            "notice_period_days": float(redrob.get("notice_period_days", 999) or 999),
            "skills":             list(profile.get("skills", []))[:20],
            "profile_completeness": float(
                redrob.get("profile_completeness_score", 0) or 0
            ),
            "github_score":       float(redrob.get("github_score", -1) or -1),
        }

    def _build_filter(self, filters: Dict[str, Any]):
        """Convert filter dict to Qdrant filter."""
        from qdrant_client.models import (
            Filter, FieldCondition, Range, MatchValue
        )

        conditions = []

        if filters.get("min_experience") is not None:
            conditions.append(
                FieldCondition(
                    key="experience_years",
                    range=Range(gte=float(filters["min_experience"])),
                )
            )
        if filters.get("max_experience") is not None:
            conditions.append(
                FieldCondition(
                    key="experience_years",
                    range=Range(lte=float(filters["max_experience"])),
                )
            )
        if filters.get("open_to_work_only"):
            conditions.append(
                FieldCondition(
                    key="open_to_work",
                    match=MatchValue(value=True),
                )
            )
        if filters.get("max_notice_period") is not None:
            conditions.append(
                FieldCondition(
                    key="notice_period_days",
                    range=Range(lte=float(filters["max_notice_period"])),
                )
            )

        if not conditions:
            return None

        return Filter(must=conditions)

    def _clear_collection(self):
        """Delete and recreate the Qdrant collection."""
        from qdrant_client.models import Distance, VectorParams

        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass

        self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.dimension,
                distance=Distance.COSINE,
            ),
        )

    def _save_checkpoint(self, uploaded_ids: List[str]):
        """Save progress checkpoint."""
        checkpoint = {
            "uploaded_ids": uploaded_ids,
            "saved_at":     datetime.now().isoformat(),
            "count":        len(uploaded_ids),
        }
        with open(self.checkpoint_path, "w") as f:
            json.dump(checkpoint, f)

    def _load_checkpoint(self) -> Dict:
        """Load progress checkpoint."""
        try:
            if self.checkpoint_path.exists():
                with open(self.checkpoint_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _clear_checkpoint(self):
        """Remove checkpoint file after successful completion."""
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()

    def _save_metadata(self, count: int):
        """Save metadata."""
        with open(self.meta_path, "w") as f:
            json.dump({
                "model_name":          self.model_name,
                "candidate_count":     count,
                "embedding_dimension": self.dimension,
                "computed_at":         datetime.now().isoformat(),
            }, f, indent=2)

    def _load_metadata(self) -> Dict:
        """Load metadata."""
        try:
            if self.meta_path.exists():
                with open(self.meta_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _estimate_time(self, total: int) -> str:
        """Estimate time for embedding computation."""
        # BGE-small on CPU: ~1000 candidates/minute
        minutes = total / 1000
        if minutes < 60:
            return f"~{minutes:.0f} minutes"
        hours = minutes / 60
        return f"~{hours:.1f} hours"

    def _id_to_int(self, candidate_id: str) -> int:
        """Convert candidate ID to integer."""
        try:
            numeric = "".join(filter(str.isdigit, candidate_id))
            if numeric:
                return int(numeric)
        except Exception:
            pass
        return abs(hash(candidate_id)) % (2 ** 63)