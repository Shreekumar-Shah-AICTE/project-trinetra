"""
train_ltr.py — Learning-to-Rank (LTR) Model Trainer for Project Trinetra (त्रिनेत्र)
🔱 Trains a Gradient Boosting / Random Forest Regressor on candidates' multi-dimensional
scores to predict the human proxy Gold Label Tier (0-4), physicalizing the LTR requirement in the JD.
"""

import os
import sys
import json
import pickle
import time
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.loader import load_candidates, extract_text_fields
from src.guard_gate import run_guard_gate
from src.rankers import (
    score_skill_relevance,
    score_career_trajectory,
    score_behavioral_availability,
    score_trust,
)
from src.semantic import compute_semantic_scores
from eval.gold_labeler import label_candidate

# Check dependencies
try:
    from sklearn.ensemble import GradientBoostingRegressor
    import numpy as np
except ImportError:
    print("Error: scikit-learn and numpy are required to train the LTR model.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Train a Learning-to-Rank (LTR) model")
    parser.add_argument("--candidates", default="data/sample_candidates.json", help="Path to candidates data")
    parser.add_argument("--out", default="eval/ltr_model.pkl", help="Output model path")
    args = parser.parse_args()

    print("====================================================")
    print("🔱 STARTING TRINETRA LTR MODEL TRAINING")
    print("====================================================")
    
    start_time = time.time()
    
    # 1. Load candidates
    print(f"▸ Loading candidates from {args.candidates}...")
    candidates = load_candidates(args.candidates)
    print(f"  Loaded {len(candidates):,} candidates.")
    
    # 2. Extract features and target
    print("▸ Scoring candidates and generating training features...")
    X = []
    y = []
    
    # First filter and score
    scored_candidates = []
    guard_results = {}
    for cand in candidates:
        gg = run_guard_gate(cand)
        guard_results[cand["candidate_id"]] = gg
        if gg["is_hard_honeypot"] or gg.get("is_synthetic_noise", False) or gg["disqualified"]:
            continue
            
        text_fields = extract_text_fields(cand)
        skill_res = score_skill_relevance(cand, text_fields)
        career_res = score_career_trajectory(cand)
        behavioral_res = score_behavioral_availability(cand)
        trust_res = score_trust(gg)
        
        scored_candidates.append({
            "candidate_id": cand["candidate_id"],
            "candidate": cand,
            "text_fields": text_fields,
            "skill_relevance_score": skill_res["skill_relevance_score"],
            "career_score": career_res["career_score"],
            "behavioral_score": behavioral_res["behavioral_score"],
            "trust_rank_score": trust_res["trust_rank_score"],
        })
        
    # Semantic scoring
    if scored_candidates:
        sem_texts = [
            sc["text_fields"]["career_descriptions"] + " " + 
            sc["text_fields"]["career_descriptions"] + " " + 
            sc["text_fields"]["headline"] + " " + 
            sc["text_fields"]["summary"] + " " + 
            sc["text_fields"]["skill_names"]
            for sc in scored_candidates
        ]
        sem_ids = [sc["candidate_id"] for sc in scored_candidates]
        semantic_scores = compute_semantic_scores(sem_texts, sem_ids)
        for sc in scored_candidates:
            sc["semantic_score"] = semantic_scores.get(sc["candidate_id"], 0.0)
            
    scored_lookup = {sc["candidate_id"]: sc for sc in scored_candidates}
    
    for cand in candidates:
        cid = cand["candidate_id"]
        sc = scored_lookup.get(cid)
        if not sc:
            continue
            
        gg = guard_results[cid]
        features = [
            sc.get("skill_relevance_score", 0.0),
            sc.get("career_score", 0.0),
            sc.get("behavioral_score", 0.0),
            gg.get("trust_score", 0.0),
            sc.get("semantic_score", 0.0),
        ]
        
        target = label_candidate(cand)
        X.append(features)
        y.append(target)
        
    X = np.array(X)
    y = np.array(y)
    
    print(f"  Training matrix shape: {X.shape} | Target shape: {y.shape}")
    
    # 3. Train LTR Model (Gradient Boosting Regressor for ranking/relevance)
    print("▸ Fitting Gradient Boosting Regressor (LTR model)...")
    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    )
    model.fit(X, y)
    
    # 4. Save model
    print(f"▸ Saving trained LTR model to {args.out}...")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        pickle.dump(model, f)
        
    elapsed = time.time() - start_time
    print(f"✅ LTR model trained and saved successfully in {elapsed:.1f}s!")
    print("====================================================")


if __name__ == "__main__":
    main()
