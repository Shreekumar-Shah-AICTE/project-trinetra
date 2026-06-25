"""
validate.py — Internal submission format validator for Project Trinetra (त्रिनेत्र)

Mirrors the organizer's validation checks to catch format errors before submission.
"""

import csv
import json
import os
import sys


def validate_submission(csv_path: str, candidates_path: str = None) -> tuple[bool, list[str]]:
    """
    Validate a submission CSV against the spec.
    
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
    if not os.path.exists(csv_path):
        return False, [f"File not found: {csv_path}"]
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        # Check header
        expected_columns = {"candidate_id", "rank", "score", "reasoning"}
        if set(reader.fieldnames or []) != expected_columns:
            errors.append(f"Expected columns {expected_columns}, got {set(reader.fieldnames or [])}")
        
        rows = list(reader)
    
    # Check row count
    if len(rows) != 100:
        errors.append(f"Expected exactly 100 rows, got {len(rows)}")
    
    # Check ranks
    ranks = []
    candidate_ids = []
    scores = []
    
    for i, row in enumerate(rows):
        try:
            rank = int(row["rank"])
            ranks.append(rank)
        except (ValueError, KeyError):
            errors.append(f"Row {i+1}: invalid rank '{row.get('rank', 'MISSING')}'")
        
        try:
            score = float(row["score"])
            scores.append(score)
        except (ValueError, KeyError):
            errors.append(f"Row {i+1}: invalid score '{row.get('score', 'MISSING')}'")
        
        cid = row.get("candidate_id", "")
        candidate_ids.append(cid)
    
    # Check rank uniqueness and range
    if ranks:
        expected_ranks = set(range(1, 101))
        actual_ranks = set(ranks)
        if actual_ranks != expected_ranks:
            missing = expected_ranks - actual_ranks
            extra = actual_ranks - expected_ranks
            if missing:
                errors.append(f"Missing ranks: {sorted(missing)[:5]}...")
            if extra:
                errors.append(f"Extra ranks: {sorted(extra)[:5]}...")
    
    # Check candidate_id uniqueness
    if len(set(candidate_ids)) != len(candidate_ids):
        dupes = [cid for cid in candidate_ids if candidate_ids.count(cid) > 1]
        errors.append(f"Duplicate candidate_ids: {set(dupes)}")
    
    # Check candidate_id format
    for cid in candidate_ids:
        if not cid.startswith("CAND_") or len(cid) != 12:
            errors.append(f"Invalid candidate_id format: '{cid}'")
            break
    
    # Check scores are monotonically non-increasing
    if scores:
        for i in range(1, len(scores)):
            if scores[i] > scores[i-1]:
                errors.append(
                    f"Scores not monotonically non-increasing at rank {i+1}: "
                    f"{scores[i]} > {scores[i-1]}"
                )
                break
    
    # Check reasoning is not empty for all rows
    reasonings = [row.get("reasoning", "") for row in rows]
    empty_count = sum(1 for r in reasonings if not r.strip())
    if empty_count > 0:
        errors.append(f"{empty_count} rows have empty reasoning (spec strongly recommends reasoning)")
    
    # Check reasoning variation
    if reasonings:
        unique_reasonings = set(reasonings)
        if len(unique_reasonings) < len(reasonings) * 0.5:
            errors.append("Reasoning strings are too similar (>50% duplicates)")
    
    # Validate against candidates file if provided
    if candidates_path and os.path.exists(candidates_path):
        valid_ids = set()
        ext = os.path.splitext(candidates_path)[1].lower()
        if ext == ".json":
            with open(candidates_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for c in (data if isinstance(data, list) else [data]):
                    valid_ids.add(c.get("candidate_id", ""))
        else:
            with open(candidates_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                        valid_ids.add(c.get("candidate_id", ""))
                    except json.JSONDecodeError:
                        continue
        
        for cid in candidate_ids:
            if cid not in valid_ids:
                errors.append(f"candidate_id '{cid}' not found in candidates file")
                break
    
    is_valid = len(errors) == 0
    return is_valid, errors


def main():
    """CLI entry point for validation."""
    if len(sys.argv) < 2:
        print("Usage: python src/validate.py <submission.csv> [candidates_path]")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    candidates_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"\n  Validating: {csv_path}")
    is_valid, errors = validate_submission(csv_path, candidates_path)
    
    if is_valid:
        print("  [PASS] Submission is valid!")
    else:
        print(f"  [FAIL] {len(errors)} error(s) found:")
        for err in errors:
            print(f"    - {err}")
    
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
