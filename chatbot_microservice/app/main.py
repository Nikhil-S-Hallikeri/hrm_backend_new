## Improved Version

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.aria_core import get_user_snapshot, handle_aria_message, init_aria_storage
from app.chatbot import generate_answer
from app.config import get_settings
from app.contact_extractor import extract_contact_details
from app.conversation import normalize_lead_data, update_profile_memory
from app.crm import send_lead_to_crm
from app.crm_payload import build_crm_payload  # ← moved out of main.py
_build_crm_payload = build_crm_payload  # Backward-compatible test/import alias
from app.ingestion.build_knowledge_base import build_local_knowledge_file
from app.lead_analyzer import analyze_lead
from app.platform.contracts import PlatformMessageRequest, PlatformMessageResponse
from app.platform.orchestrator import (
    chat_request_to_platform,
    platform_response_to_chat_response,
    process_platform_message,
)
from app.schemas import (
    ChatRequest,
    ChatResponse,
    EndChatRequest,
    EndChatResponse,
    AriaMessageRequest,
    AriaMessageResponse,
    KnowledgeRebuildResponse,
    LeadData,
    TranscriptResponse,
    PromptGenerateRequest,
    PromptGenerateResponse,
    PromptImproveRequest,
    PromptImproveResponse,
)
from app.storage import (
    append_message,
    cleanup_old_sessions,
    get_messages,
    get_or_create_session,
    get_session,
    init_storage,
    mark_session_ended,
    transcript,
    update_session_analysis,
)

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 2000

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_storage()
init_aria_storage()
cleanup_old_sessions()

# Greetings & common phrases that should never be stored as a visitor's name
GREETING_NAMES: frozenset[str] = frozenset({
    "hey", "hello", "hi", "hey there", "hii", "hiii", "helo", "helo there",
    "how you doing", "hello how you doing", "how are you", "what's your name",
    "whats your name", "who are you", "what section", "what can you help",
    "good morning", "good evening", "good afternoon"
})

# Name extraction markers — must match what contact_extractor supports
NAME_MARKERS = ("my name is", "i am", "i'm", "this is", "name:", "myself", "call me")


def _looks_like_greeting_name(value: str | None) -> bool:
    if not value:
        return True
    val = value.strip().lower()
    if val in GREETING_NAMES:
        return True
    if any(val.startswith(prefix) for prefix in ("hello", "hi ", "hey", "how are", "how you", "what ", "who ", "good morning", "good evening", "good afternoon", "tell me")):
        return True
    if len(val) > 25:
        return True
    return False


def _merge_lead_data(
    lead_data: dict,
    request: ChatRequest,
    extracted: dict,
    llm_extracted: dict | None = None,
) -> None:
    """
    Merge all contact signals into lead_data in priority order:
    1. Explicit request fields (highest trust — set by frontend)
    2. LLM answer-extracted fields (high trust — parsed from full context)
    3. Regex-extracted fields from message (medium trust)
    4. Profile memory update (lowest — regex + LLM profile extraction)
    """
    lead_data.update(normalize_lead_data(lead_data))

    # Priority 1: explicit fields from request payload
    for key in ("email", "phone"):
        explicit_value = getattr(request, key, None)
        if explicit_value:
            lead_data[key] = explicit_value

    # Priority 2: LLM answer-extracted contact fields
    if llm_extracted:
        for key in ("email", "phone", "name"):
            if llm_extracted.get(key) and not lead_data.get(key):
                lead_data[key] = llm_extracted[key]
        if llm_extracted.get("interest") and not lead_data.get("interest"):
            lead_data["interest"] = llm_extracted["interest"]

    # Priority 3: regex-extracted contact fields from message
    for key in ("email", "phone"):
        if extracted.get(key) and not lead_data.get(key):
            lead_data[key] = extracted[key]

    # Name extraction — explicit request field wins
    if request.name:
        lead_data["name"] = request.name
    elif extracted.get("name"):
        message_lower = request.message.lower()
        # Accept regex-extracted name if:
        # - contact info was also found (strong signal it's a form-style message), OR
        # - message contains an explicit self-identification marker
        has_contact = extracted.get("phone") or extracted.get("email")
        has_marker = any(marker in message_lower for marker in NAME_MARKERS)
        if has_contact or has_marker:
            if not lead_data.get("name") or _looks_like_greeting_name(lead_data.get("name")):
                lead_data["name"] = extracted["name"]

    # Clear out any greeting word accidentally stored as a name
    if _looks_like_greeting_name(lead_data.get("name")):
        lead_data["name"] = None

    # Priority 4: profile memory (status, education, domain, goal, interest)
    lead_data.update(
        update_profile_memory(lead_data, request.message, request.ai_config, llm_extracted=llm_extracted)
    )

    # Check for metadata profile updates passed from frontend
    meta = getattr(request, "metadata", {}) or {}
    if isinstance(meta, dict) and "profile_updates" in meta:
        updates = meta["profile_updates"]
        if isinstance(updates, dict):
            for k, v in updates.items():
                if v:
                    lead_data[k] = v

    if isinstance(meta, dict) and "profiling_answers" in meta:
        answers = meta["profiling_answers"]
        if isinstance(answers, dict):
            existing = lead_data.get("profiling_answers") or {}
            existing.update(answers)
            lead_data["profiling_answers"] = existing

    # WhatsApp Welcome Template trigger when phone number is freshly captured
    phone_val = lead_data.get("phone")
    if phone_val and not lead_data.get("whatsapp_welcome_sent"):
        _send_whatsapp_welcome_template(phone_val, lead_data.get("name"))
        lead_data["whatsapp_welcome_sent"] = True


def _send_whatsapp_welcome_template(phone: str, name: str | None = None) -> None:
    try:
        import requests
        payload = {
            "phone_number": phone,
            "template_name": "welcome_template",
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": name or "Valued Student"}]
                }
            ]
        }
        saas_url = getattr(settings, "saas_backend_url", "http://localhost:8001")
        requests.post(f"{saas_url}/whatsapp/send-template/", json=payload, timeout=3)
        logger.info(f"WhatsApp welcome template dispatched to {phone}")
    except Exception as exc:
        logger.warning(f"Could not dispatch WhatsApp welcome template to {phone}: {exc}")



def _session_response(
    session_id: str,
    session: dict,
    analysis,
    answer: str,
    crm_pushed: bool = False,
) -> ChatResponse:
    lead_data = session["lead_data"]
    return ChatResponse(
        answer=answer,
        session_id=session_id,
        lead_type=analysis.lead_type,
        lead_score=analysis.lead_score,
        needs_callback=analysis.needs_callback,
        next_action=analysis.next_action,
        interest=lead_data.get("interest"),
        summary=analysis.summary,
        lead_data=LeadData(**lead_data),
        crm_pushed=crm_pushed,
        quick_replies=lead_data.get("quick_replies", []),
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed."
        )

    platform_response = process_platform_message(chat_request_to_platform(request))
    return platform_response_to_chat_response(platform_response)


@app.post("/platform/message", response_model=PlatformMessageResponse)
def platform_message(request: PlatformMessageRequest):
    """
    Headless enterprise conversation endpoint.

    Channel connectors should call this endpoint with normalized input. The AI
    core remains channel-agnostic and returns a response plus memory,
    validation, and action metadata for the connector to deliver.
    """
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
        )
    return process_platform_message(request)


@app.post("/aria/message", response_model=AriaMessageResponse)
def aria_message(request: AriaMessageRequest):
    """
    Unified Aria Core endpoint for website and WhatsApp channel adapters.

    This endpoint resolves the person first, then uses the existing Aria
    conversation engine against user-level profile and journey memory.
    """
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed.",
        )
    return handle_aria_message(request)


@app.get("/aria/users/{aria_user_id}")
def aria_user(aria_user_id: str):
    snapshot = get_user_snapshot(aria_user_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Aria user not found")
    return snapshot


@app.post("/chat/end", response_model=EndChatResponse)
def end_chat(request: EndChatRequest):
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = get_messages(request.session_id)
    lead_data = session["lead_data"]
    contact_collected = bool(lead_data.get("email") or lead_data.get("phone"))
    analysis = analyze_lead(messages, contact_collected, request.ai_config, lead_data)

    payload = build_crm_payload(request.session_id, session, messages, analysis)
    crm_pushed = send_lead_to_crm(payload)
    mark_session_ended(request.session_id, crm_pushed=crm_pushed, summary=analysis.summary)

    return EndChatResponse(
        session_id=request.session_id,
        crm_pushed=crm_pushed,
        lead_type=analysis.lead_type,
        lead_score=analysis.lead_score,
        summary=analysis.summary,
        lead_data=LeadData(**lead_data),
    )


@app.get("/crm/preview/{session_id}")
def crm_preview(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = get_messages(session_id)
    contact_collected = bool(session["lead_data"].get("email") or session["lead_data"].get("phone"))
    analysis = analyze_lead(messages, contact_collected, {}, session["lead_data"])
    return build_crm_payload(session_id, session, messages, analysis)


@app.get("/sessions/{session_id}/transcript", response_model=TranscriptResponse)
def get_transcript(session_id: str):
    data = transcript(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return TranscriptResponse(
        session_id=session_id,
        lead_type=data.get("lead_status", "Cold"),
        lead_score=data.get("lead_score", 0),
        summary=data.get("summary") or "",
        lead_data=LeadData(**data.get("lead_data", {})),
        messages=data.get("messages", []),
    )


def _verify_ingestion_token(x_ingestion_token: str | None) -> None:
    if settings.ingestion_api_token and x_ingestion_token != settings.ingestion_api_token:
        raise HTTPException(status_code=401, detail="Invalid ingestion token")


@app.post("/knowledge/rebuild", response_model=KnowledgeRebuildResponse)
def rebuild_knowledge_base_endpoint(
    x_ingestion_token: str | None = Header(default=None),
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    faq_q: str | None = Form(default=None),
    faq_a: str | None = Form(default=None),
):
    _verify_ingestion_token(x_ingestion_token)
    try:
        from app.ingestion.build_knowledge_base import build_local_knowledge_file, append_knowledge_source
        
        has_params = file is not None or url is not None or faq_q is not None
        if has_params:
            file_bytes = None
            file_name = None
            if file:
                file_bytes = file.file.read()
                file_name = file.filename
                
            knowledge_file = append_knowledge_source(
                file_name=file_name,
                file_bytes=file_bytes,
                url=url,
                faq_q=faq_q,
                faq_a=faq_a
            )
        else:
            knowledge_file = build_local_knowledge_file()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Knowledge rebuild failed: {exc}"
        ) from exc

    return KnowledgeRebuildResponse(
        status="completed",
        message=(
            "Knowledge base updated."
            if has_params
            else "Knowledge base rebuilt from scratch."
        ),
        crawl_website=settings.crawl_website,
        knowledge_file=str(knowledge_file),
        file_size_bytes=knowledge_file.stat().st_size,
    )


@app.get("/knowledge/status", response_model=KnowledgeRebuildResponse)
def knowledge_status():
    from app.ingestion.build_knowledge_base import KNOWLEDGE_FILE

    if not KNOWLEDGE_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Knowledge file has not been built yet"
        )

    return KnowledgeRebuildResponse(
        status="ready",
        message="Knowledge file exists.",
        crawl_website=settings.crawl_website,
        knowledge_file=str(KNOWLEDGE_FILE),
        file_size_bytes=KNOWLEDGE_FILE.stat().st_size,
    )

@app.post("/ai-prompt/generate", response_model=PromptGenerateResponse)
def generate_prompt_endpoint(request: PromptGenerateRequest):
    from app.llm_router import generate_llm_response
    prompt_instruction = [
        {
            "role": "system",
            "content": (
                "You are an expert prompt engineer. Generate a professional, high-converting "
                "AI assistant system prompt for the business. "
                "Do NOT output any markdown tags (like ```) or conversational commentary. "
                "Directly return only the system prompt text."
            )
        },
        {
            "role": "user",
            "content": f"Generate a system prompt for business '{request.business_name}' with a '{request.tone}' tone."
        }
    ]
    try:
        generated = generate_llm_response(prompt_instruction, temperature=0.6, max_tokens=400)
        return PromptGenerateResponse(generated_prompt=generated.strip())
    except Exception as exc:
        fallback = f"You are the official AI Assistant for {request.business_name}. Your tone is {request.tone}. Answer politely and concisely."
        return PromptGenerateResponse(generated_prompt=fallback)

@app.post("/ai-prompt/improve", response_model=PromptImproveResponse)
def improve_prompt_endpoint(request: PromptImproveRequest):
    from app.llm_router import generate_llm_response
    prompt_instruction = [
        {
            "role": "system",
            "content": (
                "You are an expert prompt engineer. Improve and optimize the following AI system prompt "
                "for clarity, structure, and effectiveness. Preserve all original rules and placeholders. "
                "Do NOT wrap the response in markdown blocks or output explanations. Return ONLY the improved system prompt text."
            )
        },
        {
            "role": "user",
            "content": f"Improve this system prompt:\n\n{request.prompt}"
        }
    ]
    try:
        improved = generate_llm_response(prompt_instruction, temperature=0.5, max_tokens=500)
        return PromptImproveResponse(improved_prompt=improved.strip())
    except Exception as exc:
        fallback = request.prompt + "\n\n(Improved: Ensure you never deviate from the persona and always remain helpful.)"
        return PromptImproveResponse(improved_prompt=fallback)
