import sqlite3
import os
import hashlib
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agentstate.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Create sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create steps table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                request_hash TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                token_cost REAL DEFAULT 0,
                latency REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                UNIQUE(session_id, step_number)
            )
        """)
        # Create approvals table for Human-in-the-Loop gateway
        conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                step_number INTEGER DEFAULT 0,
                tool_name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

def calculate_hash(prompt: str, tools_json: str = "") -> str:
    """Helper to generate unique hash for request context to check for cache match"""
    content = f"{prompt}||{tools_json}".encode("utf-8")
    return hashlib.sha256(content).hexdigest()

def get_or_create_session(session_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        if not session:
            conn.execute(
                "INSERT INTO sessions (id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, "RUNNING", datetime.now(), datetime.now())
            )
            conn.commit()
            return {"id": session_id, "status": "RUNNING"}
        return dict(session)

def update_session_status(session_id: str, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now(), session_id)
        )
        conn.commit()

def get_cached_step(session_id: str, step_number: int, request_hash: str):
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM steps WHERE session_id = ? AND step_number = ? AND request_hash = ?",
            (session_id, step_number, request_hash)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

def save_step(session_id: str, step_number: int, request_hash: str, prompt: str, response: str, token_cost: float, latency: float):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO steps (session_id, step_number, request_hash, prompt, response, token_cost, latency)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, step_number) DO UPDATE SET
                request_hash = excluded.request_hash,
                prompt = excluded.prompt,
                response = excluded.response,
                token_cost = excluded.token_cost,
                latency = excluded.latency
        """, (session_id, step_number, request_hash, prompt, response, token_cost, latency))
        conn.commit()

def reset_session_from_step(session_id: str, step_number: int):
    """Delete all steps starting from step_number to allow rollback and fresh retry"""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM steps WHERE session_id = ? AND step_number >= ?",
            (session_id, step_number)
        )
        conn.execute(
            "UPDATE sessions SET status = 'RUNNING', updated_at = ? WHERE id = ?",
            (datetime.now(), session_id)
        )
        conn.commit()

def get_session_details(session_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        if not session:
            return None
        
        cursor = conn.execute("SELECT * FROM steps WHERE session_id = ? ORDER BY step_number ASC", (session_id,))
        steps = [dict(row) for row in cursor.fetchall()]
        
        return {
            "session": dict(session),
            "steps": steps
        }

def get_all_sessions():
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
        sessions = [dict(row) for row in cursor.fetchall()]
        return sessions

def create_approval_request(session_id: str, step_number: int, tool_name: str, prompt: str) -> int:
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO approvals (session_id, step_number, tool_name, prompt, status, created_at)
            VALUES (?, ?, ?, ?, 'PENDING', ?)
        """, (session_id, step_number, tool_name, prompt, datetime.now()))
        conn.commit()
        return cursor.lastrowid

def get_pending_approvals():
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM approvals WHERE status = 'PENDING' ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_approval_by_id(approval_id: int):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_approval_status(approval_id: int, status: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE approvals SET status = ? WHERE id = ?",
            (status, approval_id)
        )
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
