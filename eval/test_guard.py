"""
test_guard.py — Debugs Guard Gate outputs for LLM flagged candidates.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.guard_gate import run_guard_gate

JSON_PATH = ROOT / "eval" / "benchmark_candidates.json"


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    cand_map = {c["candidate_id"]: c for c in candidates}
    
    CANDIDATE_IDS = [
        "CAND_0000014",
        "CAND_0000073",
        "CAND_0000088",
        "CAND_0000033",
        "CAND_0000081",
        "CAND_0084182",
        "CAND_0064077",
    ]
    
    print()
    print("  === RUNNING GUARD GATE ON FLAGGED CANDIDATES ===")
    
    for cid in CANDIDATE_IDS:
        if cid not in cand_map:
            print(f"  {cid} not in benchmark dataset")
            continue
        c = cand_map[cid]
        res = run_guard_gate(c)
        print(f"\n  Candidate: {cid} ({c['profile'].get('anonymized_name')})")
        print(f"    Trust Grade:      {res['trust_grade']}")
        print(f"    Trust Score:      {res['trust_score']:.4f}")
        print(f"    Is Hard Honeypot: {res['is_hard_honeypot']}")
        print(f"    Disqualified:     {res['disqualified']}")
        print(f"    Violations ({len(res['violations'])}):")
        for v in res["violations"]:
            print(f"      - {v}")


if __name__ == "__main__":
    main()
