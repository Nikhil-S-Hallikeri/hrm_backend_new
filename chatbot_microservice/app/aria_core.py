from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from app.chatbot import generate_answer
from app.contact_extractor import extract_contact_details
from app.conversation import normalize_lead_data, update_profile_memory
from app.lead_analyzer import analyze_lead
from app.schemas import AriaMessageRequest
from app.storage import (
    init_storage,
    append_message,
    get_messages,
    get_or_create_session,
    update_session_analysis,
)
from app.storage import _connect, _conn_lock  # Aria Core extends the same local DB.


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def _loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        return None
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) > 10:
        return f"+{digits}"
    return digits


def _session_id_for(channel: str, channel_session_id: str | None, user_id: str | None = None) -> str:
    if channel_session_id:
        return f"{channel}:{channel_session_id}"
    if user_id:
        return f"{channel}:{user_id}"
    return f"{channel}:{uuid4().hex}"


def init_aria_storage() -> None:
    conn = _connect()
    with _conn_lock:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS aria_users (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                email TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_identities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aria_user_id TEXT NOT NULL,
                identity_type TEXT NOT NULL,
                identity_value TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(identity_type, identity_value),
                FOREIGN KEY(aria_user_id) REFERENCES aria_users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                aria_user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(aria_user_id) REFERENCES aria_users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS aria_sessions (
                id TEXT PRIMARY KEY,
                aria_user_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                channel_session_id TEXT,
                fastapi_session_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL DEFAULT 'DISCOVERY',
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(aria_user_id) REFERENCES aria_users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS journey_states (
                aria_user_id TEXT PRIMARY KEY,
                current_stage TEXT NOT NULL,
                current_category TEXT,
                flow_id TEXT,
                last_completed_question TEXT,
                next_question TEXT,
                completed_questions TEXT NOT NULL DEFAULT '[]',
                pending_questions TEXT NOT NULL DEFAULT '[]',
                progress_percentage INTEGER NOT NULL DEFAULT 0,
                is_complete INTEGER NOT NULL DEFAULT 0,
                last_active_channel TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(aria_user_id) REFERENCES aria_users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_memories (
                aria_user_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL DEFAULT '',
                facts TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(aria_user_id) REFERENCES aria_users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recommendation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aria_user_id TEXT NOT NULL,
                session_id TEXT,
                category TEXT,
                recommendations TEXT NOT NULL DEFAULT '[]',
                selected_course TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(aria_user_id) REFERENCES aria_users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS duplicate_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aria_user_id TEXT NOT NULL,
                candidate_user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()


def _find_user_by_identity(identity_type: str, identity_value: str | None) -> str | None:
    if not identity_value:
        return None
    conn = _connect()
    with _conn_lock:
        row = conn.execute(
            '''
            SELECT aria_user_id FROM user_identities
            WHERE identity_type = ? AND identity_value = ?
            ''',
            (identity_type, identity_value),
        ).fetchone()
    return row["aria_user_id"] if row else None


def _create_user(name: str | None = None, phone: str | None = None, email: str | None = None) -> str:
    user_id = uuid4().hex
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            '''
            INSERT INTO aria_users(id, name, phone, email, created_at, updated_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (user_id, name, phone, email, now, now, now),
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_profiles(aria_user_id, profile_data, updated_at) VALUES (?, '{}', ?)",
            (user_id, now),
        )
        conn.commit()
    return user_id


def _upsert_identity(user_id: str, identity_type: str, identity_value: str | None, verified: bool = False) -> None:
    if not identity_value:
        return
    now = _now()
    conn = _connect()
    with _conn_lock:
        existing = conn.execute(
            "SELECT aria_user_id FROM user_identities WHERE identity_type = ? AND identity_value = ?",
            (identity_type, identity_value),
        ).fetchone()
        if existing and existing["aria_user_id"] != user_id:
            conn.execute(
                '''
                INSERT INTO duplicate_candidates(aria_user_id, candidate_user_id, reason, created_at)
                VALUES (?, ?, ?, ?)
                ''',
                (user_id, existing["aria_user_id"], f"{identity_type}_conflict", now),
            )
        else:
            conn.execute(
                '''
                INSERT INTO user_identities(aria_user_id, identity_type, identity_value, verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity_type, identity_value)
                DO UPDATE SET verified = MAX(verified, excluded.verified), updated_at = excluded.updated_at
                ''',
                (user_id, identity_type, identity_value, int(verified), now, now),
            )
        conn.commit()


def resolve_user(request: AriaMessageRequest) -> str:
    phone = normalize_phone(request.identity.phone)
    whatsapp = normalize_phone(request.identity.whatsapp_number)
    email = str(request.identity.email).lower() if request.identity.email else None
    session_identity = f"{request.channel}:{request.channel_session_id}" if request.channel_session_id else None

    user_id = (
        _find_user_by_identity("whatsapp", whatsapp)
        or _find_user_by_identity("phone", phone)
        or _find_user_by_identity("email", email)
        or _find_user_by_identity("website_session", session_identity if request.channel == "website" else None)
    )
    if not user_id:
        user_id = _create_user(request.identity.name, whatsapp or phone, email)

    _upsert_identity(user_id, "whatsapp", whatsapp, verified=request.channel == "whatsapp")
    _upsert_identity(user_id, "phone", phone or whatsapp)
    _upsert_identity(user_id, "email", email)
    if request.channel == "website":
        _upsert_identity(user_id, "website_session", session_identity)

    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            '''
            UPDATE aria_users
            SET name = COALESCE(NULLIF(?, ''), name),
                phone = COALESCE(NULLIF(?, ''), phone),
                email = COALESCE(NULLIF(?, ''), email),
                updated_at = ?,
                last_seen_at = ?
            WHERE id = ?
            ''',
            (request.identity.name or "", phone or whatsapp or "", email or "", now, now, user_id),
        )
        conn.commit()
    return user_id


def _get_profile(user_id: str) -> dict:
    conn = _connect()
    with _conn_lock:
        row = conn.execute(
            "SELECT profile_data FROM user_profiles WHERE aria_user_id = ?",
            (user_id,),
        ).fetchone()
    return normalize_lead_data(_loads(row["profile_data"], {}) if row else {})


def _save_profile(user_id: str, profile: dict) -> None:
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            '''
            INSERT INTO user_profiles(aria_user_id, profile_data, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(aria_user_id)
            DO UPDATE SET profile_data = excluded.profile_data, updated_at = excluded.updated_at
            ''',
            (user_id, _json(normalize_lead_data(profile)), now),
        )
        conn.execute(
            '''
            UPDATE aria_users
            SET name = COALESCE(NULLIF(?, ''), name),
                phone = COALESCE(NULLIF(?, ''), phone),
                email = COALESCE(NULLIF(?, ''), email),
                updated_at = ?
            WHERE id = ?
            ''',
            (
                profile.get("name") or "",
                normalize_phone(profile.get("phone")) or "",
                profile.get("email") or "",
                now,
                user_id,
            ),
        )
        conn.commit()


def _session_for_user(user_id: str, channel: str, channel_session_id: str | None) -> str:
    fastapi_session_id = _session_id_for(channel, channel_session_id, user_id)
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            '''
            INSERT OR IGNORE INTO aria_sessions(
                id, aria_user_id, channel, channel_session_id, fastapi_session_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (uuid4().hex, user_id, channel, channel_session_id, fastapi_session_id, now, now),
        )
        conn.execute(
            "UPDATE aria_sessions SET updated_at = ? WHERE fastapi_session_id = ?",
            (now, fastapi_session_id),
        )
        conn.commit()
    get_or_create_session(fastapi_session_id)
    return fastapi_session_id


def _choose_flow(profile: dict, tenant_config=None) -> tuple[str, dict]:
    default_flows = {
        "investor_minimal_v1": {
            "category": "Lead Capture",
            "questions": ["name", "phone", "email"],
        },
        "investor_deep_profile_v1": {
            "category": "Deep Profile",
            "questions": ["name", "phone", "email", "interest"],
        },
    }
    flows = tenant_config.flow_definitions if tenant_config and tenant_config.flow_definitions else default_flows

    if not flows:
        flows = default_flows

    flow_id = list(flows.keys())[0] if flows else "default"
    flow_data = flows.get(flow_id) if flows else {"category": "Default", "questions": ["name", "phone"]}
    
    if len(flows) > 1:
        if profile.get("phone") and profile.get("email"):
            flow_id = list(flows.keys())[-1]
            flow_data = flows.get(flow_id)
            
    return flow_id, flow_data


def _profile_value(profile: dict, question: str):
    aliases = {
        "city": "location",
        "state": "location",
        "budget": "investment_amount",
        "timeline": "investment_timeline",
        "availability": "callback_time",
    }
    return profile.get(question) or profile.get(aliases.get(question, ""))


def _stage_for(profile: dict, progress: int) -> str:
    if profile.get("phone") and profile.get("email") and progress >= 100:
        if profile.get("recommendations"):
            return "INVESTMENT_REVIEW_READY"
        return "INVESTOR_PROFILE_COMPLETED"
    if profile.get("phone") or profile.get("email"):
        return "INVESTOR_PROFILE_IN_PROGRESS"
    if profile.get("name"):
        return "IDENTITY_COLLECTION"
    return "ANONYMOUS"


def update_journey(user_id: str, profile: dict, channel: str, tenant_config=None) -> dict:
    flow_id, flow = _choose_flow(profile, tenant_config)
    questions = flow.get("questions", [])
    completed = [question for question in questions if _profile_value(profile, question)]
    pending = [question for question in questions if question not in completed]
    progress = int(round((len(completed) / len(questions)) * 100)) if questions else 100
    state = {
        "current_stage": _stage_for(profile, progress),
        "current_category": flow.get("category"),
        "flow_id": flow_id,
        "last_completed_question": completed[-1] if completed else None,
        "next_question": pending[0] if pending else None,
        "completed_questions": completed,
        "pending_questions": pending,
        "progress_percentage": progress,
        "is_complete": not pending,
        "last_active_channel": channel,
    }
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            '''
            INSERT INTO journey_states(
                aria_user_id, current_stage, current_category, flow_id,
                last_completed_question, next_question, completed_questions,
                pending_questions, progress_percentage, is_complete,
                last_active_channel, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(aria_user_id) DO UPDATE SET
                current_stage = excluded.current_stage,
                current_category = excluded.current_category,
                flow_id = excluded.flow_id,
                last_completed_question = excluded.last_completed_question,
                next_question = excluded.next_question,
                completed_questions = excluded.completed_questions,
                pending_questions = excluded.pending_questions,
                progress_percentage = excluded.progress_percentage,
                is_complete = excluded.is_complete,
                last_active_channel = excluded.last_active_channel,
                updated_at = excluded.updated_at
            ''',
            (
                user_id,
                state["current_stage"],
                state["current_category"],
                state["flow_id"],
                state["last_completed_question"],
                state["next_question"],
                _json(state["completed_questions"]),
                _json(state["pending_questions"]),
                state["progress_percentage"],
                int(state["is_complete"]),
                channel,
                now,
            ),
        )
        conn.commit()
    return state


def _save_memory(user_id: str, profile: dict, analysis_summary: str, ai_config=None) -> str:
    facts = []
    
    ai_dict = ai_config.dict() if hasattr(ai_config, "dict") else getattr(ai_config, "__dict__", {}) if ai_config else {}
    lead_collection = ai_dict.get("lead_collection", [])
    profile_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    if not profile_fields:
        profile_fields = ["current_status", "interest", "investment_amount", "investment_timeline", "location"]
    
    for key in profile_fields:
        if profile.get(key):
            facts.append({"type": key, "value": profile[key], "source": "aria_core"})
            
    summary = analysis_summary or "No durable profile context collected yet."
    now = _now()
    conn = _connect()
    with _conn_lock:
        conn.execute(
            '''
            INSERT INTO user_memories(aria_user_id, summary, facts, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(aria_user_id)
            DO UPDATE SET summary = excluded.summary, facts = excluded.facts, updated_at = excluded.updated_at
            ''',
            (user_id, summary, _json(facts), now),
        )
        conn.commit()
    return summary


def _record_recommendations(user_id: str, session_id: str, profile: dict) -> None:
    recommendations = profile.get("recommendations") or []
    if not recommendations:
        return
    conn = _connect()
    with _conn_lock:
        existing = conn.execute(
            '''
            SELECT id FROM recommendation_history
            WHERE aria_user_id = ? AND session_id = ? AND recommendations = ?
            ''',
            (user_id, session_id, _json(recommendations)),
        ).fetchone()
        if not existing:
            conn.execute(
                '''
                INSERT INTO recommendation_history(aria_user_id, session_id, category, recommendations, selected_course, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    user_id,
                    session_id,
                    profile.get("course_category") or profile.get("interest"),
                    _json(recommendations),
                    profile.get("course_title"),
                    _now(),
                ),
            )
            conn.commit()


def handle_aria_message(request: AriaMessageRequest) -> dict:
    init_storage()
    init_aria_storage()
    user_id = resolve_user(request)
    session_id = _session_for_user(user_id, request.channel, request.channel_session_id)
    session = get_or_create_session(session_id)
    profile = _get_profile(user_id)

    for key, value in {
        "name": request.identity.name,
        "email": str(request.identity.email) if request.identity.email else None,
        "phone": normalize_phone(request.identity.phone) or normalize_phone(request.identity.whatsapp_number),
    }.items():
        if value:
            # Force update if profile doesn't have it, or if existing profile has invalid/greeting name
            if not profile.get(key) or profile.get(key) in ("Unknown", "None", "") or (key == "name" and len(value.split()) > len((profile.get("name") or "").split())):
                profile[key] = value

    extracted = extract_contact_details(request.message)
    for key in ("name", "email", "phone"):
        value = extracted.get(key)
        if value and not profile.get(key):
            profile[key] = normalize_phone(value) if key == "phone" else value

    profile.update(update_profile_memory(profile, request.message, request.ai_config))

    if profile.get("phone"):
        _upsert_identity(user_id, "phone", normalize_phone(profile.get("phone")))
        _upsert_identity(user_id, "whatsapp", normalize_phone(profile.get("phone")))
    if profile.get("email"):
        _upsert_identity(user_id, "email", str(profile.get("email")).lower())

    session["lead_data"].update(normalize_lead_data(profile))
    append_message(session_id, "user", request.message)

    messages = get_messages(session_id)
    answer, llm_extracted = generate_answer(messages, session["lead_data"], lead_status="Cold", ai_config=request.ai_config)
    if llm_extracted:
        session["lead_data"].update(update_profile_memory(session["lead_data"], request.message, request.ai_config, llm_extracted=llm_extracted))

    append_message(session_id, "assistant", answer)
    messages = get_messages(session_id)
    analysis = analyze_lead(messages, bool(session["lead_data"].get("phone") or session["lead_data"].get("email")), request.ai_config, session["lead_data"])

    profile = normalize_lead_data(session["lead_data"])
    _save_profile(user_id, profile)
    journey = update_journey(user_id, profile, request.channel, request.ai_config)
    memory_summary = _save_memory(user_id, profile, analysis.summary, request.ai_config)
    _record_recommendations(user_id, session_id, profile)

    update_session_analysis(
        session_id=session_id,
        lead_data=profile,
        lead_status=analysis.lead_type,
        lead_score=analysis.lead_score,
        summary=analysis.summary,
    )

    actions = []
    if request.channel == "website" and profile.get("phone") and profile.get("name"):
        actions.append({
            "type": "send_whatsapp_template",
            "template_name": "aria_welcome",
            "to": profile.get("phone"),
            "required": False,
        })

    return {
        "aria_user_id": user_id,
        "session_id": session_id,
        "answer": answer,
        "profile": profile,
        "journey_state": journey,
        "lead": {
            "lead_type": analysis.lead_type,
            "lead_score": analysis.lead_score,
            "needs_callback": analysis.needs_callback,
            "next_action": analysis.next_action,
        },
        "actions": actions,
        "memory_summary": memory_summary,
    }


def get_user_snapshot(user_id: str) -> dict | None:
    init_aria_storage()
    conn = _connect()
    with _conn_lock:
        user = conn.execute("SELECT * FROM aria_users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return None
        identities = conn.execute(
            "SELECT identity_type, identity_value, verified FROM user_identities WHERE aria_user_id = ?",
            (user_id,),
        ).fetchall()
        journey = conn.execute(
            "SELECT * FROM journey_states WHERE aria_user_id = ?",
            (user_id,),
        ).fetchone()
        memory = conn.execute(
            "SELECT summary, facts FROM user_memories WHERE aria_user_id = ?",
            (user_id,),
        ).fetchone()
    return {
        "user": dict(user),
        "identities": [dict(row) for row in identities],
        "profile": _get_profile(user_id),
        "journey_state": {
            **dict(journey),
            "completed_questions": _loads(journey["completed_questions"], []),
            "pending_questions": _loads(journey["pending_questions"], []),
            "is_complete": bool(journey["is_complete"]),
        } if journey else None,
        "memory": {
            "summary": memory["summary"],
            "facts": _loads(memory["facts"], []),
        } if memory else None,
    }
