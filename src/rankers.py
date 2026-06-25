"""
rankers.py — Eye 2: Multi-Dimensional Ranking Engine for Project Trinetra (त्रिनेत्र)

Four independent rankers, each producing their own sorted candidate list.
These are later fused using RRF (Eye 3) — never manually weighted.

Dimensions:
  1. Skill Relevance  — How well does the candidate's text match the JD?
  2. Career Trajectory — Product company history, seniority, YOE fit
  3. Behavioral Availability — Notice period, activity, responsiveness
  4. Trust Grade — Output from Guard Gate (Eye 1)
"""

import math
from datetime import datetime
from typing import Optional

from src.jd import (
    CORE_CONCEPTS, PREFERRED_CONCEPTS, GENERAL_AI_CONCEPTS,
    PRODUCTION_KEYWORDS,
    IDEAL_YOE_MIN, IDEAL_YOE_MAX, SWEET_SPOT_YOE_MIN, SWEET_SPOT_YOE_MAX,
    PREFERRED_LOCATIONS, TIER1_INDIA_CITIES,
    PRODUCT_COMPANIES, SERVICES_COMPANIES,
)


# ──────────────────────────────────────────────────────────────────────
#  DIMENSION 1: SKILL RELEVANCE RANKER
# ──────────────────────────────────────────────────────────────────────

def score_skill_relevance(candidate: dict, text_fields: dict) -> dict:
    """
    Score how well a candidate's profile matches the JD's technical requirements.
    
    Uses SOURCE-AWARE evidence weighting:
    - Career descriptions (weight 1.0): strongest proof of shipped work
    - Current title (weight 0.85): important but not enough alone
    - Summary/headline (weight 0.45): helpful but self-written
    - Skill names (weight 0.25): weakest — supporting evidence only
    
    Returns a score dict with detailed breakdown.
    """
    # Source-weighted concept matching
    source_weights = {
        "career_descriptions": 1.00,
        "current_title": 0.85,
        "headline": 0.45,
        "summary": 0.45,
        "skill_names": 0.25,
        "education": 0.20,
    }
    
    # Score each concept tier
    core_score = _score_concept_tier(text_fields, source_weights, CORE_CONCEPTS, tier_weight=1.0)
    preferred_score = _score_concept_tier(text_fields, source_weights, PREFERRED_CONCEPTS, tier_weight=0.6)
    general_score = _score_concept_tier(text_fields, source_weights, GENERAL_AI_CONCEPTS, tier_weight=0.3)
    production_score = _score_concept_tier(text_fields, source_weights, PRODUCTION_KEYWORDS, tier_weight=0.5)
    
    # Combine: core has dominant weight
    total_score = (
        0.45 * core_score
        + 0.20 * preferred_score
        + 0.15 * general_score
        + 0.20 * production_score
    )
    
    # Normalize to 0-1 range (cap at 1.0)
    total_score = min(1.0, total_score)
    
    return {
        "skill_relevance_score": total_score,
        "core_match": core_score,
        "preferred_match": preferred_score,
        "general_match": general_score,
        "production_match": production_score,
    }


def _score_concept_tier(text_fields: dict, source_weights: dict,
                        concepts: list, tier_weight: float) -> float:
    """
    Score a candidate against a tier of concepts using source-weighted matching.
    Higher weight for matches found in career descriptions vs skill tags.
    """
    if not concepts:
        return 0.0
    
    total_weighted_matches = 0.0
    
    for concept in concepts:
        concept_lower = concept.lower()
        best_source_weight = 0.0
        
        for source_name, weight in source_weights.items():
            text = text_fields.get(source_name, "").lower()
            if concept_lower in text:
                best_source_weight = max(best_source_weight, weight)
        
        total_weighted_matches += best_source_weight * tier_weight
    
    # Normalize by concept count, apply diminishing returns
    max_possible = len(concepts) * tier_weight * 1.0  # max weight is 1.0
    if max_possible == 0:
        return 0.0
    
    raw_ratio = total_weighted_matches / max_possible
    # Apply sqrt for diminishing returns (matching 30% of concepts well > matching 80% weakly)
    return min(1.0, math.sqrt(raw_ratio))


# ──────────────────────────────────────────────────────────────────────
#  DIMENSION 2: CAREER TRAJECTORY RANKER
# ──────────────────────────────────────────────────────────────────────

def score_career_trajectory(candidate: dict) -> dict:
    """
    Score career trajectory: product company lineage, progressive seniority,
    YOE fit, and overall career quality.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    
    yoe = profile.get("years_of_experience", 0)
    
    # ── YOE Fit (0-1) ──
    if SWEET_SPOT_YOE_MIN <= yoe <= SWEET_SPOT_YOE_MAX:
        yoe_score = 1.0
    elif IDEAL_YOE_MIN <= yoe <= IDEAL_YOE_MAX:
        yoe_score = 0.85
    elif 3 <= yoe < IDEAL_YOE_MIN:
        yoe_score = 0.5 + 0.35 * (yoe - 3) / (IDEAL_YOE_MIN - 3)
    elif IDEAL_YOE_MAX < yoe <= 12:
        yoe_score = 0.85 - 0.35 * (yoe - IDEAL_YOE_MAX) / (12 - IDEAL_YOE_MAX)
    elif yoe > 12:
        yoe_score = max(0.2, 0.5 - 0.05 * (yoe - 12))
    else:
        yoe_score = max(0.1, yoe / IDEAL_YOE_MIN * 0.5)
    
    # ── Product Company Ratio (0-1) ──
    product_jobs = 0
    services_jobs = 0
    total_months_product = 0
    total_months = 0
    
    for job in career:
        company_lower = job.get("company", "").lower()
        duration = job.get("duration_months", 0)
        total_months += duration
        
        if company_lower in PRODUCT_COMPANIES:
            product_jobs += 1
            total_months_product += duration
        elif company_lower in SERVICES_COMPANIES:
            services_jobs += 1
    
    if total_months > 0:
        product_ratio = total_months_product / total_months
    else:
        product_ratio = 0.0
    
    # ── Career Stability (0-1) ──
    # JD explicitly dislikes "title-chasers" switching every 1.5 years
    if len(career) == 0:
        stability_score = 0.0
    else:
        avg_tenure_months = total_months / len(career) if len(career) > 0 else 0
        if avg_tenure_months >= 30:
            stability_score = 1.0
        elif avg_tenure_months >= 18:
            stability_score = 0.7
        elif avg_tenure_months >= 12:
            stability_score = 0.4
        else:
            stability_score = 0.2
    
    # ── Progressive Seniority (0-1) ──
    # Check if title progression shows growth
    seniority_keywords = ["senior", "staff", "principal", "lead", "head", "director", "vp", "cto"]
    current_title = profile.get("current_title", "").lower()
    has_senior_current = any(kw in current_title for kw in seniority_keywords)
    seniority_score = 0.7 if has_senior_current else 0.4
    
    # ── Location Fit (0-1) ──
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    
    if any(loc in location for loc in PREFERRED_LOCATIONS):
        location_score = 1.0
    elif any(loc in location for loc in TIER1_INDIA_CITIES):
        location_score = 0.7
    elif "india" in country:
        location_score = 0.4
    else:
        location_score = 0.2
    
    # Combine career sub-scores
    career_score = (
        0.25 * yoe_score
        + 0.30 * product_ratio
        + 0.15 * stability_score
        + 0.10 * seniority_score
        + 0.20 * location_score
    )
    
    return {
        "career_score": min(1.0, career_score),
        "yoe_score": yoe_score,
        "product_ratio": product_ratio,
        "stability_score": stability_score,
        "seniority_score": seniority_score,
        "location_score": location_score,
        "yoe": yoe,
        "product_jobs": product_jobs,
    }


# ──────────────────────────────────────────────────────────────────────
#  DIMENSION 3: BEHAVIORAL AVAILABILITY RANKER
# ──────────────────────────────────────────────────────────────────────

def score_behavioral_availability(candidate: dict) -> dict:
    """
    Score how available and responsive the candidate is using Redrob's
    23 behavioral signals. A technically perfect candidate who hasn't
    logged in for 6 months is, for hiring purposes, not available.
    """
    signals = candidate.get("redrob_signals", {})
    
    # ── Notice Period (0-1) — Sub-30 days is preferred ──
    notice_days = signals.get("notice_period_days", 90)
    if notice_days <= 15:
        notice_score = 1.0
    elif notice_days <= 30:
        notice_score = 0.9
    elif notice_days <= 60:
        notice_score = 0.7
    elif notice_days <= 90:
        notice_score = 0.4
    else:
        notice_score = 0.2
    
    # ── Last Active Recency (0-1) ──
    last_active_str = signals.get("last_active_date", "")
    if last_active_str:
        try:
            last_active = datetime.strptime(last_active_str, "%Y-%m-%d")
            days_inactive = (datetime(2026, 6, 1) - last_active).days
            if days_inactive <= 7:
                activity_score = 1.0
            elif days_inactive <= 30:
                activity_score = 0.8
            elif days_inactive <= 90:
                activity_score = 0.5
            elif days_inactive <= 180:
                activity_score = 0.3
            else:
                activity_score = 0.1
        except (ValueError, TypeError):
            activity_score = 0.3
    else:
        activity_score = 0.3
    
    # ── Recruiter Response Rate (0-1) ──
    response_rate = signals.get("recruiter_response_rate", 0.0)
    response_score = min(1.0, response_rate)  # Already 0-1
    
    # ── Open to Work Flag ──
    open_to_work = 1.0 if signals.get("open_to_work_flag", False) else 0.4
    
    # ── Average Response Time ──
    avg_response_hours = signals.get("avg_response_time_hours", 72)
    if avg_response_hours <= 4:
        response_time_score = 1.0
    elif avg_response_hours <= 12:
        response_time_score = 0.8
    elif avg_response_hours <= 24:
        response_time_score = 0.6
    elif avg_response_hours <= 48:
        response_time_score = 0.4
    else:
        response_time_score = 0.2
    
    # ── Interview Completion Rate ──
    interview_rate = signals.get("interview_completion_rate", 0.5)
    interview_score = min(1.0, interview_rate)
    
    # ── Profile Completeness ──
    completeness = signals.get("profile_completeness_score", 50) / 100.0
    
    # ── GitHub Activity ──
    github = signals.get("github_activity_score", -1)
    github_score = max(0, github) / 100.0 if github >= 0 else 0.3  # -1 = no github
    
    # ── Willing to Relocate ──
    relocate = 0.8 if signals.get("willing_to_relocate", False) else 0.4
    
    # ── Verified Contact ──
    verified = 0
    if signals.get("verified_email", False):
        verified += 0.4
    if signals.get("verified_phone", False):
        verified += 0.3
    if signals.get("linkedin_connected", False):
        verified += 0.3
    
    # Combine behavioral sub-scores
    behavioral_score = (
        0.20 * notice_score
        + 0.18 * activity_score
        + 0.15 * response_score
        + 0.12 * open_to_work
        + 0.10 * response_time_score
        + 0.08 * interview_score
        + 0.07 * completeness
        + 0.05 * github_score
        + 0.03 * relocate
        + 0.02 * verified
    )
    
    return {
        "behavioral_score": min(1.0, behavioral_score),
        "notice_score": notice_score,
        "activity_score": activity_score,
        "response_score": response_score,
        "open_to_work": open_to_work,
        "github_score": github_score,
        "notice_days": notice_days,
    }


# ──────────────────────────────────────────────────────────────────────
#  DIMENSION 4: TRUST GRADE SCORE
#  (Uses output from Guard Gate — this is just a pass-through)
# ──────────────────────────────────────────────────────────────────────

def score_trust(guard_gate_result: dict) -> dict:
    """
    Convert Guard Gate trust output into a rankable score.
    This dimension ensures honeypots and suspicious profiles
    are pushed to the bottom even if they score well on skills.
    """
    return {
        "trust_rank_score": guard_gate_result["trust_score"],
        "trust_grade": guard_gate_result["trust_grade"],
    }
