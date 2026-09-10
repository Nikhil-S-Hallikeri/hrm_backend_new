from __future__ import annotations

from uuid import uuid4

from app.chatbot import generate_answer
from app.contact_extractor import extract_contact_details
from app.conversation import normalize_lead_data, update_profile_memory
from app.lead_analyzer import analyze_lead
from app.schemas import ChatRequest, ChatResponse, LeadData
from app.storage import append_message, get_messages, get_or_create_session, update_session_analysis

from .configuration import resolve_ai_config
from .contracts import (
    PlatformMemoryPatch,
    PlatformMessageRequest,
    PlatformMessageResponse,
    PlatformValidationResult,
)


GREETING_NAMES: frozenset[str] = frozenset({
    "hey", "hello", "hi", "hey there", "hii", "hiii", "helo", "helo there",
})
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
    request: PlatformMessageRequest,
    extracted: dict,
    llm_extracted: dict | None = None,
) -> None:
    lead_data.update(normalize_lead_data(lead_data))

    form_data = request.metadata.get("form_data")
    if form_data and isinstance(form_data, dict):
        if form_data.get("name"):
            lead_data["name"] = form_data["name"]
        if form_data.get("phone"):
            lead_data["phone"] = form_data["phone"]
        if form_data.get("email"):
            lead_data["email"] = form_data["email"]

    for key in ("email", "phone"):
        explicit_value = getattr(request.identity, key, None)
        if explicit_value:
            lead_data[key] = explicit_value

    if llm_extracted:
        for key in ("email", "phone", "name"):
            if llm_extracted.get(key) and not lead_data.get(key):
                lead_data[key] = llm_extracted[key]
        if llm_extracted.get("interest") and not lead_data.get("interest"):
            lead_data["interest"] = llm_extracted["interest"]

    for key in ("email", "phone", "company"):
        if extracted.get(key) and not lead_data.get(key):
            lead_data[key] = extracted[key]

    if request.identity.name:
        lead_data["name"] = request.identity.name
    elif extracted.get("name"):
        message_lower = request.message.lower()
        has_contact = extracted.get("phone") or extracted.get("email")
        has_marker = any(marker in message_lower for marker in NAME_MARKERS)
        if has_contact or has_marker:
            if not lead_data.get("name") or _looks_like_greeting_name(lead_data.get("name")):
                lead_data["name"] = extracted["name"]

    if _looks_like_greeting_name(lead_data.get("name")):
        lead_data["name"] = None

    lead_data.update(
        update_profile_memory(
            lead_data,
            request.message,
            request.ai_config,
            llm_extracted=llm_extracted,
        )
    )


from .planner import plan_conversation_step
from .prompt_builder import build_dynamic_system_prompt
from .state_machine import StateContext


def _validation_result(analysis, answer: str, quick_replies: list[str]) -> PlatformValidationResult:
    confidence = 70
    if analysis.lead_score >= 8:
        confidence += 10
    if quick_replies:
        confidence += 5
    if "unable to assist" in answer.lower():
        confidence = 35

    should_escalate = confidence < 50 or bool(analysis.needs_callback)
    reason = None
    if confidence < 50:
        reason = "low_confidence"
    elif analysis.needs_callback:
        reason = "human_follow_up_requested"

    return PlatformValidationResult(
        confidence=min(confidence, 95),
        knowledge_hit=confidence >= 70,
        should_escalate=should_escalate,
        escalation_reason=reason,
    )


def process_platform_message(request: PlatformMessageRequest) -> PlatformMessageResponse:
    request.ai_config = resolve_ai_config(request.ai_config, tenant_id=request.tenant_id)

    session_id = request.session_id or request.channel.channel_session_id or uuid4().hex
    session = get_or_create_session(session_id)
    lead_data = session["lead_data"]

    # 1. State Context & Slot Extraction
    extracted = extract_contact_details(request.message)
    _merge_lead_data(lead_data, request, extracted, llm_extracted=None)
    append_message(session_id, "user", request.message)

    state = StateContext(
        collected_slots={k: v for k, v in lead_data.items() if v not in (None, "", [], {})},
        summary=session.get("summary", ""),
    )

    # 2. Conversation Planner Step
    plan = plan_conversation_step(request, state, request.ai_config)

    # Sync all updated slots from state machine/planner back into lead_data for SQLite persistence across turns
    for slot_k, slot_v in state.collected_slots.items():
        if slot_v not in (None, "", [], {}):
            lead_data[slot_k] = slot_v

    messages = get_messages(session_id)

    # 3. Dynamic Prompt Generation & LLM Answer
    if plan.override_answer:
        answer = plan.override_answer
    else:
        if request.ai_config:
            dynamic_system_prompt = build_dynamic_system_prompt(request.ai_config, state)
            request.ai_config.system_prompt = dynamic_system_prompt

        answer, llm_extracted = generate_answer(
            messages=messages,
            lead_data=lead_data,
            lead_status="Cold",
            ai_config=request.ai_config,
        )

        if llm_extracted:
            _merge_lead_data(lead_data, request, extracted, llm_extracted=llm_extracted)

    append_message(session_id, "assistant", answer)
    messages = get_messages(session_id)

    contact_collected = bool(lead_data.get("email") or lead_data.get("phone"))
    analysis = analyze_lead(messages, contact_collected, request.ai_config, lead_data)

    update_session_analysis(
        session_id=session_id,
        lead_data=lead_data,
        lead_status=analysis.lead_type,
        lead_score=analysis.lead_score,
        summary=analysis.summary,
    )

    quick_replies = plan.suggested_quick_replies or lead_data.get("quick_replies", [])
    validation = plan.validation or _validation_result(analysis, answer, quick_replies)

    return PlatformMessageResponse(
        session_id=session_id,
        tenant_id=request.tenant_id,
        agent_id=request.agent_id,
        answer=answer,
        lead_type=analysis.lead_type,
        lead_score=analysis.lead_score,
        needs_callback=analysis.needs_callback,
        next_action=analysis.next_action,
        summary=analysis.summary,
        lead_data=LeadData(**lead_data),
        quick_replies=quick_replies,
        jobs=plan.jobs,
        actions=plan.actions,
        memory_patch=PlatformMemoryPatch(
            profile={k: v for k, v in lead_data.items() if v not in (None, "", [], {})},
            session={
                "channel": request.channel.channel,
                "source_url": request.channel.source_url,
                "page_title": request.channel.page_title,
            },
        ),
        validation=validation,
    )


def platform_response_to_chat_response(response: PlatformMessageResponse) -> ChatResponse:
    return ChatResponse(
        answer=response.answer,
        session_id=response.session_id,
        lead_type=response.lead_type,
        lead_score=response.lead_score,
        needs_callback=response.needs_callback,
        next_action=response.next_action,
        interest=response.lead_data.interest,
        summary=response.summary,
        lead_data=response.lead_data,
        crm_pushed=False,
        quick_replies=response.quick_replies,
    )


def chat_request_to_platform(request: ChatRequest) -> PlatformMessageRequest:
    return PlatformMessageRequest(
        session_id=request.session_id,
        message=request.message,
        channel={"channel": "website"},
        identity={
            "name": request.name,
            "email": str(request.email) if request.email else None,
            "phone": request.phone,
        },
        ai_config=request.ai_config,
    )

