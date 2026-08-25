import requests
from requests.exceptions import RequestException

from app.config import get_settings

def _normalize_payload(payload: dict) -> dict:
    return {
        "session_id": payload.get("session_id"),
        "name": payload.get("name"),
        "email": payload.get("email"),
        "phone": payload.get("phone"),
        "interest": payload.get("interest"),
        "course_title": payload.get("course_title"),
        "course_category": payload.get("course_category"),
        "lead_status": payload.get("lead_status") or "Cold",
        "lead_score": payload.get("lead_score") or 0,
        "needs_callback": bool(payload.get("needs_callback")),
        "summary": payload.get("summary") or "",
        "next_action": payload.get("next_action") or "",
        "messages": payload.get("messages") or [],
    }


def send_lead_to_crm(payload: dict) -> bool:
    if payload.get("status") == "lead_not_created":
        return False

    settings = get_settings()
    if (
        not settings.crm_api_url
        or "your-crm" in settings.crm_api_url
        or "example.com" in settings.crm_api_url
    ):
        if settings.debug:
            print("CRM_API_URL not configured; skipped CRM push.")
        return False

    headers = {"Content-Type": "application/json"}
    if settings.crm_api_token:
        headers["Authorization"] = f"Bearer {settings.crm_api_token}"

    try:
        response = requests.post(
            settings.crm_api_url,
            json=payload,
            headers=headers,
            timeout=settings.crm_timeout_seconds,
        )
        response.raise_for_status()
        return True
    except RequestException as exc:
        print(f"CRM push failed: {exc}")
        return False
    except Exception as exc:
        print(f"Unexpected CRM error: {exc}")
        return False
