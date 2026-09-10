from __future__ import annotations

import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CHATBOT_URL = settings.CHATBOT_SERVICE_URL
TIMEOUT = getattr(settings, "CHATBOT_SERVICE_TIMEOUT", 30)


class ChatbotServiceError(Exception):
    pass


def _post(endpoint: str, payload: dict) -> dict:
    """Make a POST request to FastAPI chatbot service."""
    try:
        response = requests.post(
            f"{CHATBOT_URL}{endpoint}",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.error("Chatbot service timeout on %s", endpoint)
        raise ChatbotServiceError("Chatbot service timed out. Please try again.")
    except requests.ConnectionError:
        logger.error("Chatbot service unreachable at %s", CHATBOT_URL)
        raise ChatbotServiceError("Chatbot service is currently unavailable.")
    except requests.HTTPError as e:
        logger.error("Chatbot service HTTP error: %s — %s", e, e.response.text)
        raise ChatbotServiceError(f"Chatbot error: {e.response.status_code}")


def send_message(session_id: str, message: str, **contact_fields) -> dict:
    """
    Send a user message to FastAPI and return the full response.
    contact_fields: optional name, email, phone from Django auth context.
    """
    payload = {
        "session_id": session_id,
        "message": message,
        **{k: v for k, v in contact_fields.items() if v},
    }
    return _post("/chat", payload)


def _clean_identity(identity: dict | None) -> dict:
    """Remove empty or whitespace-only identity values before sending to FastAPI."""
    if not identity:
        return {}
    import re
    clean = {}
    for key, value in identity.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        elif key in {"name", "phone", "email", "whatsapp_number"}:
            value = str(value).strip()
            if not value:
                continue
        if key == "email" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
            continue
        clean[key] = value
    return clean


def send_aria_message(
    *,
    channel: str,
    channel_session_id: str,
    message: str,
    identity: dict | None = None,
    metadata: dict | None = None,
    ai_config: dict | None = None,
) -> dict:
    """
    Send a cross-channel message to FastAPI Aria Core.

    Django remains the WhatsApp transport layer; FastAPI owns the assistant
    brain, shared user profile, journey state, and lead memory.
    """
    payload = {
        "channel": channel,
        "channel_session_id": channel_session_id,
        "message": message,
        "identity": _clean_identity(identity),
        "metadata": metadata or {},
        "ai_config": ai_config,
    }
    return _post("/aria/message", payload)


def end_session(session_id: str) -> dict:
    """End a chat session and trigger CRM push in FastAPI."""
    return _post("/chat/end", {"session_id": session_id})


def get_transcript(session_id: str) -> dict | None:
    """Fetch full transcript from FastAPI."""
    try:
        response = requests.get(
            f"{CHATBOT_URL}/sessions/{session_id}/transcript",
            timeout=TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error("Failed to fetch transcript: %s", e)
        return None


def generate_session_id() -> str:
    return uuid.uuid4().hex
