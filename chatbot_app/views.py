from __future__ import annotations

import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .models import ChatSession
from .services import (
    ChatbotServiceError,
    end_session,
    generate_session_id,
    get_transcript,
    send_message,
)

logger = logging.getLogger(__name__)


def _sync_session_to_django(django_session: ChatSession, fastapi_response: dict) -> None:
    """Mirror lead data from FastAPI response into Django model."""
    lead_data = fastapi_response.get("lead_data") or {}
    django_session.lead_type = fastapi_response.get("lead_type", "Cold")
    django_session.lead_score = fastapi_response.get("lead_score", 0)
    django_session.summary = fastapi_response.get("summary", "")
    django_session.lead_name = lead_data.get("name") or ""
    django_session.lead_email = lead_data.get("email") or ""
    django_session.lead_phone = lead_data.get("phone") or ""
    django_session.lead_interest = lead_data.get("interest") or ""
    django_session.save()


@method_decorator(csrf_exempt, name="dispatch")
class ChatView(View):
    """Handle chat messages — creates/continues a session."""

    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        message = (body.get("message") or "").strip()
        if not message:
            return JsonResponse({"error": "message is required"}, status=400)
        if len(message) > 2000:
            return JsonResponse({"error": "Message too long"}, status=400)

        # Get or create session_id
        session_id = body.get("session_id")
        if not session_id:
            session_id = generate_session_id()

        # Get or create Django ChatSession record
        django_session, _ = ChatSession.objects.get_or_create(
            fastapi_session_id=session_id,
            defaults={
                "user": request.user if request.user.is_authenticated else None,
            },
        )

        # Pass known contact info from Django auth if available
        contact_fields = {}
        if request.user.is_authenticated:
            contact_fields["email"] = getattr(request.user, "email", None)
            # Add name if your user model has it
            full_name = getattr(request.user, "get_full_name", lambda: None)()
            if full_name:
                contact_fields["name"] = full_name

        try:
            fastapi_response = send_message(session_id, message, **contact_fields)
        except ChatbotServiceError as e:
            return JsonResponse({"error": str(e)}, status=503)

        # Mirror lead data into Django
        _sync_session_to_django(django_session, fastapi_response)

        return JsonResponse(fastapi_response)


@method_decorator(csrf_exempt, name="dispatch")
class EndChatView(View):
    """End a chat session and push to CRM."""

    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        session_id = body.get("session_id")
        if not session_id:
            return JsonResponse({"error": "session_id is required"}, status=400)

        try:
            django_session = ChatSession.objects.get(fastapi_session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)

        try:
            fastapi_response = end_session(session_id)
        except ChatbotServiceError as e:
            return JsonResponse({"error": str(e)}, status=503)

        django_session.status = "ended"
        _sync_session_to_django(django_session, fastapi_response)

        return JsonResponse(fastapi_response)


class TranscriptView(View):
    """Fetch full transcript for a session."""

    def get(self, request, session_id: str):
        try:
            ChatSession.objects.get(fastapi_session_id=session_id)
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)

        data = get_transcript(session_id)
        if not data:
            return JsonResponse({"error": "Transcript unavailable"}, status=404)

        return JsonResponse(data)


class SessionListView(View):
    """List all chat sessions for the current user (or all for admin)."""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        if request.user.is_staff:
            sessions = ChatSession.objects.all()[:50]
        else:
            sessions = ChatSession.objects.filter(user=request.user)

        return JsonResponse({
            "sessions": [
                {
                    "session_id": s.fastapi_session_id,
                    "status": s.status,
                    "lead_type": s.lead_type,
                    "lead_score": s.lead_score,
                    "lead_name": s.lead_name,
                    "lead_interest": s.lead_interest,
                    "summary": s.summary,
                    "created_at": s.created_at.isoformat(),
                }
                for s in sessions
            ]
        })