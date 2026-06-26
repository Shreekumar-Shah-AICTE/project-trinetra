"""
eval.py — Offline Evaluation and Local Mock Test Engine for Project Trinetra (त्रिनेत्र)
🔱 Evaluates NDCG@10, NDCG@50, MAP, P@10, and Honeypot Rate locally.
"""

import sys
import os
import csv
import json
import math

# Add root folder to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.loader import load_candidates
from src.guard_gate import run_guard_gate
from src.rankers import score_skill_relevance, score_career_trajectory, score_behavioral_availability

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def compute_gold_relevance(candidate: dict) -> int:
    """
    Computes a rule-based 'gold relevance' tier (0 to 3) for evaluation:
    - 3: Ideal fit (5-9 YOE, AI/ML product background, strong skills, active)
    - 2: Good fit (Decent skills, product background, minor YOE/notice gaps)
    - 1: Borderline fit (Engineering background, minor AI skills, or services-only)
    - 0: Disqualified / Honeypot / Stuffer / Fictional company heavy
    """
    guard = run_guard_gate(candidate)
    
    # ── Tier 0: Disqualified or Honeypots ──
    if guard["is_hard_honeypot"] or guard["disqualified"]:
        return 0
        
    profile = candidate.get("profile", {})
    yoe = profile.get("years_of_experience", 0.0)
    
    # Check services-only
    if guard["company_info"]["services_only"]:
        # Disliked by JD, down-grade to at most Tier 1
        return 1
        
    # Extract scores
    from src.loader import extract_text_fields
    text_fields = extract_text_fields(candidate)
    
    skill_res = score_skill_relevance(candidate, text_fields)
    career_res = score_career_trajectory(candidate)
    behavior_res = score_behavioral_availability(candidate)
    
    skill_score = skill_res["skill_relevance_score"]
    career_score = career_res["career_score"]
    behavior_score = behavior_res["behavioral_score"]
    
    # ── Tier 3: Ideal Founding Team AI Engineer ──
    if (
        5.0 <= yoe <= 9.0
        and skill_score >= 0.5
        and career_res["product_ratio"] >= 0.5
        and behavior_score >= 0.6
        and guard["trust_grade"] in ("A", "B")
    ):
        return 3
        
    # ── Tier 2: Strong candidate with minor gaps ──
    if (
        4.0 <= yoe <= 11.0
        and skill_score >= 0.35
        and guard["trust_grade"] in ("A", "B", "C")
    ):
        return 2
        
    # ── Tier 1: Marginal engineering fit ──
    if skill_score >= 0.15:
        return 1
        
    return 0


def compute_dcg(relevances: list[float], n: int) -> float:
    """Calculate Discounted Cumulative Gain at rank N."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:n]):
        dcg += (2**rel - 1) / math.log2(i + 2)
    return dcg


def compute_ndcg(relevances: list[float], gold_relevances: list[float], n: int) -> float:
    """Calculate Normalized Discounted Cumulative Gain at rank N."""
    dcg = compute_dcg(relevances, n)
    ideal_relevances = sorted(gold_relevances, reverse=True)
    idcg = compute_dcg(ideal_relevances, n)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def compute_map(ranked_ids: list[str], gold_map: dict[str, int]) -> float:
    """
    Calculate Mean Average Precision (MAP).
    A candidate is considered 'relevant' if relevance tier >= 2.
    """
    ap = 0.0
    num_relevant = 0
    total_gold_relevant = sum(1 for rel in gold_map.values() if rel >= 2)
    
    if total_gold_relevant == 0:
        return 0.0
        
    for i, cid in enumerate(ranked_ids):
        rel = gold_map.get(cid, 0)
        if rel >= 2:
            num_relevant += 1
            ap += num_relevant / (i + 1)
            
    return ap / total_gold_relevant


def evaluate_submission(submission_csv: str, candidates_path: str):
    """Load submission and candidates to print evaluation scores."""
    print("  === LOCAL EVALUATION REPORT ===")
    print(f"  📂 Submission CSV: {submission_csv}")
    print(f"  📂 Candidates File: {candidates_path}")
    print()
    
    # 1. Load candidates & calculate gold labels
    candidates = load_candidates(candidates_path, quiet=True)
    gold_map = {}
    honeypots = set()
    
    for cand in candidates:
        cid = cand["candidate_id"]
        gold_map[cid] = compute_gold_relevance(cand)
        guard = run_guard_gate(cand)
        if guard["is_hard_honeypot"]:
            honeypots.add(cid)
            
    total_relevant = sum(1 for r in gold_map.values() if r >= 2)
    total_honeypots = len(honeypots)
    print(f"  💡 Dataset stats: {len(candidates)} total candidates, {total_relevant} relevant (Tier 2+), {total_honeypots} honeypots.")
    
    # 2. Load submission
    if not os.path.exists(submission_csv):
        print(f"  ❌ Error: Submission file '{submission_csv}' not found.")
        return
        
    ranked_ids = []
    with open(submission_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ranked_ids.append(row["candidate_id"])
            
    if len(ranked_ids) == 0:
        print("  ❌ Error: Submission CSV contains zero records.")
        return
        
    # Map ranked IDs to their gold relevance values
    ranked_relevances = [gold_map.get(cid, 0) for cid in ranked_ids]
    
    # 3. Calculate metrics
    ndcg_10 = compute_ndcg(ranked_relevances, list(gold_map.values()), 10)
    ndcg_50 = compute_ndcg(ranked_relevances, list(gold_map.values()), 50)
    
    p_10 = sum(1 for rel in ranked_relevances[:10] if rel >= 2) / 10.0
    map_score = compute_map(ranked_ids, gold_map)
    
    # Honeypot rate in top 100
    honeypot_count = sum(1 for cid in ranked_ids if cid in honeypots)
    honeypot_rate = (honeypot_count / len(ranked_ids)) * 100 if ranked_ids else 0.0
    
    # Calculate composite score
    composite = 0.50 * ndcg_10 + 0.30 * ndcg_50 + 0.15 * map_score + 0.05 * p_10
    
    # 4. Display Results
    print("  " + "═" * 45)
    print("  📊 METRICS PERFORMANCE")
    print("  " + "═" * 45)
    print(f"  🏆 Final Composite Score: {composite:.4f}")
    print(f"  ├─ NDCG@10 (Weight 50%):  {ndcg_10:.4f}")
    print(f"  ├─ NDCG@50 (Weight 30%):  {ndcg_50:.4f}")
    print(f"  ├─ MAP     (Weight 15%):  {map_score:.4f}")
    print(f"  └─ P@10    (Weight  5%):  {p_10:.4f}")
    print()
    
    # Honeypot Status
    h_color = "🟢 PASS" if honeypot_rate <= 10.0 else "🔴 DISQUALIFIED (>10%)"
    print(f"  🚨 Honeypot Rate in Top 100: {honeypot_rate:.1f}% ({honeypot_count} caught) &bull; [{h_color}]")
    print("  " + "═" * 45)
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Project Trinetra ranking.")
    parser.add_argument("--sub", default="submission.csv", help="Path to submission CSV")
    parser.add_argument("--candidates", default="data/sample_candidates.json", help="Path to candidates file")
    args = parser.parse_args()
    
    evaluate_submission(args.sub, args.candidates)
