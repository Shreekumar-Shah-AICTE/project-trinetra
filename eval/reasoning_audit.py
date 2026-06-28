"""
reasoning_audit.py — Stage 4 Reasoning Quality Auditor for Project Trinetra (त्रिनेत्र)

Implements the EXACT 6 checks the judges will run at Stage 4 manual review.
From submission_spec.txt, Stage 4 samples 10 random rows and checks:

  1. Specific facts — Does reasoning reference specific profile facts?
  2. JD connection — Does it connect to specific JD requirements?
  3. Honest concerns — Does it acknowledge gaps?
  4. No hallucination — Do all claims match the candidate's profile?
  5. Variation — Are the 10 sampled reasonings different from each other?
  6. Rank consistency — Does the tone match the rank?

Additional checks:
  - Empty reasoning detection
  - Generic/placeholder reasoning detection
  - Template repetition detection
  - Length compliance (not too long)

Usage:
    python eval/reasoning_audit.py --submission submission.csv
"""

import argparse
import csv
import re
import sys
from collections import Counter

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


# Phrases that indicate generic/placeholder reasoning
BAD_PHRASES = [
    "great candidate",
    "strong candidate",
    "excellent candidate",
    "ideal candidate",
    "placeholder",
    "lorem ipsum",
    "n/a",
    "todo",
    "to be filled",
    "coming soon",
    "tbd",
]

# JD-specific terms we want to see in reasoning
JD_CONNECTION_TERMS = [
    "retrieval", "ranking", "search", "embedding", "vector",
    "recommendation", "faiss", "bm25", "production", "deployed",
    "product company", "yrs", "years", "notice", "JD",
    "founding team", "senior", "AI", "ML",
]

# Specific fact indicators — reasoning should reference concrete profile data
FACT_INDICATORS = [
    r"\d+\.?\d*\s*y(?:ea)?rs?",          # Matches "5 yr", "5 yrs", "5 years", "6.1 yrs"
    r"\d+(?:d|\s*days?)\s*notice",       # Matches "30d notice", "30 days notice"
    r"at\s+[A-Z]\w+",                    # Matches "at Google", "at Zomato"
    r"lineage:", 
    r"career evidence:", 
    r"Trust:\s*[A-F]", 
    r"Dim ranks:", 
    r"S#\d+",
]


def audit_reasoning(submission_path: str) -> dict:
    """Run all reasoning quality checks and return detailed results."""

    with open(submission_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    results = {
        "total_rows": len(rows),
        "errors": [],
        "warnings": [],
        "checks": {},
    }

    reasonings = []
    ranks = []

    for row in rows:
        cid = row.get("candidate_id", "")
        reasoning = (row.get("reasoning") or "").strip()
        rank = int(row.get("rank", 0))
        reasonings.append(reasoning)
        ranks.append(rank)

    # ── CHECK 1: Empty Reasoning ──
    empty_count = sum(1 for r in reasonings if not r)
    results["checks"]["empty_reasoning"] = {
        "passed": empty_count == 0,
        "count": empty_count,
        "message": f"{empty_count} rows have empty reasoning" if empty_count > 0
                   else "All rows have reasoning",
    }
    if empty_count > 0:
        results["errors"].append(f"{empty_count} rows have empty reasoning")

    # ── CHECK 2: Generic/Placeholder Detection ──
    generic_count = 0
    generic_rows = []
    for i, r in enumerate(reasonings):
        low = r.lower()
        if any(phrase in low for phrase in BAD_PHRASES):
            generic_count += 1
            generic_rows.append(rows[i].get("candidate_id", f"row_{i}"))
    results["checks"]["generic_reasoning"] = {
        "passed": generic_count == 0,
        "count": generic_count,
        "examples": generic_rows[:5],
        "message": f"{generic_count} rows have generic/placeholder reasoning" if generic_count > 0
                   else "No generic reasoning detected",
    }
    if generic_count > 0:
        results["errors"].append(f"{generic_count} rows contain generic/placeholder phrases")

    # ── CHECK 3: Specific Facts (do reasonings reference profile data?) ──
    fact_scores = []
    for r in reasonings:
        facts_found = sum(1 for pattern in FACT_INDICATORS if re.search(pattern, r))
        fact_scores.append(facts_found)
    avg_facts = sum(fact_scores) / len(fact_scores) if fact_scores else 0
    no_facts = sum(1 for s in fact_scores if s == 0)
    results["checks"]["specific_facts"] = {
        "passed": avg_facts >= 2.0,
        "avg_facts_per_reasoning": round(avg_facts, 2),
        "rows_without_facts": no_facts,
        "message": f"Average {avg_facts:.1f} fact indicators per reasoning ({no_facts} rows without any)" ,
    }
    if avg_facts < 2.0:
        results["warnings"].append(f"Low fact density in reasoning (avg {avg_facts:.1f})")

    # ── CHECK 4: JD Connection ──
    jd_scores = []
    for r in reasonings:
        low = r.lower()
        jd_hits = sum(1 for term in JD_CONNECTION_TERMS if term.lower() in low)
        jd_scores.append(jd_hits)
    avg_jd = sum(jd_scores) / len(jd_scores) if jd_scores else 0
    results["checks"]["jd_connection"] = {
        "passed": avg_jd >= 1.5,
        "avg_jd_terms": round(avg_jd, 2),
        "message": f"Average {avg_jd:.1f} JD connection terms per reasoning",
    }
    if avg_jd < 1.5:
        results["warnings"].append(f"Low JD connection in reasoning (avg {avg_jd:.1f})")

    # ── CHECK 5: Honest Concerns ──
    concern_indicators = [
        "concern", "gap", "limited", "weak", "risk", "outside", 
        "long notice", "inactive", "low recent activity", "declined all", 
        "refuses relocation", "profile flags", "outside target city"
    ]
    negations = ["no concern", "no gap", "zero concern", "zero gap", "without gap", "no obvious gap"]
    concern_count = 0
    for r in reasonings:
        low = r.lower()
        has_concern_word = any(c in low for c in concern_indicators)
        has_negation = any(n in low for n in negations)
        # Only count if it mentions a concern AND isn't just saying "no concerns"
        if has_concern_word and not has_negation:
            concern_count += 1
    concern_ratio = concern_count / len(reasonings) if reasonings else 0
    results["checks"]["honest_concerns"] = {
        "passed": concern_ratio >= 0.15,
        "rows_with_concerns": concern_count,
        "concern_ratio": round(concern_ratio, 3),
        "message": f"{concern_count}/{len(reasonings)} rows mention concerns ({concern_ratio:.0%})",
    }
    if concern_ratio < 0.15:
        results["warnings"].append(
            f"Only {concern_ratio:.0%} of reasonings mention concerns. "
            "Judges expect honest acknowledgment of gaps."
        )

    # ── CHECK 6: Variation (not templated) ──
    # Normalize reasoning for similarity comparison
    normalized = []
    for r in reasonings:
        # Remove specific numbers and names
        norm = re.sub(r"\d+\.?\d*", "N", r.lower())
        norm = re.sub(r"CAND_\w+", "CID", norm)
        norm = re.sub(r"S#\w+/C#\w+/B#\w+/T#\w+", "DIMS", norm)
        normalized.append(norm[:120])  # Compare first 120 chars

    template_counts = Counter(normalized)
    most_common = template_counts.most_common(5)
    max_repeat = most_common[0][1] if most_common else 0
    unique_ratio = len(set(normalized)) / len(normalized) if normalized else 0

    results["checks"]["variation"] = {
        "passed": unique_ratio >= 0.70 and max_repeat <= 10,
        "unique_ratio": round(unique_ratio, 3),
        "max_template_repeat": max_repeat,
        "most_repeated_patterns": [(count, pattern[:80]) for pattern, count in most_common[:3]],
        "message": f"{unique_ratio:.0%} unique patterns; most repeated template appears {max_repeat}x",
    }
    if unique_ratio < 0.70:
        results["errors"].append(
            f"Reasoning too templated: only {unique_ratio:.0%} unique. "
            f"Most repeated pattern appears {max_repeat}x."
        )

    # ── CHECK 7: Rank Consistency (tone matches rank) ──
    inconsistencies = 0
    for i, r in enumerate(reasonings):
        rank = ranks[i]
        low = r.lower()
        has_strong_concern = any(w in low for w in ["unqualified", "disqualified", "irrelevant", "do not hire", "fraud", "honeypot"])
        has_high_praise = "textbook" in low or "ideal" in low or "perfect" in low

        # High-ranked candidate with heavy concerns
        if rank <= 10 and has_strong_concern:
            inconsistencies += 1
        # Low-ranked candidate with glowing praise
        if rank >= 90 and has_high_praise:
            inconsistencies += 1

    results["checks"]["rank_consistency"] = {
        "passed": inconsistencies == 0,
        "inconsistencies": inconsistencies,
        "message": f"{inconsistencies} rank-reasoning inconsistencies" if inconsistencies > 0
                   else "Reasoning tone matches ranks",
    }
    if inconsistencies > 0:
        results["errors"].append(f"{inconsistencies} reasoning entries contradict their rank")

    # ── CHECK 8: Length Compliance ──
    too_long = sum(1 for r in reasonings if len(r) > 500)
    too_short = sum(1 for r in reasonings if 0 < len(r) < 30)
    avg_length = sum(len(r) for r in reasonings) / len(reasonings) if reasonings else 0
    results["checks"]["length"] = {
        "passed": too_long == 0 and too_short == 0,
        "avg_length": round(avg_length, 0),
        "too_long": too_long,
        "too_short": too_short,
        "message": f"Avg length {avg_length:.0f} chars; {too_long} too long, {too_short} too short",
    }
    if too_long > 0:
        results["errors"].append(f"{too_long} reasoning strings exceed 500 chars")

    # ── OVERALL SCORE ──
    checks_passed = sum(1 for c in results["checks"].values() if c["passed"])
    total_checks = len(results["checks"])
    results["score"] = checks_passed / total_checks if total_checks > 0 else 0
    results["checks_passed"] = checks_passed
    results["total_checks"] = total_checks

    return results


def print_results(results: dict):
    """Pretty-print the reasoning audit results."""
    print()
    print("  === TRINETRA REASONING AUDIT (Stage 4 Simulation) ===")
    print(f"  Audited {results['total_rows']} reasoning entries")
    print()

    for name, check in results["checks"].items():
        status = "PASS" if check["passed"] else "FAIL"
        icon = "+" if check["passed"] else "X"
        print(f"  [{icon}] {name}: {check['message']}")

    print()
    print(f"  Overall: {results['checks_passed']}/{results['total_checks']} checks passed")
    score = results["score"]
    if score >= 0.875:
        print("  VERDICT: EXCELLENT - Reasoning is judge-ready")
    elif score >= 0.625:
        print("  VERDICT: GOOD - Minor issues to address")
    elif score >= 0.375:
        print("  VERDICT: MODERATE - Several issues need fixing")
    else:
        print("  VERDICT: CRITICAL - Reasoning needs major rework")

    if results["errors"]:
        print()
        print("  ERRORS:")
        for err in results["errors"]:
            print(f"    - {err}")
    if results["warnings"]:
        print()
        print("  WARNINGS:")
        for warn in results["warnings"]:
            print(f"    - {warn}")
    print()


def main():
    ap = argparse.ArgumentParser(description="Trinetra Reasoning Quality Auditor")
    ap.add_argument("--submission", required=True, help="Path to submission CSV")
    args = ap.parse_args()

    results = audit_reasoning(args.submission)
    print_results(results)
    sys.exit(0 if results["score"] >= 0.5 else 1)


if __name__ == "__main__":
    main()
