"""
trinetra_eval.py — THE MASTER VALIDATION COMMAND for Project Trinetra (त्रिनेत्र)

One command to rule them all. Runs the COMPLETE validation suite:
  1. Format Validation  — spec compliance check
  2. Gold Label Generation — independent proxy labels
  3. Scoring Metrics — NDCG@10, NDCG@50, MAP, P@10 (exact spec formula)
  4. Reasoning Audit — Stage 4 manual review simulation
  5. Honeypot Audit — detection count + leakage check
  6. Gem Detection — plain-language gem surfacing check
  7. Iteration Tracking — save results for comparison

Usage:
    python eval/trinetra_eval.py --candidates data/candidates.jsonl --submission submission.csv --run-name "v1_baseline"

    # Compare with previous run:
    python eval/trinetra_eval.py --candidates data/candidates.jsonl --submission submission.csv --run-name "v2_tuned" --compare-with "v1_baseline"

    # Quick mode (skip gold regeneration):
    python eval/trinetra_eval.py --submission submission.csv --run-name "quick" --quick

    # Show history:
    python eval/trinetra_eval.py --history
"""

import argparse
import json
import os
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# Import eval modules
from eval.metrics import evaluate, load_gold, load_ranking
from eval.reasoning_audit import audit_reasoning
from eval.iteration_tracker import save_run, compare_runs, show_history, get_latest_run
from eval.hallucination_validator import verify_reasoning_facts
from eval.adversarial_generator import generate_suite_of_adversaries
from eval.interview_simulator import generate_defense_brief, generate_interview_prep


def print_banner():
    """Print the Trinetra Eval banner."""
    print()
    print("  ====================================================")
    print("  PROJECT TRINETRA - MASTER VALIDATION SUITE")
    print("  ====================================================")
    print("  One command. Full validation. Track every iteration.")
    print()


def run_format_validation(submission_path: str, candidates_path: str = None) -> dict:
    """Phase 1: Format validation (mirrors organizer auto-validator)."""
    print("  [1/6] FORMAT VALIDATION")
    print("  " + "-" * 40)

    from src.validate import validate_submission
    is_valid, errors = validate_submission(submission_path, candidates_path)

    if is_valid:
        print("  [PASS] Submission format is valid")
    else:
        print(f"  [FAIL] {len(errors)} format error(s):")
        for err in errors[:10]:
            print(f"    - {err}")

    print()
    return {"valid": is_valid, "errors": errors}


def run_gold_generation(candidates_path: str, gold_path: str) -> dict:
    """Phase 2: Generate proxy gold labels."""
    print("  [2/6] GOLD LABEL GENERATION")
    print("  " + "-" * 40)

    from eval.gold_labeler import label_candidate
    import csv

    ext = os.path.splitext(candidates_path)[1].lower()
    counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    total = 0

    Path(gold_path).parent.mkdir(parents=True, exist_ok=True)

    with open(gold_path, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["candidate_id", "tier"])

        if ext == ".json":
            with open(candidates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates = data if isinstance(data, list) else [data]
            for c in candidates:
                tier = label_candidate(c)
                counts[tier] += 1
                total += 1
                writer.writerow([c["candidate_id"], tier])
        else:
            with open(candidates_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tier = label_candidate(c)
                    counts[tier] += 1
                    total += 1
                    writer.writerow([c["candidate_id"], tier])

    print(f"  Labeled {total:,} candidates -> {gold_path}")
    for t in (4, 3, 2, 1, 0):
        pct = counts[t] / total * 100 if total > 0 else 0
        print(f"    Tier {t}: {counts[t]:6,} ({pct:5.1f}%)")
    print()

    return {"total": total, "counts": counts}


def run_scoring_metrics(submission_path: str, gold_path: str) -> dict:
    """Phase 3: Compute the EXACT hackathon composite score."""
    print("  [3/6] SCORING METRICS (Hackathon Composite)")
    print("  " + "-" * 40)

    gold = load_gold(gold_path)
    ranked = load_ranking(submission_path)
    results = evaluate(ranked, gold)

    for k, v in results.items():
        weight = ""
        if k == "NDCG@10":
            weight = " (50% weight)"
        elif k == "NDCG@50":
            weight = " (30% weight)"
        elif k == "MAP":
            weight = " (15% weight)"
        elif k == "P@10":
            weight = " (5% weight)"
        elif k == "P@5":
            weight = " (tiebreaker)"
        elif k == "composite":
            weight = " << MAIN SCORE"
        bar = "#" * int(v * 30)
        print(f"  {k:12s}: {v:.4f}  |{bar}|{weight}")

    # Interpret composite
    comp = results["composite"]
    print()
    if comp >= 0.8:
        print("  Level: CHAMPIONSHIP-TIER")
    elif comp >= 0.6:
        print("  Level: COMPETITIVE")
    elif comp >= 0.4:
        print("  Level: MODERATE (needs tuning)")
    elif comp >= 0.2:
        print("  Level: WEAK (significant gaps)")
    else:
        print("  Level: CRITICAL (fundamental issues)")
    print()

    return results


def run_reasoning_audit(submission_path: str, candidates_path: str = None) -> dict:
    """Phase 4: Simulate Stage 4 reasoning review."""
    print("  [4/6] REASONING AUDIT (Stage 4 Simulation)")
    print("  " + "-" * 40)

    results = audit_reasoning(submission_path)

    for name, check in results["checks"].items():
        status = "PASS" if check["passed"] else "FAIL"
        print(f"  [{status}] {name}: {check['message']}")

    # Fact Hallucination Verification
    if candidates_path and os.path.exists(candidates_path):
        import csv
        
        # Load candidates lookup by ID
        candidates_lookup = {}
        ext = os.path.splitext(candidates_path)[1].lower()
        if ext == ".json":
            with open(candidates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates = data if isinstance(data, list) else [data]
            for c in candidates:
                candidates_lookup[c["candidate_id"]] = c
        else:
            with open(candidates_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                        candidates_lookup[c["candidate_id"]] = c
                    except:
                        pass
        
        # Audit each row in submission
        hallucination_errors = []
        with open(submission_path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
            for row in rows:
                cid = row.get("candidate_id", "")
                reasoning = row.get("reasoning", "")
                if cid in candidates_lookup:
                    cand = candidates_lookup[cid]
                    val_res = verify_reasoning_facts(cand, reasoning)
                    if not val_res["passed"]:
                        for err in val_res["errors"]:
                            hallucination_errors.append(f"Candidate {cid}: {err}")
                            
        hallucination_ok = len(hallucination_errors) == 0
        status = "PASS" if hallucination_ok else "FAIL"
        msg = "No hallucinations detected" if hallucination_ok else f"{len(hallucination_errors)} hallucination(s) found"
        print(f"  [{status}] hallucination_check: {msg}")
        results["checks"]["hallucination_check"] = {
            "passed": hallucination_ok,
            "message": msg
        }
        if not hallucination_ok:
            results["errors"].extend(hallucination_errors[:5])
            print("    Sample Hallucinations:")
            for err in hallucination_errors[:5]:
                print(f"      - {err}")
            
            # Recompute checks score
            results["checks_passed"] = sum(1 for c in results["checks"].values() if c["passed"])
            results["total_checks"] = len(results["checks"])
            results["score"] = results["checks_passed"] / results["total_checks"]
    else:
        print("  [SKIP] hallucination_check: Requires candidates path")

    print()
    print(f"  Score: {results['checks_passed']}/{results['total_checks']} checks passed")
    print()

    return {"score": results["score"], "checks_passed": results["checks_passed"],
            "total_checks": results["total_checks"], "errors": results["errors"]}


def run_adversarial_test_suite(candidates_path: str) -> bool:
    """
    Generate synthetic adversarial clones, feed them to Guard Gate,
    and verify they are caught with 100% precision.
    """
    print()
    print("  ====================================================")
    print("  ADVERSARIAL RED-TEAM TEST SUITE (Guard Gate Audit)")
    print("  ====================================================")
    print("  Generating synthetic anomalies to stress-test border security...")
    print()

    from src.guard_gate import run_guard_gate

    # Load 5 sample base candidates
    base_candidates = []
    ext = os.path.splitext(candidates_path)[1].lower()
    if ext == ".json":
        with open(candidates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            base_candidates = (data if isinstance(data, list) else [data])[:10]
    else:
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    base_candidates.append(json.loads(line))
                    if len(base_candidates) >= 10:
                        break
                except:
                    pass

    if len(base_candidates) < 5:
        print("  [ERROR] Aligned test requires at least 5 candidate profiles.")
        return False

    # Generate adversaries
    adversaries = generate_suite_of_adversaries(base_candidates)
    
    test_cases = [
        ("Time-Travel Tech Fraud", adversaries[0], lambda res: res["is_hard_honeypot"]),
        ("Date Inflation Fraud", adversaries[1], lambda res: len(res["violations"]) > 0),
        ("Fictional Company Fraud", adversaries[2], lambda res: len(res["company_info"]["fictional_companies"]) > 0),
        ("Expert-Zero Duration Fraud", adversaries[3], lambda res: res["is_hard_honeypot"] or res["expertise_info"]["is_suspicious"]),
        ("YOE-Education Mismatch", adversaries[4], lambda res: len(res["violations"]) > 0 or res["edu_exp_info"]["is_suspicious"]),
    ]

    all_passed = True
    print(f"  Running {len(test_cases)} adversarial test vectors:")
    print("  " + "-" * 50)
    
    for name, cand, validator_fn in test_cases:
        res = run_guard_gate(cand)
        passed = validator_fn(res)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name:<30}")
        if not passed:
            all_passed = False
            print(f"    - Violations detected: {res['violations']}")
            print(f"    - Trust score: {res['trust_score']:.4f} | Grade: {res['trust_grade']}")
            
    print()
    if all_passed:
        print("  VERDICT: PERFECT - Guard Gate successfully blocked all adversarial injections!")
    else:
        print("  VERDICT: VULNERABLE - Guard Gate failed to block one or more adversarial vectors.")
    print()
    return all_passed


def run_honeypot_check(candidates_path: str, submission_path: str) -> dict:
    """Phase 5: Honeypot detection and leakage check."""
    print("  [5/6] HONEYPOT AUDIT")
    print("  " + "-" * 40)

    from src.guard_gate import run_guard_gate
    import csv

    ext = os.path.splitext(candidates_path)[1].lower()
    if ext == ".json":
        with open(candidates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            candidates = data if isinstance(data, list) else [data]
    else:
        candidates = []
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Load submission
    top_100_ids = set()
    if os.path.exists(submission_path):
        with open(submission_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
            top_100_ids = {row["candidate_id"].strip() for row in rows}

    total_honeypots = 0
    hp_in_top100 = 0

    for cand in candidates:
        result = run_guard_gate(cand)
        if result["is_hard_honeypot"]:
            total_honeypots += 1
            if cand["candidate_id"] in top_100_ids:
                hp_in_top100 += 1

    hp_rate = hp_in_top100 / 100 if top_100_ids else 0

    print(f"  Total honeypots detected: {total_honeypots} (expected ~80)")
    print(f"  Honeypots in Top 100:     {hp_in_top100} ({hp_rate:.0%})")
    print(f"  DQ threshold:             10% (max 10)")

    if hp_in_top100 == 0:
        print("  Status: PERFECT - Zero honeypots in submission")
    elif hp_rate <= 0.10:
        print(f"  Status: SAFE - Under threshold")
    else:
        print(f"  Status: CRITICAL - DISQUALIFICATION RISK!")
    print()

    return {
        "total_honeypots": total_honeypots,
        "honeypots_in_top100": hp_in_top100,
        "honeypot_rate": hp_rate,
    }


def run_gem_check(candidates_path: str, submission_path: str) -> dict:
    """Phase 6: Check if plain-language gems are being surfaced."""
    print("  [6/6] GEM DETECTION")
    print("  " + "-" * 40)

    from eval.gem_detector import is_gem, load_submission_ranks
    import json

    ext = os.path.splitext(candidates_path)[1].lower()
    if ext == ".json":
        with open(candidates_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            candidates = data if isinstance(data, list) else [data]
    else:
        candidates = []
        with open(candidates_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    submission_ranks = {}
    if os.path.exists(submission_path):
        submission_ranks = load_submission_ranks(submission_path)

    total_gems = 0
    gems_in_top100 = 0
    gems_in_top10 = 0

    for c in candidates:
        if is_gem(c):
            total_gems += 1
            cid = c["candidate_id"]
            rank = submission_ranks.get(cid)
            if rank is not None and rank <= 100:
                gems_in_top100 += 1
            if rank is not None and rank <= 10:
                gems_in_top10 += 1

    print(f"  Total plain-language gems: {total_gems}")
    print(f"  Gems in Top 10:           {gems_in_top10}")
    print(f"  Gems in Top 100:          {gems_in_top100}")

    if gems_in_top100 >= 5:
        print("  Status: GOOD - Engine surfaces gems well")
    elif gems_in_top100 >= 2:
        print("  Status: MODERATE - Some gems, room for improvement")
    else:
        print("  Status: WARNING - Gems may be buried")
    print()

    return {
        "total_gems": total_gems,
        "gems_in_top10": gems_in_top10,
        "gems_in_top100": gems_in_top100,
    }


def print_final_report(
    format_result: dict,
    metrics_result: dict,
    reasoning_result: dict,
    honeypot_result: dict,
    gem_result: dict,
    elapsed: float,
):
    """Print the final consolidated report."""
    print()
    print("  ====================================================")
    print("  FINAL VALIDATION REPORT")
    print("  ====================================================")
    print()

    # Scorecard
    checks = []

    # Format
    fmt_ok = format_result["valid"]
    checks.append(("Format Validation", fmt_ok, "PASS" if fmt_ok else "FAIL"))

    # Composite score
    comp = metrics_result.get("composite", 0)
    comp_ok = comp >= 0.3
    checks.append(("Composite Score", comp_ok, f"{comp:.4f}"))

    # NDCG@10 (most important — 50% weight)
    ndcg10 = metrics_result.get("NDCG@10", 0)
    ndcg10_ok = ndcg10 >= 0.3
    checks.append(("NDCG@10 (50% wt)", ndcg10_ok, f"{ndcg10:.4f}"))

    # Reasoning
    r_score = reasoning_result.get("score", 0)
    r_ok = r_score >= 0.625
    checks.append(("Reasoning Quality", r_ok, f"{reasoning_result.get('checks_passed', 0)}/{reasoning_result.get('total_checks', 0)}"))

    # Honeypots
    hp100 = honeypot_result.get("honeypots_in_top100", 0)
    hp_ok = hp100 <= 10
    checks.append(("Honeypot Safety", hp_ok, f"{hp100} in top 100"))

    # Gems
    g100 = gem_result.get("gems_in_top100", 0)
    g_ok = g100 >= 2
    checks.append(("Gem Surfacing", g_ok, f"{g100} in top 100"))

    for name, ok, detail in checks:
        icon = "+" if ok else "X"
        print(f"  [{icon}] {name:<25} {detail}")

    total_pass = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)

    print()
    print(f"  OVERALL: {total_pass}/{total} checks passed")
    print(f"  Runtime: {elapsed:.1f}s")
    print()

    if total_pass == total:
        print("  === SUBMISSION READY FOR UPLOAD ===")
    elif total_pass >= total - 1:
        print("  === NEARLY READY - Fix remaining issue ===")
    else:
        print("  === NOT READY - Address failures before submitting ===")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Trinetra Master Validation Suite"
    )
    parser.add_argument("--candidates", help="Path to candidates JSONL/JSON")
    parser.add_argument("--submission", default="submission.csv", help="Submission CSV")
    parser.add_argument("--run-name", default=None, help="Name for this eval run (for tracking)")
    parser.add_argument("--compare-with", default=None, help="Compare with a previous run")
    parser.add_argument("--gold", default="eval/gold_auto.csv", help="Gold labels CSV path")
    parser.add_argument("--quick", action="store_true", help="Skip gold regeneration (use existing)")
    parser.add_argument("--history", action="store_true", help="Show run history and exit")
    parser.add_argument("--notes", default="", help="Notes about what changed in this run")
    parser.add_argument("--adversarial", action="store_true", help="Run adversarial red-team test suite and exit")
    args = parser.parse_args()

    # History mode
    if args.history:
        show_history()
        return

    # Adversarial mode
    if args.adversarial:
        if not args.candidates:
            print("  ERROR: Candidates file required for adversarial tests. Provide --candidates.")
            sys.exit(1)
        passed = run_adversarial_test_suite(args.candidates)
        sys.exit(0 if passed else 1)

    if not os.path.exists(args.submission):
        print(f"  ERROR: Submission file not found: {args.submission}")
        sys.exit(1)

    print_banner()
    start = time.time()

    # Phase 1: Format Validation
    format_result = run_format_validation(args.submission, args.candidates)

    # Phase 2: Gold Label Generation (skip if --quick)
    if not args.quick and args.candidates:
        run_gold_generation(args.candidates, args.gold)
    elif not os.path.exists(args.gold):
        if not args.candidates:
            print("  ERROR: Gold labels not found. Provide --candidates or generate gold first.")
            sys.exit(1)
        run_gold_generation(args.candidates, args.gold)
    else:
        print("  [2/6] GOLD LABELS: Using existing file")
        print()

    # Phase 3: Scoring Metrics
    metrics_result = run_scoring_metrics(args.submission, args.gold)

    # Phase 4: Reasoning Audit
    reasoning_result = run_reasoning_audit(args.submission, args.candidates)

    # Phase 5: Honeypot Check
    if args.candidates:
        honeypot_result = run_honeypot_check(args.candidates, args.submission)
    else:
        honeypot_result = {"total_honeypots": "?", "honeypots_in_top100": 0, "honeypot_rate": 0}
        print("  [5/6] HONEYPOT AUDIT: Skipped (no candidates file)")
        print()

    # Phase 6: Gem Detection
    if args.candidates:
        gem_result = run_gem_check(args.candidates, args.submission)
    else:
        gem_result = {"total_gems": "?", "gems_in_top100": 0}
        print("  [6/6] GEM DETECTION: Skipped (no candidates file)")
        print()

    elapsed = time.time() - start

    # Final Report
    print_final_report(format_result, metrics_result, reasoning_result,
                       honeypot_result, gem_result, elapsed)

    # Phase 7: Recruiter Defense Brief Generation
    if args.candidates and os.path.exists(args.submission):
        print("  [7/7] RECRUITER DEFENSE BRIEF")
        print("  " + "-" * 40)
        
        # Load submission IDs in rank order
        ranked_ids = load_ranking(args.submission)
        top_10_ids = ranked_ids[:10]
        
        # Load candidates
        top_10_candidates = []
        candidates_lookup = {}
        ext = os.path.splitext(args.candidates)[1].lower()
        if ext == ".json":
            with open(args.candidates, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates = data if isinstance(data, list) else [data]
            for c in candidates:
                candidates_lookup[c["candidate_id"]] = c
        else:
            with open(args.candidates, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                        candidates_lookup[c["candidate_id"]] = c
                    except:
                        pass
        
        # Assemble in rank order
        for cid in top_10_ids:
            if cid in candidates_lookup:
                top_10_candidates.append(candidates_lookup[cid])
                
        if top_10_candidates:
            brief_path = os.path.join(os.path.dirname(args.submission), "eval", "interview_defense.txt")
            gold_labels = load_gold(args.gold)
            generate_defense_brief(top_10_candidates, brief_path, gold_labels)
        else:
            print("  [SKIP] Could not load top-10 candidates for defense card.")
        print()

    # Save to iteration tracker
    if args.run_name:
        ranked_ids = load_ranking(args.submission)
        run = save_run(
            run_name=args.run_name,
            metrics=metrics_result,
            honeypot_stats=honeypot_result,
            reasoning_score=reasoning_result.get("score", 0),
            gem_stats=gem_result,
            notes=args.notes,
            top_100_ids=ranked_ids[:100],
        )
        print(f"  Run saved as: {run['name']}")

        # Compare with previous run if specified
        if args.compare_with:
            compare_runs(args.compare_with, run["name"])
        else:
            # Auto-compare with latest if there's a previous run
            latest = get_latest_run()
            if latest and latest.get("name") != run["name"]:
                print(f"  (Tip: Use --compare-with \"{latest['name']}\" to see what changed)")
        print()


if __name__ == "__main__":
    main()
