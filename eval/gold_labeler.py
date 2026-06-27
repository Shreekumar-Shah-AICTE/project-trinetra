"""
gold_labeler.py — Independent Proxy Gold Label Generator for Project Trinetra (त्रिनेत्र)

CRITICAL DESIGN PRINCIPLE: This labeler is DELIBERATELY independent of our
ranking engine. It uses DIFFERENT signals, DIFFERENT weights, and DIFFERENT
logic. If we used the same scoring as our ranker, the evaluation would be
circular (measuring the ranker against itself).

Relevance tiers (0-4), modeled on how a human recruiter reads the JD:
  4 = Textbook fit — Senior AI/ML engineer, 5-9 yrs, built retrieval/ranking/
      search systems in production at product companies, active on platform
  3 = Strong fit — Relevant AI/ML title with some systems depth, minor gaps
      (experience slightly outside band, or missing one dimension)
  2 = Adjacent fit — Non-AI title but career clearly describes building
      retrieval/ranking/recommendation systems (these are "plain-language gems")
  1 = Weak fit — Some AI/ML background but unclear depth or wrong sub-field
  0 = Irrelevant — Wrong domain entirely, or honeypot

This generates labels for ALL candidates, then eval/metrics.py scores our
submission against these labels.

Usage:
    python eval/gold_labeler.py --candidates data/candidates.jsonl --out eval/gold_auto.csv
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


# ──────────────────────────────────────────────────────────────────────
#  LABELER-SPECIFIC CONSTANTS
#  These are intentionally DIFFERENT from jd.py / rankers.py
# ──────────────────────────────────────────────────────────────────────

# Senior AI/ML titles that are direct JD matches
SENIOR_AI_TITLES = (
    "ai engineer", "machine learning engineer", "ml engineer",
    "applied scientist", "search engineer", "ranking engineer",
    "recommendation engineer", "nlp engineer", "applied ml",
    "staff machine learning", "senior machine learning",
    "senior ai", "senior nlp", "research engineer",
    "data scientist",  # can be relevant if career shows systems
)

# Adjacent titles — could be gems if career text shows real systems work
ADJACENT_TITLES = (
    "software engineer", "backend engineer", "data engineer",
    "full stack developer", "platform engineer", "developer",
    "senior software engineer", "staff software engineer",
)

# Definitively wrong-domain titles — JD explicitly excludes these
WRONG_DOMAIN_TITLES = (
    "hr manager", "marketing manager", "sales executive", "content writer",
    "graphic designer", "accountant", "financial analyst", "operations manager",
    "mechanical engineer", "civil engineer", "electrical engineer",
    "business analyst", "project manager", "product manager",
    "customer support", "customer success", "recruiter",
    "teacher", "professor", "lawyer", "doctor", "nurse",
)

# Verbs that indicate BUILDING systems (not just using tools)
BUILD_VERBS = (
    "built", "build", "building", "shipped", "ship", "shipping",
    "deployed", "deploying", "designed", "designing",
    "implemented", "implementing", "developed", "developing",
    "owned", "led", "launched", "launching", "scaled", "scaling",
    "architected", "created", "engineered",
)

# Systems that the JD specifically wants experience with
RELEVANT_SYSTEMS = (
    "retrieval", "ranking", "rank", "recommendation", "recommender",
    "search relevance", "semantic search", "embedding", "vector search",
    "learning to rank", "faiss", "bm25", "personalization", "matching",
    "information retrieval", "reranking", "re-ranking",
    "search engine", "search system", "search infrastructure",
    "candidate matching", "talent matching",
)


# ──────────────────────────────────────────────────────────────────────
#  HONEYPOT DETECTION (independent of guard_gate.py)
# ──────────────────────────────────────────────────────────────────────

FICTIONAL_COMPANIES = {
    "pied piper", "hooli", "raviga capital", "bachmanity",
    "wayne enterprises", "wayne industries", "stark industries",
    "initech", "intertrode", "dunder mifflin",
    "acme corp", "acme corporation", "acme inc",
    "globex", "globex corporation", "umbrella corporation",
    "cyberdyne systems", "cyberdyne", "tyrell corporation",
    "weyland-yutani", "weyland yutani", "oscorp", "lexcorp",
    "massive dynamic", "prestige worldwide", "virtucon",
    "soylent corp",
}


def _is_honeypot(candidate: dict) -> bool:
    """Independent honeypot detection for the labeler.
    Uses simpler, high-confidence checks — not our full Guard Gate.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    ref_year = 2026

    chrono_violations = 0

    for job in career:
        company = (job.get("company") or "").lower()
        if company in FICTIONAL_COMPANIES:
            chrono_violations += 1

        start = job.get("start_date", "")
        end = job.get("end_date", "")
        claimed_months = job.get("duration_months", 0)

        if start and end and not job.get("is_current", False):
            try:
                from datetime import datetime
                s = datetime.strptime(start, "%Y-%m-%d")
                e = datetime.strptime(end, "%Y-%m-%d")
                actual_months = (e.year - s.year) * 12 + (e.month - s.month)
                if actual_months < 0:
                    chrono_violations += 1
                elif claimed_months > actual_months * 2 and claimed_months - actual_months > 12:
                    chrono_violations += 1
            except (ValueError, TypeError):
                pass

    # Expert skills with 0 months — classic honeypot pattern
    expert_zero = sum(
        1 for s in skills
        if s.get("proficiency") == "expert"
        and s.get("duration_months", 0) == 0
        and s.get("endorsements", 0) <= 1
    )

    # YOE vs education check
    yoe = profile.get("years_of_experience", 0)
    edu_start_years = [
        e.get("start_year", 9999)
        for e in candidate.get("education", [])
        if e.get("start_year", 0) > 0
    ]
    if edu_start_years:
        min_edu_start = min(edu_start_years)
        max_possible_yoe = ref_year - min_edu_start + 2
        if yoe > max_possible_yoe and yoe > 5:
            chrono_violations += 1

    return (
        chrono_violations >= 2
        or expert_zero >= 8
        or (chrono_violations >= 1 and expert_zero >= 6)
    )


# ──────────────────────────────────────────────────────────────────────
#  LABELING LOGIC
# ──────────────────────────────────────────────────────────────────────

def _get_career_text(candidate: dict) -> str:
    """Combine all career descriptions into searchable text."""
    career = candidate.get("career_history", [])
    parts = []
    for job in career:
        desc = job.get("description", "")
        title = job.get("title", "")
        if desc:
            parts.append(desc)
        if title:
            parts.append(title)
    return " ".join(parts).lower()


def _describes_real_systems(text: str) -> bool:
    """Does the career text show BUILDING relevant systems?"""
    has_build = any(v in text for v in BUILD_VERBS)
    has_sys = any(s in text for s in RELEVANT_SYSTEMS)
    return has_build and has_sys


def _has_production_depth(text: str) -> bool:
    """Does the career text show production deployment experience?"""
    prod_markers = (
        "production", "deployed to", "million users", "real users",
        "latency", "throughput", "served", "scale", "load balancer",
        "monitoring", "alerting", "ci/cd", "kubernetes", "docker",
    )
    return sum(1 for m in prod_markers if m in text) >= 2


def label_candidate(candidate: dict) -> int:
    """Assign a relevance tier 0-4 to a candidate.
    
    This is the core labeling function. It must be INDEPENDENT of our
    scoring engine to avoid circular evaluation.
    """
    # Check honeypot first
    if _is_honeypot(candidate):
        return 0

    profile = candidate.get("profile", {})
    title = (profile.get("current_title") or "").lower()
    headline = (profile.get("headline") or "").lower()
    yoe = profile.get("years_of_experience", 0)
    career_text = _get_career_text(candidate)
    signals = candidate.get("redrob_signals", {})

    # Title classification
    is_senior_ai = any(t in title or t in headline for t in SENIOR_AI_TITLES)
    is_adjacent = any(t in title or t in headline for t in ADJACENT_TITLES)
    is_wrong = any(t in title or t in headline for t in WRONG_DOMAIN_TITLES)

    # Career evidence
    has_real_systems = _describes_real_systems(career_text)
    has_production = _has_production_depth(career_text)

    # Experience band checks
    in_sweet_spot = 5.0 <= yoe <= 9.0
    in_acceptable = 4.0 <= yoe <= 11.0

    # ── TIER 0: Definitively irrelevant ──
    if is_wrong and not has_real_systems:
        return 0

    # ── TIER 4: Textbook fit ──
    if is_senior_ai and has_real_systems and in_sweet_spot:
        if has_production:
            return 4
        return 4  # Systems evidence + right title + right YOE = tier 4

    # ── TIER 3: Strong fit with minor gaps ──
    if is_senior_ai and has_real_systems and in_acceptable:
        return 3
    if is_senior_ai and in_sweet_spot:
        return 3  # Right title and experience, may lack specific systems proof
    if is_senior_ai and has_real_systems:
        return 3  # Has systems but YOE outside sweet spot

    # ── TIER 2: Adjacent / "plain-language gem" ──
    if is_adjacent and has_real_systems:
        return 2  # This is THE gem the JD talks about
    if is_senior_ai and in_acceptable:
        return 2  # AI title + ok experience
    if is_senior_ai:
        return 2  # AI title but weaker signals
    if has_real_systems and in_acceptable:
        return 2  # Systems evidence with off-title

    # ── TIER 1: Weakly relevant ──
    if is_adjacent and in_acceptable:
        return 1
    if is_adjacent:
        return 1
    if is_wrong and has_real_systems:
        return 1  # Wrong title but somehow built relevant systems

    # ── TIER 0: Everything else ──
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Trinetra Gold Labeler - Independent proxy gold label generator"
    )
    ap.add_argument("--candidates", required=True, help="Path to candidates JSONL/JSON file")
    ap.add_argument("--out", default="eval/gold_auto.csv", help="Output gold labels CSV")
    args = ap.parse_args()

    start = time.time()
    counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    total = 0

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    # Determine file format
    ext = os.path.splitext(args.candidates)[1].lower()

    with open(args.out, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["candidate_id", "tier"])

        if ext == ".json":
            with open(args.candidates, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates = data if isinstance(data, list) else [data]
            for c in candidates:
                tier = label_candidate(c)
                counts[tier] += 1
                total += 1
                writer.writerow([c["candidate_id"], tier])
        else:
            with open(args.candidates, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tier = label_candidate(c)
                    counts[tier] += 1
                    total += 1
                    writer.writerow([c["candidate_id"], tier])

    elapsed = time.time() - start

    print()
    print("  === TRINETRA GOLD LABELER ===")
    print(f"  Labeled {total:,} candidates in {elapsed:.1f}s -> {args.out}")
    print()
    for t in (4, 3, 2, 1, 0):
        pct = counts[t] / total * 100 if total > 0 else 0
        bar = "#" * int(pct)
        print(f"  Tier {t}: {counts[t]:6,} ({pct:5.1f}%)  |{bar}")
    print()


if __name__ == "__main__":
    main()
