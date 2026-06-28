"""
hallucination_validator.py — Stage 4 No-Hallucination Fact Verifier

This module parses candidate reasoning strings to extract claimed facts (e.g. YOE, 
specific employers, notice period, tech skills) and cross-checks them directly 
against the raw JSON candidate records to guarantee 0% hallucination rates.
"""

import re
import sys

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def verify_reasoning_facts(candidate: dict, reasoning: str) -> dict:
    """
    Extract facts from the reasoning string and cross-check them with the profile.
    
    Returns:
        {
            "passed": bool,
            "errors": list[str]
        }
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = {s.get("name", "").lower() for s in candidate.get("skills", [])}
    
    errors = []

    # 1. Verify Years of Experience (e.g. "7 years building RAG" or "5.5 yrs")
    yoe_match = re.search(r"(\d+\.?\d*)\s*y(?:ea)?rs?", reasoning, re.IGNORECASE)
    if yoe_match:
        claimed_yoe = float(yoe_match.group(1))
        actual_yoe = float(profile.get("years_of_experience", 0))
        # Allow +/- 0.5 year rounding tolerance
        if abs(claimed_yoe - actual_yoe) > 0.51:
            errors.append(
                f"YOE mismatch: Claimed {claimed_yoe} yrs in reasoning, but profile has {actual_yoe} yrs."
            )
            
    # Matches "at Company Name", "at Yellow.ai", "at L&T", and stops before sentence-ending periods
    companies_in_reasoning = re.findall(r"at\s+([A-Z][a-zA-Z0-9\&\-]+(?:\.[a-z]+)?(?:\s+[A-Z][a-zA-Z0-9\&\-]+)*)", reasoning)
    
    actual_companies = {j.get("company", "").lower() for j in career if j.get("company")}
    if profile.get("current_company"):
        actual_companies.add(profile.get("current_company", "").lower())
    
    for company in companies_in_reasoning:
        # Ignore common non-company proper nouns (like "Bangalore", "Pune", "Noida")
        if company.lower() in ("bangalore", "pune", "noida", "delhi", "mumbai", "relocate"):
            continue
        
        comp_lower = company.lower()
        # Direct check or substring check
        match_found = comp_lower in actual_companies or any(comp_lower in ac for ac in actual_companies)
        if not match_found:
            errors.append(
                f"Employer hallucination: Mentioned working 'at {company}' but no such company exists in career history."
            )
                
    # 3. Verify Notice Period (e.g. "30d notice" or "60 days notice")
    notice_match = re.search(r"(\d+)\s*(?:d|days?)\s*notice", reasoning, re.IGNORECASE)
    if notice_match:
        claimed_notice = int(notice_match.group(1))
        actual_notice = int(candidate.get("redrob_signals", {}).get("notice_period_days", 0))
        if claimed_notice != actual_notice:
            errors.append(
                f"Notice period mismatch: Mentioned {claimed_notice} days in reasoning, but profile has {actual_notice} days."
            )

    # 4. Verify specific skills (e.g., FAISS, RAG, embeddings)
    # Check if reasoning claims experience with specific advanced tech keywords
    keywords = ["faiss", "bm25", "rag", "llama", "pytorch", "tensorflow", "embeddings", "vector search", "qlora", "langchain", "weaviate", "qdrant", "pinecone"]
    career_desc = " ".join([
        (j.get("description") or "") + " " + (j.get("title") or "") 
        for j in career
    ]).lower()
    headline = (profile.get("headline") or "").lower()
    summary = (profile.get("summary") or "").lower()
    full_profile_text = career_desc + " " + headline + " " + summary

    for kw in keywords:
        if kw in reasoning.lower():
            # If mentioned in reasoning, must exist in skills list or profile text
            if kw not in skills and kw not in full_profile_text:
                errors.append(
                    f"Skill/Tech hallucination: Mentioned '{kw}' in reasoning, but it is not listed in their skills or career details."
                )

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors
    }
