"""
generate_hfsb.py — High-Fidelity Stratified Benchmark (HFSB) Generator
🔱 Creates a 5,000-candidate sub-dataset containing 100% of the critical signals
(all honeypots and Tier 1-4 candidates) and 4,000 sampled Tier 0 candidates.

This cuts pipeline execution time from 3.5 minutes to under 8 seconds,
enabling rapid iterative optimization of the ranking engine.
"""

import csv
import json
import os
import sys
import random
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

CANDIDATES_PATH = r"C:\Users\Shree Shah\Desktop\India RUNS hackathon\Analysis Material\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
GOLD_PATH = ROOT / "eval" / "gold_auto.csv"
OUT_PATH = ROOT / "data" / "candidates_hfsb.json"
OUT_GOLD_PATH = ROOT / "eval" / "gold_hfsb.csv"


def load_gold_mapping() -> dict[str, int]:
    """Loads candidate ID to tier mapping from gold_auto.csv."""
    mapping = {}
    if not os.path.exists(GOLD_PATH):
        print(f"ERROR: Gold labels file not found at {GOLD_PATH}. Run trinetra_eval.py on the full dataset first.")
        sys.exit(1)
    with open(GOLD_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row["candidate_id"].strip()] = int(float(row["tier"]))
    return mapping


def main():
    print()
    print("  ====================================================")
    print("  🔱 HIGH-FIDELITY STRATIFIED BENCHMARK (HFSB) GENERATOR")
    print("  ====================================================")
    
    # Load gold tiers
    gold_map = load_gold_mapping()
    
    # Bucket candidate IDs by tier
    buckets = {0: [], 1: [], 2: [], 3: [], 4: []}
    for cid, tier in gold_map.items():
        if tier in buckets:
            buckets[tier].append(cid)
            
    # Count totals
    print("  Available candidate counts by Tier:")
    for tier in sorted(buckets.keys(), reverse=True):
        print(f"    - Tier {tier}: {len(buckets[tier]):,}")
        
    # We want 100% of Tiers 1, 2, 3, and 4
    # And we sample 4,000 candidates from Tier 0
    random.seed(42)
    sampled_tier0 = random.sample(buckets[0], min(4000, len(buckets[0])))
    
    selected_cids = set(
        buckets[4] +
        buckets[3] +
        buckets[2] +
        buckets[1] +
        sampled_tier0
    )
    
    print(f"  Selected {len(selected_cids):,} total candidates for HFSB.")
    print("  Extracting profiles from raw candidates.jsonl...")
    
    hfsb_candidates = []
    
    # Scan raw candidates file and extract selected candidates
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                cand = json.loads(line)
                cid = cand["candidate_id"]
                if cid in selected_cids:
                    hfsb_candidates.append(cand)
            except json.JSONDecodeError:
                continue
                
    # Shuffle for randomization
    random.shuffle(hfsb_candidates)
    
    # Save candidates json
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(hfsb_candidates, f, indent=2)
    print(f"  [SUCCESS] Wrote {len(hfsb_candidates):,} candidates to {OUT_PATH}")
    
    # Generate matching gold file for HFSB
    with open(OUT_GOLD_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "tier"])
        for cand in hfsb_candidates:
            cid = cand["candidate_id"]
            writer.writerow([cid, gold_map.get(cid, 0)])
            
    print(f"  [SUCCESS] Wrote HFSB gold mapping to {OUT_GOLD_PATH}")
    print()


if __name__ == "__main__":
    main()
