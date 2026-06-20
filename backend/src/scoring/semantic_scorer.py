"""
Semantic Scorer
Computes semantic similarity between JD and candidate embeddings.
"""

import math
import numpy as np
from typing import Dict, Any


class SemanticScorer:
    """Score candidates based on semantic embedding similarity."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def score(self, jd_embedding: np.ndarray,
              candidate_embedding: np.ndarray) -> float:
        """
        Compute semantic fit score using cosine similarity.
        Embeddings are already normalized, so dot product = cosine similarity.
        """
        raw_similarity = float(np.dot(jd_embedding, candidate_embedding))
        raw_similarity = max(-1.0, min(1.0, raw_similarity))
        return max(0.0, min(1.0, self._rescale_similarity(raw_similarity)))

    def _rescale_similarity(self, sim: float,
                             center: float = 0.45,
                             spread: float = 5.0) -> float:
        """
        Rescale cosine similarity to full 0-1 range.
        Made public (no double underscore) so main.py can call it directly
        via: scorers["semantic"]._rescale_similarity(raw_sim)

        Typical sentence-transformer cosine similarities cluster in 0.2-0.7.
        This sigmoid spreads them into a more discriminative 0-1 range.
        """
        try:
            return 1.0 / (1.0 + math.exp(-spread * (sim - center)))
        except OverflowError:
            return 0.0 if sim < center else 1.0