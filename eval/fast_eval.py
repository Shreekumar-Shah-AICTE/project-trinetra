"""
fast_eval.py — Fast Loop Execution and Evaluation script for Project Trinetra (त्रिनेत्र)
🔱 Runs the full pipeline on our 5,000-candidate HFSB dataset in under 15 seconds.

Usage:
    python eval/fast_eval.py --run-name "my_iteration_1"
"""

import subprocess
import argparse
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


def main():
    parser = argparse.ArgumentParser(description="🔱 Fast Pipeline Execution & Evaluation Loop")
    parser.add_argument("--run-name", default="fast_test", help="Name of this run")
    parser.add_argument("--notes", default="", help="Notes about what changed in this run")
    args = parser.parse_args()
    
    print()
    print("  ====================================================")
    print("  🚀 STARTING FAST PIPELINE ITERATION (HFSB)")
    print("  ====================================================")
    start = time.time()
    
    # 1. Run rank.py on HFSB
    rank_cmd = [
        sys.executable, str(ROOT / "src" / "rank.py"),
        "--candidates", str(ROOT / "data" / "candidates_hfsb.json"),
        "--out", str(ROOT / "submission_fast.csv")
    ]
    
    print("  ▸ Step 1: Running ranking pipeline on 4,595 HFSB candidates...")
    t1 = time.time()
    res1 = subprocess.run(rank_cmd, capture_output=True, text=True, encoding="utf-8")
    if res1.returncode != 0:
        print("  ❌ RANKER FAILED:")
        print(res1.stderr)
        sys.exit(1)
    print(f"    ✅ Completed in {time.time() - t1:.1f}s")
    
    # 2. Run trinetra_eval.py
    eval_cmd = [
        sys.executable, str(ROOT / "eval" / "trinetra_eval.py"),
        "--candidates", str(ROOT / "data" / "candidates_hfsb.json"),
        "--submission", str(ROOT / "submission_fast.csv"),
        "--gold", str(ROOT / "eval" / "gold_hfsb.csv"),
        "--run-name", args.run_name,
        "--notes", args.notes,
        "--quick"
    ]
    
    print("  ▸ Step 2: Running evaluation suite on HFSB outputs...")
    t2 = time.time()
    res2 = subprocess.run(eval_cmd, capture_output=True, text=True, encoding="utf-8")
    print(f"    ✅ Completed in {time.time() - t2:.1f}s")
    
    print("-" * 52)
    print(res2.stdout)
    if res2.returncode != 0 and res2.stderr:
        print("  ❌ EVALUATION ERROR:")
        print(res2.stderr)
        
    print(f"  ✨ TOTAL FAST ITERATION LOOP COMPLETED IN {time.time() - start:.1f}s")
    print()


if __name__ == "__main__":
    main()
