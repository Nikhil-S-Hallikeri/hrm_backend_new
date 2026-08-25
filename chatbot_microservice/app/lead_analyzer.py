from __future__ import annotations

import re

from app.conversation import (
    calculate_lead_score,
    has_full_name,
    lead_type_from_score,
    normalize_lead_data,
)
from app.schemas import LeadAnalysis
from typing import Any


TRANSCRIPT_WINDOW = 12

URGENCY_SIGNALS = re.compile(
    r"\b(want to invest|ready to invest|start now|register|current projects?|available projects?|"
    r"call me|callback|schedule|meeting|documentation|agreement|this week|this month|asap|immediately)\b",
    re.I,
)

BUDGET_CONCERN_SIGNALS = {
    "minimum", "budget", "too much", "expensive", "small amount", "no money",
    "not enough", "can't invest", "cannot invest", "afford",
}


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _get_ai_dict(ai_config: Any) -> dict:
    defaults = {
        "assistant_name": "Assistant",
        "business_name": "Company",
        "personality": "Support",
        "tone": "Friendly and Professional",
        "primary_language": "en",
        "prompt": "",
        "system_prompt": "",
        "conversation_behaviours": [],
        "lead_collection": [],
        "auto_replies": [],
        "websites": [],
        "faqs": [],
        "context_window_size": 15,
        "fallback_rule": "transfer",
        "confidence_threshold": 70,
        "human_handoff_alert": True
    }
    if not ai_config:
        return defaults
    
    config_dict = {}
    if isinstance(ai_config, dict):
        config_dict = ai_config
    elif hasattr(ai_config, "model_dump"):
        config_dict = ai_config.model_dump()
    elif hasattr(ai_config, "dict"):
        config_dict = ai_config.dict()
    else:
        config_dict = getattr(ai_config, "__dict__", {})

    for k, v in config_dict.items():
        if v is not None:
            defaults[k] = v
    return defaults


def _build_summary(lead_data: dict, ai_config: Any) -> str:
    ai_dict = _get_ai_dict(ai_config)
    parts = []
    
    if lead_data.get("name"):
        parts.append(f"Name: {lead_data['name']}")
    if lead_data.get("phone"):
        parts.append(f"Phone: {lead_data['phone']}")
    if lead_data.get("email"):
        parts.append(f"Email: {lead_data['email']}")
        
    lead_collection = ai_dict.get("lead_collection", [])
    active_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    standard_capture = {"name", "phone", "email"}
    profile_fields = [f for f in active_fields if f.lower() not in standard_capture]
    
    for field in profile_fields:
        value = lead_data.get(field)
        if value:
            parts.append(f"{field.replace('_', ' ').capitalize()}: {value}")

    if not parts:
        return "Visitor has not shared qualification details yet."

    return " | ".join(parts)


def _missing_fields(lead_data: dict, ai_config: Any) -> list[str]:
    ai_dict = _get_ai_dict(ai_config)
    has_full = has_full_name(lead_data.get("name"))
    missing: list[str] = []
    lead_collection = ai_dict.get("lead_collection", [])
    capture_fields = [f.get("field_name", "").lower() for f in lead_collection if f.get("is_active")]
    
    for field in capture_fields:
        if not lead_data.get(field):
            if field == "name" and not has_full:
                missing.append("full name")
            else:
                missing.append(field.replace("_", " "))
    return missing

def _build_next_action(lead_data: dict, state: str | None, ai_config: Any) -> str:
    missing = _missing_fields(lead_data, ai_config)
    
    if not missing:
        return "All required lead details collected — ready for advisor handoff."
        
    return f"Need to collect missing info: {', '.join(missing)}."

    if state in {"LEAD_CAPTURE", "CALLBACK_REQUEST"}:
        return f"Collect {', '.join(missing)}."

    return "Continue nurturing and answer questions."


def analyze_lead(
    messages: list[dict[str, str]],
    contact_collected: bool,
    ai_config: dict,
    lead_data: dict | None = None,
) -> LeadAnalysis:
    transcript = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in messages[-TRANSCRIPT_WINDOW:]
    )
    transcript_lower = transcript.lower()

    lead_data = normalize_lead_data(lead_data)

    has_phone = bool(lead_data.get("phone"))
    has_email = bool(lead_data.get("email"))
    contact_collected = has_phone or has_email or contact_collected

    score = calculate_lead_score(lead_data, ai_config)
    lead_type = lead_type_from_score(score, transcript)
    state = lead_data.get("conversation_state")

    if score >= 11 or URGENCY_SIGNALS.search(transcript):
        urgency = "high"
    elif score >= 6:
        urgency = "medium"
    else:
        urgency = "low"

    budget_signal = "concern" if _contains_any(transcript_lower, BUDGET_CONCERN_SIGNALS) else "unknown"

    needs_callback = bool(
        has_phone
        or lead_data.get("advisor_requested")
        or "call me" in transcript_lower
        or "callback" in transcript_lower
        or "current project" in transcript_lower
        or "documentation" in transcript_lower
    )

    return LeadAnalysis(
        lead_type=lead_type,
        interest=lead_data.get("interest"),
        urgency=urgency,
        budget_signal=budget_signal,
        needs_callback=needs_callback,
        contact_collected=contact_collected,
        lead_score=score,
        summary=_build_summary(lead_data, ai_config),
        next_action=_build_next_action(lead_data, state, ai_config),
    )
