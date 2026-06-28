"""
iteration_tracker.py — Run History & Comparison Engine for Project Trinetra (त्रिनेत्र)

THE SECRET WEAPON. Without a public leaderboard, we need our OWN way to
track whether changes improve or hurt our ranking. This module:

  1. Saves the results of every eval run to a local JSON history file
  2. Compares any two runs side-by-side (A/B testing for ranking)
  3. Shows improvement trends across the project lifecycle
  4. Highlights which metric moved and in which direction

Usage:
    # Save a run result
    python eval/iteration_tracker.py save --run-name "v1_baseline" --results '{"composite": 0.72, ...}'

    # Compare two runs
    python eval/iteration_tracker.py compare --old "v1_baseline" --new "v2_rrf_tuning"

    # Show all runs
    python eval/iteration_tracker.py history
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


HISTORY_FILE = Path(__file__).resolve().parents[1] / "eval" / "run_history.json"


def _load_history() -> dict:
    """Load run history from JSON file."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"runs": []}


def _save_history(history: dict):
    """Save run history to JSON file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)


def save_run(
    run_name: str,
    metrics: dict,
    honeypot_stats: dict = None,
    reasoning_score: float = None,
    gem_stats: dict = None,
    notes: str = "",
    top_100_ids: list = None,
) -> dict:
    """Save a complete eval run to history.
    
    Args:
        run_name: Human-readable name for this run (e.g., "v1_baseline")
        metrics: Output from eval/metrics.py evaluate() function
        honeypot_stats: Honeypot detection stats
        reasoning_score: Overall reasoning audit score
        gem_stats: Gem detection stats
        notes: Optional human notes about what changed
        top_100_ids: Optional list of top 100 candidate IDs for volatility analysis
    
    Returns:
        The saved run record.
    """
    history = _load_history()

    run = {
        "name": run_name,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "honeypot_stats": honeypot_stats or {},
        "reasoning_score": reasoning_score,
        "gem_stats": gem_stats or {},
        "notes": notes,
        "top_100_ids": top_100_ids or [],
    }

    # Check for duplicate names and auto-suffix
    existing_names = {r["name"] for r in history["runs"]}
    if run_name in existing_names:
        i = 2
        while f"{run_name}_{i}" in existing_names:
            i += 1
        run["name"] = f"{run_name}_{i}"
        print(f"  (Name '{run_name}' exists; saved as '{run['name']}')")

    history["runs"].append(run)
    _save_history(history)

    return run


def compare_runs(old_name: str, new_name: str) -> dict:
    """Compare two runs and show metric deltas.
    
    Returns a comparison dict with deltas and improvement status.
    """
    history = _load_history()

    old_run = None
    new_run = None
    for r in history["runs"]:
        if r["name"] == old_name:
            old_run = r
        if r["name"] == new_name:
            new_run = r

    if not old_run:
        print(f"  ERROR: Run '{old_name}' not found in history")
        return {}
    if not new_run:
        print(f"  ERROR: Run '{new_name}' not found in history")
        return {}

    comparison = {
        "old": old_name,
        "new": new_name,
        "metric_deltas": {},
        "improved": False,
    }

    old_metrics = old_run.get("metrics", {})
    new_metrics = new_run.get("metrics", {})

    print()
    print("  === TRINETRA RUN COMPARISON ===")
    print(f"  OLD: {old_name} ({old_run['timestamp'][:19]})")
    print(f"  NEW: {new_name} ({new_run['timestamp'][:19]})")
    print()

    # Metric comparison
    all_metric_keys = sorted(set(list(old_metrics.keys()) + list(new_metrics.keys())))
    
    for key in all_metric_keys:
        old_val = old_metrics.get(key, 0)
        new_val = new_metrics.get(key, 0)
        delta = new_val - old_val

        comparison["metric_deltas"][key] = {
            "old": old_val,
            "new": new_val,
            "delta": delta,
        }

        if delta > 0:
            icon = "+"
            direction = "IMPROVED"
        elif delta < 0:
            icon = "-"
            direction = "REGRESSED"
        else:
            icon = "="
            direction = "NO CHANGE"

        print(f"  {key:12s}: {old_val:.4f} -> {new_val:.4f}  ({icon}{abs(delta):.4f}) {direction}")

    # Overall verdict
    composite_delta = comparison["metric_deltas"].get("composite", {}).get("delta", 0)
    comparison["improved"] = composite_delta > 0

    print()
    if composite_delta > 0.01:
        print(f"  VERDICT: IMPROVEMENT (+{composite_delta:.4f} composite)")
    elif composite_delta < -0.01:
        print(f"  VERDICT: REGRESSION ({composite_delta:.4f} composite) -- REVERT CHANGES!")
    else:
        print(f"  VERDICT: NEUTRAL (delta within noise: {composite_delta:+.4f})")

    # Additional comparisons
    old_hp = old_run.get("honeypot_stats", {})
    new_hp = new_run.get("honeypot_stats", {})
    if old_hp and new_hp:
        print()
        old_hp100 = old_hp.get("honeypots_in_top100", "?")
        new_hp100 = new_hp.get("honeypots_in_top100", "?")
        print(f"  Honeypots in Top 100: {old_hp100} -> {new_hp100}")

    old_gems = old_run.get("gem_stats", {})
    new_gems = new_run.get("gem_stats", {})
    if old_gems and new_gems:
        old_g100 = old_gems.get("gems_in_top100", "?")
        new_g100 = new_gems.get("gems_in_top100", "?")
        print(f"  Gems in Top 100:     {old_g100} -> {new_g100}")

    # Check Top 100 Overlap
    old_ids = set(old_run.get("top_100_ids", []))
    new_ids = set(new_run.get("top_100_ids", []))
    if old_ids and new_ids:
        overlap = len(old_ids.intersection(new_ids))
        print(f"  Top 100 Overlap:     {overlap}/100 candidates remained")
        if overlap < 50:
            print("  ⚠️ WARNING: High ranking volatility! Over 50% of your shortlist changed.")

    if old_run.get("notes"):
        print(f"\n  OLD notes: {old_run['notes']}")
    if new_run.get("notes"):
        print(f"  NEW notes: {new_run['notes']}")

    print()
    return comparison


def show_history():
    """Print a table of all historical runs."""
    history = _load_history()

    if not history["runs"]:
        print("  No runs recorded yet. Run trinetra_eval.py to create the first entry.")
        return

    print()
    print("  === TRINETRA RUN HISTORY ===")
    print(f"  {'#':>3}  {'Name':<25} {'Composite':>10} {'NDCG@10':>8} {'P@10':>6} {'HP in 100':>9} {'Time'}")
    print("  " + "-" * 95)

    for i, run in enumerate(history["runs"], 1):
        m = run.get("metrics", {})
        hp = run.get("honeypot_stats", {})
        ts = run.get("timestamp", "")[:16]
        composite = m.get("composite", 0)
        ndcg10 = m.get("NDCG@10", 0)
        p10 = m.get("P@10", 0)
        hp100 = hp.get("honeypots_in_top100", "?")

        print(f"  {i:3d}  {run['name']:<25} {composite:10.4f} {ndcg10:8.4f} {p10:6.2f} {str(hp100):>9} {ts}")

    print()

    # Show trend if 2+ runs
    if len(history["runs"]) >= 2:
        first = history["runs"][0].get("metrics", {}).get("composite", 0)
        last = history["runs"][-1].get("metrics", {}).get("composite", 0)
        trend = last - first
        if trend > 0:
            print(f"  TREND: +{trend:.4f} composite improvement since first run")
        elif trend < 0:
            print(f"  TREND: {trend:.4f} composite regression since first run. Review changes!")
        else:
            print(f"  TREND: No change since first run.")
    print()


def get_latest_run() -> dict:
    """Get the most recent run from history."""
    history = _load_history()
    if history["runs"]:
        return history["runs"][-1]
    return {}


def main():
    parser = argparse.ArgumentParser(description="Trinetra Iteration Tracker")
    subparsers = parser.add_subparsers(dest="command")

    # save command
    save_parser = subparsers.add_parser("save", help="Save a run result")
    save_parser.add_argument("--run-name", required=True, help="Name for this run")
    save_parser.add_argument("--results", required=True, help="JSON string of metric results")
    save_parser.add_argument("--notes", default="", help="Optional notes")

    # compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two runs")
    compare_parser.add_argument("--old", required=True, help="Old run name")
    compare_parser.add_argument("--new", required=True, help="New run name")

    # history command
    subparsers.add_parser("history", help="Show all runs")

    args = parser.parse_args()

    if args.command == "save":
        results = json.loads(args.results)
        run = save_run(args.run_name, results, notes=args.notes)
        print(f"  Saved run: {run['name']}")
    elif args.command == "compare":
        compare_runs(args.old, args.new)
    elif args.command == "history":
        show_history()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
