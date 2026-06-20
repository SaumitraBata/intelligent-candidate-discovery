# Intelligent Candidate Discovery System

> AI-powered candidate ranking for the **Redrob India Runs Data & AI Challenge** — ranks the top 100 candidates from a pool of 100,000 against any job description using a 7-signal scoring pipeline, fully offline on CPU.

---

## Table of Contents

- [The Problem](#the-problem)
- [Our Approach](#our-approach)
- [Pre-Computed Data Setup](#pre-computed-data-setup-required-first)
- [Architecture Diagram](#architecture-diagram)
- [Quick Start](#quick-start-local-python)
- [Docker Sandbox](#docker-sandbox-recommended-for-judges)
- [Scoring Pipeline Deep Dive](#scoring-pipeline-deep-dive)
- [Example: How a Candidate Gets Scored](#example-how-a-candidate-gets-scored)
- [Anti-Patterns We Catch](#anti-patterns-we-catch)
- [Performance Benchmarks](#performance-benchmarks)
- [Project Structure](#project-structure)
- [Design Decisions](#key-design-decisions)
- [Limitations & Honest Tradeoffs](#limitations-and-honest-tradeoffs)
- [Tech Stack](#tech-stack)

---

## The Problem

The hackathon JD is for a **Senior AI Engineer** at Redrob, and the dataset contains 100,000 candidate profiles. The challenge isn't just finding candidates with "AI" in their skills — the dataset deliberately includes traps:

- **Keyword stuffers** — Civil Engineers with "RAG, LangChain, embeddings" listed as advanced skills despite zero relevant work history
- **Honeypot profiles** — ~80 candidates with structurally impossible profiles (8 years at a 3-year-old company, all skills at "expert" with no tenure)
- **Title-description mismatches** — Profiles claiming "Civil Engineer" titles but describing marketing or consulting work
- **Generic high-scorers** — Marketing Managers with 11 of 55 skills matched (mostly soft skills like "communication")

A naive keyword-matching system surfaces these traps in the top 10. The right approach must reason about role fit beyond surface keywords.

---

## Our Approach

We built a **7-signal scoring pipeline** that combines semantic understanding with rule-based validation:

1. Vector search (BGE-small embeddings via Qdrant) for fast retrieval
2. Importance-weighted skill matching (skills are weighted by JD signals, not counted equally)
3. Behavioral signal integration (8 Redrob platform signals)
4. Career trajectory analysis (seniority, company prestige, growth)
5. Experience fit (Gaussian penalty around required years)
6. Profile quality checks
7. Structural anomaly detection (catches honeypots and keyword stuffers)

All seven dimensions combine via **weighted geometric mean** — a mathematical choice that punishes zero performance in any critical dimension and prevents gaming through specialization.

**Crucially, the system is generic.** It contains zero hardcoded role-specific rules. The same code that ranks AI Engineers for this JD would correctly rank HR Managers for an HR JD, Civil Engineers for a construction JD, or Marketing Managers for a marketing JD — because all signals are derived from the JD text itself.

---

## Pre-Computed Data Setup (Required First)

This system uses pre-computed candidate embeddings (~820MB total) that exceed GitHub's repository file size limits. They're hosted on Google Drive and downloaded automatically by a setup script.

**Before running anything else, download the pre-computed data:**

```bash
cd backend
python download_precomputed.py
```

This downloads and extracts approximately 500MB of compressed data into:

- `backend/cache/processed_profiles.pkl` (325 MB) — Processed candidate profiles
- `backend/qdrant_data/` (492 MB) — Pre-computed BGE-small embeddings stored in Qdrant

**Why pre-computed?** Embedding 100,000 candidates with BGE-small on CPU takes approximately 2.5 hours. By pre-computing once and hosting the artifacts externally, judges can reproduce results in 2-3 minutes instead of waiting hours.

**Manual download fallback:** If the script fails (network issues, Google Drive rate limits), download manually from [this Google Drive link](https://drive.google.com/file/d/1p2HjVsxhfPI3YwqF25veBqQGa-HooywJ/view?usp=sharing) and extract `precomputed_data.zip` into the `backend/` folder. The extracted folders should be `backend/cache/` and `backend/qdrant_data/`.

You can also direct download it through this link : https://drive.google.com/uc?export=download&id=1p2HjVsxhfPI3YwqF25veBqQGa-HooywJ
---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT                                    │
│  job_description.docx (the JD)                                  │
│  candidates.jsonl (100,000 candidates)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PARSING LAYER                                 │
│  JDParser → role keywords, skills, importance scores,           │
│             negative requirements, seniority                    │
│  DataLoader → flat candidate profiles (cached as pickle)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EMBEDDING & RETRIEVAL                          │
│  EmbeddingEngine → BGE-small encodes JD into 384-dim vector     │
│  Qdrant Vector Store → HNSW search over 100k vectors            │
│                        Returns similarity score per candidate   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   7-SIGNAL SCORING                              │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │ Semantic Fit    │  │ Skill Match     │                       │
│  │ (sigmoid)       │  │ (importance-    │                       │
│  │                 │  │  weighted)      │                       │
│  └─────────────────┘  └─────────────────┘                       │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │ Redrob Signals  │  │ Career Path     │                       │
│  │ (8 platform     │  │ (seniority,     │                       │
│  │  signals)       │  │  prestige)      │                       │
│  └─────────────────┘  └─────────────────┘                       │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │ Experience Fit  │  │ Profile Quality │                       │
│  │ (Gaussian)      │  │ + Anomaly Flags │                       │
│  └─────────────────┘  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  FUSION & PENALTIES                             │
│  Weighted geometric mean (requires balanced scores)             │
│  + Honeypot penalty (35% per structural anomaly)                │
│  + Negative requirement penalty (only if JD specifies)          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  RANKING & OUTPUT                               │
│  Sort by score desc, tie-break by candidate_id asc              │
│  Deduplicate by name                                            │
│  Take top 100                                                   │
│  Generate template-based reasoning (zero hallucination)         │
│  Write submission.csv                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Local Python)

### Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
```

### Download Pre-Computed Data (One-Time)

```bash
python download_precomputed.py
```

### Generate Submission CSV

```bash
python generate_submission.py
```

The script:
1. Loads pre-cached candidate profiles (instant if cache exists)
2. Loads BGE-small embedding model
3. Connects to Qdrant vector store (pre-populated with embeddings)
4. Reads the JD from the dataset folder
5. Runs the full scoring pipeline
6. Writes `results/submission.csv`

### Validate Submission

```bash
python "Dataset/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/validate_submission.py" backend/results/submission.csv
```

Expected output: `Submission is valid.`

---

## Docker Sandbox (Recommended for Judges)

Build and run the system in an isolated container matching hackathon compute constraints (CPU only, no GPU, no network during ranking).

### Build the Image

```bash
cd backend
docker build -t redrob-ranker .
```

First build takes ~10-15 minutes (downloads Python base image, ML dependencies, BGE model, and pre-computed data from Google Drive). The download step happens once during build, so subsequent runs are instant.

### Run the Container

**Linux/Mac:**

```bash
docker run --rm \
  -v "$(pwd)/../Dataset:/app/Dataset" \
  -v "$(pwd)/results:/app/results" \
  redrob-ranker
```

**Windows PowerShell:**

```bash
docker run --rm `
  -v "${PWD}/../Dataset:/app/Dataset" `
  -v "${PWD}/results:/app/results" `
  redrob-ranker
```

**Windows CMD:**

```bash
docker run --rm -v "%cd%\..\Dataset:/app/Dataset" -v "%cd%\results:/app/results" redrob-ranker
```

The container produces `submission.csv` in `backend/results/` using pre-computed embeddings baked into the image.

### What's Included in the Image

- All Python source code
- Pre-processed candidate profiles cache (downloaded during build)
- Pre-computed BGE embeddings in Qdrant (downloaded during build)
- BGE-small-en-v1.5 model weights (~130MB)
- All Python dependencies

### What's Mounted from the Host

- `Dataset/` folder — contains `job_description.docx` and `candidates.jsonl`
- `results/` folder — receives the generated `submission.csv`

### Runtime Constraints

- **Time:** ~3 minutes for ranking 100,000 candidates
- **Memory:** ~3-4GB peak (well within 16GB limit)
- **Network:** Disabled at runtime via `HF_HUB_OFFLINE=1` environment variable
- **GPU:** None required, CPU-only inference

---

## Scoring Pipeline Deep Dive

### Semantic Fit (Weight: 30%)

The JD text is encoded into a 384-dimensional vector using BGE-small-en-v1.5. Candidate profiles are pre-encoded into the same vector space. Cosine similarity gives a raw score, which we rescale via sigmoid to spread the typical 0.3-0.7 range across the full 0-1 spectrum.

```python
score = 1 / (1 + exp(-5 × (cosine_sim - 0.45)))
```

### Skill Match (Weight: 25%)

Instead of counting matched skills equally, we weight matches by **importance** derived from generic JD text signals:

- Position in document (skills mentioned in title/first paragraph score highest)
- Mention frequency
- Proximity to "must have" / "required" markers
- Inverse proximity to "nice to have" / "preferred" markers

A candidate matching 3 high-importance skills outscores one matching 10 generic low-importance skills.

We also enforce a **critical skills gate**: candidates matching zero of the top 5 most important skills get a near-zero skill score regardless of other matches.

### Redrob Behavioral Signals (Weight: 20%)

8 sub-signals from the platform combine into one Redrob score:

| Signal | Weight | What It Captures |
|--------|--------|------------------|
| Open to work flag | 20% | Direct availability signal |
| Recruiter response rate | 15% | Reliability and engagement |
| Profile completeness | 15% | Investment in profile |
| GitHub activity | 12% | Verified technical proof |
| Skill assessments | 12% | Platform-verified skills |
| Notice period | 10% | Time-to-hire |
| Verification status | 8% | Trust/authenticity |
| Offer acceptance rate | 8% | Hiring success history |

### Career Trajectory (Weight: 15%)

Combines seniority alignment, company prestige (based on company size enum), growth velocity (years vs expected level), and domain relevance. Importantly, this scorer down-weights inflated startup titles (a "CTO" at a 2-person company with 3 years experience is treated as a mid-level engineer).

### Experience Fit (Weight: 7%)

Asymmetric Gaussian penalty: perfect score within the JD's range, gentler penalty for over-experience than under-experience (over-qualified candidates can still do the work).

### Profile Quality (Weight: 3%)

Completeness, internal consistency, description quality. Low weight because it measures form rather than substance.

### Anomaly Detection (Applied as Multiplier)

Generic structural checks that flag honeypot and keyword-stuffer patterns:

- **Title-description mismatch** — Title says "Civil Engineer" but description describes business analysis work
- **Duplicate job descriptions** — Same description text across multiple jobs (copy-paste artifact)
- **Inflated proficiency claims** — "Advanced" in a skill used for fewer than 8 months
- **Experience-timeline mismatch** — Claimed years exceed sum of career history
- **Uniform tenure patterns** — All jobs have identical durations (generated profile)
- **Zero engagement** — No verifications, no responses, no activity

Each anomaly flag reduces the final score by 35% multiplicatively.

---

## Example: How a Candidate Gets Scored

Consider a candidate profile from the dataset:

```
Title:    AI Engineer at Salesforce
Years:    5
Skills:   Python, ML, PyTorch, Embeddings, Pinecone, Vector Search, ...
Redrob:   Open to work, 64% response rate, verified email + phone
```

**Step 1: Semantic similarity** → 0.85 (profile content aligns well with JD)

**Step 2: Skill importance from JD parser:**

- "ml" (importance: 8.5) → matched ✓
- "embeddings" (importance: 7.0) → matched ✓
- "vector search" (importance: 6.5) → matched ✓
- "python" (importance: 6.0) → matched ✓
- "rag" (importance: 5.0) → not in skills ✗

Top 5 critical: 4/5 matched → critical gate passed (multiplier 1.0)
Weighted match score: 0.78

**Step 3: Redrob signals** → 0.72 (good engagement, verified, open to work)

**Step 4: Career trajectory** → 0.80 (senior at large product company)

**Step 5: Experience fit** → 0.95 (5 years fits 5-9 year requirement)

**Step 6: Profile quality** → 0.85 (complete profile, consistent)

**Step 7: Anomaly detection** → 0 flags

**Fusion (weighted geometric mean):**

```
final = exp(0.30·ln(0.85) + 0.25·ln(0.78) + 0.20·ln(0.72)
          + 0.15·ln(0.80) + 0.07·ln(0.95) + 0.03·ln(0.85))
      ≈ 0.79
```

No anomaly penalty applied. Final ranking: **Top 5**.

**Generated reasoning:**
> "AI Engineer at Salesforce with 5 years of experience. Has all required skills (matches 8 of 55). Actively looking for new role. Responds quickly to recruiters."

---

## Anti-Patterns We Catch

The dataset includes deliberate trap candidates. Here are real examples of what our system correctly down-ranks:

### Trap 1: Civil Engineer with Stuffed AI Skills

```
Title:        Civil Engineer at TCS
Years:        7
Skills:       RAG (advanced, 4 months), LangChain, Embeddings,
              Pinecone, Sentence Transformers (all "advanced")
Description:  "Business analyst at a consulting firm... AI-strategy
               advisory but my own technical depth in AI is limited"
```

**Flags raised:**

- `title_description_mismatch` (Civil Engineer title, business analyst description)
- `inflated_proficiency_claims` (RAG "advanced" with 4 months experience)
- `severe_role_inconsistency` (multiple jobs with mismatched descriptions)

**Result:** 3 honeypot flags → score multiplied by 0.275 → drops from top 10 to rank 5000+

### Trap 2: Duplicate Job Descriptions

A candidate with two different job titles (Civil Engineer + Accountant) at different companies, both with identical "Marketing leadership role at B2B SaaS" descriptions.

**Flags raised:** `duplicate_job_descriptions`, `title_description_mismatch`

### Trap 3: Generic High-Match Stuffer

A Marketing Manager matching 11/55 skills, all soft skills (communication, teamwork, problem-solving, project management, presentation).

**How we catch it:** Critical skills gate. None of the top 5 JD-important skills (Python, ML, embeddings, vector databases, RAG) are matched → critical_ratio = 0 → role_multiplier = 0.05 → near-zero final score.

---

## Performance Benchmarks

Measured on Windows 11, Intel CPU, 16GB RAM:

| Stage | Time | Notes |
|-------|------|-------|
| Load profile cache | ~3 sec | Pre-pickled, instant load |
| Load BGE-small model | ~1 sec | Cached on disk |
| Load Qdrant store | ~20 sec | 100k vectors with HNSW index |
| Parse JD | <1 sec | Pure regex |
| Embed JD query | ~1 sec | Single BGE forward pass |
| Score 100k candidates | ~120 sec | 7 scorers per candidate |
| Fuse and rank | ~2 sec | In-memory operations |
| Write CSV | <1 sec | 100 rows |
| **Total** | **~150 sec** | Well within 5-min limit |

**Pre-computation (one-time, not counted in runtime):**
- Embedding 100k candidates with BGE-small on CPU: ~2.5 hours
- This is committed externally (Google Drive) so judges don't repeat it

---

## Project Structure

```
.
├── backend/
│   ├── generate_submission.py    # Main entry point
│   ├── download_precomputed.py   # Downloads embeddings from Google Drive
│   ├── main.py                   # FastAPI server (optional UI)
│   ├── config.yaml               # All configuration
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile                # Container recipe for sandbox
│   ├── src/
│   │   ├── data_loader.py        # Loads candidates with smart caching
│   │   ├── jd_parser.py          # JD requirement extraction
│   │   ├── jd_reader.py          # .docx file reader
│   │   ├── embedding_engine.py   # BGE-small embeddings
│   │   ├── ranker.py             # Sorting with tie-breaking
│   │   ├── explainer.py          # Reasoning generation
│   │   ├── utils.py              # Shared utilities
│   │   ├── vector_store/
│   │   │   └── qdrant_store.py   # Qdrant integration
│   │   └── scoring/
│   │       ├── semantic_scorer.py
│   │       ├── skill_matcher.py
│   │       ├── redrob_scorer.py
│   │       ├── career_scorer.py
│   │       ├── experience_scorer.py
│   │       ├── quality_scorer.py
│   │       └── score_fusion.py
│   ├── cache/                    # Profile cache (downloaded by script)
│   ├── qdrant_data/              # Pre-computed embeddings (downloaded by script)
│   └── results/
│       └── submission.csv        # Generated submission
├── frontend/                     # Optional React UI
└── submission_metadata.yaml      # Hackathon metadata
```

---

## Key Design Decisions

### Why BGE-small over OpenAI embeddings?

BGE-small (130MB) runs locally on CPU and is specifically trained for retrieval tasks. OpenAI embeddings require API calls, violating the no-network constraint. BGE-small achieves comparable retrieval quality for this domain at zero latency cost after initial embedding.

### Why Qdrant over numpy arrays?

Qdrant provides HNSW indexing for sub-millisecond similarity search over 100k vectors. The naive numpy approach loads all vectors into RAM and performs O(n) linear scans, which scales poorly. Qdrant also supports filtered search (e.g., "find similar AND experience > 5 years") in one operation.

### Why weighted geometric mean over arithmetic mean?

Geometric mean punishes zero performance in any dimension. With arithmetic mean, a candidate with 0.95 in 5 dimensions and 0.05 in one dimension scores 0.80 — looks fine. With geometric mean, the same candidate scores 0.42, correctly identifying the critical gap. This prevents gaming through specialization.

### Why generic anomaly detection over hardcoded rules?

We deliberately avoided role-specific rules ("if Civil Engineer + AI skills → penalty"). Instead, all anomaly checks are structural: title-description consistency, duplicate content patterns, proficiency-tenure consistency. The same checks work for any role family, ensuring the system generalizes to future JDs without modification.

### Why importance-weighted skill matching over counting?

A Civil Engineer matching 11/55 skills (mostly soft skills) shouldn't outrank an AI Engineer matching 6/55 critical technical skills. We extract importance from generic JD text signals (position, frequency, proximity to "must have") and weight matches accordingly.

### Why external hosting for pre-computed data?

The pre-computed embeddings (~820MB) exceed GitHub's 100MB per-file limit. We could use Git LFS, but Git LFS free tier limits bandwidth (1GB/month) — judges cloning the repo would exhaust the quota quickly. Google Drive hosting is unlimited and free, making the system more accessible to evaluators.

---

## Reproducibility

The repository includes everything needed to reproduce the submission:

- Pre-computed candidate embeddings (downloaded from Google Drive via setup script)
- Processed profile cache (downloaded from Google Drive via setup script)
- Generated submission CSV in `backend/results/`
- Dockerfile for isolated, reproducible execution

A judge cloning this repo can run either the local Python command or the Docker commands and reproduce the exact submission in under 5 minutes total (including one-time download). The 2.5-hour embedding pre-computation only needs to happen once and is already done.

---

## Limitations and Honest Tradeoffs

**What this system does well:**

- Catches obvious honeypots and keyword stuffers
- Generalizes to any JD without code changes
- Runs fully offline within hackathon compute constraints
- Produces explainable, hallucination-free reasoning

**What this system cannot do without an LLM:**

- Perfectly distinguish a genuine career transitioner from a keyword stuffer (e.g., a Content Writer who legitimately moved into AI)
- Understand subtle role suitability that requires reading between the lines
- Catch every honeypot (some require semantic understanding our rules can't replicate)

These limitations are honest reflections of rule-based scoring without LLM re-ranking. The hackathon explicitly prohibits LLM calls during ranking, so we built the best rule-based system we could within those constraints.

In a production environment, this system would serve as the fast retrieval layer, with an LLM re-ranker on the top 200-500 candidates for final ordering. That two-stage architecture is what real platforms like LinkedIn Recruiter use.

---

## Tech Stack

**Backend:** Python 3.11+, FastAPI, Sentence-Transformers (BGE-small-en-v1.5), Qdrant (local mode), NumPy, RapidFuzz, python-docx, gdown

**Frontend (optional):** React 18, Vite, TailwindCSS, Framer Motion, Recharts

**Container:** Docker

---

## License

MIT License — built for the Redrob India Runs Data & AI Challenge 2024.

---

## Acknowledgments

Built by **Quadzilla** team for the Redrob hackathon. AI tools (Claude, ChatGPT, AmazonQ) were used as coding assistants for architecture discussion, code generation, and debugging. All algorithmic decisions and the final implementation were validated by the team.