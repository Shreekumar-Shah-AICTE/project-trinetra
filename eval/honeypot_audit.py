"""
honeypot_audit.py — Deep Honeypot Diagnostics for Project Trinetra (त्रिनेत्र)

Performs comprehensive honeypot analysis:
  1. How many honeypots did Guard Gate detect?
  2. Are any honeypots leaking into our Top 100?
  3. What check patterns fire most often?
  4. Are we OVER-flagging (false positives)?

The hackathon spec says:
  - ~80 honeypots exist in the dataset
  - Honeypot rate >10% in top 100 = DISQUALIFICATION

Usage:
    python eval/honeypot_audit.py --candidates data/candidates.jsonl --submission submission.csv
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
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

from src.guard_gate import run_guard_gate


def load_submission_ids(path: str) -> list[str]:
    """Load ranked candidate IDs from submission CSV."""
    ids = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ids.append(row["candidate_id"].strip())
    return ids


def main():
    ap = argparse.ArgumentParser(description="Trinetra Honeypot Audit")
    ap.add_argument("--candidates", required=True, help="Path to candidates JSONL/JSON")
    ap.add_argument("--submission", default="submission.csv", help="Submission CSV")
    args = ap.parse_args()

    start = time.time()

    # Load candidates
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

    # Load submission if available
    top_100_ids = set()
    top_10_ids = set()
    submission_exists = os.path.exists(args.submission)
    if submission_exists:
        ranked_ids = load_submission_ids(args.submission)
        top_100_ids = set(ranked_ids[:100])
        top_10_ids = set(ranked_ids[:10])

    # Run Guard Gate on all candidates
    total = 0
    honeypots = []
    flagged_in_top100 = []
    flagged_in_top10 = []
    grade_counts = Counter()
    violation_types = Counter()

    for cand in candidates:
        total += 1
        cid = cand["candidate_id"]
        result = run_guard_gate(cand)
        grade_counts[result["trust_grade"]] += 1

        if result["is_hard_honeypot"]:
            profile = cand.get("profile", {})
            honeypots.append({
                "candidate_id": cid,
                "title": profile.get("current_title", ""),
                "company": profile.get("current_company", ""),
                "yoe": profile.get("years_of_experience", 0),
                "violations": result["violations"],
                "trust_score": result["trust_score"],
                "in_top100": cid in top_100_ids,
                "in_top10": cid in top_10_ids,
            })

            # Track violation types
            for v in result["violations"]:
                # Bucket by first 5 words
                key = " ".join(v.split()[:5])
                violation_types[key] += 1

            if cid in top_100_ids:
                flagged_in_top100.append(cid)
            if cid in top_10_ids:
                flagged_in_top10.append(cid)

    elapsed = time.time() - start

    # ── REPORT ──
    print()
    print("  === TRINETRA HONEYPOT AUDIT ===")
    print(f"  Scanned {total:,} candidates in {elapsed:.1f}s")
    print()
    print(f"  Hard honeypots detected: {len(honeypots)}")
    print(f"  Expected range: ~60-100 (spec says ~80)")
    print()

    # Trust grade distribution
    print("  Trust Grade Distribution:")
    for grade in ("A", "B", "C", "D", "F"):
        count = grade_counts[grade]
        pct = count / total * 100 if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"    {grade}: {count:6,} ({pct:5.1f}%) |{bar}")
    print()

    # Submission impact
    if submission_exists:
        honeypot_rate = len(flagged_in_top100) / 100
        print("  SUBMISSION IMPACT:")
        print(f"    Honeypots in Top 10:  {len(flagged_in_top10)} {'-- CRITICAL!' if flagged_in_top10 else '-- CLEAN'}")
        print(f"    Honeypots in Top 100: {len(flagged_in_top100)} ({honeypot_rate:.0%})")
        print(f"    DQ threshold: 10% (max 10 honeypots in top 100)")
        print()

        if honeypot_rate > 0.10:
            print("  ** DISQUALIFICATION RISK: Honeypot rate exceeds 10%! **")
        elif honeypot_rate > 0.05:
            print("  ** WARNING: Honeypot rate approaching danger zone **")
        elif len(flagged_in_top100) == 0:
            print("  VERDICT: PERFECT - Zero honeypots in submission")
        else:
            print(f"  VERDICT: SAFE - {len(flagged_in_top100)} honeypots (under 10% threshold)")
    else:
        print("  (No submission file found — skipping impact analysis)")
    print()

    # Violation type breakdown
    if violation_types:
        print("  Most Common Violation Patterns:")
        for pattern, count in violation_types.most_common(10):
            print(f"    {count:4d}x  {pattern}")
        print()

    # Sample honeypots
    if honeypots:
        print("  Sample Honeypots (first 5):")
        for hp in honeypots[:5]:
            flag = " ** IN TOP 100 **" if hp["in_top100"] else ""
            print(f"    {hp['candidate_id']}: {hp['title']} @ {hp['company']} | {hp['yoe']:.1f} yrs{flag}")
            if hp["violations"]:
                print(f"      Violations: {hp['violations'][0][:80]}")
        print()

    # Detection accuracy estimate
    if len(honeypots) < 40:
        print("  WARNING: Only detected {len(honeypots)} honeypots. Expected ~80.")
        print("  Guard Gate may be UNDER-detecting. Review check thresholds.")
    elif len(honeypots) > 150:
        print(f"  WARNING: Detected {len(honeypots)} honeypots. Expected ~80.")
        print("  Guard Gate may be OVER-flagging (false positives).")
    else:
        print(f"  Detection count ({len(honeypots)}) is within expected range (~80).")
    print()


if __name__ == "__main__":
    main()
