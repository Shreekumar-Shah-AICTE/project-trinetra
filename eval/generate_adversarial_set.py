import csv
import json
import os
import sys
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.guard_gate import run_guard_gate

CANDIDATES_PATH = r"C:\Users\Shree Shah\Desktop\India RUNS hackathon\Analysis Material\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
SUBMISSION_PATH = str(ROOT / "submission.csv")
OUTPUT_PATH = str(ROOT / "eval" / "adversarial_profiles.txt")


def load_top_15_ids(path: str) -> list[str]:
    """Load top 15 ranked candidate IDs from submission CSV."""
    ids = []
    if not os.path.exists(path):
        print(f"Warning: submission.csv not found at {path}")
        return []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 15:
                break
            ids.append(row["candidate_id"].strip())
    return ids


def main():
    print("Generating Adversarial Dataset...")
    
    top_15_ids = load_top_15_ids(SUBMISSION_PATH)
    if not top_15_ids:
        print("Error: No candidates found in submission.csv. Run ranking first!")
        return
        
    top_15_set = set(top_15_ids)
    
    top_15_candidates = []
    disqualified_candidates = []
    
    # Scan candidates file
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                cand = json.loads(line)
                cid = cand["candidate_id"]
                
                # Check if top 15
                if cid in top_15_set:
                    top_15_candidates.append(cand)
                    
                # Collect disqualified/honeypot candidates (limit to 5)
                elif len(disqualified_candidates) < 5:
                    result = run_guard_gate(cand)
                    if result["is_hard_honeypot"] or result["disqualified"]:
                        disqualified_candidates.append((cand, result))
            except Exception as e:
                continue
                
    # Sort top 15 according to their rank in submission.csv
    top_15_candidates_sorted = []
    for cid in top_15_ids:
        for cand in top_15_candidates:
            if cand["candidate_id"] == cid:
                top_15_candidates_sorted.append(cand)
                break
                
    # Format output file
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write("========================================================================\n")
        out.write("🔱 PROJECT TRINETRA — ADVERSARIAL PROFILE DATASET FOR GEMINI 3.1 PRO\n")
        out.write("========================================================================\n\n")
        
        out.write("--- JOB DESCRIPTION (TARGET ROLE) ---\n")
        out.write("Role: Senior Machine Learning Engineer (Search & Recommendation Relevance)\n")
        out.write("Core Technologies: NLP, Information Retrieval, Vector Search, FAISS, BM25, RRF, PyTorch, Python.\n")
        out.write("Scale/Experience: 5-9 years of experience. Deploying search/relevance systems to production scale.\n\n")
        
        out.write("--- PART 1: TRINETRA TOP 15 RANKED CANDIDATES ---\n")
        out.write("The following 15 candidates are ranked highest by Trinetra. Verify if their experience is genuinely relevant, or if they are keyword-stuffing / possessing subtle logical profile contradictions.\n\n")
        
        for rank, cand in enumerate(top_15_candidates_sorted, 1):
            profile = cand.get("profile", {})
            out.write(f"RANK #{rank} | CANDIDATE ID: {cand['candidate_id']}\n")
            out.write(f"Name: {profile.get('anonymized_name', 'N/A')}\n")
            out.write(f"Current Title: {profile.get('current_title', 'N/A')}\n")
            out.write(f"Current Company: {profile.get('current_company', 'N/A')}\n")
            out.write(f"Years of Experience: {profile.get('years_of_experience', 0.0)}\n")
            out.write(f"Location: {profile.get('location', 'N/A')}\n")
            out.write("Skills:\n")
            for s in cand.get("skills", []):
                out.write(f"  - {s.get('name')}: {s.get('proficiency')} ({s.get('duration_months', 0)} months, {s.get('endorsements', 0)} endorsements)\n")
            out.write("Career History:\n")
            for job in cand.get("career_history", []):
                out.write(f"  * Company: {job.get('company')} | Title: {job.get('title')} | Date: {job.get('start_date')} to {job.get('end_date')} | Duration: {job.get('duration_months')} months\n")
                out.write(f"    Description: {job.get('description')}\n")
            out.write("Education:\n")
            for edu in cand.get("education", []):
                out.write(f"  * Degree: {edu.get('degree')} | Field: {edu.get('field_of_study')} | Start: {edu.get('start_year')} | End: {edu.get('end_year')}\n")
            out.write("\n------------------------------------------------------------------------\n\n")
            
        out.write("--- PART 2: TRINETRA DISQUALIFIED / HONEYPOT CANDIDATES (SAMPLE OF 5) ---\n")
        out.write("The following 5 candidates were flagged as fraud/honeypots or domain-disqualified by Trinetra. Verify if our engine was correct to block them, or if we suffered a false positive.\n\n")
        
        for cand, res in disqualified_candidates:
            profile = cand.get("profile", {})
            out.write(f"DISQUALIFIED | CANDIDATE ID: {cand['candidate_id']}\n")
            out.write(f"Reason Flagged: {res['disqualify_reason'] or 'Hard Honeypot / Behavioral Fraud'}\n")
            out.write(f"Trust Grade assigned: {res['trust_grade']} | Trust Score: {res['trust_score']}\n")
            out.write(f"Name: {profile.get('anonymized_name', 'N/A')}\n")
            out.write(f"Current Title: {profile.get('current_title', 'N/A')}\n")
            out.write(f"Current Company: {profile.get('current_company', 'N/A')}\n")
            out.write(f"Years of Experience: {profile.get('years_of_experience', 0.0)}\n")
            out.write("Skills:\n")
            for s in cand.get("skills", []):
                out.write(f"  - {s.get('name')}: {s.get('proficiency')} ({s.get('duration_months', 0)} months, {s.get('endorsements', 0)} endorsements)\n")
            out.write("Career History:\n")
            for job in cand.get("career_history", []):
                out.write(f"  * Company: {job.get('company')} | Title: {job.get('title')} | Date: {job.get('start_date')} to {job.get('end_date')} | Duration: {job.get('duration_months')} months\n")
                out.write(f"    Description: {job.get('description')}\n")
            out.write("Education:\n")
            for edu in cand.get("education", []):
                out.write(f"  * Degree: {edu.get('degree')} | Field: {edu.get('field_of_study')} | Start: {edu.get('start_year')} | End: {edu.get('end_year')}\n")
            out.write("\n------------------------------------------------------------------------\n\n")
            
    print(f"Success! Format written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
