"""
Embedding Engine
Generates semantic embeddings for job descriptions and candidate profiles.
Updated for BGE-small model with BGE-specific prompt formatting.
"""

import logging
from typing import Dict, List, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Generate and manage semantic embeddings."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config["model"]["embedding_model"]
        self.batch_size = config["model"]["batch_size"]
        self.dimension = config["model"]["embedding_dimension"]

        logger.info(f"  Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)

        # BGE models need a query prefix for retrieval tasks
        self.is_bge = "bge" in self.model_name.lower()
        self.query_prefix = (
            "Represent this sentence for searching relevant passages: "
            if self.is_bge
            else ""
        )

        logger.info(
            f"  Model loaded | BGE mode: {self.is_bge} | "
            f"Dimension: {self.dimension}"
        )




    def embed_jd(self, jd_text: str, jd_requirements: Dict[str, Any] = None) -> np.ndarray:
        """
        Create a focused JD embedding.
        Uses only the role-defining portion (first 800 chars) plus extracted
        role keywords and skills — avoids matching on cultural/process boilerplate.
        """
        # ── Layer 1: Core role description (focused signal) ──────────
        # First 800 chars typically contain title, mandate, key skills
        # NOT cultural notes, comp details, or anti-patterns
        core_role = jd_text[:800] if len(jd_text) > 800 else jd_text

        # ── Layer 2: Role keywords from parser ───────────────────────
        role_text = ""
        if jd_requirements:
            roles = jd_requirements.get("role_keywords", [])
            if roles:
                role_text = "Role: " + ", ".join(roles[:5])

        # ── Layer 3: Top critical skills only ────────────────────────
        # Use must_have_skills (already ranked by importance from parser)
        skills_text = ""
        if jd_requirements:
            must_haves = jd_requirements.get("must_have_skills", [])[:10]
            if must_haves:
                skills_text = "Required skills: " + ", ".join(must_haves)

        # ── Layer 4: Domain concepts ─────────────────────────────────
        domain_text = ""
        if jd_requirements:
            domains = jd_requirements.get("domain_concepts", [])[:5]
            if domains:
                domain_text = "Domains: " + ", ".join(domains)

        # ── Build focused embedding text ─────────────────────────────
        focused_text = " . ".join(filter(None, [
            core_role,
            role_text,
            skills_text,
            domain_text,
        ]))

        # Embed with BGE prefix
        prefix = self.query_prefix if self.is_bge else ""
        vec = self.model.encode(
            prefix + focused_text,
            normalize_embeddings=True,
        )

        return vec
    




    def embed_candidates(
        self,
        candidate_profiles: Dict[str, Dict[str, Any]],
    ) -> Dict[str, np.ndarray]:
        """
        Generate embeddings for all candidate profiles.
        Candidates are the "documents" in retrieval (no prefix needed).
        """
        cids = list(candidate_profiles.keys())
        texts = []

        for cid in cids:
            profile = candidate_profiles[cid]
            text = self._build_candidate_text(profile)
            texts.append(text)

        logger.info(
            f"  Encoding {len(texts)} candidates "
            f"in batches of {self.batch_size}..."
        )

        # Batch encode — no query prefix for documents
        all_embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        return {cid: all_embeddings[i] for i, cid in enumerate(cids)}
    
    

    def embed_query(self, query: str, jd_requirements: Dict = None) -> np.ndarray:
        """
        Embed a query — uses the parser's pre-built search-optimized text
        plus additional context layers for maximum semantic match quality.
        """
        if jd_requirements:
            # Start with the parser's pre-built search text (already contains
            # role, domain, skills, qualities, related concepts)
            search_text = jd_requirements.get("search_text", "")

            # If search_text is empty (shouldn't happen but defensive), build manually
            if not search_text:
                parts = [query]

                expanded = jd_requirements.get("expanded_text", "")
                if expanded and expanded != query.lower():
                    parts.append(expanded)

                for field, label in [
                    ("role_keywords", "Role"),
                    ("domain_concepts", "Domain"),
                    ("hard_skills", "Skills"),
                    ("soft_skills", "Soft skills"),
                    ("expanded_concepts", "Related"),
                    ("implicit_skills", "Implicit"),
                ]:
                    values = jd_requirements.get(field, [])
                    if values:
                        parts.append(f"{label}: " + ", ".join(values[:8]))

                search_text = " . ".join(parts)
            else:
                # search_text exists — optionally append implicit skills if present
                implicit = jd_requirements.get("implicit_skills", [])
                if implicit:
                    search_text += f" . Implicit: {', '.join(implicit[:6])}"

            enriched_query = search_text
        else:
            enriched_query = query

        prefix = self.query_prefix if self.is_bge else ""
        vec = self.model.encode(
            prefix + enriched_query,
            normalize_embeddings=True,
        )
        return vec




    def _build_candidate_text(
        self, profile: Dict[str, Any]
    ) -> str:
        """
        Build a rich text representation of a candidate for embedding.
        Order matters — put most important info first.
        """
        parts = []

        # Title and headline (most important)
        if profile.get("current_title"):
            parts.append(f"Role: {profile['current_title']}")

        if profile.get("headline"):
            parts.append(profile["headline"])

        # Summary / bio
        if profile.get("summary"):
            parts.append(profile["summary"])

        # Skills (very important for matching)
        if profile.get("skills"):
            skills = profile["skills"]
            if isinstance(skills, list):
                # Prioritize advanced/expert skills
                advanced = profile.get("advanced_skills", [])
                if advanced:
                    parts.append(f"Expert skills: {', '.join(advanced[:10])}")
                parts.append(f"Skills: {', '.join(skills[:20])}")

        # Career history descriptions
        for desc in (profile.get("experience_descriptions") or [])[:4]:
            if desc and len(str(desc)) > 20:
                parts.append(str(desc)[:300])

        # Education
        if profile.get("education"):
            parts.append(f"Education: {profile['education']}")

        # Certifications
        certs = profile.get("certifications", [])
        if certs:
            parts.append(f"Certifications: {', '.join(certs[:5])}")

        # Industry
        if profile.get("current_industry"):
            parts.append(f"Industry: {profile['current_industry']}")

        text = " . ".join(filter(None, parts))

        # Fallback for sparse profiles
        if len(text.strip()) < 20:
            text = " ".join(
                str(v)
                for v in profile.values()
                if v and isinstance(v, str) and len(str(v)) > 3
            )

        return text.strip() or "No profile information available"