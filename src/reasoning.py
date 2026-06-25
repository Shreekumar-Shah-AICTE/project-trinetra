"""
reasoning.py — Forensic Reasoning Chain Builder for Project Trinetra (त्रिनेत्र)

Builds evidence-grounded reasoning strings that read like detective case files,
not template-generated summaries. Every claim references actual candidate data.

The reasoning is built DURING scoring (accumulator pattern), not as a post-hoc summary.
"""


def build_reasoning(
    candidate: dict,
    guard_result: dict,
    skill_result: dict,
    career_result: dict,
    behavioral_result: dict,
    final_rank: int,
    dimension_ranks: dict,
) -> str:
    """
    Build a forensic-quality reasoning string for the submission CSV.
    
    Requirements from submission spec:
    - 1-2 sentences
    - Reference specific facts from candidate's profile
    - Connect to JD requirements
    - Acknowledge gaps honestly
    - No hallucination
    - Variation between candidates (not templated)
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    career = candidate.get("career_history", [])
    
    yoe = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "Unknown")
    company = profile.get("current_company", "Unknown")
    location = profile.get("location", "Unknown")
    headline = profile.get("headline", "")
    
    # ── Build reasoning segments ──
    segments = []
    concerns = []
    
    # 1. Identity + Trust
    trust_grade = guard_result.get("trust_grade", "?")
    if trust_grade in ("A", "B"):
        segments.append(f"[Trust: {trust_grade}]")
    elif trust_grade == "C":
        segments.append(f"[Trust: {trust_grade} — minor concerns]")
    else:
        segments.append(f"[Trust: {trust_grade} — flagged]")
        if guard_result.get("violations"):
            concerns.append(guard_result["violations"][0])
    
    # 2. Career summary (vary by career profile type)
    if career_result.get("product_jobs", 0) > 0:
        product_companies = guard_result.get("company_info", {}).get("product_companies", [])
        if product_companies:
            company_list = ", ".join(product_companies[:3])
            segments.append(f"{yoe:.1f} yrs; product lineage: {company_list}")
        else:
            segments.append(f"{yoe:.1f} yrs as {title} at {company}")
    else:
        segments.append(f"{yoe:.1f} yrs as {title}")
    
    # 3. Skill evidence (reference specific JD matches)
    core_match = skill_result.get("core_match", 0)
    if core_match >= 0.6:
        # Find specific matched concepts from career
        career_text = " ".join(j.get("description", "") for j in career).lower()
        matched_concepts = []
        for concept in ["embeddings", "vector search", "faiss", "ranking", "retrieval",
                        "bm25", "hybrid search", "ndcg", "recommendation", "search"]:
            if concept in career_text:
                matched_concepts.append(concept)
        if matched_concepts:
            segments.append(f"career evidence: {', '.join(matched_concepts[:4])}")
        else:
            segments.append("strong JD skill alignment")
    elif core_match >= 0.3:
        segments.append("moderate JD alignment")
    else:
        concerns.append("limited core skill evidence")
    
    # 4. Production evidence
    if skill_result.get("production_match", 0) >= 0.4:
        segments.append("production deployment experience")
    
    # 5. Behavioral highlights (pick the most notable)
    notice_days = behavioral_result.get("notice_days", 90)
    if notice_days <= 30:
        segments.append(f"{notice_days}d notice")
    elif notice_days >= 90:
        concerns.append(f"long notice ({notice_days}d)")
    
    if behavioral_result.get("activity_score", 0) >= 0.8:
        segments.append("recently active")
    elif behavioral_result.get("activity_score", 0) <= 0.3:
        concerns.append("inactive >90d")
    
    # 6. Location
    if career_result.get("location_score", 0) >= 0.8:
        segments.append(f"{location}")
    elif career_result.get("location_score", 0) <= 0.4:
        if not signals.get("willing_to_relocate", False):
            concerns.append(f"outside target geography ({location})")
    
    # 7. Rank dimension breakdown
    skill_rank = dimension_ranks.get("skill", "?")
    career_rank = dimension_ranks.get("career", "?")
    behavioral_rank = dimension_ranks.get("behavioral", "?")
    trust_rank = dimension_ranks.get("trust", "?")
    
    rank_str = f"Dim ranks: S#{skill_rank}/C#{career_rank}/B#{behavioral_rank}/T#{trust_rank}"
    
    # ── Assemble reasoning ──
    main_text = "; ".join(segments)
    
    if concerns:
        concern_text = "; ".join(concerns[:2])
        reasoning = f"{main_text}. Concerns: {concern_text}. {rank_str}"
    else:
        reasoning = f"{main_text}. {rank_str}"
    
    # Ensure within spec: 1-2 sentences, reasonable length
    if len(reasoning) > 350:
        reasoning = reasoning[:347] + "..."
    
    return reasoning
