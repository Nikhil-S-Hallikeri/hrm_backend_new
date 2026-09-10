from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.config import get_settings
from app.conversation import normalize_lead_data

logger = logging.getLogger(__name__)

# ── Module-level DB path (computed once) ───────────────────────────────────────

def _resolve_db_path() -> Path:
    settings = get_settings()
    path = Path(settings.database_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH: Path = _resolve_db_path()

# Thread-safe connection cache
_conn_lock = Lock()
_connection: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    """
    Return a module-level SQLite connection, creating it if needed.
    check_same_thread=False is safe here because we serialize access via _conn_lock.
    """
    global _connection
    with _conn_lock:
        if _connection is None:
            _connection = sqlite3.connect(
                DB_PATH,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            _connection.row_factory = sqlite3.Row
            _connection.execute("PRAGMA journal_mode=WAL")   # better concurrency
            _connection.execute("PRAGMA foreign_keys=ON")
        return _connection


def _now() -> str:
    """UTC timestamp with timezone suffix for unambiguous storage."""
    return datetime.now(timezone.utc).isoformat()


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_storage() -> None:
    conn = _connect()
    with _conn_lock:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT    PRIMARY KEY,
                lead_data    TEXT    NOT NULL DEFAULT '{}',
                lead_status  TEXT    NOT NULL DEFAULT 'Cold',
                lead_score   INTEGER NOT NULL DEFAULT 0,
                summary      TEXT    NOT NULL DEFAULT '',
                crm_pushed   INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL,
                updated_at   TEXT    NOT NULL,
                ended_at     TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)"
        )
        conn.commit()


# ── Session management ─────────────────────────────────────────────────────────

def get_or_create_session(session_id: str) -> dict:
    """
    Fetch or create a session atomically.
    Uses INSERT OR IGNORE to avoid race conditions on concurrent requests.
    """
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            """
            INSERT OR IGNORE INTO sessions(session_id, lead_data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, json.dumps(normalize_lead_data({})), now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return _row_to_session(row)


def get_session(session_id: str) -> dict | None:
    conn = _connect()
    with _conn_lock:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return _row_to_session(row) if row else None


def _row_to_session(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["lead_data"] = normalize_lead_data(json.loads(data.get("lead_data") or "{}"))
    data["crm_pushed"] = bool(data.get("crm_pushed"))
    return data


def update_session_analysis(
    session_id: str,
    lead_data: dict,
    lead_status: str,
    lead_score: int,
    summary: str = "",
) -> None:
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            """
            UPDATE sessions
            SET lead_data = ?, lead_status = ?, lead_score = ?,
                summary = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (json.dumps(lead_data), lead_status, lead_score, summary or "", now, session_id),
        )
        conn.commit()


def mark_session_ended(session_id: str, crm_pushed: bool, summary: str) -> None:
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            """
            UPDATE sessions
            SET ended_at = ?, crm_pushed = ?, summary = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (now, int(crm_pushed), summary or "", now, session_id),
        )
        conn.commit()


# ── Message management ─────────────────────────────────────────────────────────

def append_message(session_id: str, role: str, content: str) -> None:
    """
    Insert a message and update session timestamp atomically.
    Both writes are in a single transaction — no partial state on crash.
    """
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )
        conn.commit()


def get_messages(
    session_id: str,
    limit: int | None = None,
) -> list[dict[str, str]]:
    """
    Return messages for a session as {role, content} dicts only.
    Pass limit to fetch only the most recent N messages.
    """
    conn = _connect()
    if limit:
        query = """
            SELECT role, content FROM (
                SELECT role, content, id
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
        """
        params = (session_id, limit)
    else:
        query = "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC"
        params = (session_id,)

    with _conn_lock:
        rows = conn.execute(query, params).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


# ── Cleanup ────────────────────────────────────────────────────────────────────

def cleanup_old_sessions() -> None:
    """Delete sessions older than retention_days in two bulk queries."""
    settings = get_settings()
    cutoff = (
        datetime.now(timezone.utc) - __import__("datetime").timedelta(days=settings.retention_days)
    ).isoformat()

    conn = _connect()
    with _conn_lock:
        conn.execute(
            "DELETE FROM messages WHERE session_id IN (SELECT session_id FROM sessions WHERE created_at < ?)",
            (cutoff,),
        )
        conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
        conn.commit()
    logger.info("Cleaned up sessions older than %d days", settings.retention_days)


# ── Transcript ─────────────────────────────────────────────────────────────────

def get_transcript(session_id: str) -> dict | None:
    """Return full session data including message history."""
    session = get_session(session_id)
    if not session:
        return None
    return {**session, "messages": get_messages(session_id)}


# Keep old name as alias so existing callers don't break immediately
transcript = get_transcript