from __future__ import annotations

import json
import os
import re
from enum import StrEnum
from typing import Any

from app.config import get_settings
from app.llm_router import generate_llm_response


class ConversationState(StrEnum):
    DISCOVERY = "DISCOVERY"
    PROFILE_COLLECTION = "PROFILE_COLLECTION"
    RECOMMENDATION = "RECOMMENDATION"
    LEAD_CAPTURE = "LEAD_CAPTURE"
    QUALIFIED = "QUALIFIED"


LEAD_DATA_DEFAULTS: dict[str, Any] = {
    "name": None,
    "email": None,
    "phone": None,
    "interest": None,
    "email_refused": False,
    "phone_refused": False,
    "callback_deferred": False,
    "conversation_state": ConversationState.DISCOVERY.value,
    "recommendations": [],
    "advisor_requested": False,
    "brochure_requested": False,
}

SPAM_RE = re.compile(r"\b(spam|asdf|hello123|random|ignore|fake|test123)\b", re.I)

HIGH_INTENT_RE = re.compile(
    r"\b(want to buy|ready to buy|how do i start|where do i register|"
    r"can someone call|call me|callback|contact me|schedule a meeting|current projects?|available|"
    r"documentation|agreement|register|purchase|buy)\b",
    re.I,
)

CALLBACK_RE = re.compile(
    r"\b(call me|callback|call back|contact me|advisor|representative|human|schedule|meeting|"
    r"how do i start|send brochure|send email)\b",
    re.I,
)

EMAIL_REFUSAL_RE = re.compile(
    r"\b(no|nope|not interested|don't want|do not want|dont want|won't|will not|can't|cannot|skip|later)\b.{0,80}\b(email|mail)\b|"
    r"\b(email|mail)\b.{0,80}\b(no|nope|not interested|don't want|do not want|dont want|won't|will not|can't|cannot|skip|later)\b",
    re.I,
)

PHONE_REFUSAL_RE = re.compile(
    r"\b(no|nope|not interested|don't want|do not want|dont want|won't|will not|can't|cannot|skip|later)\b.{0,80}\b(phone|number|mobile)\b|"
    r"\b(phone|number|mobile)\b.{0,80}\b(no|nope|not interested|don't want|do not want|dont want|won't|will not|can't|cannot|skip|later)\b",
    re.I,
)

CALLBACK_DEFER_RE = re.compile(
    r"\b(not now|later|some other time|better time|busy|call later|don't call now|do not call now|dont call now)\b",
    re.I,
)

BROCHURE_RE = re.compile(r"\b(brochure|deck|pdf|send details|send email|mail me|whatsapp details)\b", re.I)

PROFILE_EXTRACTION_PROMPT = """Extract only explicitly stated qualification facts from the latest user message.
Return ONLY valid JSON with this shape:
{
%s
}
Rules:
- Use null when the user did not explicitly say it.
- Evidence must be a short exact phrase from the user message.
- Do not invent facts, locations, amounts, or timelines.
"""

def _evidence_is_present(message: str, evidence: str | None) -> bool:
    return bool(evidence and evidence.strip().lower() in message.lower())

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

def clean_json_response(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
        cleaned = "\n".join(lines).strip()
    return cleaned

def _llm_profile_extraction(message: str, ai_config: Any) -> dict[str, str]:
    if not message.strip() or os.getenv("PYTEST_CURRENT_TEST"):
        return {}

    ai_dict = _get_ai_dict(ai_config)
    lead_collection = ai_dict.get("lead_collection", [])
    active_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    profile_fields = active_fields
    if not profile_fields:
        return {}

    settings = get_settings()
    ai_key = None
    if ai_config:
        ai_key = getattr(ai_config, 'api_key', None) or (ai_config.get('api_key') if isinstance(ai_config, dict) else None)

    if not (ai_key or settings.openrouter_api_key or settings.openai_api_key or settings.groq_api_key or os.getenv("GEMINI_API_KEY")):
        return {}

    json_shape_lines = ',\n'.join([f'  "{field}": {{"value": null|string, "evidence": null|string}}' for field in profile_fields])
    prompt = PROFILE_EXTRACTION_PROMPT % json_shape_lines

    try:
        content = generate_llm_response(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ],
            lead_status="Cold",
            temperature=0,
            max_tokens=360,
        )
        print(f"LLM Raw Output: {content}")
        raw = json.loads(clean_json_response(content))
    except Exception as e:
        print(f"LLM Exception: {e}")
        return {}

    extracted: dict[str, str] = {}
    for key in profile_fields:
        item = raw.get(key)
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        evidence = item.get("evidence")
        if isinstance(value, str) and _evidence_is_present(message, evidence):
            extracted[key] = value.strip()
    return extracted

def normalize_lead_data(lead_data: dict | None) -> dict:
    normalized = {**LEAD_DATA_DEFAULTS, **(lead_data or {})}
    if not isinstance(normalized.get("recommendations"), list):
        normalized["recommendations"] = []
    if str(normalized.get("email") or "").strip().lower() in {"refused", "none", "null", "n/a", "na"}:
        normalized["email"] = None
    return normalized

def merge_llm_extracted_contact(lead_data: dict, llm_extracted: dict) -> dict:
    for llm_key, value in llm_extracted.items():
        if value and value != "null" and not lead_data.get(llm_key):
            lead_data[llm_key] = value
            
            # Synchronize standard keys for compatibility
            key_lower = llm_key.lower()
            if "name" in key_lower and not lead_data.get("name"):
                lead_data["name"] = value
            elif "phone" in key_lower and not lead_data.get("phone"):
                lead_data["phone"] = value
            elif "email" in key_lower and not lead_data.get("email"):
                lead_data["email"] = value
            elif ("budget" in key_lower or "investment" in key_lower) and not lead_data.get("investment_amount"):
                lead_data["investment_amount"] = value
    return lead_data

def update_profile_memory(lead_data: dict, message: str, ai_config: Any = None, llm_extracted: dict | None = None) -> dict:
    lead_data = normalize_lead_data(lead_data)

    if EMAIL_REFUSAL_RE.search(message or ""):
        lead_data["email_refused"] = True
    if PHONE_REFUSAL_RE.search(message or ""):
        lead_data["phone_refused"] = True
    if CALLBACK_DEFER_RE.search(message or ""):
        lead_data["callback_deferred"] = True
    if CALLBACK_RE.search(message or ""):
        lead_data["advisor_requested"] = True
    if BROCHURE_RE.search(message or ""):
        lead_data["brochure_requested"] = True
    
    if llm_extracted:
        lead_data = merge_llm_extracted_contact(lead_data, llm_extracted)

    llm_profile = _llm_profile_extraction(message, ai_config)
    lead_data = merge_llm_extracted_contact(lead_data, llm_profile)

    lead_data["conversation_state"] = determine_state(lead_data, message, ai_config).value
    return lead_data

def has_sufficient_recommendation_data(lead_data: dict, ai_config: Any) -> bool:
    ai_dict = _get_ai_dict(ai_config)
    lead_data = normalize_lead_data(lead_data)
    
    lead_collection = ai_dict.get("lead_collection", [])
    active_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    standard_capture = {"name", "phone", "email"}
    profile_fields = [f for f in active_fields if f.lower() not in standard_capture]
    
    collected_fields = sum(1 for f in profile_fields if lead_data.get(f))
    
    return bool(
        (len(profile_fields) == 0)
        or (len(profile_fields) > 0 and collected_fields >= min(2, len(profile_fields)))
    )

def determine_state(lead_data: dict, latest_message: str, ai_config: Any = None) -> ConversationState:
    ai_dict = _get_ai_dict(ai_config)
    lead_data = normalize_lead_data(lead_data)

    if lead_data.get("phone") and lead_data.get("email") and has_sufficient_recommendation_data(lead_data, ai_dict):
        return ConversationState.QUALIFIED

    if lead_data.get("advisor_requested") or HIGH_INTENT_RE.search(latest_message or ""):
        return ConversationState.LEAD_CAPTURE

    if lead_data.get("phone") or lead_data.get("name"):
        return ConversationState.LEAD_CAPTURE

    if has_sufficient_recommendation_data(lead_data, ai_dict):
        return ConversationState.RECOMMENDATION
    
    lead_collection = ai_dict.get("lead_collection", [])
    active_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    standard_capture = {"name", "phone", "email"}
    profile_fields = [f for f in active_fields if f.lower() not in standard_capture]
    
    if any(lead_data.get(f) for f in profile_fields):
        return ConversationState.PROFILE_COLLECTION
        
    return ConversationState.DISCOVERY

def recommend_courses(lead_data: dict, limit: int = 3) -> list[dict[str, str | None]]:
    del limit
    lead_data = normalize_lead_data(lead_data)
    recommendations: list[dict[str, str | None]] = []

    if lead_data.get("interest"):
        recommendations.append({"title": f"Explore {lead_data['interest']}", "category": "General"})
    
    return recommendations[:3]

def calculate_lead_score(lead_data: dict, ai_config: Any) -> int:
    ai_dict = _get_ai_dict(ai_config)
    score = 0
    
    lead_collection = ai_dict.get("lead_collection", [])
    active_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    standard_capture = {"name", "phone", "email"}
    profile_fields = [f for f in active_fields if f.lower() not in standard_capture]
    
    if lead_data.get("phone"):
        score += 30
    if lead_data.get("email"):
        score += 20
        
    for field in profile_fields:
        if lead_data.get(field):
            score += 15
            
    return min(100, score)

def lead_type_from_score(score: int, transcript: str = "") -> str:
    if SPAM_RE.search(transcript or ""):
        return "Dead"
    if HIGH_INTENT_RE.search(transcript or "") and score >= 5:
        return "Hot"
    if score >= 11:
        return "Hot"
    if score >= 6:
        return "Warm"
    return "Cold"

def first_name(name: str | None) -> str:
    return (name or "").strip().split()[0] if (name or "").strip() else ""

def has_full_name(name: str | None) -> bool:
    return len((name or "").strip().split()) >= 2

def profile_prefix(lead_data: dict, ai_config: Any) -> str:
    ai_dict = _get_ai_dict(ai_config)
    lead_collection = ai_dict.get("lead_collection", [])
    active_fields = [f.get("field_name", "") for f in lead_collection if f.get("is_active")]
    standard_capture = {"name", "phone", "email"}
    profile_fields = [f for f in active_fields if f.lower() not in standard_capture]
    parts = []
    for f in profile_fields:
        if lead_data.get(f):
            parts.append(f"[{f}: {lead_data[f]}]")
    if parts:
        return " " + " ".join(parts)
    return ""
