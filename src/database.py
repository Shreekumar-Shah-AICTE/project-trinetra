"""
database.py — SQLite Local Persistence Engine for Project Trinetra (त्रिनेत्र)
🔱 Multi-Table Audit and Caching Architecture
"""

import sqlite3
import os
import uuid
from datetime import datetime

DEFAULT_DB_PATH = os.path.join("data", "trinetra.db")


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Establish and return a connection to the SQLite database."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH):
    """
    Initialize the database schema with exactly 5 tables:
    1. candidates — Profile metadata
    2. violations — Integrity check details (Foreign Key to candidates)
    3. scores — Multi-dimensional raw scores (Foreign Key to candidates)
    4. rankings — Final fusion ranks and reasons (Foreign Key to candidates)
    5. audit_log — System run analytics log
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Table 1: candidates
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            anonymized_name TEXT,
            current_title TEXT,
            current_company TEXT,
            years_of_experience REAL,
            trust_grade TEXT,
            is_honeypot INTEGER,
            disqualified INTEGER,
            last_updated TEXT
        );
        """
    )

    # Table 2: violations
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id TEXT,
            violation_text TEXT,
            severity TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id) ON DELETE CASCADE
        );
        """
    )

    # Table 3: scores
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            candidate_id TEXT PRIMARY KEY,
            skill_relevance REAL,
            career_trajectory REAL,
            behavioral_availability REAL,
            trust_score REAL,
            semantic_fit REAL,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id) ON DELETE CASCADE
        );
        """
    )

    # Table 4: rankings
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rankings (
            candidate_id TEXT PRIMARY KEY,
            run_id TEXT,
            rank_position INTEGER,
            rrf_score REAL,
            reasoning TEXT,
            FOREIGN KEY (candidate_id) REFERENCES candidates (candidate_id) ON DELETE CASCADE,
            FOREIGN KEY (run_id) REFERENCES audit_log (run_id) ON DELETE CASCADE
        );
        """
    )

    # Table 5: audit_log
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            run_id TEXT PRIMARY KEY,
            timestamp TEXT,
            duration_seconds REAL,
            total_scanned INTEGER,
            honeypots_caught INTEGER,
            disqualified_count INTEGER,
            dataset_name TEXT
        );
        """
    )

    conn.commit()
    conn.close()


def save_pipeline_run(
    candidates: list[dict],
    guard_results: dict[str, dict],
    scored_candidates: list[dict],
    fused_ranking: list[tuple[str, float]],
    output_rows: list[dict],
    duration: float,
    dataset_name: str = "candidates.jsonl",
    db_path: str = DEFAULT_DB_PATH,
) -> str:
    """
    Save all processed metrics, candidate data, violations, and final RRF ranks
    to the 5 tables in the SQLite database.
    
    Returns the generated run_id.
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    run_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Calculate stats
    total_scanned = len(candidates)
    honeypots_caught = sum(1 for res in guard_results.values() if res["is_hard_honeypot"])
    disqualified_count = sum(1 for res in guard_results.values() if res["disqualified"])

    # 1. Insert into audit_log
    cursor.execute(
        """
        INSERT INTO audit_log (run_id, timestamp, duration_seconds, total_scanned, honeypots_caught, disqualified_count, dataset_name)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (run_id, timestamp, duration, total_scanned, honeypots_caught, disqualified_count, dataset_name),
    )

    # Convert lists to lookups
    scored_lookup = {sc["candidate_id"]: sc for sc in scored_candidates}
    rank_lookup = {cid: (rank, score) for rank, (cid, score) in enumerate(fused_ranking, 1)}
    reasoning_lookup = {row["candidate_id"]: row["reasoning"] for row in output_rows}

    # 2. Insert candidates, violations, scores, and rankings
    for cand in candidates:
        cid = cand["candidate_id"]
        profile = cand.get("profile", {})
        guard = guard_results[cid]
        
        # Save or update candidate
        cursor.execute(
            """
            INSERT OR REPLACE INTO candidates (
                candidate_id, anonymized_name, current_title, current_company, 
                years_of_experience, trust_grade, is_honeypot, disqualified, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                cid,
                profile.get("anonymized_name", "Anonymized"),
                profile.get("current_title", "Unknown"),
                profile.get("current_company", "Unknown"),
                profile.get("years_of_experience", 0.0),
                guard["trust_grade"],
                1 if guard["is_hard_honeypot"] else 0,
                1 if guard["disqualified"] else 0,
                timestamp,
            ),
        )

        # Clear existing violations for candidate to avoid duplication
        cursor.execute("DELETE FROM violations WHERE candidate_id = ?;", (cid,))
        
        # Save violations
        for violation in guard["violations"]:
            cursor.execute(
                """
                INSERT INTO violations (candidate_id, violation_text, severity)
                VALUES (?, ?, ?);
                """,
                (cid, violation, "high" if guard["is_hard_honeypot"] else "medium"),
            )

        # Save scores (if the candidate survived and was scored)
        if cid in scored_lookup:
            sc = scored_lookup[cid]
            cursor.execute(
                """
                INSERT OR REPLACE INTO scores (
                    candidate_id, skill_relevance, career_trajectory, 
                    behavioral_availability, trust_score, semantic_fit
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    cid,
                    sc["skill_relevance_score"],
                    sc["career_score"],
                    sc["behavioral_score"],
                    sc["trust_rank_score"],
                    sc["semantic_score"],
                ),
            )

        # Save ranking (if in top 100 / fused ranks)
        if cid in rank_lookup:
            rank_pos, score = rank_lookup[cid]
            reasoning = reasoning_lookup.get(cid, "")
            cursor.execute(
                """
                INSERT OR REPLACE INTO rankings (candidate_id, run_id, rank_position, rrf_score, reasoning)
                VALUES (?, ?, ?, ?, ?);
                """,
                (cid, run_id, rank_pos, score, reasoning),
            )

    conn.commit()
    conn.close()
    return run_id


def get_latest_runs(limit: int = 10, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Retrieve the list of recent pipeline runs."""
    if not os.path.exists(db_path):
        return []
        
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?;", (limit,))
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return runs


def get_run_results(run_id: str, db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Retrieve detailed ranking results for a specific pipeline run."""
    if not os.path.exists(db_path):
        return []
        
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.rank_position as rank, r.rrf_score as score, r.reasoning,
               c.candidate_id, c.anonymized_name as name, c.current_title, c.current_company,
               c.years_of_experience as yoe, c.trust_grade, c.is_honeypot,
               s.skill_relevance as skill_score, s.career_trajectory as career_score,
               s.behavioral_availability as behavioral_score, s.semantic_fit as semantic_score
        FROM rankings r
        JOIN candidates c ON r.candidate_id = c.candidate_id
        LEFT JOIN scores s ON r.candidate_id = s.candidate_id
        WHERE r.run_id = ?
        ORDER BY r.rank_position ASC;
        """,
        (run_id,),
    )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_candidate_violations(candidate_id: str, db_path: str = DEFAULT_DB_PATH) -> list[str]:
    """Retrieve all violations logged for a specific candidate."""
    if not os.path.exists(db_path):
        return []
        
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT violation_text FROM violations WHERE candidate_id = ?;", (candidate_id,))
    violations = [row["violation_text"] for row in cursor.fetchall()]
    conn.close()
    return violations
