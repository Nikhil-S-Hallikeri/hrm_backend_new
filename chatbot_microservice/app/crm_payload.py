
from __future__ import annotations

import json
import logging

from app.contact_extractor import extract_contact_details
from app.llm_router import generate_llm_response

logger = logging.getLogger(__name__)

B2B_SIGNALS = frozenset({
    "business owner", "entrepreneur", "founder", "company representative",
    "invest through company", "company account", "pvt ltd", "llp",
})


def _detect_b2b(lead_data: dict, transcript_lower: str) -> bool:
    """Check B2B signals in lead_data AND full transcript."""
    status = (lead_data.get("current_status") or "").lower()
    # Word-boundary safe check on status
    for signal in ("business owner", "entrepreneur", "founder"):
        if signal in status:
            return True
    # Broader transcript check for B2B language
    return any(signal in transcript_lower for signal in B2B_SIGNALS)

def build_crm_payload(
    session_id: str,
    session: dict,
    messages: list[dict],
    analysis=None,
) -> dict:
    lead_data = session.get("lead_data", {})
    name = lead_data.get("name")
    phone = lead_data.get("phone")
    email = lead_data.get("email")

    # Fallback: scan conversation history for contact details
    if not name or not phone or not email:
        for msg in messages:
            if msg.get("role") == "user":
                extracted = extract_contact_details(msg.get("content", ""))
                if not name and extracted.get("name"):
                    name = extracted["name"]
                if not phone and extracted.get("phone"):
                    phone = extracted["phone"]
                if not email and extracted.get("email"):
                    email = extracted["email"]

    if not name or not phone:
        return {
            "status": "lead_not_created",
            "reason": "Mandatory fields missing",
        }

    transcript_text = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in messages
    )
    transcript_lower = transcript_text.lower()
    investment_interest = lead_data.get("course_title") or lead_data.get("interest")
    is_b2b = _detect_b2b(lead_data, transcript_lower)

    # Attempt LLM-based payload enrichment
    try:
        payload = _llm_build_payload(
            session_id=session_id,
            name=name,
            phone=phone,
            email=email,
            transcript_text=transcript_text,
            is_b2b=is_b2b,
        )
        if payload:
            # Always enforce ground-truth fields — never trust LLM to set these
            payload["name"] = name
            payload["contact_number"] = phone
            payload["lead_id"] = session_id
            payload["investment_amount"] = lead_data.get("investment_amount")
            payload["investment_timeline"] = lead_data.get("investment_timeline")
            payload["return_preference"] = lead_data.get("return_preference")
            payload["investment_mode"] = lead_data.get("investment_mode")
            payload["preferred_callback_time"] = lead_data.get("callback_time")
            payload["course_enquired"] = course
            payload["preferred_course"] = lead_data.get("course_title") or lead_data.get("interest")
            return payload
    except Exception as exc:
        logger.warning("LLM CRM payload generation failed: %s — using fallback", exc)

    # Programmatic fallback
    return _fallback_payload(
        session_id=session_id,
        name=name,
        phone=phone,
        email=email,
        course=investment_interest,
        lead_data=lead_data,
        is_b2b=is_b2b,
    )


def _llm_build_payload(
    session_id: str,
    name: str,
    phone: str,
    email: str | None,
    transcript_text: str,
    is_b2b: bool,
) -> dict | None:
    lead_type_label = "B2B" if is_b2b else "B2C"

    system_prompt = f"""You are an AI assistant that generates CRM lead payloads from chat transcripts.

The lead type is: {lead_type_label}

Rules:
- Populate every field you can confidently extract from the transcript.
- If a field is not mentioned, set it to null. Never guess or invent values.
- Return ONLY valid JSON. No markdown, no explanation, no code fences.
- These fields are already known and must appear exactly as given:
  - lead_id: "{session_id}"
  - name: "{name}"
  - contact_number: "{phone}"
  - email: {json.dumps(email)}
  - source: "JPM Property Flipping AI Chatbot"
  - priority: "High"
  - level_lead: "newlead"
"""

    content = generate_llm_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transcript:\n{transcript_text}"},
        ],
        temperature=0.0,
        max_tokens=1000,
    )

    if not content:
        return None

    # Strip markdown fences if present
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines and lines[-1].startswith("```") else lines
        cleaned = "\n".join(lines).strip()

    return json.loads(cleaned)


def _fallback_payload(
    session_id: str,
    name: str,
    phone: str,
    email: str | None,
    course: str | None,
    lead_data: dict,
    is_b2b: bool,
) -> dict:
    base = {
        "lead_id": session_id,
        "name": name,
        "contact_number": phone,
        "email": email,
        "source": "JPM Property Flipping AI Chatbot",
        "priority": "High",
        "level_lead": "newlead",
        # CRM field names are retained for compatibility with the existing integration.
        "course_enquired": course,
        "preferred_course": lead_data.get("course_title") or lead_data.get("interest"),
        "investment_amount": lead_data.get("investment_amount"),
        "investment_timeline": lead_data.get("investment_timeline"),
        "return_preference": lead_data.get("return_preference"),
        "investment_mode": lead_data.get("investment_mode"),
        "preferred_callback_time": lead_data.get("callback_time"),
    }

    if is_b2b:
        return {
            **base,
            "designation": None,
            "whatsapp": None,
            "company_name": None,
            "company_website": None,
            "company_field": None,
            "company_contact_number": None,
            "gst_number": None,
            "door_number": None,
            "street_name": None,
            "area": None,
            "city": None,
            "state": None,
            "pincode": None,
            "mode_of_training": None,
            "num_candidates_trained": None,
            "place_of_training": None,
            "preferred_duration_per_day": None,
            "noofdays": None,
            "tentative_batch_start_date": None,
            "cost": None,
            "purpose": None,
            "technology": None,
            "description": None,
            "remarks": None,
        }

    return {
        **base,
        "gender": None,
        "whatsapp": None,
        "othersource": None,
        "enquiry_location": None,
        "remarks": None,
        "othercourseenquired": None,
        "preferred_batch_type": None,
        "preferred_class_type": None,
        "upcoming_batch_id": None,
        "expected_registration_date": None,
        "tentative_batch_start_date": None,
        "bachelor_degree": None,
        "bachelor_specification": None,
        "percentage_bachelor": None,
        "master_degree": None,
        "master_specification": None,
        "percentage_master": None,
        "technical_skills_known": None,
        "soft_skills_known": None,
        "contacted_person_name": None,
        "contacted_person_number": None,
    }
