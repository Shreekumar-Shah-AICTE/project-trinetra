"""
loader.py — Memory-efficient JSONL streaming loader for Project Trinetra (त्रिनेत्र)

Streams candidates line-by-line from JSONL, never loading the full 465MB into memory.
Handles both .jsonl (line-delimited) and .json (array) formats for sandbox compatibility.
"""

import json
import os
import time
from typing import Generator


def load_candidates(path: str, quiet: bool = False) -> list[dict]:
    """
    Load all candidates from a JSONL or JSON file.
    Returns a list of candidate dicts.
    
    Supports:
    - .jsonl: One JSON object per line
    - .json: A JSON array of objects
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Candidate file not found: {path}")
    
    start = time.time()
    candidates = []
    
    ext = os.path.splitext(path)[1].lower()
    
    if ext == ".json":
        # JSON array format (used in sample/sandbox)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                candidates = data
            else:
                candidates = [data]
    else:
        # JSONL format (used in full dataset)
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError:
                    if not quiet:
                        print(f"  ⚠ Skipping malformed line {line_num}")
    
    elapsed = time.time() - start
    if not quiet:
        print(f"  👁 Loaded {len(candidates):,} candidates in {elapsed:.1f}s")
    
    return candidates


def stream_candidates(path: str) -> Generator[dict, None, None]:
    """
    Generator that yields candidates one at a time for memory-constrained environments.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Candidate file not found: {path}")
    
    ext = os.path.splitext(path)[1].lower()
    
    if ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                yield from data
            else:
                yield data
    else:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def extract_text_fields(candidate: dict) -> dict[str, str]:
    """
    Extract all text fields from a candidate for downstream analysis.
    Returns a dict of field_name -> text content, with source awareness.
    
    This is critical for source-weighted evidence: career descriptions
    carry more weight than skill tags.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    education = candidate.get("education", [])
    skills = candidate.get("skills", [])
    
    # Build source-aware text buckets
    texts = {
        "headline": profile.get("headline", ""),
        "summary": profile.get("summary", ""),
        "current_title": profile.get("current_title", ""),
        "current_company": profile.get("current_company", ""),
        "current_industry": profile.get("current_industry", ""),
    }
    
    # Career descriptions — STRONGEST evidence (weight 1.0)
    career_descs = []
    career_titles = []
    career_companies = []
    for job in career:
        desc = job.get("description", "")
        if desc:
            career_descs.append(desc)
        title = job.get("title", "")
        if title:
            career_titles.append(title)
        company = job.get("company", "")
        if company:
            career_companies.append(company)
    
    texts["career_descriptions"] = " ".join(career_descs)
    texts["career_titles"] = " ".join(career_titles)
    texts["career_companies"] = " ".join(career_companies)
    
    # Skills — WEAKEST evidence for ranking (but used for corroboration)
    skill_names = [s.get("name", "") for s in skills]
    texts["skill_names"] = " ".join(skill_names)
    
    # Education
    edu_texts = []
    for edu in education:
        parts = [
            edu.get("degree", ""),
            edu.get("field_of_study", ""),
            edu.get("institution", ""),
        ]
        edu_texts.append(" ".join(p for p in parts if p))
    texts["education"] = " ".join(edu_texts)
    
    # Full combined text (for TF-IDF)
    texts["full_text"] = " ".join([
        texts["headline"],
        texts["summary"],
        texts["career_descriptions"],
        texts["skill_names"],
    ])
    
    return texts
