"""
tuner.py — Hyperparameter Grid Search Optimizer for Project Trinetra (त्रिनेत्र)
🔱 Optimizes RRF weights by loading precomputed scores from SQLite.

Since scoring 100K candidates takes ~3 minutes but rank fusion takes milliseconds,
this script bypasses the scoring pipeline, loading candidates' raw scores from
the database and testing thousands of weight combinations in seconds.
"""

import sqlite3
import csv
import os
import sys
import time
from pathlib import Path
import math

# Force UTF-8 stdout/stderr encoding on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

DB_PATH = ROOT / "data" / "trinetra.db"
GOLD_PATH = ROOT / "eval" / "gold_auto.csv"


def load_gold_labels(path) -> dict[str, float]:
    """Loads gold labels from CSV."""
    gold = {}
    if not os.path.exists(path):
        print(f"ERROR: Gold labels file not found at {path}. Run trinetra_eval.py first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gold[row["candidate_id"].strip()] = float(row["tier"])
    return gold


def load_scores_from_db(db_path) -> list[dict]:
    """Loads all raw candidate scores from the SQLite database."""
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}. Run a full rank.py execution first to populate the DB.")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT s.candidate_id, s.skill_relevance, s.career_trajectory, s.behavioral_availability, s.trust_score, s.semantic_fit
        FROM scores s
        JOIN candidates c ON s.candidate_id = c.candidate_id
        WHERE c.disqualified = 0
          AND c.last_updated = (SELECT MAX(timestamp) FROM audit_log);
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ──────────────────────────────────────────────────────────────────────
#  FAST EVALUATION FUNCTIONS (Optimized for speed in grid search loops)
# ──────────────────────────────────────────────────────────────────────

def dcg(relevances: list[float]) -> float:
    return sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(relevances))


def evaluate_ranking(ranked_ids: list[str], gold: dict[str, float], ideal_dcg_10: float, ideal_dcg_50: float, n_relevant: int) -> float:
    """Fast composite evaluator using precalculated IDEAL DCG and relevant counts."""
    # NDCG@10
    rels10 = [gold.get(cid, 0.0) for cid in ranked_ids[:10]]
    dcg10 = sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels10))
    ndcg10 = dcg10 / ideal_dcg_10 if ideal_dcg_10 > 0 else 0.0
    
    # NDCG@50
    rels50 = [gold.get(cid, 0.0) for cid in ranked_ids[:50]]
    dcg50 = sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels50))
    ndcg50 = dcg50 / ideal_dcg_50 if ideal_dcg_50 > 0 else 0.0
    
    # P@10
    hits10 = sum(1 for r in rels10 if r >= 3.0)
    p10 = hits10 / 10.0
    
    # MAP
    if n_relevant == 0:
        mapv = 0.0
    else:
        hits = 0
        ap = 0.0
        for i, cid in enumerate(ranked_ids, start=1):
            if gold.get(cid, 0.0) >= 1.0:
                hits += 1
                ap += hits / i
        mapv = ap / n_relevant
        
    return 0.50 * ndcg10 + 0.30 * ndcg50 + 0.15 * mapv + 0.05 * p10


def run_optimizer():
    print()
    print("  ====================================================")
    print("  🔱 TRINETRA HYPERPARAMETER OPTIMIZER (THO)")
    print("  ====================================================")
    print("  Loading records from SQLite database...")
    
    scored_candidates = load_scores_from_db(DB_PATH)
    print(f"  Loaded {len(scored_candidates):,} active candidates.")
    
    gold = load_gold_labels(GOLD_PATH)
    print(f"  Loaded {len(gold):,} gold labels.")
    
    # Precalculate ideal DCGs and totals for speed
    ideal_list = sorted(gold.values(), reverse=True)
    ideal_dcg_10 = dcg(ideal_list[:10])
    ideal_dcg_50 = dcg(ideal_list[:50])
    n_relevant = sum(1 for v in gold.values() if v >= 1.0)
    
    print("  Building dimension ranks...")
    # Convert raw scores to sorted lists for rank mapping
    # Sort tuples once for performance
    dim_sorted = {
        "skill": sorted([(c["skill_relevance"], c["candidate_id"]) for c in scored_candidates], key=lambda x: (-x[0], x[1])),
        "career": sorted([(c["career_trajectory"], c["candidate_id"]) for c in scored_candidates], key=lambda x: (-x[0], x[1])),
        "behavioral": sorted([(c["behavioral_availability"], c["candidate_id"]) for c in scored_candidates], key=lambda x: (-x[0], x[1])),
        "trust": sorted([(c["trust_score"], c["candidate_id"]) for c in scored_candidates], key=lambda x: (-x[0], x[1])),
        "semantic": sorted([(c["semantic_fit"], c["candidate_id"]) for c in scored_candidates], key=lambda x: (-x[0], x[1]))
    }
    
    # Build candidate lookup ranks {cid: {dim: rank}}
    candidate_ranks = {}
    for dim_name, sorted_list in dim_sorted.items():
        for rank, (_, cid) in enumerate(sorted_list, 1):
            if cid not in candidate_ranks:
                candidate_ranks[cid] = {}
            candidate_ranks[cid][dim_name] = rank
            
    print("  Starting grid search...")
    start_time = time.time()
    
    # Search grid configuration
    w_skill_vals = [0.4, 0.8, 1.0, 1.2, 1.6]
    w_career_vals = [0.4, 0.8, 1.0, 1.2, 1.6]
    w_behavioral_vals = [0.2, 0.5, 0.8, 1.0]
    w_trust_vals = [0.8, 1.2, 1.5, 2.0]
    w_semantic_vals = [0.2, 0.4, 0.6, 0.8, 1.0]
    k_vals = [60]  # Standard RRF constant
    
    total_combinations = (
        len(w_skill_vals) * len(w_career_vals) * len(w_behavioral_vals) *
        len(w_trust_vals) * len(w_semantic_vals) * len(k_vals)
    )
    print(f"  Testing {total_combinations:,} weight combinations...")
    
    best_runs = []
    checked = 0
    
    # Pre-render flat candidate data for maximum iteration speed
    cids = list(candidate_ranks.keys())
    candidate_data = []
    for cid in cids:
        ranks = candidate_ranks[cid]
        candidate_data.append((
            cid,
            ranks["skill"],
            ranks["career"],
            ranks["behavioral"],
            ranks["trust"],
            ranks["semantic"]
        ))
    
    for w_skill in w_skill_vals:
        for w_career in w_career_vals:
            for w_behavioral in w_behavioral_vals:
                for w_trust in w_trust_vals:
                    for w_semantic in w_semantic_vals:
                        for k in k_vals:
                            checked += 1
                            if checked % 200 == 0:
                                elapsed = time.time() - start_time
                                speed = checked / elapsed if elapsed > 0 else 0
                                print(f"    Tested {checked}/{total_combinations} ({checked/total_combinations:.1%}) | Speed: {speed:.0f} runs/sec", end="\r")
                            
                            # Perform RRF calculations inline for maximum performance
                            rrf_scores = []
                            for cid, r_skill, r_career, r_behavioral, r_trust, r_semantic in candidate_data:
                                score = (
                                    w_skill * (1.0 / (k + r_skill)) +
                                    w_career * (1.0 / (k + r_career)) +
                                    w_behavioral * (1.0 / (k + r_behavioral)) +
                                    w_trust * (1.0 / (k + r_trust)) +
                                    w_semantic * (1.0 / (k + r_semantic))
                                )
                                rrf_scores.append((score, cid))
                            
                            # Sort and take top 100
                            rrf_scores.sort(key=lambda x: (-x[0], x[1]))
                            top_100_ids = [cid for _, cid in rrf_scores[:100]]
                            
                            # Evaluate
                            composite = evaluate_ranking(top_100_ids, gold, ideal_dcg_10, ideal_dcg_50, n_relevant)
                            
                            best_runs.append({
                                "composite": composite,
                                "weights": {
                                    "skill": w_skill,
                                    "career": w_career,
                                    "behavioral": w_behavioral,
                                    "trust": w_trust,
                                    "semantic": w_semantic,
                                }
                            })
                            
                            # Keep only top 10 in memory to prevent allocations
                            best_runs.sort(key=lambda x: -x["composite"])
                            best_runs = best_runs[:10]
                            
    elapsed = time.time() - start_time
    print(f"\n  Tuning finished in {elapsed:.1f}s.")
    print()
    print("  === TOP 5 OPTIMAL WEIGHT CONFIGURATIONS ===")
    print()
    
    for rank, run in enumerate(best_runs[:5], 1):
        w = run["weights"]
        print(f"  #{rank} | Composite Score: {run['composite']:.5f}")
        print(f"      Weights -> Skill: {w['skill']:.1f} | Career: {w['career']:.1f} | Behavior: {w['behavioral']:.1f} | Trust: {w['trust']:.1f} | Semantic: {w['semantic']:.1f}")
        print()
        
    best_config = best_runs[0]["weights"]
    print(f"  🎯 Recommended weights for project-trinetra:")
    print(f"  Update w_skill={best_config['skill']}, w_career={best_config['career']}, w_behavioral={best_config['behavioral']}, w_trust={best_config['trust']}, w_semantic={best_config['semantic']}")
    print()


if __name__ == "__main__":
    run_optimizer()
