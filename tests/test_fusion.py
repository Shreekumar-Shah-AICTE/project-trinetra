"""
test_fusion.py — Tests for Eye 3: Reciprocal Rank Fusion
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fusion import reciprocal_rank_fusion, build_dimension_ranks


def test_rrf_basic():
    """Candidate ranked #1 in all dimensions should be #1 overall."""
    ranks = {
        "A": {"skill": 1, "career": 1, "behavioral": 1, "trust": 1, "semantic": 1},
        "B": {"skill": 2, "career": 2, "behavioral": 2, "trust": 2, "semantic": 2},
        "C": {"skill": 3, "career": 3, "behavioral": 3, "trust": 3, "semantic": 3},
    }
    result = reciprocal_rank_fusion(ranks, k=60)
    assert result[0][0] == "A"
    assert result[1][0] == "B"
    assert result[2][0] == "C"


def test_rrf_cross_dimension_fusion():
    """Candidate good across ALL dimensions beats specialist in one."""
    ranks = {
        "Specialist": {"skill": 1, "career": 50, "behavioral": 50, "trust": 50, "semantic": 50},
        "Balanced": {"skill": 10, "career": 10, "behavioral": 10, "trust": 10, "semantic": 10},
    }
    result = reciprocal_rank_fusion(ranks, k=60)
    # Balanced should win because RRF rewards consistency
    assert result[0][0] == "Balanced"


def test_rrf_scores_are_positive():
    """All RRF scores should be positive."""
    ranks = {
        "A": {"skill": 100, "career": 200, "behavioral": 300, "trust": 400, "semantic": 500},
    }
    result = reciprocal_rank_fusion(ranks, k=60)
    assert result[0][1] > 0


def test_rrf_deterministic_tiebreak():
    """Identical ranks should be broken by candidate_id (alphabetical)."""
    ranks = {
        "B_candidate": {"skill": 1, "career": 1, "behavioral": 1, "trust": 1, "semantic": 1},
        "A_candidate": {"skill": 1, "career": 1, "behavioral": 1, "trust": 1, "semantic": 1},
    }
    result = reciprocal_rank_fusion(ranks, k=60)
    assert result[0][0] == "A_candidate"  # Alphabetically first


def test_build_dimension_ranks():
    """Dimension ranks should be correctly assigned based on scores."""
    scored = [
        {"candidate_id": "A", "skill_relevance_score": 0.9, "career_score": 0.5,
         "behavioral_score": 0.7, "trust_rank_score": 1.0, "semantic_score": 0.8},
        {"candidate_id": "B", "skill_relevance_score": 0.7, "career_score": 0.8,
         "behavioral_score": 0.9, "trust_rank_score": 0.5, "semantic_score": 0.6},
    ]
    ranks = build_dimension_ranks(scored)
    assert ranks["A"]["skill"] == 1  # A has higher skill score
    assert ranks["B"]["career"] == 1  # B has higher career score
    assert ranks["B"]["behavioral"] == 1  # B has higher behavioral score
    assert ranks["A"]["trust"] == 1  # A has higher trust score
