import json
import sys
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

cids = ["CAND_0033861", "CAND_0000031", "CAND_0082086"]
candidates = {}
with open("../Analysis Material/[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        if c["candidate_id"] in cids:
            candidates[c["candidate_id"]] = c

from eval.gold_labeler import _is_honeypot, label_candidate, _get_career_text, _describes_real_systems, _has_production_depth, FICTIONAL_COMPANIES

for cid in cids:
    if cid not in candidates:
        print(f"CID {cid} not found in candidates file")
        continue
    cand = candidates[cid]
    is_hp = _is_honeypot(cand)
    
    # Trace the logic inside label_candidate
    profile = cand.get("profile", {})
    signals = cand.get("redrob_signals", {})
    career_history = cand.get("career_history", [])
    location = (profile.get("location") or "").lower()
    willing_to_relocate = signals.get("willing_to_relocate", True)
    
    target_cities = ["noida", "pune", "delhi", "ncr", "gurgaon", "ghaziabad", "faridabad"]
    is_target_local = any(city in location for city in target_cities)
    approved_remote_cities = ["hyderabad", "mumbai"]
    is_approved_remote = any(city in location for city in approved_remote_cities)
    
    geography_failed = not is_target_local and not is_approved_remote and not willing_to_relocate
    
    career_companies = [j.get("company", "").lower().strip() for j in career_history if j.get("company")]
    consulting_firms = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini", "tata consultancy"]
    all_consulting = all(any(c in comp for c in consulting_firms) for comp in career_companies) if career_companies else False
    
    title = (profile.get("current_title") or "").lower()
    headline = (profile.get("headline") or "").lower()
    career_text = _get_career_text(cand)
    
    wrong_specialization_keywords = ["computer vision", " cv ", "vision engineer", "speech engineer", "audio engineer", "robotics", "perception engineer"]
    is_wrong_spec = any(kw in title or kw in headline for kw in wrong_specialization_keywords)
    
    academic_keywords = ["university", "institute", "college", "research lab", "academy"]
    all_academic = True
    for job in career_history:
        company = (job.get("company") or "").lower()
        if company and not any(kw in company for kw in academic_keywords):
            all_academic = False
            break
    if len(career_history) == 0:
        all_academic = False
        
    has_real_systems = _describes_real_systems(career_text)
    has_production = _has_production_depth(career_text)
    
    is_academic_failed = all_academic and not has_production

    print(f"ID: {cid}")
    print(f"  Is Honeypot (oracle): {is_hp}")
    print(f"  Geography failed: {geography_failed} (Loc: '{profile.get('location')}', Reloc: {willing_to_relocate})")
    print(f"  Consulting-only: {all_consulting} (Companies: {career_companies})")
    print(f"  Wrong spec: {is_wrong_spec} (Title: '{profile.get('current_title')}')")
    print(f"  Academic failed: {is_academic_failed} (Academic companies: {all_academic}, Has prod: {has_production})")
    print(f"  Has real systems: {has_real_systems} | Has production depth: {has_production}")
    print(f"  Final Tier: {label_candidate(cand)}")
    print()
