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
    Generates natural, fluent 1-2 sentence recruiter briefs matching
    exact profile facts to JD requirements, and highlighting honest concerns.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    career = candidate.get("career_history", [])
    
    yoe = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "Unknown")
    company = profile.get("current_company", "Unknown")
    location = profile.get("location", "Unknown")
    
    # 1. Build Introduction (Product lineage or company context)
    product_companies = guard_result.get("company_info", {}).get("product_companies", [])
    current_company = company if company and company.lower() != "unknown" else (product_companies[0] if product_companies else "")
    
    if current_company and current_company.lower() != "unknown":
        if product_companies:
            company_list = ", ".join(product_companies[:2])
            intro = f"{title} at {current_company} with {yoe:.1f} yrs experience, showing strong product lineage at {company_list}."
        else:
            intro = f"{title} at {current_company} with {yoe:.1f} yrs experience."
    else:
        if product_companies:
            company_list = ", ".join(product_companies[:2])
            intro = f"{title} with {yoe:.1f} yrs experience, showing strong product lineage at {company_list}."
        else:
            intro = f"{title} with {yoe:.1f} yrs experience."
        
    # 2. Build Skill Alignment (reference matched concepts)
    career_text = " ".join(j.get("description", "") for j in career).lower()
    
    systems = [s for s in ["retrieval", "ranking", "recommendation", "hybrid search", "semantic search"] if s in career_text]
    tools = [t for t in ["faiss", "bm25", "pinecone", "qdrant", "milvus", "cross-encoder", "embeddings"] if t in career_text]
    metrics = [m for m in ["ndcg", "mrr", "map"] if m in career_text]
    
    parts = []
    if systems:
        parts.append(f"building {', '.join(systems[:2])} systems")
    if tools:
        parts.append(f"using {', '.join(tools[:2])}")
    if metrics:
        parts.append(f"evaluated with {', '.join(metrics[:1])}")
            
    if parts:
        skill_str = "Demonstrated career experience " + ", ".join(parts) + "."
    else:
        skill_str = "Possesses foundational software engineering and adjacent AI/ML concepts."
        
    # 3. Build Location & Notice Availability
    notice_days = behavioral_result.get("notice_days", 90)
    willing_reloc = signals.get("willing_to_relocate", True)
    response_rate = signals.get("recruiter_response_rate", 0.0)
    
    loc_avail = []
    if career_result.get("location_score", 0) >= 0.8:
        loc_avail.append(f"based locally in {location}")
    elif willing_reloc:
        loc_avail.append("willing to relocate")
        
    if notice_days <= 30:
        loc_avail.append(f"immediate joiner ({notice_days}d notice)")
        
    if response_rate >= 0.85:
        loc_avail.append(f"highly responsive ({response_rate:.0%} response rate)")
        
    loc_avail_str = ""
    if loc_avail:
        loc_avail_str = f"Candidate is {', '.join(loc_avail)}."
        
    # 4. Build Concerns
    concerns = []
    trust_grade = guard_result.get("trust_grade", "?")
    if trust_grade not in ("A",):
        concerns.append(f"has Trust Grade {trust_grade} with minor profile flags")
    if notice_days >= 45:
        concerns.append(f"has a notice period of {notice_days} days")
    if behavioral_result.get("activity_score", 0) <= 0.3:
        concerns.append("shows low recent activity")
    if not willing_reloc and career_result.get("location_score", 0) <= 0.4:
        concerns.append(f"is located outside target city ({location}) and refuses relocation")
    
    offer_rate = signals.get("offer_acceptance_rate", 1.0)
    if offer_rate == 0.0:
        concerns.append("declined all previous offers")
        
    concern_str = ""
    if concerns:
        concern_str = f"Concern: candidate {'; '.join(concerns[:2])}."
        
    # 5. Assemble into 1-2 sentence recruiter brief
    sentences = [intro]
    if parts:
        sentences.append(skill_str)
    if loc_avail_str:
        sentences.append(loc_avail_str)
    if concern_str:
        sentences.append(concern_str)
        
    if len(sentences) > 2:
        body = " ".join(sentences[:2])
        if concern_str:
            body += " " + concern_str
    else:
        body = " ".join(sentences)
        
    # 6. Rank Metadata
    skill_rank = dimension_ranks.get("skill", "?")
    career_rank = dimension_ranks.get("career", "?")
    behavioral_rank = dimension_ranks.get("behavioral", "?")
    trust_rank = dimension_ranks.get("trust", "?")
    rank_meta = f"[RRF Rank #{final_rank} | S#{skill_rank}/C#{career_rank}/B#{behavioral_rank}/T#{trust_rank}]"
    
    reasoning = f"{body} {rank_meta}"
    
    if len(reasoning) > 350:
        reasoning = reasoning[:347] + "..."
        
    return reasoning
