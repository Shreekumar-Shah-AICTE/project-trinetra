import json
import sys
import os

# Insert project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.guard_gate import _parse_date, _months_between

candidates_path = r"c:\Users\Shree Shah\Desktop\India RUNS hackathon\Analysis Material\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
TECH_RELEASE_YEARS = {
    "qlora": 2023, "llama-2": 2023, "llama 2": 2023, "bge embeddings": 2023, 
    "langchain": 2022, "qdrant": 2021, "peft": 2023, "llama-3": 2024,
    "llama 3": 2024, "mistral": 2023, "gpt-4": 2023, "chatgpt": 2022
}

def investigate():
    flagged = 0
    reasons = []
    
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            cand = json.loads(line)
            cid = cand["candidate_id"]
            
            # 1. Check career history
            has_career_fraud = False
            career_details = []
            for job in cand.get("career_history", []):
                end = _parse_date(job.get("end_date"))
                is_current = job.get("is_current", False)
                if not end and is_current:
                    end_year = 2026
                elif end:
                    end_year = end.year
                else:
                    continue
                    
                desc = (job.get("description") or "").lower()
                title_job = (job.get("title") or "").lower()
                full_job_text = desc + " " + title_job
                
                for tech, release_year in TECH_RELEASE_YEARS.items():
                    if tech in full_job_text and end_year < release_year:
                        has_career_fraud = True
                        career_details.append((tech, release_year, end_year, job.get("company")))
                        
            # 2. Check skills list
            has_skill_fraud = False
            skill_details = []
            ref_year = 2026
            for skill in cand.get("skills", []):
                skill_name = skill.get("name", "").lower()
                claimed_months = skill.get("duration_months", 0)
                
                for tech, release_year in TECH_RELEASE_YEARS.items():
                    if tech in skill_name:
                        max_possible_months = (ref_year - release_year + 1) * 12
                        if claimed_months > max_possible_months:
                            has_skill_fraud = True
                            skill_details.append((tech, release_year, claimed_months, skill_name))
                            
            if has_career_fraud or has_skill_fraud:
                flagged += 1
                if flagged <= 15:
                    print(f"Candidate {cid}:")
                    if has_career_fraud:
                        print(f"  Career Fraud: {career_details}")
                    if has_skill_fraud:
                        print(f"  Skill Fraud: {skill_details}")
                else:
                    # Collect reason statistics
                    for tech, ry, ey, comp in career_details:
                        reasons.append(f"Career: {tech} (rel {ry}) in job ending {ey}")
                    for tech, ry, cm, sn in skill_details:
                        reasons.append(f"Skill: {tech} (rel {ry}) claimed {cm} mo")
                        
    print(f"\nTotal Flagged: {flagged}")
    from collections import Counter
    print("\nTop Reasons:")
    for r, count in Counter(reasons).most_common(15):
        print(f"  {count}x {r}")

if __name__ == "__main__":
    investigate()
