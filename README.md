<div align="center">

# 🎯 Intelligent Candidate Discovery

**Redrob India Runs Data & AI Challenge**

*Ranks the top 100 candidates from 100,000 profiles against any job description.*
*7-signal scoring pipeline · Fully offline · CPU only · Under 3 minutes.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC382D)](https://qdrant.tech)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Quick Start](#quick-start-local-python) · [Docker](#docker-sandbox-recommended-for-judges) · [Architecture](#architecture-diagram) · [How It Works](#scoring-pipeline-deep-dive)

</div>

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

```
Signal 1  →  Semantic Fit          (BGE-small embeddings via Qdrant)
Signal 2  →  Skill Match           (importance-weighted, not just counted)
Signal 3  →  Behavioral Signals    (8 Redrob platform signals)
Signal 4  →  Career Trajectory     (seniority, company prestige, growth)
Signal 5  →  Experience Fit        (Gaussian penalty around required years)
Signal 6  →  Profile Quality       (completeness, consistency)
Signal 7  →  Anomaly Detection     (catches honeypots and keyword stuffers)
```

All seven dimensions combine via **weighted geometric mean** — a mathematical choice that punishes zero performance in any critical dimension and prevents gaming through specialization.

> **The system is generic.** It contains zero hardcoded role-specific rules. The same code ranks AI Engineers for this JD, HR Managers for an HR JD, or Civil Engineers for a construction JD — because all signals are derived from the JD text itself.

---

## Pre-Computed Data Setup

> ⚠️ **Required before running anything else.**

Pre-computed candidate embeddings (~820MB total) exceed GitHub's file size limits. They're hosted on Google Drive and downloaded automatically:

```bash
cd backend
python download_precomputed.py
```

This downloads and extracts:

```
backend/cache/processed_profiles.pkl   →  325 MB (processed candidate profiles)
backend/qdrant_data/                   →  492 MB (BGE-small embeddings in Qdrant)
```

**Why pre-computed?** Embedding 100,000 candidates with BGE-small on CPU takes ~2.5 hours. Pre-computing once lets judges reproduce results in 2-3 minutes.

<details>
<summary>Manual download fallback</summary>

If the script fails, download from [this Google Drive link](https://drive.google.com/file/d/1p2HjVsxhfPI3YwqF25veBqQGa-HooywJ/view?usp=sharing) and extract `precomputed_data.zip` into the `backend/` folder. The extracted folders should be `backend/cache/` and `backend/qdrant_data/`.

</details>

---

## Architecture Diagram

<img width="1416" height="3500" alt="_- visual selection (2)" src="https://github.com/user-attachments/assets/5337e437-b3ca-46e4-87ad-faa0ca4ce8ea" />


---

## Quick Start (Local Python)

**1. Setup environment**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
```

**2. Download pre-computed data** (one-time)

```bash
python download_precomputed.py
```

**3. Generate submission**

```bash
python generate_submission.py
```

**4. Validate**

```bash
python validate_submission.py backend/results/submission.csv
```

Expected output: `Submission is valid.`

---

## Docker Sandbox (Recommended for Judges)

Build and run in an isolated container matching hackathon constraints:

**Build:**

```bash
cd backend
docker build -t redrob-ranker .
```

**Run:**

```bash
# Linux/Mac
docker run --rm \
  -v "$(pwd)/../Dataset:/app/Dataset" \
  -v "$(pwd)/results:/app/results" \
  redrob-ranker

# Windows CMD
docker run --rm -v "%cd%\..\Dataset:/app/Dataset" -v "%cd%\results:/app/results" redrob-ranker
```

<details>
<summary>What's inside the container</summary>

**Included in image:** All source code, profile cache, BGE embeddings in Qdrant, BGE-small model weights, all Python dependencies.

**Mounted from host:** `Dataset/` folder (JD + candidates), `results/` folder (output CSV).

**Runtime:** ~3 minutes · ~3-4GB RAM · No GPU · No network calls.

</details>

---

## Scoring Pipeline Deep Dive

### Semantic Fit · Weight: 30%

JD and candidate profiles encoded into 384-dim vectors using BGE-small-en-v1.5. Cosine similarity rescaled via sigmoid for better discrimination:

```python
score = 1 / (1 + exp(-5 × (cosine_sim - 0.45)))
```

### Skill Match · Weight: 25%

Skills weighted by **importance** from generic JD signals — position in document, frequency, proximity to "must have" markers. A candidate matching 3 critical skills outscores one matching 10 generic skills.

Enforces a **critical skills gate**: zero matches on the top 5 skills → near-zero score.

### Redrob Signals · Weight: 20%

Eight behavioral sub-signals from the platform:

- **Open to work** (20%) — direct availability signal
- **Response rate** (15%) — recruiter engagement
- **Completeness** (15%) — profile investment
- **GitHub activity** (12%) — verified technical proof
- **Skill assessments** (12%) — platform-verified scores
- **Notice period** (10%) — time-to-hire
- **Verifications** (8%) — email, phone, LinkedIn
- **Offer acceptance** (8%) — hiring history

### Career Trajectory · Weight: 15%

Seniority alignment, company prestige (company size → prestige score), growth velocity, domain relevance. Down-weights inflated titles — a "CTO" at a 2-person company with 3 years experience is treated as mid-level.

### Experience Fit · Weight: 7%

Asymmetric Gaussian penalty: perfect within the JD range, gentler penalty for over-experience than under-experience.

### Profile Quality · Weight: 3%

Completeness, consistency, description quality. Low weight — measures form, not substance.

### Anomaly Detection · Applied as Multiplier

Six structural checks catch honeypots:

- Title-description mismatch
- Duplicate job descriptions
- Inflated proficiency claims (advanced in <8 months)
- Experience-timeline mismatch
- Uniform tenure patterns
- Zero engagement signals

Each flag → **35% score reduction** multiplicatively.

---

## Example: How a Candidate Gets Scored

```
Candidate:  AI Engineer at Salesforce, 5 years
Skills:     Python, ML, PyTorch, Embeddings, Pinecone, Vector Search
Redrob:     Open to work, 64% response rate, verified email + phone
```

```
Step 1  Semantic similarity      →  0.85
Step 2  Skill match (weighted)   →  0.78  (4/5 critical skills matched)
Step 3  Redrob signals           →  0.72  (engaged, verified, available)
Step 4  Career trajectory        →  0.80  (product company, senior level)
Step 5  Experience fit           →  0.95  (5y fits 5-9y requirement)
Step 6  Profile quality          →  0.85  (complete, consistent)
Step 7  Anomaly flags            →  0     (clean profile)
```

**Fusion:** `exp(0.30·ln(0.85) + 0.25·ln(0.78) + ... ) ≈ 0.79`

**Ranking:** Top 5.

---

## Anti-Patterns We Catch

<details>
<summary><b>Trap 1:</b> Civil Engineer with Stuffed AI Skills</summary>

```
Title:   Civil Engineer at TCS (7 years)
Skills:  RAG (advanced, 4 months), LangChain, Embeddings, Pinecone
Desc:    "Business analyst at a consulting firm... AI depth is limited"
```

Flags: `title_description_mismatch` + `inflated_proficiency_claims` + `severe_role_inconsistency`

Result: 3 flags → score × 0.275 → drops from rank 1 to rank 5000+

</details>

<details>
<summary><b>Trap 2:</b> Duplicate Job Descriptions</summary>

Two jobs (Civil Engineer + Accountant) at different companies, both with identical "Marketing leadership role at B2B SaaS" descriptions.

Flags: `duplicate_job_descriptions` + `title_description_mismatch`

</details>

<details>
<summary><b>Trap 3:</b> Generic High-Match Stuffer</summary>

Marketing Manager matching 11/55 skills — all soft skills (communication, teamwork, etc.)

Caught by: Critical skills gate. 0/5 JD-critical skills matched → role_multiplier = 0.05 → near-zero score.

</details>

---

## Performance Benchmarks

```
Measured on: Windows 11, Intel CPU, 16GB RAM

Load profile cache ........... ~3 sec   (pre-pickled)
Load BGE-small model ......... ~1 sec   (cached on disk)
Load Qdrant store ............ ~20 sec  (100k vectors, HNSW index)
Parse JD ..................... <1 sec   (regex-based)
Embed JD query ............... ~1 sec   (single forward pass)
Score 100k candidates ........ ~120 sec (7 scorers per candidate)
Fuse and rank ................ ~2 sec   (in-memory)
Write CSV .................... <1 sec   (100 rows)
─────────────────────────────────────
Total                          ~150 sec  ✓ (limit: 300 sec)
```

---

## Project Structure

```
.
├── backend/
│   ├── generate_submission.py      ← Main entry point
│   ├── download_precomputed.py     ← Google Drive data downloader
│   ├── main.py                     ← FastAPI server (optional UI)
│   ├── config.yaml                 ← All configuration
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── src/
│   │   ├── data_loader.py          ← Smart incremental caching
│   │   ├── jd_parser.py            ← 8-layer JD understanding
│   │   ├── jd_reader.py            ← .docx extraction
│   │   ├── embedding_engine.py     ← BGE-small embeddings
│   │   ├── ranker.py               ← Sorting + tie-breaking
│   │   ├── explainer.py            ← Reasoning generation
│   │   ├── utils.py                ← Config + factory
│   │   ├── vector_store/
│   │   │   └── qdrant_store.py     ← Qdrant integration
│   │   └── scoring/
│   │       ├── semantic_scorer.py
│   │       ├── skill_matcher.py
│   │       ├── redrob_scorer.py
│   │       ├── career_scorer.py
│   │       ├── experience_scorer.py
│   │       ├── quality_scorer.py
│   │       └── score_fusion.py
│   ├── cache/                      ← Profile cache
│   ├── qdrant_data/                ← Pre-computed embeddings
│   └── results/
│       └── submission.csv
├── frontend/                       ← Optional React UI
└── submission_metadata.yaml
```

---

## Key Design Decisions

<details>
<summary><b>Why BGE-small over OpenAI embeddings?</b></summary>

BGE-small (130MB) runs locally on CPU and is trained specifically for retrieval tasks. OpenAI embeddings require API calls, violating the no-network constraint.

</details>

<details>
<summary><b>Why Qdrant over numpy arrays?</b></summary>

Qdrant's HNSW indexing provides sub-millisecond search over 100k vectors. Numpy requires O(n) linear scans. Qdrant also supports filtered search in one operation.

</details>

<details>
<summary><b>Why weighted geometric mean over arithmetic mean?</b></summary>

Geometric mean punishes zero in any dimension. With arithmetic mean, a candidate scoring 0.95 on 5 dimensions and 0.05 on one still gets 0.80. With geometric mean, the same candidate gets 0.42 — correctly flagging the gap.

</details>

<details>
<summary><b>Why generic anomaly detection over hardcoded rules?</b></summary>

All checks are structural (title-description consistency, duplicate content, proficiency-tenure). No role-specific rules. Same system works for any JD without modification.

</details>

<details>
<summary><b>Why importance-weighted skill matching?</b></summary>

A Civil Engineer matching 11/55 mostly-soft skills shouldn't outrank an AI Engineer matching 6/55 critical skills. Importance is derived from generic JD text signals, not role-specific lists.

</details>

<details>
<summary><b>Why external hosting for pre-computed data?</b></summary>

The ~820MB of embeddings exceed GitHub's 100MB limit. Git LFS free tier limits bandwidth (1GB/month). Google Drive hosting is unlimited and free.

</details>

---

## Reproducibility

Everything needed to reproduce the submission:

- ✅ Pre-computed embeddings — [Google Drive](https://drive.google.com/file/d/1p2HjVsxhfPI3YwqF25veBqQGa-HooywJ/view) via `download_precomputed.py`
- ✅ Profile cache — included in the download
- ✅ Submission CSV — committed at `backend/results/submission.csv`
- ✅ Dockerfile — builds a self-contained image

Judges can reproduce the exact output in **under 5 minutes** (including one-time data download).

---

## Limitations and Honest Tradeoffs

**What works well:**
- Catches obvious honeypots and keyword stuffers
- Generalizes to any JD without code changes
- Fully offline within hackathon constraints
- Explainable, hallucination-free reasoning

**What needs an LLM to do better:**
- Distinguishing genuine career transitioners from keyword stuffers
- Understanding subtle role suitability beyond structural signals
- Catching every honeypot (some require semantic reasoning)

In production, this system would serve as the fast retrieval layer, with an LLM re-ranker on the top 200-500 candidates — the two-stage architecture used by LinkedIn Recruiter and similar platforms.

---

## Tech Stack

**Backend** · Python 3.11+ · FastAPI · Sentence-Transformers · BGE-small-en-v1.5 · Qdrant · NumPy · RapidFuzz · python-docx · gdown

**Frontend** · React 18 · Vite · TailwindCSS · Framer Motion · Recharts

**Infrastructure** · Docker

---

<div align="center">

Built by **Team Quadzilla** for the Redrob India Runs Data & AI Challenge.

AI tools (Claude, ChatGPT, AmazonQ) were used as coding assistants.
All algorithmic decisions and the final implementation were validated by the team.

</div>
