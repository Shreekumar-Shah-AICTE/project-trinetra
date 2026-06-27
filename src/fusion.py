"""
fusion.py — Eye 3: Reciprocal Rank Fusion (RRF) for Project Trinetra (त्रिनेत्र)

The Wisdom Eye — fuses 4 independent rank lists into a single ranking
using RRF. This eliminates the need for manual weight tuning, which is
the fundamental weakness of every competitor's approach.

Formula: RRF_score(d) = Σ 1 / (k + rank_i(d))

Where:
- k = smoothing constant (default 60, standard in IR literature)
- rank_i(d) = rank of document d in the i-th rank list
"""

from typing import Optional


def reciprocal_rank_fusion(
    candidate_ranks: dict[str, dict[str, int]],
    k: int = 60,
    dimension_weights: Optional[dict[str, float]] = None,
) -> list[tuple[str, float]]:
    """
    Perform Reciprocal Rank Fusion across multiple rank lists.
    
    Args:
        candidate_ranks: {candidate_id: {dimension_name: rank_position}}
            e.g., {"CAND_001": {"skill": 1, "career": 5, "behavioral": 3, "trust": 2}}
        k: Smoothing constant (default 60 per IR literature)
        dimension_weights: Optional weights per dimension. If None, all equal.
            These are MILD preferences, not the aggressive weights competitors use.
            Default: skill=1.0, career=1.0, behavioral=0.8, trust=1.2
    
    Returns:
        Sorted list of (candidate_id, rrf_score) in descending score order.
    """
    if dimension_weights is None:
        dimension_weights = {
            "skill": 1.0,
            "career": 1.6,
            "behavioral": 1.0,
            "trust": 0.8,
            "semantic": 0.8,
        }
    
    rrf_scores: dict[str, float] = {}
    
    for cid, ranks in candidate_ranks.items():
        score = 0.0
        for dim_name, rank in ranks.items():
            weight = dimension_weights.get(dim_name, 1.0)
            score += weight * (1.0 / (k + rank))
        rrf_scores[cid] = score
    
    # Sort by RRF score (descending), break ties by candidate_id (ascending)
    sorted_candidates = sorted(
        rrf_scores.items(),
        key=lambda x: (-x[1], x[0])
    )
    
    return sorted_candidates


def build_dimension_ranks(
    scored_candidates: list[dict],
) -> dict[str, dict[str, int]]:
    """
    Convert raw scores into per-dimension rank positions.
    
    Args:
        scored_candidates: List of dicts, each containing:
            - candidate_id
            - skill_relevance_score
            - career_score
            - behavioral_score
            - trust_rank_score
    
    Returns:
        {candidate_id: {dimension: rank}} ready for RRF fusion.
    """
    dimensions = {
        "skill": "skill_relevance_score",
        "career": "career_score",
        "behavioral": "behavioral_score",
        "trust": "trust_rank_score",
        "semantic": "semantic_score",
    }
    
    candidate_ranks: dict[str, dict[str, int]] = {}
    
    for dim_name, score_key in dimensions.items():
        # Sort candidates by this dimension's score (descending), tie-break by ID
        sorted_by_dim = sorted(
            scored_candidates,
            key=lambda c: (-c.get(score_key, 0), c["candidate_id"])
        )
        
        # Assign ranks (1-indexed)
        for rank, candidate in enumerate(sorted_by_dim, 1):
            cid = candidate["candidate_id"]
            if cid not in candidate_ranks:
                candidate_ranks[cid] = {}
            candidate_ranks[cid][dim_name] = rank
    
    return candidate_ranks
