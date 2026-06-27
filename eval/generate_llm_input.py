"""
generate_llm_input.py — Formatter for Gemini LLM Benchmark Input
🔱 Converts 167 JSON profiles into a highly readable, token-compact text format.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "eval" / "benchmark_candidates.json"
TXT_PATH = ROOT / "eval" / "llm_benchmark_input.txt"


def format_candidate(cand: dict) -> str:
    profile = cand.get("profile", {})
    cid = cand["candidate_id"]
    name = profile.get("anonymized_name", "Anonymous")
    title = profile.get("current_title", "Unknown")
    company = profile.get("current_company", "Unknown")
    yoe = profile.get("years_of_experience", 0.0)
    headline = profile.get("headline", "")
    
    # Redrob signals
    signals = cand.get("redrob_signals", {})
    notice = signals.get("notice_period_days", 90)
    completeness = signals.get("profile_completeness_score", 50)
    last_active = signals.get("last_active_date", "Unknown")
    
    # Career History
    career_str = []
    for job in cand.get("career_history", []):
        j_comp = job.get("company", "Unknown")
        j_title = job.get("title", "Unknown")
        j_start = job.get("start_date", "")
        j_end = job.get("end_date", "Present")
        j_months = job.get("duration_months", 0)
        j_desc = job.get("description", "")
        
        # Truncate description slightly for context window constraints
        if len(j_desc) > 200:
            j_desc = j_desc[:200] + "..."
            
        career_str.append(
            f"    - Job: {j_title} at {j_comp} ({j_start} to {j_end}, claimed {j_months} mos)\n"
            f"      Desc: {j_desc}"
        )
    career_full = "\n".join(career_str)
    
    # Education
    edu_str = []
    for edu in cand.get("education", []):
        school = edu.get("school", "Unknown")
        degree = edu.get("degree", "Unknown")
        start = edu.get("start_year", 0)
        end = edu.get("end_year", 0)
        edu_str.append(f"    - {degree} from {school} ({start}-{end})")
    edu_full = "\n".join(edu_str)
    
    # Skills
    skills_list = [s.get("name", "") for s in cand.get("skills", [])]
    skills_list = [s for s in skills_list if s][:20]  # Take top 20
    skills_full = ", ".join(skills_list)
    
    return f"""=========================================
CANDIDATE: {cid} ({name})
Current Title: {title} at {company} | YOE: {yoe} years
Headline: {headline}
Behavioral: Notice period: {notice} days | Active: {last_active} | Completeness: {completeness}%
Skills: {skills_full}
Education:
{edu_full}
Career History:
{career_full}
"""


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    output = []
    output.append(f"TOTAL CANDIDATES FOR EVALUATION: {len(candidates)}\n")
    
    for c in candidates:
        output.append(format_candidate(c))
        
    with open(TXT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
        
    print(f"  Successfully wrote LLM input to {TXT_PATH}")


if __name__ == "__main__":
    main()
