"""
integrations.py — External Integrations Service Layer for Project Trinetra (त्रिनेत्र)
🔱 Level 4 Integration Engine — Graceful Fallback & Active Data Flows

Features:
  1. Slack Webhook Alerts: Post candidate forensic reports and notifications.
  2. Resend Email Invitation: Send styled interview invitations to candidates.
  3. GitHub Inspector: Fetch live profile and repo stats via GitHub REST API.
  4. SQLite Run Comparison: Quantify ranking movements against previous pipeline runs.
"""

import json
import urllib.request
import urllib.error
import sqlite3
import os
from typing import Optional, Any

# Default SQLite Database Path
DEFAULT_DB_PATH = os.path.join("data", "trinetra.db")


# ──────────────────────────────────────────────────────────────────────
#  1. SLACK WEBHOOK ALERT INTEGRATION
# ──────────────────────────────────────────────────────────────────────

def send_slack_alert(
    webhook_url: Optional[str],
    candidate_id: str,
    name: str,
    rank: int,
    score: float,
    trust_grade: str,
    reasoning: str,
) -> tuple[bool, str, dict]:
    """
    Sends a beautifully structured Slack Block Kit message to the hiring team channel.
    If webhook_url is empty/None, runs in simulated mode.
    
    Returns (success, message, payload_sent).
    """
    # Build Block Kit payload
    color = "#10B981" if trust_grade in ("A", "B") else "#F59E0B" if trust_grade == "C" else "#EF4444"
    emoji = "🟢" if trust_grade in ("A", "B") else "🟡" if trust_grade == "C" else "🔴"
    
    payload = {
        "text": f"🔱 Trinetra Alert: New Candidate Shortlisted",
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🔱 Trinetra Talent Forensics Alert",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Candidate:* {name} (`{candidate_id}`)"},
                            {"type": "mrkdwn", "text": f"*Trust Grade:* {emoji} *Grade {trust_grade}*"},
                            {"type": "mrkdwn", "text": f"*Shortlist Rank:* `#{rank}`"},
                            {"type": "mrkdwn", "text": f"*RRF score:* `{score:.6f}`"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Forensic Reasoning:*\n>_{reasoning}_"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "💼 Project Trinetra | Active Recruitment Flow"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    if not webhook_url:
        return (
            True,
            "SUCCESS (SIMULATED): Integration is in Simulated Mode. Set a Slack Webhook URL in Sidebar Settings to send real messages.",
            payload
        )
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        # Add User-Agent header
        req.add_header("User-Agent", "Trinetra-Talent-Forensics-Engine")
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            if res_body.strip().lower() == "ok" or response.status in (200, 201):
                return True, "SUCCESS: Alert posted successfully to Slack channel.", payload
            else:
                return False, f"ERROR: Slack API responded with: {res_body}", payload
    except urllib.error.URLError as e:
        return False, f"CONNECTION ERROR: Failed to reach Slack API. Details: {str(e)}", payload
    except Exception as e:
        return False, f"UNEXPECTED ERROR: {str(e)}", payload


# ──────────────────────────────────────────────────────────────────────
#  2. RESEND EMAIL INTEGRATION
# ──────────────────────────────────────────────────────────────────────

def send_candidate_email(
    api_key: Optional[str],
    candidate_id: str,
    candidate_name: str,
    candidate_email: str,
    subject: str,
    email_body_html: str,
) -> tuple[bool, str, dict]:
    """
    Sends a structured HTML email via Resend's API.
    If api_key is empty/None, runs in simulated mode.
    
    Returns (success, message, payload_sent).
    """
    # Standard email template wrap
    wrapped_html = f"""
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; border: 1px solid #EAEAEA; border-radius: 8px; background-color: #FAFAFA;">
        <div style="text-align: center; border-bottom: 2px solid #00E5CC; padding-bottom: 15px; margin-bottom: 25px;">
            <h1 style="color: #0F172A; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">PROJECT TRINETRA</h1>
            <p style="color: #8F9CAE; margin: 5px 0 0 0; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Founding Team Recruitment</p>
        </div>
        
        <div style="color: #334155; font-size: 16px; line-height: 1.6; margin-bottom: 25px;">
            {email_body_html}
        </div>
        
        <div style="border-top: 1px solid #EAEAEA; padding-top: 20px; font-size: 12px; color: #94A3B8; text-align: center;">
            <p style="margin: 0;">This email was sent by the hiring team via the Project Trinetra Recruiting Dashboard.</p>
            <p style="margin: 5px 0 0 0;">Candidate Reference: <strong>{candidate_id}</strong></p>
        </div>
    </div>
    """
    
    payload = {
        "from": "Redrob Hiring Team <recruitment@resend.dev>",
        "to": [candidate_email],
        "subject": subject,
        "html": wrapped_html
    }
    
    if not api_key:
        return (
            True,
            "SUCCESS (SIMULATED): Interview invitation email simulated. Set a Resend API Key in Sidebar Settings to send real emails.",
            payload
        )
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if "id" in res_data:
                return True, f"SUCCESS: Email sent successfully. Resend ID: {res_data['id']}", payload
            else:
                return False, f"ERROR: Resend API returned unexpected response: {res_data}", payload
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            err_json = json.loads(err_body)
            err_msg = err_json.get("message", err_body)
        except Exception:
            err_msg = str(e)
        return False, f"API ERROR: Resend API returned status {e.code}. Details: {err_msg}", payload
    except Exception as e:
        return False, f"UNEXPECTED ERROR: {str(e)}", payload


# ──────────────────────────────────────────────────────────────────────
#  3. GITHUB PROFILE INSPECTOR
# ──────────────────────────────────────────────────────────────────────

def fetch_github_profile(
    username: str,
    token: Optional[str] = None
) -> dict[str, Any]:
    """
    Fetches real-time profile data and repositories for a candidate's GitHub username.
    Falls back deterministically to mock data if rate-limited or offline.
    """
    cleaned_username = username.strip().replace(" ", "")
    headers = {"User-Agent": "Trinetra-Talent-Forensics-Engine"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    try:
        # 1. Fetch User Profile
        user_url = f"https://api.github.com/users/{cleaned_username}"
        req = urllib.request.Request(user_url, headers=headers)
        with urllib.request.urlopen(req, timeout=4) as response:
            profile_data = json.loads(response.read().decode("utf-8"))
            
        # 2. Fetch User Repos
        repos_url = f"https://api.github.com/users/{cleaned_username}/repos?per_page=10&sort=updated"
        req_repos = urllib.request.Request(repos_url, headers=headers)
        with urllib.request.urlopen(req_repos, timeout=4) as response_repos:
            repos_data = json.loads(response_repos.read().decode("utf-8"))
            
        # Calculate summaries
        stars = sum(repo.get("stargazers_count", 0) for repo in repos_data)
        forks = sum(repo.get("forks_count", 0) for repo in repos_data)
        languages = {}
        for r in repos_data:
            lang = r.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        top_languages = sorted(languages.items(), key=lambda x: -x[1])
        
        return {
            "source": "live_github_api",
            "login": profile_data.get("login", cleaned_username),
            "name": profile_data.get("name", cleaned_username),
            "avatar_url": profile_data.get("avatar_url", ""),
            "bio": profile_data.get("bio", ""),
            "public_repos": profile_data.get("public_repos", 0),
            "followers": profile_data.get("followers", 0),
            "following": profile_data.get("following", 0),
            "stars": stars,
            "forks": forks,
            "top_languages": [lang for lang, _ in top_languages[:3]],
            "recent_repos": [
                {
                    "name": repo.get("name", ""),
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language", ""),
                    "url": repo.get("html_url", "")
                }
                for repo in repos_data[:5]
            ]
        }
        
    except Exception as e:
        # Fallback to high-fidelity mock details derived from the username seed
        seed_num = sum(ord(c) for c in cleaned_username)
        # Create different mock language allocations based on seed
        langs = ["Python", "C++", "TypeScript", "Rust", "Go", "Java"]
        primary_lang = langs[seed_num % len(langs)]
        secondary_lang = langs[(seed_num + 2) % len(langs)]
        
        repo_count = 12 + (seed_num % 25)
        followers = 8 + (seed_num % 120)
        stars = (seed_num % 45) + (5 if seed_num % 3 == 0 else 0)
        
        return {
            "source": "simulated_fallback",
            "login": cleaned_username,
            "name": username.title(),
            "avatar_url": f"https://api.dicebear.com/7.x/identicon/svg?seed={cleaned_username}",
            "bio": f"ML Engineer & Backend Architect. Building scalable retrieval pipelines & vector index infrastructure. ({str(e)})",
            "public_repos": repo_count,
            "followers": followers,
            "following": 5 + (seed_num % 30),
            "stars": stars,
            "forks": int(stars * 0.4),
            "top_languages": [primary_lang, secondary_lang, "SQL"],
            "recent_repos": [
                {
                    "name": "vector-search-accelerator",
                    "description": "Fast vector index construction with custom cluster-based quantization.",
                    "stars": int(stars * 0.5),
                    "language": primary_lang,
                    "url": f"https://github.com/{cleaned_username}/vector-search-accelerator"
                },
                {
                    "name": "retrieval-evaluation-harness",
                    "description": "Deterministic scoring harness for computing MAP, MRR, and NDCG values.",
                    "stars": int(stars * 0.3),
                    "language": secondary_lang,
                    "url": f"https://github.com/{cleaned_username}/retrieval-evaluation-harness"
                },
                {
                    "name": "rag-routing-service",
                    "description": "LLM intent classifier for dynamic routing across context indexes.",
                    "stars": int(stars * 0.2),
                    "language": "Python",
                    "url": f"https://github.com/{cleaned_username}/rag-routing-service"
                }
            ]
        }


# ──────────────────────────────────────────────────────────────────────
#  4. SQLITE RUN COMPARISON ENGINE
# ──────────────────────────────────────────────────────────────────────

def compare_candidate_ranks(
    candidate_id: str,
    current_rank: int,
    current_score: float,
    db_path: str = DEFAULT_DB_PATH
) -> dict[str, Any]:
    """
    Queries the SQLite relational database to identify the candidate's rank & score
    in the PREVIOUS run, computing rank delta movements.
    """
    if not os.path.exists(db_path):
        return {"status": "no_db", "message": "Database archive not found."}
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Fetch the second most recent run ID (previous run)
        cursor.execute(
            """
            SELECT run_id, timestamp, dataset_name 
            FROM audit_log 
            ORDER BY timestamp DESC 
            LIMIT 1 OFFSET 1;
            """
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {
                "status": "no_previous_run",
                "message": "Only one run exists in the SQLite database. Run comparison requires at least 2 runs."
            }
            
        prev_run_id, prev_timestamp, prev_dataset = row
        
        # 2. Query candidates rankings in the previous run
        cursor.execute(
            """
            SELECT rank_position, rrf_score 
            FROM rankings 
            WHERE candidate_id = ? AND run_id = ?;
            """,
            (candidate_id, prev_run_id)
        )
        rank_row = cursor.fetchone()
        
        conn.close()
        
        if not rank_row:
            return {
                "status": "not_in_previous",
                "prev_run_timestamp": prev_timestamp,
                "prev_dataset": prev_dataset,
                "message": f"Candidate was not present in the Top 100 of the previous run."
            }
            
        prev_rank, prev_score = rank_row
        rank_delta = prev_rank - current_rank  # positive = climbed, negative = fell
        score_delta = current_score - prev_score
        
        if rank_delta > 0:
            status_text = f"▲ Climbed {rank_delta} position(s)"
        elif rank_delta < 0:
            status_text = f"▼ Fell {abs(rank_delta)} position(s)"
        else:
            status_text = "■ Position unchanged"
            
        return {
            "status": "success",
            "prev_run_id": prev_run_id,
            "prev_run_timestamp": prev_timestamp,
            "prev_dataset": prev_dataset,
            "prev_rank": prev_rank,
            "prev_score": prev_score,
            "rank_delta": rank_delta,
            "score_delta": score_delta,
            "status_text": status_text,
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Database query error: {str(e)}"}
