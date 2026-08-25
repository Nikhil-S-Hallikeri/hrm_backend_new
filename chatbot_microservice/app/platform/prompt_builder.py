from __future__ import annotations

from typing import Any

from app.schemas import AIConfig
from .state_machine import StateContext


def build_dynamic_system_prompt(
    ai_config: AIConfig,
    state: StateContext,
    grounding_docs: list[str] | None = None,
) -> str:
    """Assembles a enterprise dynamic system prompt including brand voice, tenant instructions,
    state/slots, and grounding context."""

    assistant_name = getattr(ai_config, "assistant_name", None) or "AI Assistant"
    business_name = getattr(ai_config, "business_name", None) or "Enterprise"
    personality = getattr(ai_config, "personality", None) or getattr(ai_config, "ai_personality", None) or "Professional, helpful, and concise."
    tone = getattr(ai_config, "tone", None) or getattr(ai_config, "ai_tone", None) or "Professional"

    sections: list[str] = []

    # 1. Identity & Brand Voice
    sections.append(
        f"You are {assistant_name}, the AI representative for {business_name}.\n"
        f"Tone of voice: {tone}.\n"
        f"Personality: {personality}"
    )

    # 2. Base Instructions & Business Prompt
    business_prompt = getattr(ai_config, "prompt", None) or getattr(ai_config, "business_prompt", None)
    system_prompt = getattr(ai_config, "system_prompt", None)
    if business_prompt:
        sections.append(f"CORE BUSINESS GOALS & CONTEXT:\n{business_prompt}")
    if system_prompt:
        sections.append(f"CUSTOM INSTRUCTIONS:\n{system_prompt}")

    # 3. Grounding / Knowledge Base Context
    if grounding_docs:
        formatted_docs = "\n---\n".join(grounding_docs)
        sections.append(
            "VERIFIED KNOWLEDGE BASE CONTEXT (Use strictly for answers):\n"
            f"{formatted_docs}\n"
            "Rule: If the information is not present in the context above or user state, state that you cannot verify it and offer escalation."
        )

    # 4. Conversation State & Memory Context
    state_lines: list[str] = []
    if state.collected_slots:
        slots_str = ", ".join(f"{k}='{v}'" for k, v in state.collected_slots.items() if v)
        state_lines.append(f"Known User Information: {slots_str}")
    if state.summary:
        state_lines.append(f"Conversation Summary So Far: {state.summary}")
    if state.workflow_stack:
        state_lines.append(f"Interrupted Flow On Hold: {state.workflow_stack[-1].workflow_id}")

    if state_lines:
        sections.append("ACTIVE CONVERSATION STATE:\n" + "\n".join(state_lines))

    # 5. Output & Guardrail Rules
    rules = [
        "1. Never repeat questions if the user has already supplied the information.",
        "2. Keep responses structured, concise, and focused on helping the user.",
        "3. If the user changes topic mid-flow, answer their topic immediately and offer to resume the previous task.",
        f"4. STRICT BUSINESS SCOPE: You are exclusively an AI Assistant for {business_name}.",
        f"5. NEVER offer, promise, or attempt to fulfill out-of-scope requests outside the services offered by {business_name}.",
        f"6. If an out-of-scope request is sent, politely state that you specialize in {business_name} services and ask how you can assist them with their needs. DO NOT ask for contact details for out-of-scope requests.",
    ]
    extra_rules = getattr(ai_config, "conversation_behaviours", None) or getattr(ai_config, "conversation_rules", None) or []
    if extra_rules:
        rule_texts = [r.rule if hasattr(r, "rule") else str(r) for r in extra_rules]
        rules.extend([f"{idx+7}. {r}" for idx, r in enumerate(rule_texts)])

    sections.append("GUARDRAIL RULES:\n" + "\n".join(rules))

    return "\n\n".join(sections)
