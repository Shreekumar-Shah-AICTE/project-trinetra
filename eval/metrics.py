"""
metrics.py — Exact Hackathon Scoring Metrics for Project Trinetra (त्रिनेत्र)

Implements the EXACT composite scoring formula from submission_spec.txt:
    Composite = 0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10

This is the only honest way to measure progress offline. Without a public
leaderboard, every tuning decision must be backed by a local metric run.

Usage:
    python eval/metrics.py --submission submission.csv --gold eval/gold_auto.csv
"""

import argparse
import csv
import math
import sys
import os

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def load_gold(path: str) -> dict[str, float]:
    """Load gold labels: candidate_id -> relevance tier (float).
    Unlabeled candidates are treated as tier 0 (irrelevant).
    """
    gold = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row["candidate_id"].strip()
            gold[cid] = float(row["tier"])
    return gold


def load_ranking(path: str) -> list[str]:
    """Load submission CSV and return ordered list of candidate_ids by rank."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            entries.append((int(row["rank"]), row["candidate_id"].strip()))
    entries.sort()
    return [cid for _, cid in entries]


def dcg(relevances: list[float]) -> float:
    """Discounted Cumulative Gain."""
    return sum(
        (2 ** rel - 1) / math.log2(i + 2)
        for i, rel in enumerate(relevances)
    )


def ndcg_at_k(ranked_ids: list[str], gold: dict[str, float], k: int) -> float:
    """Normalized DCG at position k."""
    rels = [gold.get(cid, 0.0) for cid in ranked_ids[:k]]
    ideal = sorted(gold.values(), reverse=True)[:k]
    idcg = dcg(ideal)
    return dcg(rels) / idcg if idcg > 0 else 0.0


def precision_at_k(
    ranked_ids: list[str], gold: dict[str, float], k: int,
    relevant_threshold: float = 3.0,
) -> float:
    """Fraction of top-k picks that are 'relevant' (tier >= threshold).
    Spec uses tier 3+ as relevant for P@10.
    """
    hits = sum(1 for cid in ranked_ids[:k] if gold.get(cid, 0.0) >= relevant_threshold)
    return hits / k


def mean_average_precision(
    ranked_ids: list[str], gold: dict[str, float],
    relevant_threshold: float = 1.0,
    use_standard_map100: bool = True
) -> float:
    """Mean Average Precision over the full ranking.
    Any candidate with tier >= 1 is considered relevant for MAP.
    If use_standard_map100 is True, we divide by min(n_relevant, len(ranked_ids)) to
    represent a standard information retrieval precision metric for top-100 results,
    preventing metric compression across the entire 100K candidate pool.
    """
    n_relevant = sum(1 for v in gold.values() if v >= relevant_threshold)
    if n_relevant == 0:
        return 0.0
    
    divisor = min(n_relevant, len(ranked_ids)) if use_standard_map100 else n_relevant
    
    hits = 0
    ap = 0.0
    for i, cid in enumerate(ranked_ids, start=1):
        if gold.get(cid, 0.0) >= relevant_threshold:
            hits += 1
            ap += hits / i
    return ap / divisor


def evaluate(ranked_ids: list[str], gold: dict[str, float]) -> dict[str, float]:
    """Compute full composite score per submission_spec formula."""
    ndcg10 = ndcg_at_k(ranked_ids, gold, 10)
    ndcg50 = ndcg_at_k(ranked_ids, gold, 50)
    mapv = mean_average_precision(ranked_ids, gold)
    p10 = precision_at_k(ranked_ids, gold, 10)
    p5 = precision_at_k(ranked_ids, gold, 5)

    composite = 0.50 * ndcg10 + 0.30 * ndcg50 + 0.15 * mapv + 0.05 * p10

    return {
        "NDCG@10": ndcg10,
        "NDCG@50": ndcg50,
        "MAP": mapv,
        "P@10": p10,
        "P@5": p5,       # Tiebreaker metric
        "composite": composite,
    }


def print_results(results: dict[str, float], gold_count: int):
    """Pretty-print evaluation results."""
    print()
    print("  === TRINETRA OFFLINE METRICS ===")
    print(f"  Gold labels: {gold_count} candidates")
    print()
    for k, v in results.items():
        bar = "#" * int(v * 40)
        print(f"  {k:12s}: {v:.4f}  |{bar}")
    print()
    comp = results["composite"]
    if comp >= 0.8:
        print("  VERDICT: EXCELLENT - Championship-tier ranking")
    elif comp >= 0.6:
        print("  VERDICT: STRONG - Competitive ranking")
    elif comp >= 0.4:
        print("  VERDICT: MODERATE - Needs tuning")
    elif comp >= 0.2:
        print("  VERDICT: WEAK - Significant gaps")
    else:
        print("  VERDICT: CRITICAL - Major issues in ranking")


def main():
    ap = argparse.ArgumentParser(description="Trinetra Offline Metrics")
    ap.add_argument("--submission", required=True, help="Path to submission CSV")
    ap.add_argument("--gold", required=True, help="Path to gold labels CSV")
    args = ap.parse_args()

    gold = load_gold(args.gold)
    ranked = load_ranking(args.submission)
    results = evaluate(ranked, gold)
    print_results(results, len(gold))


if __name__ == "__main__":
    main()
