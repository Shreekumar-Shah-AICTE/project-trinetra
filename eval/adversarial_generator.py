"""
adversarial_generator.py — Adversarial Profile Mutator for Project Trinetra (त्रिनेत्र)

Generates synthetic, cloned candidates with specific chronological, company, 
and skill fraud anomalies to test Guard Gate's safety boundaries.
"""

import copy
import sys

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


def generate_time_travel_adversary(base_candidate: dict) -> dict:
    """Clones a candidate and injects a 2023 technology in pre-2023 employment."""
    adv = copy.deepcopy(base_candidate)
    adv["candidate_id"] = f"{base_candidate['candidate_id']}_adv_timetravel"
    
    if adv.get("career_history"):
        # Make the oldest job end in 2018 but claim experience with Llama-2 (released 2023)
        adv["career_history"][-1]["end_date"] = "2018-05-14"
        adv["career_history"][-1]["is_current"] = False
        adv["career_history"][-1]["description"] = (
            "Successfully trained a custom search reranker utilizing llama-2 embeddings."
        )
    return adv


def generate_date_inflation_adversary(base_candidate: dict) -> dict:
    """Clones a candidate and sets job duration_months vastly higher than calendar span."""
    adv = copy.deepcopy(base_candidate)
    adv["candidate_id"] = f"{base_candidate['candidate_id']}_adv_inflation"
    
    if adv.get("career_history"):
        # Set start/end to span 12 months, but claim 96 months (8 years)
        adv["career_history"][0]["start_date"] = "2024-01-01"
        adv["career_history"][0]["end_date"] = "2025-01-01"
        adv["career_history"][0]["is_current"] = False
        adv["career_history"][0]["duration_months"] = 96
    return adv


def generate_fictional_company_adversary(base_candidate: dict) -> dict:
    """Clones a candidate and adds a fictional company to career history."""
    adv = copy.deepcopy(base_candidate)
    adv["candidate_id"] = f"{base_candidate['candidate_id']}_adv_fictional"
    
    if adv.get("career_history"):
        adv["career_history"][0]["company"] = "Wayne Enterprises"
    return adv


def generate_expert_zero_duration_adversary(base_candidate: dict) -> dict:
    """Clones a candidate and injects many expert skills with 0 duration_months (honeypot)."""
    adv = copy.deepcopy(base_candidate)
    adv["candidate_id"] = f"{base_candidate['candidate_id']}_adv_expertzero"
    
    # Replace skills list with 10 expert skills, all 0 duration
    expert_skills = [
        {"name": "FAISS", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "BM25", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "Sentence-Transformers", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "Vector Search", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "Pinecone", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "Qdrant", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "RAG", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "LLM Fine-tuning", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "PyTorch", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
        {"name": "LangChain", "proficiency": "expert", "duration_months": 0, "endorsements": 0},
    ]
    adv["skills"] = expert_skills
    return adv


def generate_yoe_education_adversary(base_candidate: dict) -> dict:
    """Clones a candidate and sets YOE way higher than college graduation span."""
    adv = copy.deepcopy(base_candidate)
    adv["candidate_id"] = f"{base_candidate['candidate_id']}_adv_edu_yoe"
    
    adv["profile"]["years_of_experience"] = 12.0
    adv["education"] = [
        {
            "institution": "IIT Delhi",
            "degree": "B.Tech in Computer Science",
            "start_year": 2022,
            "end_year": 2026
        }
    ]
    return adv


def generate_suite_of_adversaries(base_candidates: list[dict]) -> list[dict]:
    """Take a list of base clean candidates and generate a suite of 5 adversarial profiles."""
    if not base_candidates:
        return []
    
    adversaries = []
    # Pick first few candidates to mutate
    if len(base_candidates) >= 1:
        adversaries.append(generate_time_travel_adversary(base_candidates[0]))
    if len(base_candidates) >= 2:
        adversaries.append(generate_date_inflation_adversary(base_candidates[1]))
    if len(base_candidates) >= 3:
        adversaries.append(generate_fictional_company_adversary(base_candidates[2]))
    if len(base_candidates) >= 4:
        adversaries.append(generate_expert_zero_duration_adversary(base_candidates[3]))
    if len(base_candidates) >= 5:
        adversaries.append(generate_yoe_education_adversary(base_candidates[4]))
        
    return adversaries
