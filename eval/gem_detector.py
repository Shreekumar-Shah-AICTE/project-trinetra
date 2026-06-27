"""
gem_detector.py — Plain-Language Gem Finder for Project Trinetra (त्रिनेत्र)

The JD explicitly says: candidates who don't use AI buzzwords but whose career
history shows they BUILT recommendation/search/retrieval systems at product
companies ARE a fit. These are the "hidden gems" that keyword-based systems
bury. If our engine buries them, we lose points.

This script:
1. Identifies ALL gems in the dataset (non-AI title + real systems career)
2. Checks where our ranker places them
3. Raises alarms if gems are buried below the top-100 cutoff

Usage:
    python eval/gem_detector.py --candidates data/candidates.jsonl --submission submission.csv
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# Titles that are NOT traditional AI/ML roles
AI_TITLES = (
    "ai engineer", "machine learning engineer", "ml engineer",
    "applied scientist", "search engineer", "ranking engineer",
    "recommendation engineer", "nlp engineer", "applied ml",
    "data scientist", "research scientist",
    "staff machine learning", "senior machine learning",
    "senior ai", "senior nlp",
)

# Evidence of BUILDING relevant systems
BUILD_VERBS = (
    "built", "build", "shipped", "deployed", "designed",
    "implemented", "developed", "owned", "led", "launched", "scaled",
    "architected", "engineered", "created",
)

RELEVANT_SYSTEMS = (
    "retrieval", "ranking", "recommendation", "recommender",
    "semantic search", "embedding", "vector search",
    "learning to rank", "faiss", "bm25", "personalization",
    "search relevance", "search engine", "search system",
    "matching", "reranking",
)


def _get_career_text(candidate: dict) -> str:
    """Combine career descriptions + titles."""
    career = candidate.get("career_history", [])
    parts = []
    for job in career:
        if job.get("description"):
            parts.append(job["description"])
        if job.get("title"):
            parts.append(job["title"])
    return " ".join(parts).lower()


def is_gem(candidate: dict) -> bool:
    """Is this candidate a 'plain-language gem'?
    
    Criteria:
    - NOT an AI/ML title (that would be an obvious match)
    - Career text shows BUILDING relevant systems
    - Reasonable experience range (4-11 years)
    """
    profile = candidate.get("profile", {})
    title = (profile.get("current_title") or "").lower()
    headline = (profile.get("headline") or "").lower()
    yoe = profile.get("years_of_experience", 0)

    # Must NOT have an AI title (otherwise it's not a "hidden" gem)
    if any(t in title or t in headline for t in AI_TITLES):
        return False

    # Must be in reasonable experience range
    if not (4.0 <= yoe <= 11.0):
        return False

    # Career text must show building relevant systems
    career_text = _get_career_text(candidate)
    import re
    has_build = any(re.search(r'\b' + re.escape(v) + r'\b', career_text) for v in BUILD_VERBS)
    has_system = any(re.search(r'\b' + re.escape(s) + r'\b', career_text) for s in RELEVANT_SYSTEMS)

    return has_build and has_system


def load_submission_ranks(path: str) -> dict[str, int]:
    """Load submission CSV and return {candidate_id: rank}."""
    ranks = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ranks[row["candidate_id"].strip()] = int(row["rank"])
    return ranks


def main():
    ap = argparse.ArgumentParser(description="Trinetra Gem Detector")
    ap.add_argument("--candidates", required=True, help="Path to candidates JSONL/JSON file")
    ap.add_argument("--submission", default="submission.csv", help="Current submission CSV")
    args = ap.parse_args()

    start = time.time()
    gems = []
    total = 0

    # Load submission ranks if available
    submission_ranks = {}
    if os.path.exists(args.submission):
        submission_ranks = load_submission_ranks(args.submission)

    # Scan all candidates
    ext = os.path.splitext(args.candidates)[1].lower()

    if ext == ".json":
        with open(args.candidates, "r", encoding="utf-8") as f:
            data = json.load(f)
            candidates = data if isinstance(data, list) else [data]
    else:
        candidates = []
        with open(args.candidates, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    for c in candidates:
        total += 1
        if is_gem(c):
            cid = c["candidate_id"]
            profile = c.get("profile", {})
            rank = submission_ranks.get(cid, None)
            gems.append({
                "candidate_id": cid,
                "title": profile.get("current_title", ""),
                "company": profile.get("current_company", ""),
                "yoe": profile.get("years_of_experience", 0),
                "location": profile.get("location", ""),
                "rank": rank,
            })

    elapsed = time.time() - start

    # Classify gems
    gems_in_top100 = [g for g in gems if g["rank"] is not None and g["rank"] <= 100]
    gems_in_top10 = [g for g in gems if g["rank"] is not None and g["rank"] <= 10]
    gems_buried = [g for g in gems if g["rank"] is None]

    print()
    print("  === TRINETRA GEM DETECTOR ===")
    print(f"  Scanned {total:,} candidates in {elapsed:.1f}s")
    print(f"  Found {len(gems)} plain-language gems (non-AI title, built real systems)")
    print()
    print(f"  Gems in Top 10:  {len(gems_in_top10)}")
    print(f"  Gems in Top 100: {len(gems_in_top100)}")
    print(f"  Gems BURIED:     {len(gems_buried)} (not in submission)")
    print()

    if gems_in_top100:
        print("  Top gems that MADE the cut:")
        for g in sorted(gems_in_top100, key=lambda x: x["rank"])[:15]:
            print(f"    Rank {g['rank']:3d} | {g['candidate_id']} | {g['title']} @ {g['company']} | {g['yoe']:.1f} yrs")
        print()

    if gems_buried:
        print("  Sample BURIED gems (WARNING — these might be scoring points we're missing):")
        for g in gems_buried[:10]:
            print(f"    BURIED | {g['candidate_id']} | {g['title']} @ {g['company']} | {g['yoe']:.1f} yrs")
        print()

    # Verdict
    if len(gems_in_top100) >= 5:
        print("  VERDICT: GOOD - Engine is surfacing plain-language gems")
    elif len(gems_in_top100) >= 2:
        print("  VERDICT: MODERATE - Some gems found, but room for improvement")
    else:
        print("  VERDICT: WARNING - Possible gem burial issue!")
    print()

    return {
        "total_gems": len(gems),
        "gems_in_top10": len(gems_in_top10),
        "gems_in_top100": len(gems_in_top100),
        "gems_buried": len(gems_buried),
    }


if __name__ == "__main__":
    main()
