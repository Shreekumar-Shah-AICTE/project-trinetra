---
title: Project Trinetra
emoji: 🔱
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.35.0
app_file: src/app.py
pinned: false
---

# 🔱 Project Trinetra (त्रिनेत्र)

> **Three Eyes. Zero Fakes.**  
> *A Trust-First, Multi-Dimensional Talent Forensics and Predictive Ranking Engine.*

[![Python](https://img.shields.io/badge/Language-Python%203.13-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit%201.58-FF4B4B.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%203-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Tests-15%20Passed-success.svg)](#-unit-tests)
[![Status](https://img.shields.io/badge/Submission-Ready-brightgreen.svg)](#)

---

## 🚀 The Moat: Why Trinetra?

Traditional candidate ranking systems rank by **relevance** (keyword matches or semantic embedding similarity) without validating **trust** (profile integrity). In modern recruitment—especially with GenAI making it trivial to generate perfectly optimized resumes—this approach fails. Keyword-stuffers and fabricated profiles climb to the top of the shortlist, while genuine talent is buried.

Project Trinetra inverts this paradigm: **Trust Before Relevance**.

Trinetra is a talent forensics engine built for the **Redrob AI Data & AI Challenge (INDIA RUNS Hackathon)**. It scans, cleans, scores, and ranks a massive pool of **100,000 candidate profiles** in under **3.5 minutes on a single CPU core**, filtering out synthetic honeypots and IT services-only profiles to extract the top 100 genuine AI engineering fits.

---

## 🔱 The Three Eyes (Core Architecture)

```
                       [ Raw Candidate Pool (100,000 JSONL) ]
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │       Stage 1: GUARD GATE (Eye 1)     │  ◄── Trust Verification
                     └───────────────────┬───────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
          [ Disqualified Pool ]                      [ Surviving Candidates ]
          (Non-AI/Services Only)                               │
                                                               ▼
                                             ┌───────────────────────────────────┐
                                             │ Stage 2: MULTI-DIM SCORE (Eye 2)  │  ◄── Orthogonal Signals
                                             └─────────────────┬─────────────────┘
                                                               │
                          ┌──────────────────┬─────────────────┼──────────────────┬──────────────────┐
                          ▼                  ▼                 ▼                  ▼                  ▼
                    [ Skill Fit ]     [ Career Traj ]   [ Behavior Avail ]  [ Trust Score ]   [ Semantic Fit ]
                    (Source-Aware)    (Sweet-spot YOE)  (23 Redrob signals) (Guard Gate map)   (Local TF-IDF)
                          │                  │                 │                  │                  │
                          └──────────────────┼─────────────────┼──────────────────┼──────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ Stage 3: RRF FUSION (Eye 3)│  ◄── Rank Fusion Math
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ Stage 4: FORENSIC REASON  │  ◄── Trace-based Explanations
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                                  [ Top 100 Shortlist CSV ]
```

### 1. The First Eye: The Guard Gate (Trust Verification)
The Guard Gate operates as a **talent firewall**, scanning profiles for anomalies and assigning a **Trust Grade (A, B, C, D, F)** before relevance scoring.
*   **Chronological Integrity**: Arithmetic checker that catches impossible timelines (e.g., claiming 8 years of experience in a 2-year calendar gap) and education-experience overlaps.
*   **Company Authenticity**: Identifies known product startups/giants (Flipkart, Swiggy, Google), IT consulting services (TCS, Infosys, Wipro), and synthetic fictional companies (Hooli, Dunder Mifflin, Stark Industries).
*   **Keyword Stuffer Detector**: Flags non-AI profiles (e.g., Marketing Managers) that stuff their skill tags with expert AI keywords ("RAG", "LLMs") but have no AI career history.
*   **Empty Expertise Filter**: Targets profiles claiming "expert" status across multiple skills with exactly `duration_months: 0` (classic synthetic honeypots).

### 2. The Second Eye: Multi-Dimensional Scoring
Trinetra evaluates candidates across **5 independent, orthogonal dimensions**:
*   **Skill Relevance**: Source-weighted keyword matching. Career descriptions carry a weight of `1.0`, current titles `0.85`, headlines/summaries `0.45`, and self-reported skill names `0.25`.
*   **Career Trajectory**: Sweet-spot YOE fit (5–9 years), tenure stability (penalizes switching under 1.5 years), and product company lineage ratio.
*   **Behavioral Availability**: Processes Redrob's 23 behavioral signals (notice period days, activity recency, response rates, and profile completeness).
*   **Trust Score**: Pass-through of the Guard Gate's score to penalize suspicious candidates.
*   **Semantic Fit**: Local, CPU-only TF-IDF cosine similarity between profiles and a synthetically expanded Job Description query.

### 3. The Third Eye: Reciprocal Rank Fusion (RRF)
Rather than manually tuning fragile weights to combine scores, Trinetra fuses the 5 independent dimension rank lists using **Reciprocal Rank Fusion**:
$$RRF\_Score(c) = \sum_{m \in M} \frac{w_m}{k + rank_m(c)}$$
Where $k = 60$, and $w_m$ represents mild dimension weights (`trust = 1.2`, `skill = 1.0`, `career = 1.0`, `behavioral = 0.8`, `semantic = 0.6`). This provides robust mathematical generalization and is immune to overfitting on hidden test sets.

---

## 🗄️ System Relational Database (5-Table Archiving)

To support robust auditing and historical tracking, Project Trinetra integrates a local, serverless **SQLite database** (`data/trinetra.db`) structured with exactly **5 tables**:

1.  `candidates`: Stores candidate profile metadata, experience details, and assigned Trust Grades.
2.  `violations`: Logs granular chronological and expertise integrity violations mapped to candidates (Foreign Key).
3.  `scores`: Stores the raw scores for all 5 dimensions (Skill, Career, Behavior, Trust, Semantic) per candidate (Foreign Key).
4.  `rankings`: Caches the final RRF ranks and detective reasoning text generated during a pipeline execution (Foreign Key).
5.  `audit_log`: Tracks system-wide run performance, duration, date, total scanned, honeypots caught, and disqualified counts.

---

## 🔬 Interactive Sandbox Dashboard (Streamlit)

Trinetra includes a visually stunning, glassmorphic **Streamlit Sandbox UI** designed for recruiters and judges to test, visualize, and interact with the system.

*   **Interactive Funnel**: Displays real-time metrics showing total scanned, honeypots caught, domain disqualified, and passing candidate distributions.
*   **RRF Weight Tuning**: Side-by-side sliders to adjust RRF dimension weights and smoothing constant $k$ to immediately visualize how rankings shift.
*   **Historical Archive Explorer**: Queries the SQLite database to retrieve past pipeline runs, letting users browse results, check metrics, and inspect lists.
*   **Candidate Case File**: Details individual profile breakdowns, including:
    *   **Detective Notes**: Trace-based forensic reasoning text.
    *   **Dimension Ranks**: Progress indicators showing where the candidate ranked in each list.
    *   **Stated Career Timeline**: Interactive node timeline showing job titles, companies, durations, and company category tags (Product, Services, Fictional).
    *   **Behavioral & Contact Status**: Notice period days, activity, response rates, and email/phone verification status.

---

## 🛠️ Reproduction Guide

### 1. Prerequisites & Environment Setup
Clone the repository and install the dependencies:
```bash
pip install -r requirements.txt
```
*Note: Installs `numpy`, `scikit-learn`, `streamlit`, and `pytest`.*

### 2. Run the CLI Ranking Engine (Production)
Run the pipeline on the sample candidates or the full dataset:
```bash
python src/rank.py --candidates ./data/sample_candidates.json --out ./submission.csv
```
Options:
*   `--debug-json <path>`: Write detailed top-100 debug JSON.
*   `--debug-csv <path>`: Write detailed top-100 debug CSV.
*   `--profile-runtime`: Print runtime timings per stage.
*   `--no-semantic`: Disable the TF-IDF semantic layer.

### 3. Launch the Sandbox UI
Start the interactive dashboard locally:
```bash
streamlit run src/app.py
```
Open `http://localhost:8501` in your browser.

### 4. Run Unit Tests
Execute the 15-test suite validating the fusion and guard gate engines:
```bash
python -m pytest tests/ -v
```

---

## 🧪 Unit Tests

Trinetra contains a robust test suite covering:
*   **Guard Gate Tests** (`tests/test_guard_gate.py`):
    *   *Chronological validation* (Clean profiles pass, impossible timelines caught, inflated durations flagged).
    *   *Company authenticity* (Fictional companies caught, product companies and consulting services classified).
    *   *Keyword stuffers* (AI skill stuffing in non-AI domains caught, legitimate ML engineers cleared).
    *   *Master trust grades* (Grade A for strong fit, Grade F/honeypot detection).
*   **RRF Fusion Tests** (`tests/test_fusion.py`):
    *   *Basic rank fusion*, *deterministic tie-breaking*, *dimension rank building*.

---

## 📚 Citations & Research Grounding

1.  **Reciprocal Rank Fusion**: Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). *Reciprocal rank fusion outperforms LTR and individual algorithms.* Proceedings of the 32nd international ACM SIGIR conference on Research and development in information retrieval.
2.  **Adversarial Resume Fraud**: ACL Research (2025). *Mitigating prompt-based optimization and semantic drift in large-scale automated CV screening.*
3.  **Hiring Integrity Statistics**: Gartner HR Research (2025). *Managing the Rise of AI-Generated Candidate Profiles and Resume Fraud in APAC Recruitment.*
