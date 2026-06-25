"""
test_guard_gate.py — Tests for Eye 1: Trust Verification Layer
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.guard_gate import (
    check_chronological_integrity,
    check_company_authenticity,
    check_skill_corroboration,
    check_keyword_stuffer,
    check_empty_expertise,
    check_education_experience,
    run_guard_gate,
)


# ──────────────────────────────────────────────────────────────────────
#  CHRONOLOGICAL INTEGRITY TESTS
# ──────────────────────────────────────────────────────────────────────

def test_clean_candidate_passes():
    """A legitimate candidate with consistent dates should have no violations."""
    candidate = {
        "profile": {"years_of_experience": 6.0, "headline": "ML Engineer"},
        "career_history": [
            {
                "company": "Google",
                "title": "ML Engineer",
                "start_date": "2020-01-15",
                "end_date": None,
                "duration_months": 77,
                "is_current": True,
                "description": "Built ranking systems",
            }
        ],
        "education": [{"institution": "IIT Bombay", "start_year": 2014, "end_year": 2018}],
        "skills": [],
        "redrob_signals": {},
    }
    violations = check_chronological_integrity(candidate)
    assert len(violations) == 0, f"Expected 0 violations, got: {violations}"


def test_end_before_start_detected():
    """Job with end_date before start_date should be caught."""
    candidate = {
        "profile": {"years_of_experience": 5},
        "career_history": [
            {
                "company": "TestCo",
                "title": "Engineer",
                "start_date": "2023-06-01",
                "end_date": "2021-01-01",
                "duration_months": 30,
                "is_current": False,
                "description": "",
            }
        ],
        "education": [],
        "skills": [],
        "redrob_signals": {},
    }
    violations = check_chronological_integrity(candidate)
    assert len(violations) >= 1
    assert "before start_date" in violations[0]


def test_inflated_duration_detected():
    """Claimed duration vastly exceeding calendar span should be caught."""
    candidate = {
        "profile": {"years_of_experience": 8},
        "career_history": [
            {
                "company": "TestCo",
                "title": "Engineer",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
                "duration_months": 96,  # Claims 8 years but dates span 1 year
                "is_current": False,
                "description": "",
            }
        ],
        "education": [],
        "skills": [],
        "redrob_signals": {},
    }
    violations = check_chronological_integrity(candidate)
    assert len(violations) >= 1


# ──────────────────────────────────────────────────────────────────────
#  COMPANY AUTHENTICITY TESTS
# ──────────────────────────────────────────────────────────────────────

def test_fictional_company_detected():
    """Dunder Mifflin should be flagged as fictional."""
    candidate = {
        "profile": {"current_company": "Dunder Mifflin"},
        "career_history": [
            {"company": "Dunder Mifflin", "title": "Engineer"},
            {"company": "Google", "title": "Engineer"},
        ],
    }
    result = check_company_authenticity(candidate)
    assert result["has_fictional"] is True
    assert "Dunder Mifflin" in result["fictional_companies"]


def test_product_company_recognized():
    """Known product companies should be identified."""
    candidate = {
        "profile": {"current_company": "Flipkart"},
        "career_history": [
            {"company": "Flipkart", "title": "Engineer", "duration_months": 36},
        ],
    }
    result = check_company_authenticity(candidate)
    assert result["has_product"] is True


def test_services_only_detected():
    """All-TCS career should be flagged as services-only."""
    candidate = {
        "profile": {"current_company": "TCS"},
        "career_history": [
            {"company": "tcs", "title": "Engineer", "duration_months": 60},
        ],
    }
    result = check_company_authenticity(candidate)
    assert result["services_only"] is True


# ──────────────────────────────────────────────────────────────────────
#  KEYWORD STUFFER TESTS
# ──────────────────────────────────────────────────────────────────────

def test_stuffer_detected():
    """Marketing Manager with many AI skills and no AI career = stuffer."""
    candidate = {
        "profile": {"headline": "Marketing Manager | Brand Strategy"},
        "skills": [
            {"name": "machine learning"}, {"name": "deep learning"},
            {"name": "nlp"}, {"name": "pytorch"}, {"name": "tensorflow"},
            {"name": "transformers"}, {"name": "bert"}, {"name": "gpt"},
            {"name": "natural language processing"}, {"name": "neural network"},
            {"name": "recommendation system"}, {"name": "search engine"},
        ],
        "career_history": [
            {"title": "Marketing Manager", "description": "Led brand campaigns and PR"},
        ],
    }
    result = check_keyword_stuffer(candidate)
    assert result["is_stuffer"] is True


def test_legit_ai_engineer_not_stuffer():
    """AI Engineer with AI skills and AI career = NOT a stuffer."""
    candidate = {
        "profile": {"headline": "Senior ML Engineer | NLP & Search"},
        "skills": [
            {"name": "machine learning"}, {"name": "deep learning"},
            {"name": "nlp"}, {"name": "pytorch"},
        ],
        "career_history": [
            {"title": "ML Engineer", "description": "Built NLP ranking pipeline for search"},
        ],
    }
    result = check_keyword_stuffer(candidate)
    assert result["is_stuffer"] is False


# ──────────────────────────────────────────────────────────────────────
#  MASTER GUARD GATE TESTS
# ──────────────────────────────────────────────────────────────────────

def test_honeypot_gets_grade_f():
    """A candidate with fictional company + bad dates = hard honeypot, grade F."""
    candidate = {
        "candidate_id": "CAND_TEST001",
        "profile": {
            "years_of_experience": 12,
            "headline": "Software Engineer",
            "current_title": "Engineer",
            "current_company": "Hooli",
        },
        "career_history": [
            {
                "company": "Hooli",
                "title": "Engineer",
                "start_date": "2024-01-01",
                "end_date": "2023-01-01",  # Impossible
                "duration_months": 60,
                "is_current": False,
                "description": "Worked on AI stuff",
            },
        ],
        "education": [{"institution": "MIT", "start_year": 2018, "end_year": 2022}],
        "skills": [],
        "redrob_signals": {},
    }
    result = run_guard_gate(candidate)
    assert result["is_hard_honeypot"] is True
    assert result["trust_grade"] == "F"
    assert result["trust_score"] <= 0.15


def test_strong_candidate_gets_grade_a():
    """A legitimate strong candidate should get Trust Grade A."""
    candidate = {
        "candidate_id": "CAND_TEST002",
        "profile": {
            "years_of_experience": 7,
            "headline": "Senior ML Engineer | Retrieval & Ranking",
            "current_title": "Senior ML Engineer",
            "current_company": "Flipkart",
        },
        "career_history": [
            {
                "company": "Flipkart",
                "title": "Senior ML Engineer",
                "start_date": "2021-01-01",
                "end_date": None,
                "duration_months": 65,
                "is_current": True,
                "description": "Built search ranking pipeline with embeddings and FAISS",
            },
            {
                "company": "Amazon",
                "title": "ML Engineer",
                "start_date": "2019-01-01",
                "end_date": "2020-12-31",
                "duration_months": 24,
                "is_current": False,
                "description": "Recommendation engine with hybrid search",
            },
        ],
        "education": [{"institution": "IIT Delhi", "start_year": 2013, "end_year": 2017}],
        "skills": [
            {"name": "pytorch", "proficiency": "expert", "endorsements": 15, "duration_months": 48},
            {"name": "faiss", "proficiency": "advanced", "endorsements": 8, "duration_months": 36},
            {"name": "embeddings", "proficiency": "expert", "endorsements": 12, "duration_months": 40},
        ],
        "redrob_signals": {},
    }
    result = run_guard_gate(candidate)
    assert result["is_hard_honeypot"] is False
    assert result["trust_grade"] == "A"
    assert result["trust_score"] >= 0.85
