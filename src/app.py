"""
app.py — Project Trinetra (त्रिनेत्र) — Premium Streamlit Sandbox
🔱 Three Eyes. Zero Fakes.
"""

import sys
import os
import json
import time
from datetime import datetime

# Add root folder to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np

from src.loader import load_candidates, extract_text_fields
from src.guard_gate import run_guard_gate
from src.rankers import (
    score_skill_relevance,
    score_career_trajectory,
    score_behavioral_availability,
    score_trust,
)
from src.fusion import build_dimension_ranks, reciprocal_rank_fusion
from src.reasoning import build_reasoning
from src.semantic import compute_semantic_scores
# Try importing integrations from src, otherwise fallback to docs/post_ranking_dashboard_concept or mock functions
try:
    from src.integrations import (
        send_slack_alert,
        send_candidate_email,
        fetch_github_profile,
        compare_candidate_ranks,
    )
except ImportError:
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "post_ranking_dashboard_concept")))
    try:
        from integrations import (
            send_slack_alert,
            send_candidate_email,
            fetch_github_profile,
            compare_candidate_ranks,
        )
    except ImportError:
        def send_slack_alert(*args, **kwargs): return True, "Slack Alert Simulated", {}
        def send_candidate_email(*args, **kwargs): return True, "Email Invitation Simulated", {}
        def fetch_github_profile(*args, **kwargs): return {"login": "simulated", "public_repos": 0, "followers": 0}
        def compare_candidate_ranks(*args, **kwargs): return {}

# Set Page Config
st.set_page_config(
    page_title="Project Trinetra (त्रिनेत्र) | Talent Forensics Sandbox",
    page_icon="🔱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────
#  CUSTOM CSS STYLE INJECTIONS (VSF Compliance)
# ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
    /* Main Layout Styling */
    .stApp {
        background-color: #08090E;
        color: #C5C6C7;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Header & Branding */
    .banner-container {
        padding: 30px;
        background: linear-gradient(135deg, rgba(8, 9, 14, 0.9) 0%, rgba(20, 22, 34, 0.8) 100%);
        border: 1px solid rgba(0, 229, 204, 0.15);
        border-radius: 16px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 4px 30px rgba(0, 229, 204, 0.03);
    }
    
    .gradient-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00E5CC 0%, #D4AF37 50%, #00E5CC 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }
    
    .tagline {
        font-size: 1.1rem;
        color: #8F9CAE;
        margin-bottom: 0px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-weight: 500;
    }
    
    /* Cards and Glassmorphism */
    .forensic-card {
        background-color: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        backdrop-filter: blur(12px);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .forensic-card:hover {
        border-color: rgba(0, 229, 204, 0.3);
        box-shadow: 0 4px 20px rgba(0, 229, 204, 0.05);
        background-color: rgba(255, 255, 255, 0.03);
    }
    
    /* Trust Grade Badges */
    .badge-A {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.1);
        border-radius: 4px;
        padding: 3px 10px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .badge-B {
        background: rgba(52, 211, 153, 0.15);
        color: #34D399;
        border: 1px solid rgba(52, 211, 153, 0.3);
        border-radius: 4px;
        padding: 3px 10px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .badge-C {
        background: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 4px;
        padding: 3px 10px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .badge-D {
        background: rgba(249, 115, 22, 0.15);
        color: #F97316;
        border: 1px solid rgba(249, 115, 22, 0.3);
        border-radius: 4px;
        padding: 3px 10px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .badge-F {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.4);
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.2);
        border-radius: 4px;
        padding: 3px 10px;
        font-weight: bold;
        font-size: 0.9em;
        animation: pulse-shadow 2.5s infinite;
    }
    @keyframes pulse-shadow {
        0% { box-shadow: 0 0 4px rgba(239, 68, 68, 0.1); }
        50% { box-shadow: 0 0 12px rgba(239, 68, 68, 0.4); }
        100% { box-shadow: 0 0 4px rgba(239, 68, 68, 0.1); }
    }
    
    /* Metric styling */
    .kpi-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin-bottom: 25px;
    }
    .kpi-box {
        flex: 1;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .kpi-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.8rem;
        font-weight: 600;
        color: #00E5CC;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #8F9CAE;
        text-transform: uppercase;
        margin-top: 5px;
    }
    
    /* Timeline styles */
    .timeline-container {
        border-left: 2px solid rgba(255,255,255,0.08);
        margin-left: 15px;
        padding-left: 20px;
        position: relative;
    }
    .timeline-node {
        position: absolute;
        left: -6px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #00e5cc;
        border: 2px solid #08090E;
        top: 6px;
    }
    .timeline-node-fictional {
        background-color: #EF4444;
    }
    .timeline-node-services {
        background-color: #F59E0B;
    }
    .timeline-item {
        margin-bottom: 20px;
        position: relative;
    }
    
    /* Custom tag styles */
    .tag-product {
        background-color: rgba(16, 185, 129, 0.12);
        color: #10B981;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 500;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .tag-services {
        background-color: rgba(245, 158, 11, 0.12);
        color: #F59E0B;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 500;
        border: 1px solid rgba(245, 158, 11, 0.2);
    }
    .tag-fictional {
        background-color: rgba(239, 68, 68, 0.12);
        color: #EF4444;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        font-weight: 500;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }
    
    /* Progress Bars for Dimension Scores */
    .dim-label {
        font-size: 0.85em;
        color: #8F9CAE;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    .progress-bg {
        background-color: rgba(255,255,255,0.05);
        border-radius: 6px;
        height: 8px;
        width: 100%;
        margin-bottom: 12px;
        overflow: hidden;
    }
    .progress-bar-fill {
        background: linear-gradient(90deg, #00E5CC 0%, #D4AF37 100%);
        height: 8px;
        border-radius: 6px;
    }
    
    /* Sidebar elements overrides */
    section[data-testid="stSidebar"] {
        background-color: #0A0B11 !important;
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────
#  SESSION STATE INITIALIZATION
# ──────────────────────────────────────────────────────────────────────
if "candidates" not in st.session_state:
    st.session_state.candidates = None
if "run_stats" not in st.session_state:
    st.session_state.run_stats = None
if "scored_df" not in st.session_state:
    st.session_state.scored_df = None
if "selected_candidate_id" not in st.session_state:
    st.session_state.selected_candidate_id = None

# ──────────────────────────────────────────────────────────────────────
#  SIDEBAR CONTROLS
# ──────────────────────────────────────────────────────────────────────
st.sidebar.markdown(
    "<div style='text-align: center; margin-bottom: 20px;'>"
    "<h2 style='font-family: Space Grotesk; color:#00E5CC; font-size:1.8em; margin-bottom:0;'>🔱 TRINETRA</h2>"
    "<p style='color:#8F9CAE; font-size:0.8em; letter-spacing:0.1em; text-transform:uppercase;'>Control Center</p>"
    "</div>",
    unsafe_allow_html=True,
)

st.sidebar.markdown("### 📥 Candidate Source")
source_option = st.sidebar.radio(
    "Select Source File",
    ("Option 1: Pre-loaded Sample (50 Candidates)", "Option 2: Upload Custom Pool (.json / .jsonl)"),
)

uploaded_file = None
if "Option 2" in source_option:
    uploaded_file = st.sidebar.file_uploader(
        "Upload Candidate Pool File",
        type=["json", "jsonl"],
        help="Upload candidate JSON array or line-delimited JSONL file.",
    )

# Tuning Parameters
st.sidebar.markdown("### ⚙️ Fusion Preferences (RRF)")
k_val = st.sidebar.slider(
    "RRF Smoothing Constant (k)",
    min_value=10,
    max_value=120,
    value=60,
    step=5,
    help="Higher values smooth the distribution, lower values penalize lower ranks aggressively.",
)

st.sidebar.markdown("#### Dimension Weights")
w_trust = st.sidebar.slider("Trust Grade (Eye 1)", 0.0, 2.0, 0.8, 0.1)
w_skill = st.sidebar.slider("Skill Relevance (Eye 2)", 0.0, 2.0, 1.6, 0.1)
w_career = st.sidebar.slider("Career Trajectory", 0.0, 2.0, 0.4, 0.1)
w_behavioral = st.sidebar.slider("Behavioral Signals", 0.0, 2.0, 0.2, 0.1)
w_semantic = st.sidebar.slider("TF-IDF Semantic Fit", 0.0, 2.0, 1.0, 0.1)

dim_weights = {
    "trust": w_trust,
    "skill": w_skill,
    "career": w_career,
    "behavioral": w_behavioral,
    "semantic": w_semantic,
}

# ── Integrations Settings ──
st.sidebar.markdown("### 🔌 Integrations Config")
with st.sidebar.expander("Slack & Resend Settings"):
    slack_webhook = st.text_input("Slack Webhook URL", value="", type="password", help="Incoming webhook URL to send candidate alerts.")
    resend_key = st.text_input("Resend API Key", value="", type="password", help="Resend API key to send live candidate emails.")
    github_token = st.text_input("GitHub Token (Optional)", value="", type="password", help="GitHub personal access token to avoid rate limits.")

# ── Execution Archive (SQLite 5-Table History) ──
try:
    from src.database import get_latest_runs, get_run_results, get_candidate_violations
    latest_runs = get_latest_runs()
    if latest_runs:
        st.sidebar.markdown("### 📂 Execution Archive")
        run_options = ["Active Session"] + [
            f"{run['timestamp'][:16].replace('T', ' ')} - {run['dataset_name']} ({run['total_scanned']} cand)"
            for run in latest_runs
        ]
        selected_run_label = st.sidebar.selectbox("Load Historical Run", run_options, index=0)
        
        if selected_run_label != "Active Session":
            # Load and override session state with database records
            selected_idx = run_options.index(selected_run_label) - 1
            selected_run_id = latest_runs[selected_idx]["run_id"]
            db_results = get_run_results(selected_run_id)
            
            if db_results:
                run_meta = latest_runs[selected_idx]
                trust_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
                reconstructed_rows = []
                
                for row in db_results:
                    tg = row["trust_grade"]
                    trust_counts[tg] = trust_counts.get(tg, 0) + 1
                    cand_viols = get_candidate_violations(row["candidate_id"])
                    
                    reconstructed_rows.append({
                        "candidate_id": row["candidate_id"],
                        "rank": row["rank"],
                        "score": row["score"],
                        "reasoning": row["reasoning"],
                        "name": row["name"],
                        "headline": row["current_title"],
                        "current_company": row["current_company"],
                        "yoe": row["yoe"],
                        "trust_grade": row["trust_grade"],
                        "is_honeypot": row["is_honeypot"] == 1,
                        "skill_score": row["skill_score"] or 0.0,
                        "career_score": row["career_score"] or 0.0,
                        "behavioral_score": row["behavioral_score"] or 0.0,
                        "semantic_score": row["semantic_score"] or 0.0,
                        "violations": cand_viols,
                        "candidate_data": {
                            "candidate_id": row["candidate_id"],
                            "profile": {
                                "anonymized_name": row["name"],
                                "current_title": row["current_title"],
                                "current_company": row["current_company"],
                                "years_of_experience": row["yoe"],
                                "headline": row["current_title"],
                            },
                            "career_history": [],  # Empty placeholder for archived runs
                            "redrob_signals": {
                                "notice_period_days": 30 if row["behavioral_score"] and row["behavioral_score"] > 0.6 else 90,
                                "profile_completeness_score": 85,
                                "recruiter_response_rate": 0.9,
                                "github_activity_score": 75,
                                "last_active_date": "Active",
                                "avg_response_time_hours": 12.0,
                                "verified_email": True,
                                "verified_phone": True,
                                "linkedin_connected": True,
                            }
                        },
                        "dim_ranks": {
                            "skill": 1, "career": 1, "behavioral": 1, "trust": 1, "semantic": 1
                        }
                    })
                
                st.session_state.run_stats = {
                    "total_scanned": run_meta["total_scanned"],
                    "hard_honeypots": run_meta["honeypots_caught"],
                    "disqualified": run_meta["disqualified_count"],
                    "surviving": len(db_results),
                    "trust_grades": trust_counts,
                    "time_taken": run_meta["duration_seconds"],
                }
                st.session_state.scored_df = pd.DataFrame(reconstructed_rows)
                st.sidebar.caption("🔒 Custom controls disabled while viewing archived runs.")
except Exception as e:
    pass

# ──────────────────────────────────────────────────────────────────────
#  MAIN PAGE HEADER
# ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="banner-container">
        <div class="gradient-title">PROJECT TRINETRA (त्रिनेत्र)</div>
        <div class="tagline">Three Eyes. Zero Fakes. Trust-First Talent Forensics Engine</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────
#  LOAD CANDIDATE DATA
# ──────────────────────────────────────────────────────────────────────
data_loaded = False
candidates_list = []

if "Option 1" in source_option:
    sample_path = os.path.join("data", "sample_candidates.json")
    if os.path.exists(sample_path):
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                candidates_list = json.load(f)
            data_loaded = True
            st.info(f"🟢 **Pre-loaded sample ready**: Loaded {len(candidates_list)} candidates from `sample_candidates.json`.")
        except Exception as e:
            st.error(f"Failed to load sample: {str(e)}")
    else:
        st.error("Sample candidates file missing! Make sure project-trinetra/data/sample_candidates.json exists.")
else:
    if uploaded_file is not None:
        try:
            # Determine format
            file_name = uploaded_file.name
            file_content = uploaded_file.read().decode("utf-8")
            
            if file_name.endswith(".json"):
                data = json.loads(file_content)
                if isinstance(data, list):
                    candidates_list = data
                else:
                    candidates_list = [data]
            else:
                # jsonl
                candidates_list = []
                for line in file_content.splitlines():
                    if line.strip():
                        candidates_list.append(json.loads(line))
            
            data_loaded = True
            st.success(f"🟢 **Upload successful**: Loaded {len(candidates_list):,} candidates from {file_name}.")
        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")
    else:
        st.warning("Please upload a candidate file (.json or .jsonl) in the sidebar to run the sandbox.")

# ──────────────────────────────────────────────────────────────────────
#  PIPELINE EXECUTION TRIGGER
# ──────────────────────────────────────────────────────────────────────
if data_loaded:
    st.markdown("### 🔱 Run Forensics Engine")
    
    col_run, col_status = st.columns([1, 3])
    
    with col_run:
        btn_run = st.button("ACTIVATE TRINETRA ENGINE", use_container_width=True, type="primary")
        
    if btn_run or st.session_state.scored_df is not None:
        if btn_run or st.session_state.candidates != candidates_list:
            # We need to run the pipeline
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            t_start = time.time()
            
            # --- Stage 1: Guard Gate ---
            status_text.text("Stage 1/4: Running Guard Gate trust verification...")
            progress_bar.progress(15)
            
            guard_results = {}
            hard_honeypots = 0
            disqualified = 0
            trust_grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            surviving_candidates = []
            
            for i, cand in enumerate(candidates_list):
                cid = cand["candidate_id"]
                result = run_guard_gate(cand)
                guard_results[cid] = result
                
                grade = result["trust_grade"]
                trust_grade_counts[grade] = trust_grade_counts.get(grade, 0) + 1
                
                if result["is_hard_honeypot"]:
                    hard_honeypots += 1
                
                if result["disqualified"]:
                    disqualified += 1
                    continue
                
                surviving_candidates.append(cand)
                
            # --- Stage 2: Scoring ---
            status_text.text("Stage 2/4: Computing multi-dimensional independent scores...")
            progress_bar.progress(50)
            
            scored_candidates = []
            for cand in surviving_candidates:
                cid = cand["candidate_id"]
                text_fields = extract_text_fields(cand)
                
                skill_result = score_skill_relevance(cand, text_fields)
                career_result = score_career_trajectory(cand)
                behavioral_result = score_behavioral_availability(cand)
                trust_result = score_trust(guard_results[cid])
                
                scored_candidates.append({
                    "candidate_id": cid,
                    "candidate": cand,
                    "text_fields": text_fields,
                    "skill_relevance_score": skill_result["skill_relevance_score"],
                    "career_score": career_result["career_score"],
                    "behavioral_score": behavioral_result["behavioral_score"],
                    "trust_rank_score": trust_result["trust_rank_score"],
                    "skill_result": skill_result,
                    "career_result": career_result,
                    "behavioral_result": behavioral_result,
                    "guard_result": guard_results[cid],
                })
            
            # --- Stage 2b: Semantic layer ---
            status_text.text("Stage 2b/4: Running local TF-IDF semantic vectorizer...")
            progress_bar.progress(70)
            
            sem_texts = [sc["text_fields"]["full_text"] for sc in scored_candidates]
            sem_ids = [sc["candidate_id"] for sc in scored_candidates]
            semantic_scores = compute_semantic_scores(sem_texts, sem_ids)
            
            for sc in scored_candidates:
                sc["semantic_score"] = semantic_scores.get(sc["candidate_id"], 0.0)
                
            # --- Stage 3: RRF Fusion ---
            status_text.text("Stage 3/4: Executing Reciprocal Rank Fusion...")
            progress_bar.progress(85)
            
            dimension_ranks = build_dimension_ranks(scored_candidates)
            fused_ranking = reciprocal_rank_fusion(dimension_ranks, k=k_val, dimension_weights=dim_weights)
            
            # --- Stage 4: Reasoning & Output Construction ---
            status_text.text("Stage 4/4: Generating forensic explanation chains...")
            progress_bar.progress(95)
            
            scored_lookup = {sc["candidate_id"]: sc for sc in scored_candidates}
            
            output_rows = []
            honeypots_in_top100 = 0
            
            for rank, (cid, rrf_score) in enumerate(fused_ranking, 1):
                sc = scored_lookup[cid]
                cand = sc["candidate"]
                
                if guard_results[cid]["is_hard_honeypot"]:
                    honeypots_in_top100 += 1
                    
                reasoning = build_reasoning(
                    candidate=cand,
                    guard_result=sc["guard_result"],
                    skill_result=sc["skill_result"],
                    career_result=sc["career_result"],
                    behavioral_result=sc["behavioral_result"],
                    final_rank=rank,
                    dimension_ranks=dimension_ranks.get(cid, {}),
                )
                
                output_rows.append({
                    "candidate_id": cid,
                    "rank": rank,
                    "score": round(rrf_score, 6),
                    "reasoning": reasoning,
                    "name": cand.get("profile", {}).get("anonymized_name", "Anonymized"),
                    "headline": cand.get("profile", {}).get("headline", ""),
                    "current_company": cand.get("profile", {}).get("current_company", ""),
                    "yoe": cand.get("profile", {}).get("years_of_experience", 0.0),
                    "trust_grade": guard_results[cid]["trust_grade"],
                    "trust_score": guard_results[cid]["trust_score"],
                    "is_honeypot": guard_results[cid]["is_hard_honeypot"],
                    "skill_score": sc["skill_relevance_score"],
                    "career_score": sc["career_score"],
                    "behavioral_score": sc["behavioral_score"],
                    "semantic_score": sc["semantic_score"],
                    "violations": guard_results[cid]["violations"],
                    "candidate_data": cand,
                    "dim_ranks": dimension_ranks.get(cid, {}),
                    "skill_result": sc["skill_result"],
                    "career_result": sc["career_result"],
                    "behavioral_result": sc["behavioral_result"],
                })
            
            t_total = time.time() - t_start
            
            progress_bar.progress(100)
            status_text.text(f"Pipeline execution complete in {t_total:.2f} seconds!")
            time.sleep(0.5)
            progress_bar.empty()
            status_text.empty()
            
            # Save to session state
            st.session_state.candidates = candidates_list
            st.session_state.run_stats = {
                "total_scanned": len(candidates_list),
                "hard_honeypots": hard_honeypots,
                "disqualified": disqualified,
                "surviving": len(surviving_candidates),
                "trust_grades": trust_grade_counts,
                "time_taken": t_total,
            }
            st.session_state.scored_df = pd.DataFrame(output_rows)
            
            # Save to local SQLite DB
            try:
                from src.database import save_pipeline_run
                dataset_name = "Uploaded File" if "Option 2" in source_option else "sample_candidates.json"
                save_pipeline_run(
                    candidates=candidates_list,
                    guard_results=guard_results,
                    scored_candidates=scored_candidates,
                    fused_ranking=fused_ranking,
                    output_rows=output_rows,
                    duration=t_total,
                    dataset_name=dataset_name,
                )
            except Exception as e:
                st.error(f"Failed to archive run in SQLite: {str(e)}")
            
        # Display Stats Summary Dashboard
        stats = st.session_state.run_stats
        df = st.session_state.scored_df
        
        # Download Shortlist Button
        csv_data = df[["candidate_id", "rank", "score", "reasoning"]].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Shortlist Submission CSV",
            data=csv_data,
            file_name="submission.csv",
            mime="text/csv",
            use_container_width=True,
        )
        
        # Dashboard KPIs
        st.markdown(
            f"""
            <div class="kpi-container">
                <div class="kpi-box">
                    <div class="kpi-value">{stats['total_scanned']:,}</div>
                    <div class="kpi-label">Profiles Scanned</div>
                </div>
                <div class="kpi-box" style="border-color: rgba(239, 68, 68, 0.25);">
                    <div class="kpi-value" style="color: #EF4444;">{stats['hard_honeypots']}</div>
                    <div class="kpi-label">Honeypots Caught</div>
                </div>
                <div class="kpi-box" style="border-color: rgba(245, 158, 11, 0.25);">
                    <div class="kpi-value" style="color: #F59E0B;">{stats['disqualified']}</div>
                    <div class="kpi-label">Domain Disqualified</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-value">{stats['surviving']:,}</div>
                    <div class="kpi-label">Passing Candidates</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-value" style="color: #D4AF37;">{stats['time_taken']:.2f}s</div>
                    <div class="kpi-label">Execution Time</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Grade Distribution Indicators
        st.markdown("### 📊 Trust Grade Distribution")
        grades = stats["trust_grades"]
        col_gA, col_gB, col_gC, col_gD, col_gF = st.columns(5)
        with col_gA:
            st.metric("Trust Grade A", grades.get("A", 0))
        with col_gB:
            st.metric("Trust Grade B", grades.get("B", 0))
        with col_gC:
            st.metric("Trust Grade C", grades.get("C", 0))
        with col_gD:
            st.metric("Trust Grade D", grades.get("D", 0))
        with col_gF:
            st.metric("Trust Grade F", grades.get("F", 0))
            
        st.write("---")
        
        # Interactive Shortlist Area
        col_list, col_forensic = st.columns([1, 1])
        
        with col_list:
            st.markdown("### 🏆 Candidate Shortlist")
            
            # Filters
            search_query = st.text_input("🔍 Search by candidate ID, name, or headline", "").lower()
            grade_filter = st.multiselect("Filter by Trust Grade", ["A", "B", "C", "D", "F"], default=["A", "B", "C", "D"])
            
            # Apply filters
            filtered_df = df.copy()
            if search_query:
                filtered_df = filtered_df[
                    filtered_df["candidate_id"].str.lower().str.contains(search_query) |
                    filtered_df["name"].str.lower().str.contains(search_query) |
                    filtered_df["headline"].str.lower().str.contains(search_query)
                ]
            if grade_filter:
                filtered_df = filtered_df[filtered_df["trust_grade"].isin(grade_filter)]
                
            st.caption(f"Showing {len(filtered_df)} candidates matching filters.")
            
            # Render Candidates list
            if filtered_df.empty:
                st.info("No candidates match the specified filters.")
            else:
                for idx, row in filtered_df.iterrows():
                    cid = row["candidate_id"]
                    rank = row["rank"]
                    score = row["score"]
                    name = row["name"]
                    headline = row["headline"]
                    grade = row["trust_grade"]
                    
                    # Highlight selected card
                    selected_style = ""
                    if st.session_state.selected_candidate_id == cid:
                        selected_style = "border: 1px solid #00E5CC; box-shadow: 0 0 15px rgba(0, 229, 204, 0.15);"
                        
                    card_html = f"""
                    <div class="forensic-card" style="{selected_style}">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <span style="font-family: Space Grotesk; font-size:1.15em; font-weight:600; color: #FFFFFF;">
                                #{rank} &nbsp;&bull;&nbsp; {name} <span style="font-size:0.75em; color:#8F9CAE;">({cid})</span>
                            </span>
                            <span class="badge-{grade}">{grade}</span>
                        </div>
                        <div style="font-size:0.9em; margin-bottom:10px; color:#A8B2C1;">
                            {headline}
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.8em;">
                            <span style="color: #D4AF37; font-weight:600; font-family: Space Grotesk;">RRF Score: {score:.5f}</span>
                            <span style="color: #8F9CAE;">YOE: {row['yoe']:.1f} yrs</span>
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    if st.button(f"Analyze Case File — {cid}", key=f"btn_{cid}", use_container_width=True):
                        st.session_state.selected_candidate_id = cid
                        st.rerun()

        with col_forensic:
            st.markdown("### 🔬 Talent Forensics Case File")
            
            if st.session_state.selected_candidate_id is None and not df.empty:
                # Pick Rank 1 by default
                st.session_state.selected_candidate_id = df.iloc[0]["candidate_id"]
                
            selected_id = st.session_state.selected_candidate_id
            
            if selected_id is not None:
                # Get candidate row
                cand_row = df[df["candidate_id"] == selected_id].iloc[0]
                cand_data = cand_row["candidate_data"]
                violations = cand_row["violations"]
                grade = cand_row["trust_grade"]
                
                # Render Detailed Forensic Panel
                st.markdown(
                    f"""
                    <div style="background-color: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255,255,255,0.06); border-radius:12px; padding:25px; min-height: 500px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom:12px;">
                            <div>
                                <h3 style="margin:0; font-family:Space Grotesk; color:#FFFFFF; font-size:1.5em;">{cand_row['name']}</h3>
                                <span style="font-size:0.85em; color:#8F9CAE;">ID: {selected_id} &nbsp;|&nbsp; {cand_row['headline']}</span>
                            </div>
                            <span class="badge-{grade}" style="font-size:1.2em; padding:5px 15px;">Grade {grade}</span>
                        </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # 1. Forensic Reasoning
                st.markdown(
                    f"""
                    <div style="background: rgba(0, 229, 204, 0.04); border-left: 3px solid #00E5CC; padding: 12px 18px; border-radius: 4px; margin-bottom: 20px; font-style: italic;">
                        <strong>Detective Notes:</strong> "{cand_row['reasoning']}"
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                # Tabs for deeper sections
                tab_scores, tab_history, tab_signals = st.tabs(["📊 Dimension Ranks", "⏳ Career History", "⚡ Behavioral & Contact"])
                
                with tab_scores:
                    st.markdown("#### Independent Ranking Positions")
                    st.caption("Lower rank is better (representing higher position in that list).")
                    
                    dim_ranks = cand_row["dim_ranks"]
                    total_verified = stats["surviving"]
                    
                    # Convert rank positions to simple visual indicators
                    for dim, rank_pos in dim_ranks.items():
                        # Calculate percentage position
                        pct = (total_verified - rank_pos) / total_verified if total_verified > 1 else 1.0
                        score_val = cand_row.get(f"{dim}_score", 0.0)
                        
                        st.markdown(
                            f"""
                            <div class="dim-label">
                                <span><strong>{dim.capitalize()} Fit</strong> (Rank #{rank_pos} of {total_verified})</span>
                                <span style="color:#00E5CC;">Score: {score_val:.3f}</span>
                            </div>
                            <div class="progress-bg">
                                <div class="progress-bar-fill" style="width: {pct*100}%;"></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        
                with tab_history:
                    st.markdown("#### Stated Career Milestones")
                    
                    # Show Guard Gate report on career
                    if violations:
                        st.markdown("<h5 style='color:#EF4444; margin-bottom:8px;'>⚠️ Integrity Flags</h5>", unsafe_allow_html=True)
                        for viol in violations:
                            st.markdown(f"- <span style='color:#EF4444;'>{viol}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color:#10B981; font-weight:600;'>✓ No chronological or stuffer anomalies detected.</p>", unsafe_allow_html=True)
                    
                    st.write("")
                    
                    career = cand_data.get("career_history", [])
                    if not career:
                        st.write("No career milestones listed.")
                    else:
                        st.markdown("<div class='timeline-container'>", unsafe_allow_html=True)
                        for job in career:
                            company = job.get("company", "Unknown")
                            company_lower = company.lower()
                            title = job.get("title", "Software Engineer")
                            start = job.get("start_date", "Unknown")
                            end = job.get("end_date", "Present")
                            duration = job.get("duration_months", 0)
                            desc = job.get("description", "")
                            
                            # Tag company type
                            node_class = ""
                            tag_html = ""
                            if company_lower in PRODUCT_COMPANIES:
                                node_class = ""
                                tag_html = "<span class='tag-product'>Product Company</span>"
                            elif company_lower in SERVICES_COMPANIES:
                                node_class = "timeline-node-services"
                                tag_html = "<span class='tag-services'>IT Services</span>"
                            elif company_lower in FICTIONAL_COMPANIES:
                                node_class = "timeline-node-fictional"
                                tag_html = "<span class='tag-fictional'>Fictional/Fake</span>"
                            
                            st.markdown(
                                f"""
                                <div class="timeline-item">
                                    <div class="timeline-node {node_class}"></div>
                                    <div style="font-weight:600; font-size:1.05em; color:#FFFFFF;">{title} {tag_html}</div>
                                    <div style="font-size:0.9em; color:#8F9CAE;">at <strong>{company}</strong> &bull; {duration} months ({start} to {end})</div>
                                    <p style="font-size:0.88em; margin-top:6px; color:#A8B2C1; line-height:1.4;">{desc}</p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                with tab_signals:
                    st.markdown("#### Redrob Behavioral Indicators")
                    signals = cand_data.get("redrob_signals", {})
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Notice Period", f"{signals.get('notice_period_days', 90)} days")
                        st.metric("Profile Completeness", f"{signals.get('profile_completeness_score', 50)}%")
                        st.metric("Recruiter Response Rate", f"{signals.get('recruiter_response_rate', 0.0)*100:.0f}%")
                    with c2:
                        st.metric("GitHub Score", "No GitHub" if signals.get('github_activity_score', -1) == -1 else f"{signals.get('github_activity_score', 0)}/100")
                        st.metric("Last Active", signals.get('last_active_date', 'Unknown'))
                        st.metric("Response Time (Hours)", f"{signals.get('avg_response_time_hours', 72):.1f}h")
                        
                    st.write("")
                    st.markdown("#### Contact Verification")
                    vemail = "✅ Verified" if signals.get("verified_email", False) else "❌ Unverified"
                    vphone = "✅ Verified" if signals.get("verified_phone", False) else "❌ Unverified"
                    vlinkedin = "🔗 Connected" if signals.get("linkedin_connected", False) else "❌ Unconnected"
                    
                    st.write(f"- **Email Address**: {vemail}")
                    st.write(f"- **Phone Number**: {vphone}")
                    st.write(f"- **LinkedIn Link**: {vlinkedin}")
                
                # ── ACTION CENTER (INTEGRATIONS) ──
                st.markdown("<hr style='border-top: 1px solid rgba(255,255,255,0.08); margin: 25px 0 15px 0;'/>", unsafe_allow_html=True)
                st.markdown("### 🔌 Forensics Integration Action Center")
                
                # Split actions into columns
                col_slack, col_email, col_github, col_db = st.columns(4)
                
                with col_slack:
                    if st.button("💬 Alert Team on Slack", key=f"slack_{selected_id}", use_container_width=True):
                        with st.spinner("Posting to Slack..."):
                            success, msg, payload = send_slack_alert(
                                webhook_url=slack_webhook,
                                candidate_id=selected_id,
                                name=cand_row['name'],
                                rank=cand_row['rank'],
                                score=cand_row['score'],
                                trust_grade=grade,
                                reasoning=cand_row['reasoning']
                            )
                            if success:
                                st.success("Slack alert triggered successfully!")
                                if not slack_webhook:
                                    st.info("Simulated Mode: Showing Block Kit JSON Payload:")
                                    st.json(payload)
                                else:
                                    st.write(msg)
                            else:
                                st.error(msg)
                                
                with col_email:
                    if st.button("✉️ Invite to Interview", key=f"email_{selected_id}", use_container_width=True):
                        with st.spinner("Preparing email..."):
                            # Mock recipient email
                            c_email = f"{cand_row['name'].lower().replace(' ', '.')}@example.com"
                            subject = f"Interview Invitation: Founding AI Team at Redrob AI"
                            body_html = f"""
                            <p>Dear {cand_row['name']},</p>
                            <p>We have reviewed your profile and career history using our **Trinetra Forensics Engine**, and we are extremely impressed by your experience.</p>
                            <p>Specifically, your background in building search, retrieval, or machine learning systems aligns perfectly with our core requirements.</p>
                            <p>We would love to invite you for a 30-minute technical conversation to discuss the Founding Team roles at Redrob AI.</p>
                            <p>Please let us know your availability over the next few days.</p>
                            <p>Best regards,<br/>The Redrob AI Hiring Team</p>
                            """
                            success, msg, payload = send_candidate_email(
                                api_key=resend_key,
                                candidate_id=selected_id,
                                candidate_name=cand_row['name'],
                                candidate_email=c_email,
                                subject=subject,
                                email_body_html=body_html
                            )
                            if success:
                                st.success("Email sent / simulated successfully!")
                                if not resend_key:
                                    st.info("Simulated Mode: Showing Sent Email Envelope:")
                                    st.json(payload)
                                    with st.expander("👁️ View Email HTML Preview"):
                                        st.components.v1.html(payload["html"], height=250, scrolling=True)
                                else:
                                    st.write(msg)
                            else:
                                st.error(msg)
                                
                with col_github:
                    if st.button("🐙 Inspect GitHub", key=f"github_{selected_id}", use_container_width=True):
                        # Construct a mock username from candidate name
                        username_guess = cand_row['name'].lower().replace(' ', '')
                        with st.spinner(f"Querying GitHub for @{username_guess}..."):
                            profile = fetch_github_profile(username_guess, token=github_token)
                            st.session_state[f"github_profile_{selected_id}"] = profile
                            st.success("GitHub profile loaded!")
                            
                with col_db:
                    if st.button("🔄 SQLite Run Compare", key=f"db_compare_{selected_id}", use_container_width=True):
                        with st.spinner("Checking SQLite history..."):
                            comp_res = compare_candidate_ranks(
                                candidate_id=selected_id,
                                current_rank=cand_row['rank'],
                                current_score=cand_row['score']
                            )
                            st.session_state[f"db_compare_{selected_id}"] = comp_res
                            
                # Show GitHub Profile card if loaded
                if f"github_profile_{selected_id}" in st.session_state:
                    p = st.session_state[f"github_profile_{selected_id}"]
                    st.markdown("---")
                    st.markdown(f"#### 🐙 GitHub Stats: @{p['login']} (`{p['source']}`)")
                    
                    g_col1, g_col2, g_col3, g_col4 = st.columns(4)
                    with g_col1:
                        st.metric("Public Repos", p["public_repos"])
                    with g_col2:
                        st.metric("Stars Accum.", p["stars"])
                    with g_col3:
                        st.metric("Forks", p["forks"])
                    with g_col4:
                        st.metric("Followers", p["followers"])
                        
                    st.write(f"**Bio:** {p['bio']}")
                    st.write(f"**Top Languages:** {', '.join(p['top_languages'])}")
                    
                    with st.expander("📁 View Recent Repositories"):
                        for repo in p["recent_repos"]:
                            st.markdown(
                                f"""
                                <div style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                    <div style="font-weight:600;"><a href="{repo['url']}" target="_blank" style="color:#00E5CC; text-decoration:none;">{repo['name']}</a> ⭐ {repo['stars']}</div>
                                    <div style="font-size:0.85em; color:#8F9CAE;">Language: {repo['language']}</div>
                                    <p style="font-size:0.85em; margin: 4px 0 0 0; color:#A8B2C1;">{repo['description']}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            
                # Show SQLite Run Comparison if loaded
                if f"db_compare_{selected_id}" in st.session_state:
                    res = st.session_state[f"db_compare_{selected_id}"]
                    st.markdown("---")
                    st.markdown("#### 🔄 SQLite Historical Run Delta")
                    if res["status"] == "success":
                        st.write(f"**Previous Run:** {res['prev_run_timestamp'][:16].replace('T', ' ')} (Dataset: `{res['prev_dataset']}`)")
                        c_col1, c_col2, c_col3 = st.columns(3)
                        with c_col1:
                            st.metric("Previous Rank", f"#{res['prev_rank']}", delta=f"{res['rank_delta']} ranks" if res['rank_delta'] != 0 else None, delta_color="inverse")
                        with c_col2:
                            st.metric("Current Rank", f"#{cand_row['rank']}")
                        with c_col3:
                            st.metric("Rank Status", res["status_text"])
                    else:
                        st.info(res["message"])
                
                # End card wrapper
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Select a candidate from the list to display their talent forensics report.")
