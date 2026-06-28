"""
gold_labeler.py — Independent Proxy Gold Label Generator for Project Trinetra (त्रिनेत्र)

CRITICAL DESIGN PRINCIPLE: This labeler is DELIBERATELY independent of our
ranking engine. It uses DIFFERENT signals, DIFFERENT weights, and DIFFERENT
logic. If we used the same scoring as our ranker, the evaluation would be
circular (measuring the ranker against itself).

Relevance tiers (0-4), modeled on how a human recruiter reads the JD:
  4 = Textbook fit — Senior AI/ML engineer, 5-9 yrs, built retrieval/ranking/
      search systems in production at product companies, active on platform
  3 = Strong fit — Relevant AI/ML title with some systems depth, minor gaps
      (experience slightly outside band, or missing one dimension)
  2 = Adjacent fit — Non-AI title but career clearly describes building
      retrieval/ranking/recommendation systems (these are "plain-language gems")
  1 = Weak fit — Some AI/ML background but unclear depth or wrong sub-field
  0 = Irrelevant — Wrong domain entirely, or honeypot

This generates labels for ALL candidates, then eval/metrics.py scores our
submission against these labels.

Usage:
    python eval/gold_labeler.py --candidates data/candidates.jsonl --out eval/gold_auto.csv
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


# ──────────────────────────────────────────────────────────────────────
#  LABELER-SPECIFIC CONSTANTS
#  These are intentionally DIFFERENT from jd.py / rankers.py
# ──────────────────────────────────────────────────────────────────────

# Senior AI/ML titles that are direct JD matches
SENIOR_AI_TITLES = (
    "ai engineer", "machine learning engineer", "ml engineer",
    "applied scientist", "search engineer", "ranking engineer",
    "recommendation engineer", "nlp engineer", "applied ml",
    "staff machine learning", "senior machine learning",
    "senior ai", "senior nlp", "research engineer",
    "data scientist",  # can be relevant if career shows systems
)

# Adjacent titles — could be gems if career text shows real systems work
ADJACENT_TITLES = (
    "software engineer", "backend engineer", "data engineer",
    "full stack developer", "platform engineer", "developer",
    "senior software engineer", "staff software engineer",
)

# Definitively wrong-domain titles — JD explicitly excludes these
WRONG_DOMAIN_TITLES = (
    "hr manager", "marketing manager", "sales executive", "content writer",
    "graphic designer", "accountant", "financial analyst", "operations manager",
    "mechanical engineer", "civil engineer", "electrical engineer",
    "business analyst", "project manager", "product manager",
    "customer support", "customer success", "recruiter",
    "teacher", "professor", "lawyer", "doctor", "nurse",
)

# Verbs that indicate BUILDING systems (not just using tools)
BUILD_VERBS = (
    "built", "build", "building", "shipped", "ship", "shipping",
    "deployed", "deploying", "designed", "designing",
    "implemented", "implementing", "developed", "developing",
    "owned", "led", "launched", "launching", "scaled", "scaling",
    "architected", "created", "engineered",
)

# Systems that the JD specifically wants experience with
RELEVANT_SYSTEMS = (
    "retrieval", "ranking", "rank", "recommendation", "recommender",
    "search relevance", "semantic search", "embedding", "vector search",
    "learning to rank", "faiss", "bm25", "personalization", "matching",
    "information retrieval", "reranking", "re-ranking",
    "search engine", "search system", "search infrastructure",
    "candidate matching", "talent matching",
)


# ──────────────────────────────────────────────────────────────────────
#  HONEYPOT DETECTION (independent of guard_gate.py)
# ──────────────────────────────────────────────────────────────────────

FICTIONAL_COMPANIES = {
    "pied piper", "hooli", "raviga capital", "bachmanity",
    "wayne enterprises", "wayne industries", "stark industries",
    "initech", "intertrode", "dunder mifflin",
    "acme corp", "acme corporation", "acme inc",
    "globex", "globex corporation", "umbrella corporation",
    "cyberdyne systems", "cyberdyne", "tyrell corporation",
    "weyland-yutani", "weyland yutani", "oscorp", "lexcorp",
    "massive dynamic", "prestige worldwide", "virtucon",
    "soylent corp",
}


TECH_RELEASE_YEARS = {
    "qlora": 2023, "llama-2": 2023, "llama 2": 2023, "bge embeddings": 2023, 
    "langchain": 2022, "qdrant": 2021, "peft": 2023, "llama-3": 2024,
    "llama 3": 2024, "mistral": 2023, "gpt-4": 2023, "chatgpt": 2022
}


def _is_honeypot(candidate: dict) -> bool:
    """Independent honeypot detection for the labeler.
    Uses simpler, high-confidence checks — not our full Guard Gate.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    ref_year = 2026


    # Check for impossible skill durations (time-traveling skills)
    for skill in skills:
        skill_name = skill.get("name", "").lower()
        claimed_months = skill.get("duration_months", 0)
        
        for tech, release_year in TECH_RELEASE_YEARS.items():
            if tech in skill_name:
                max_possible_months = (ref_year - release_year + 1) * 12
                if claimed_months > max_possible_months:
                    return True

    # Time-travel checking
    for job in career:
        end_date = job.get("end_date")
        if not end_date and job.get("is_current"):
            end_year = 2026
        elif end_date:
            try:
                end_year = int(end_date.split("-")[0])
            except:
                continue
        else:
            continue
            
        desc = (job.get("description") or "").lower()
        title_job = (job.get("title") or "").lower()
        full_job_text = desc + " " + title_job
        
        for tech, release_year in TECH_RELEASE_YEARS.items():
            if tech in full_job_text and end_year < release_year:
                return True

    chrono_violations = 0

    for job in career:
        start = job.get("start_date", "")
        end = job.get("end_date", "")
        claimed_months = job.get("duration_months", 0)

        if start and end and not job.get("is_current", False):
            try:
                from datetime import datetime
                s = datetime.strptime(str(start).strip()[:10], "%Y-%m-%d")
                e = datetime.strptime(str(end).strip()[:10], "%Y-%m-%d")
                actual_months = (e.year - s.year) * 12 + (e.month - s.month)
                if actual_months < 0:
                    chrono_violations += 1
                elif claimed_months > actual_months * 2 and claimed_months - actual_months > 12:
                    chrono_violations += 1
            except (ValueError, TypeError):
                pass

    # Expert skills with 0 months — classic honeypot pattern
    expert_zero = sum(
        1 for s in skills
        if s.get("proficiency") == "expert"
        and s.get("duration_months", 0) == 0
        and s.get("endorsements", 0) <= 1
    )

    # YOE vs education check
    yoe = profile.get("years_of_experience", 0)
    edu_start_years = [
        e.get("start_year", 9999)
        for e in candidate.get("education", [])
        if e.get("start_year", 0) > 0
    ]
    if edu_start_years:
        min_edu_start = min(edu_start_years)
        max_possible_yoe = ref_year - min_edu_start + 2
        if yoe > max_possible_yoe and yoe > 5:
            chrono_violations += 1

    return (
        chrono_violations >= 2
        or expert_zero >= 8
        or (chrono_violations >= 1 and expert_zero >= 6)
    )


# ──────────────────────────────────────────────────────────────────────
#  LABELING LOGIC
# ──────────────────────────────────────────────────────────────────────

def _get_career_text(candidate: dict) -> str:
    """Combine all career descriptions into searchable text."""
    career = candidate.get("career_history", [])
    parts = []
    for job in career:
        desc = job.get("description", "")
        title = job.get("title", "")
        if desc:
            parts.append(desc)
        if title:
            parts.append(title)
    return " ".join(parts).lower()


def _describes_real_systems(text: str) -> bool:
    """Does the career text show BUILDING relevant systems?"""
    import re
    has_build = any(re.search(r'\b' + re.escape(v) + r'\b', text) for v in BUILD_VERBS)
    
    def match_sys(s):
        if s == "rank":
            pattern = r'\b' + re.escape(s) + r'(?:s|ed|ing|er|ers)?\b'
        else:
            pattern = r'\b' + re.escape(s) + r'(?:s|es)?\b'
        return bool(re.search(pattern, text))
        
    has_sys = any(match_sys(s) for s in RELEVANT_SYSTEMS)
    return has_build and has_sys


def _has_production_depth(text: str) -> bool:
    """Does the career text show production deployment experience?"""
    prod_markers = (
        "production", "deployed to", "million users", "real users",
        "latency", "throughput", "served", "scale", "load balancer",
        "monitoring", "alerting", "ci/cd", "kubernetes", "docker",
    )
    return sum(1 for m in prod_markers if m in text) >= 2


def is_senior_ai_title(title_str: str, headline_str: str) -> bool:
    t = (title_str.lower() + " " + headline_str.lower()).strip()
    if not t:
        return False
    # Core AI titles
    if any(kw in t for kw in ["machine learning", "ml engineer", "applied scientist", "data scientist", "nlp scientist", "applied ml"]):
        return True
    # Search / Ranking / Recommendation / Retrieval titles
    if any(kw in t for kw in ["search", "ranking", "recommend", "retrieval"]):
        if any(role in t for role in ["engineer", "scientist", "developer", "lead", "staff", "senior", "specialist"]):
            return True
    # AI roles
    if "ai " in t or " ai" in t or "artificial intelligence" in t:
        if any(role in t for role in ["engineer", "scientist", "developer", "lead", "staff", "senior", "researcher"]):
            return True
    # Specific senior roles
    if "nlp engineer" in t or "senior nlp" in t or "research engineer" in t:
        return True
    return False


def is_adjacent_title(title_str: str, headline_str: str) -> bool:
    t = (title_str.lower() + " " + headline_str.lower()).strip()
    if not t:
        return False
    adjacent_roles = ["software engineer", "backend engineer", "data engineer", "full stack", "platform engineer", "developer", "systems engineer", "programmer"]
    return any(role in t for role in adjacent_roles)


def is_wrong_title(title_str: str, headline_str: str) -> bool:
    t = (title_str.lower() + " " + headline_str.lower()).strip()
    if not t:
        return False
    wrong_roles = ["hr manager", "marketing", "sales", "content writer", "graphic designer", "accountant", "financial", "operations", "mechanical", "civil", "electrical", "business analyst", "project manager", "product manager", "support", "success", "recruiter", "teacher", "professor", "lawyer", "doctor", "nurse"]
    return any(role in t for role in wrong_roles)


def label_candidate(candidate: dict) -> int:
    """Assign a relevance tier 0-4 to a candidate.
    
    This is the core labeling function. It must be INDEPENDENT of our
    scoring engine to avoid circular evaluation.
    """
    # Check honeypot first
    if _is_honeypot(candidate):
        return 0

    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    career_history = candidate.get("career_history", [])
    
    # 1. GEOGRAPHIC COMPLIANCE CHECK
    location = (profile.get("location") or "").lower()
    willing_to_relocate = signals.get("willing_to_relocate", True)
    
    # Target cities Noida/Pune/Delhi NCR
    target_cities = ["noida", "pune", "delhi", "ncr", "gurgaon", "ghaziabad", "faridabad"]
    is_target_local = any(city in location for city in target_cities)
    
    # Approved Remote Cities (from JD L48)
    approved_remote_cities = ["hyderabad", "mumbai"]
    is_approved_remote = any(city in location for city in approved_remote_cities)
    
    # If not in target city and not in approved remote city, relocation MUST be True
    if not is_target_local and not is_approved_remote and not willing_to_relocate:
        return 0
        
    # Check for international candidates who are unwilling to relocate
    international_markers = ["usa", "united states", "london", "uk", "sf", "california", "germany", "canada"]
    is_international = any(marker in location for marker in international_markers)
    if is_international and not willing_to_relocate:
        return 0

    title = (profile.get("current_title") or "").lower()
    headline = (profile.get("headline") or "").lower()
    yoe = profile.get("years_of_experience", 0)
    career_text = _get_career_text(candidate)

    # 2. CONSULTING-ONLY CAREER CHECK
    career_companies = [j.get("company", "").lower().strip() for j in career_history if j.get("company")]
    if career_companies:
        consulting_firms = ["tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini", "tata consultancy"]
        all_consulting = all(any(c in comp for c in consulting_firms) for comp in career_companies)
        if all_consulting:
            return 0  # Disqualified if entire career is consulting

    # 3. CV/SPEECH/ROBOTICS EXCLUSION CHECK
    wrong_specialization_keywords = ["computer vision", " cv ", "vision engineer", "speech engineer", "audio engineer", "robotics", "perception engineer"]
    is_wrong_spec = any(kw in title or kw in headline for kw in wrong_specialization_keywords)
    skills_list = {s.get("name", "").lower() for s in candidate.get("skills", [])}
    if is_wrong_spec:
        has_nlp_ir = any(kw in career_text.lower() or kw in str(skills_list).lower() for kw in ["nlp", "natural language", "retrieval", "search", "ranking", "bm25", "faiss", "embedding"])
        if not has_nlp_ir:
            return 0  # Disqualified if wrong specialization and no NLP/IR work

    # 4. PURE RESEARCH / ACADEMIC CHECK
    academic_keywords = ["university", "institute", "college", "research lab", "academy"]
    all_academic = True
    for job in career_history:
        company = (job.get("company") or "").lower()
        if company and not any(kw in company for kw in academic_keywords):
            all_academic = False
            break
    has_real_systems = _describes_real_systems(career_text)
    has_production = _has_production_depth(career_text)
    if all_academic and len(career_history) > 0 and not has_production:
        return 0  # Disqualified if pure research and no production ML work

    # 5. LANGCHAIN WRAPPER CHECK
    has_langchain = "langchain" in skills_list or "langchain" in career_text.lower()
    is_senior_ai = is_senior_ai_title(title, headline)
    is_wrapper = False
    if has_langchain and not is_senior_ai and len(skills_list) < 5:
        is_wrapper = True

    # Title classification
    is_adjacent = is_adjacent_title(title, headline)
    is_wrong = is_wrong_title(title, headline)

    # Experience band checks
    in_sweet_spot = 5.0 <= yoe <= 9.0
    in_acceptable = 4.0 <= yoe <= 11.0

    # Determine base tier
    base_tier = 0

    if is_wrong and not has_real_systems:
        base_tier = 0
    elif is_senior_ai and has_real_systems and in_sweet_spot:
        base_tier = 4
    elif is_senior_ai and has_real_systems and in_acceptable:
        base_tier = 3
    elif is_senior_ai and in_sweet_spot:
        base_tier = 3
    elif is_senior_ai and has_real_systems:
        base_tier = 3
    elif is_adjacent and has_real_systems:
        base_tier = 2
    elif is_senior_ai and in_acceptable:
        base_tier = 2
    elif is_senior_ai:
        base_tier = 2
    elif has_real_systems and in_acceptable:
        base_tier = 2
    elif is_adjacent and in_acceptable:
        base_tier = 1
    elif is_adjacent:
        base_tier = 1
    elif is_wrong and has_real_systems:
        base_tier = 1
    else:
        base_tier = 0

    if base_tier == 0:
        return 0

    # ── BEHAVIORAL DEMOTIONS (Crucial for Hackathon alignment) ──
    demotion = 0
    
    # A. Inactive for > 6 months
    last_active = signals.get("last_active_date")
    if last_active:
        try:
            from datetime import datetime
            clean_date = str(last_active)[:10]
            last_date = datetime.strptime(clean_date, "%Y-%m-%d")
            ref_date = datetime(2026, 6, 27)
            months_inactive = (ref_date.year - last_date.year) * 12 + (ref_date.month - last_date.month)
            if months_inactive > 6:
                demotion += 2  # Drop 2 tiers
        except Exception:
            demotion += 2  # Fail-closed demotion for mangled dates

    # B. Poor Recruiter Response Rate (< 10%)
    response_rate = signals.get("recruiter_response_rate")
    if response_rate is not None and response_rate < 0.10:
        demotion += 1

    # C. Not Open To Work + Low Engagement
    if not signals.get("open_to_work_flag", True) and response_rate is not None and response_rate < 0.50:
        demotion += 1

    # D. Job Hopper / Title Chaser check
    job_durations = [j.get("duration_months", 0) for j in career_history if j.get("duration_months")]
    if len(job_durations) >= 3:
        avg_tenure = sum(job_durations) / len(job_durations)
        if avg_tenure < 18.0:
            demotion += 1  # Demote 1 tier for job hopping

    # E. Notice Period Check
    notice_days = signals.get("notice_period_days", 0)
    if notice_days > 30:
        if notice_days > 60:
            demotion += 2  # Demote 2 tiers for notice period > 60 days
        else:
            demotion += 1  # Demote 1 tier for notice period 31-60 days

    # F. Verification Status Check
    verified_email = signals.get("verified_email", True)
    verified_phone = signals.get("verified_phone", True)
    linkedin_connected = signals.get("linkedin_connected", True)
    unverified_count = sum([not verified_email, not verified_phone, not linkedin_connected])
    if unverified_count >= 2:
        demotion += 1  # Demote 1 tier if multiple validation links are missing

    # G. Interview Completion Rate Check
    completion_rate = signals.get("interview_completion_rate")
    if completion_rate is not None and completion_rate < 0.60:
        demotion += 1  # Demote for flaking on interviews

    # H. Offer Acceptance Rate Check
    acceptance_rate = signals.get("offer_acceptance_rate")
    if acceptance_rate == 0.0:
        demotion += 1  # Demote for declining all previous offers

    # I. Architecture Astronaut Check (Hands-off managers / pure architects)
    current_job = career_history[0] if career_history else {}
    current_title = (current_job.get("title") or "").lower()
    current_desc = (current_job.get("description") or "").lower()
    
    is_hands_off_manager = any(kw in current_title for kw in ["director", "vp", "head", "manager"])
    is_pure_architect = "architect" in current_title and "engineer" not in current_title
    
    hands_on_markers = ["wrote", "coded", "developed", "hands-on", "implemented", "python", "git"]
    has_hands_on_proof = any(marker in current_desc for marker in hands_on_markers)
    
    if (is_hands_off_manager or is_pure_architect) and not has_hands_on_proof:
        demotion += 2  # Demote heavily for being a hands-off architect/manager

    final_tier = max(0, base_tier - demotion)
    if is_wrapper:
        return min(1, final_tier)  # Cap wrapper candidate to Tier 1 maximum
    return final_tier


def main():
    ap = argparse.ArgumentParser(
        description="Trinetra Gold Labeler - Independent proxy gold label generator"
    )
    ap.add_argument("--candidates", required=True, help="Path to candidates JSONL/JSON file")
    ap.add_argument("--out", default="eval/gold_auto.csv", help="Output gold labels CSV")
    args = ap.parse_args()

    start = time.time()
    counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    total = 0

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    # Determine file format
    ext = os.path.splitext(args.candidates)[1].lower()

    with open(args.out, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["candidate_id", "tier"])

        if ext == ".json":
            with open(args.candidates, "r", encoding="utf-8") as f:
                data = json.load(f)
                candidates = data if isinstance(data, list) else [data]
            for c in candidates:
                tier = label_candidate(c)
                counts[tier] += 1
                total += 1
                writer.writerow([c["candidate_id"], tier])
        else:
            with open(args.candidates, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        c = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tier = label_candidate(c)
                    counts[tier] += 1
                    total += 1
                    writer.writerow([c["candidate_id"], tier])

    elapsed = time.time() - start

    print()
    print("  === TRINETRA GOLD LABELER ===")
    print(f"  Labeled {total:,} candidates in {elapsed:.1f}s -> {args.out}")
    print()
    for t in (4, 3, 2, 1, 0):
        pct = counts[t] / total * 100 if total > 0 else 0
        bar = "#" * int(pct)
        print(f"  Tier {t}: {counts[t]:6,} ({pct:5.1f}%)  |{bar}")
    print()


if __name__ == "__main__":
    main()
