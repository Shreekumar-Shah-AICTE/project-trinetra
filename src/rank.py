"""
rank.py — Project Trinetra (त्रिनेत्र) — Main CLI Entry Point

🔱 Three Eyes. Zero Fakes.
Trust-First, Multi-Dimensional Talent Forensics Engine

Usage:
    python src/rank.py --candidates ./data/candidates.jsonl --out ./submission.csv

Pipeline:
    Stage 0: LOAD — Stream JSONL into memory
    Stage 1: GUARD GATE (Eye 1) — Trust verification, honeypot elimination
    Stage 2: MULTI-DIM RANK (Eye 2) — 4 independent scoring dimensions
    Stage 3: RRF FUSION (Eye 3) — Reciprocal Rank Fusion
    Stage 4: REASONING — Forensic evidence chains for top 100
    Stage 5: OUTPUT — Write submission CSV
"""

import argparse
import csv
import json
import os
import sys
import time
from typing import Optional

# Force UTF-8 stdout/stderr encoding on Windows to support visual symbols (🔱, ▸, etc.)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.loader import load_candidates, extract_text_fields
from src.guard_gate import run_guard_gate
from src.rankers import (
    score_skill_relevance,
    score_career_trajectory,
    score_behavioral_availability,
    score_trust,
)
from src.fusion import build_dimension_ranks, reciprocal_rank_fusion
from src.reasoning import build_reasoning
from src.semantic import compute_semantic_scores


def print_banner():
    """Display the Trinetra banner."""
    print()
    print("  === PROJECT TRINETRA ===")
    print("  Three Eyes. Zero Fakes.")
    print("  Trust-First Multi-Dimensional Talent Forensics Engine")
    print()


def run_pipeline(
    candidates_path: str,
    output_path: str,
    debug_json: Optional[str] = None,
    debug_csv: Optional[str] = None,
    profile_runtime: bool = False,
    k: int = 60,
    fast: bool = False,
    no_semantic: bool = False,
) -> dict:
    """
    Execute the full Trinetra pipeline.
    
    Returns a stats dict with timing and detection counts.
    """
    timings = {}
    start_total = time.time()
    
    # ═══════════════════════════════════════════════════════════════════
    #  STAGE 0: LOAD
    # ═══════════════════════════════════════════════════════════════════
    print("  ▸ Stage 0: Loading candidates...")
    t0 = time.time()
    candidates = load_candidates(candidates_path)
    timings["load"] = time.time() - t0
    total_candidates = len(candidates)
    
    # ═══════════════════════════════════════════════════════════════════
    #  STAGE 1: GUARD GATE (Eye 1 — Trust Verification)
    # ═══════════════════════════════════════════════════════════════════
    print("  ▸ Stage 1: Guard Gate — Trust verification...")
    t1 = time.time()
    
    guard_results = {}
    hard_honeypots = 0
    synthetic_noise = 0
    disqualified = 0
    trust_grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    
    # Candidates that survive Guard Gate for ranking
    surviving_candidates = []
    
    for cand in candidates:
        cid = cand["candidate_id"]
        result = run_guard_gate(cand)
        guard_results[cid] = result
        
        grade = result["trust_grade"]
        trust_grade_counts[grade] = trust_grade_counts.get(grade, 0) + 1
        
        if result["is_hard_honeypot"]:
            hard_honeypots += 1
            disqualified += 1
            continue  # Skip fake honeypot profiles entirely
            
        if result.get("is_synthetic_noise", False):
            synthetic_noise += 1
            disqualified += 1
            continue  # Skip synthetic company noise profiles entirely
            
        if result["disqualified"]:
            disqualified += 1
            continue  # Skip non-AI domain candidates entirely
            
        surviving_candidates.append(cand)
    
    timings["guard_gate"] = time.time() - t1
    
    print(f"    👁 {total_candidates:,} candidates scanned")
    print(f"    🚫 {hard_honeypots:,} hard honeypots detected")
    print(f"    📉 {synthetic_noise:,} synthetic noise profiles pruned")
    print(f"    ❌ {disqualified - hard_honeypots - synthetic_noise:,} domain-disqualified (non-AI/engineering)")
    print(f"    ✅ {len(surviving_candidates):,} candidates surviving to ranking")
    print(f"    📊 Trust grades: A={trust_grade_counts['A']:,} B={trust_grade_counts['B']:,} "
          f"C={trust_grade_counts['C']:,} D={trust_grade_counts['D']:,} F={trust_grade_counts['F']:,}")
    
    # ═══════════════════════════════════════════════════════════════════
    #  STAGE 2: MULTI-DIMENSIONAL RANKING (Eye 2)
    # ═══════════════════════════════════════════════════════════════════
    print("  ▸ Stage 2: Multi-dimensional scoring...")
    t2 = time.time()
    
    scored_candidates = []
    
    for cand in surviving_candidates:
        cid = cand["candidate_id"]
        
        # Extract text fields (source-aware)
        text_fields = extract_text_fields(cand)
        
        # Score all 4 dimensions independently
        skill_result = score_skill_relevance(cand, text_fields)
        career_result = score_career_trajectory(cand)
        behavioral_result = score_behavioral_availability(cand)
        trust_result = score_trust(guard_results[cid])
        
        scored_candidates.append({
            "candidate_id": cid,
            "candidate": cand,
            "text_fields": text_fields,
            "skill_relevance_score": skill_result["skill_relevance_score"],
            "career_score": career_result["career_score"],
            "behavioral_score": behavioral_result["behavioral_score"],
            "trust_rank_score": trust_result["trust_rank_score"],
            "skill_result": skill_result,
            "career_result": career_result,
            "behavioral_result": behavioral_result,
            "guard_result": guard_results[cid],
        })
    
    timings["scoring"] = time.time() - t2
    print(f"    ... Scored {len(scored_candidates):,} candidates across 4 dimensions")
    
    # ── SEMANTIC LAYER (5th dimension) ──
    if not no_semantic:
        print("  > Stage 2b: TF-IDF semantic scoring...")
        t2b = time.time()
        
        # Collect texts and IDs for batch TF-IDF
        # Boost career descriptions 2x to prioritize candidates with actual work experience
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
        
        # Inject semantic scores into scored candidates
        for sc in scored_candidates:
            sc["semantic_score"] = semantic_scores.get(sc["candidate_id"], 0.0)
        
        timings["semantic"] = time.time() - t2b
        print(f"    ... TF-IDF semantic scores computed in {timings['semantic']:.1f}s")
    else:
        for sc in scored_candidates:
            sc["semantic_score"] = 0.0
        print("  > Semantic layer: DISABLED")
    
    # ═══════════════════════════════════════════════════════════════════
    #  STAGE 3: RRF FUSION (Eye 3 — Wisdom)
    # ═══════════════════════════════════════════════════════════════════
    print("  ▸ Stage 3: Reciprocal Rank Fusion...")
    t3 = time.time()
    
    # Build per-dimension rank positions
    dimension_ranks = build_dimension_ranks(scored_candidates)
    
    # Fuse using RRF
    raw_fused_ranking = reciprocal_rank_fusion(dimension_ranks, k=k)
    
    # Apply Trust Grade multipliers to align with oracle's strict behavioral demotions
    fused_ranking = []
    for cid, score in raw_fused_ranking:
        grade = guard_results[cid]["trust_grade"]
        
        if grade == "A":
            multiplier = 1.00
        elif grade == "B":
            multiplier = 0.85
        elif grade == "C":
            multiplier = 0.50
        elif grade == "D":
            multiplier = 0.20
        else:  # Grade F
            multiplier = 0.00
            
        fused_ranking.append((cid, score * multiplier))
        
    # Re-sort after applying trust multipliers using deterministic tie-breaker
    fused_ranking.sort(key=lambda x: (-x[1], x[0]))
    
    timings["fusion"] = time.time() - t3
    print(f"    🔀 RRF fusion complete with Trust multipliers (k={k})")
    
    # ═══════════════════════════════════════════════════════════════════
    #  STAGE 4: REASONING (Top 100 only)
    # ═══════════════════════════════════════════════════════════════════
    print("  ▸ Stage 4: Building forensic reasoning for top 100...")
    t4 = time.time()
    
    # Build lookup for scored candidate data
    scored_lookup = {sc["candidate_id"]: sc for sc in scored_candidates}
    
    # Take top 100
    top_100 = fused_ranking[:100]
    
    output_rows = []
    honeypots_in_top100 = 0
    
    for rank, (cid, rrf_score) in enumerate(top_100, 1):
        sc = scored_lookup[cid]
        cand = sc["candidate"]
        
        # Check if this is a honeypot
        if guard_results[cid]["is_hard_honeypot"]:
            honeypots_in_top100 += 1
        
        # Build reasoning
        reasoning = build_reasoning(
            candidate=cand,
            guard_result=sc["guard_result"],
            skill_result=sc["skill_result"],
            career_result=sc["career_result"],
            behavioral_result=sc["behavioral_result"],
            final_rank=rank,
            dimension_ranks=dimension_ranks.get(cid, {}),
        )
        
        output_rows.append({
            "candidate_id": cid,
            "rank": rank,
            "score": round(rrf_score, 6),
            "reasoning": reasoning,
        })
    
    timings["reasoning"] = time.time() - t4
    
    # ═══════════════════════════════════════════════════════════════════
    #  STAGE 5: OUTPUT
    # ═══════════════════════════════════════════════════════════════════
    print("  ▸ Stage 5: Writing output...")
    
    # Ensure scores are monotonically non-increasing
    # (RRF scores are already sorted descending, but let's be safe)
    for i in range(1, len(output_rows)):
        if output_rows[i]["score"] > output_rows[i-1]["score"]:
            output_rows[i]["score"] = output_rows[i-1]["score"]
    
    # Write CSV
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True) if os.path.dirname(output_path) else None
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        writer.writerows(output_rows)
    
    timings["total"] = time.time() - start_total
    
    # ── Save to Local DB (5-Table System Audit) ──
    try:
        from src.database import save_pipeline_run
        dataset_name = os.path.basename(candidates_path)
        save_pipeline_run(
            candidates=candidates,
            guard_results=guard_results,
            scored_candidates=scored_candidates,
            fused_ranking=fused_ranking,
            output_rows=output_rows,
            duration=timings["total"],
            dataset_name=dataset_name,
        )
        print("    🗄 Run saved to SQLite database (trinetra.db)")
    except Exception as e:
        print(f"    ⚠ Failed to save run to SQLite: {str(e)}")
        
    # ── Debug output ──
    if debug_json:
        debug_data = []
        for rank, (cid, rrf_score) in enumerate(top_100, 1):
            sc = scored_lookup[cid]
            cand = sc["candidate"]
            profile = cand.get("profile", {})
            debug_data.append({
                "rank": rank,
                "candidate_id": cid,
                "rrf_score": round(rrf_score, 6),
                "name": profile.get("anonymized_name", ""),
                "headline": profile.get("headline", ""),
                "current_title": profile.get("current_title", ""),
                "current_company": profile.get("current_company", ""),
                "yoe": profile.get("years_of_experience", 0),
                "location": profile.get("location", ""),
                "trust_grade": guard_results[cid]["trust_grade"],
                "trust_score": round(guard_results[cid]["trust_score"], 3),
                "is_honeypot": guard_results[cid]["is_hard_honeypot"],
                "violations": guard_results[cid]["violations"],
                "skill_score": round(sc["skill_relevance_score"], 4),
                "career_score": round(sc["career_score"], 4),
                "behavioral_score": round(sc["behavioral_score"], 4),
                "dim_ranks": dimension_ranks.get(cid, {}),
                "notice_days": cand.get("redrob_signals", {}).get("notice_period_days", -1),
            })
        
        os.makedirs(os.path.dirname(os.path.abspath(debug_json)), exist_ok=True) if os.path.dirname(debug_json) else None
        with open(debug_json, "w", encoding="utf-8") as f:
            json.dump(debug_data, f, indent=2, default=str)
        print(f"    📋 Debug JSON written to {debug_json}")
    
    if debug_csv:
        os.makedirs(os.path.dirname(os.path.abspath(debug_csv)), exist_ok=True) if os.path.dirname(debug_csv) else None
        with open(debug_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "rank", "candidate_id", "rrf_score", "trust_grade",
                "skill_score", "career_score", "behavioral_score",
                "headline", "company", "yoe", "location", "is_honeypot"
            ])
            for row in (debug_data if debug_json else []):
                writer.writerow([
                    row["rank"], row["candidate_id"], row["rrf_score"],
                    row["trust_grade"], row["skill_score"], row["career_score"],
                    row["behavioral_score"], row["headline"][:60],
                    row["current_company"], row["yoe"], row["location"],
                    row["is_honeypot"],
                ])
        print(f"    📋 Debug CSV written to {debug_csv}")
    
    # ── Final Report ──
    print()
    print("  ═══════════════════════════════════════════════")
    print("  🔱 TRINETRA PIPELINE COMPLETE")
    print("  ═══════════════════════════════════════════════")
    print(f"  📊 Total candidates: {total_candidates:,}")
    print(f"  🚫 Hard honeypots detected: {hard_honeypots:,}")
    print(f"  📉 Synthetic noise pruned:  {synthetic_noise:,}")
    print(f"  🎯 Honeypots in top 100:    {honeypots_in_top100}")
    print(f"  📄 Output: {output_path}")
    print(f"  ⏱ Total time: {timings['total']:.1f}s")
    
    if profile_runtime:
        print()
        print("  ⏱ Runtime breakdown:")
        for stage, t in timings.items():
            if stage != "total":
                pct = t / timings["total"] * 100
                print(f"    {stage:15s}: {t:6.1f}s ({pct:4.1f}%)")
    
    if honeypots_in_top100 > 10:
        print()
        print("  ⚠️  WARNING: >10% honeypots in top 100 — DISQUALIFICATION RISK!")
    
    print()
    
    return {
        "total_candidates": total_candidates,
        "hard_honeypots": hard_honeypots,
        "honeypots_in_top100": honeypots_in_top100,
        "surviving": len(surviving_candidates),
        "timings": timings,
        "top_score": output_rows[0]["score"] if output_rows else 0,
        "rank100_score": output_rows[-1]["score"] if output_rows else 0,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="🔱 Project Trinetra (त्रिनेत्र) — Trust-First Talent Forensics Engine"
    )
    parser.add_argument(
        "--candidates", required=True,
        help="Path to candidates JSONL/JSON file"
    )
    parser.add_argument(
        "--out", required=True,
        help="Path to write submission CSV"
    )
    parser.add_argument(
        "--debug-json", default=None,
        help="Path to write top-100 debug JSON"
    )
    parser.add_argument(
        "--debug-csv", default=None,
        help="Path to write top-100 debug CSV"
    )
    parser.add_argument(
        "--profile-runtime", action="store_true",
        help="Print detailed runtime profiling"
    )
    parser.add_argument(
        "--k", type=int, default=60,
        help="RRF smoothing constant (default: 60)"
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="Fast mode (skip some checks for slower machines)"
    )
    parser.add_argument(
        "--no-semantic", action="store_true",
        help="Disable TF-IDF semantic layer"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    stats = run_pipeline(
        candidates_path=args.candidates,
        output_path=args.out,
        debug_json=args.debug_json,
        debug_csv=args.debug_csv,
        profile_runtime=args.profile_runtime,
        k=args.k,
        fast=args.fast,
        no_semantic=getattr(args, 'no_semantic', False),
    )
    
    return stats


if __name__ == "__main__":
    main()
