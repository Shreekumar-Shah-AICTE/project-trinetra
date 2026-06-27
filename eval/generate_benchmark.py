"""
generate_benchmark.py — Benchmark Dataset Generator for Project Trinetra (त्रिनेत्र)
🔱 Selects 200 diverse candidates for Trinetra vs LLM battle.

Selection strategy:
  - 30 Top-tier (Grade A/B, high skill score, textbook fit)
  - 30 Adjacent Gems (non-AI title, built real systems, moderate scores)
  - 40 Honeypots (impossible timelines, expert fraud, Tier 0)
  - 100 General entries (services company, junior, unrelated engineering)
"""

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
sys.path.insert(0, str(ROOT / "src"))

from src.guard_gate import run_guard_gate

CANDIDATES_PATH = r"C:\Users\Shree Shah\Desktop\India RUNS hackathon\Analysis Material\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
OUT_PATH = ROOT / "eval" / "benchmark_candidates.json"


def iter_candidates(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main():
    print()
    print("  === TRINETRA BENCHMARK GENERATOR ===")
    print(f"  Reading candidates from: {CANDIDATES_PATH}")
    
    top_entries = []
    gem_entries = []
    honeypots = []
    general_entries = []
    
    # Import logic to check if they are gems
    from eval.gem_detector import is_gem
    from src.rankers import score_skill_relevance, score_career_trajectory
    from src.loader import extract_text_fields
    
    scanned = 0
    for cand in iter_candidates(CANDIDATES_PATH):
        scanned += 1
        if scanned % 10000 == 0:
            print(f"    Scanned {scanned:,} candidates...")
            
        cid = cand["candidate_id"]
        guard = run_guard_gate(cand)
        
        # 1. Honeypots
        if guard["is_hard_honeypot"] and len(honeypots) < 40:
            honeypots.append(cand)
            continue
            
        # Skip disqualified for others
        if guard["disqualified"]:
            continue
            
        # 2. Plain language gems
        if is_gem(cand) and len(gem_entries) < 30:
            gem_entries.append(cand)
            continue
            
        # Score skill relevance for top-tier selection
        text_fields = extract_text_fields(cand)
        skill_res = score_skill_relevance(cand, text_fields)
        
        # 3. Top entries (Grade A/B, high skill score)
        if guard["trust_grade"] in ("A", "B") and skill_res["skill_relevance_score"] >= 0.45 and len(top_entries) < 30:
            top_entries.append(cand)
            continue
            
        # 4. General entries
        if len(general_entries) < 100:
            general_entries.append(cand)
            
        # Stop early if all buckets are filled
        if (len(top_entries) >= 30 and len(gem_entries) >= 30 and 
                len(honeypots) >= 40 and len(general_entries) >= 100):
            break
            
    print(f"  Buckets filled:")
    print(f"    - Top Entries:      {len(top_entries)}")
    print(f"    - Adjacent Gems:    {len(gem_entries)}")
    print(f"    - Hard Honeypots:   {len(honeypots)}")
    print(f"    - General Entries:  {len(general_entries)}")
    
    # Combine and shuffle
    combined = top_entries + gem_entries + honeypots + general_entries
    random.seed(42)
    random.shuffle(combined)
    
    # Save to file
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
        
    print(f"  Successfully wrote {len(combined)} shuffled candidates to {OUT_PATH}")
    print()


if __name__ == "__main__":
    main()
