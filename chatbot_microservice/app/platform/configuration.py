from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from app.schemas import AIConfig


def _env_list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


@lru_cache
def get_default_ai_config() -> AIConfig:
    """Default configurable agent used when an admin config is not supplied.

    This is intentionally environment-driven so the platform can be deployed for
    any tenant without changing source code. Existing callers may still pass a
    full AIConfig payload from the admin panel and override every field.
    """

    return AIConfig(
        assistant_name=os.getenv("DEFAULT_ASSISTANT_NAME", "AI Assistant"),
        business_name=os.getenv("DEFAULT_BUSINESS_NAME", "Company"),
        personality=os.getenv("DEFAULT_AI_PERSONALITY", "Support"),
        tone=os.getenv("DEFAULT_AI_TONE", "Friendly and Professional"),
        primary_language=os.getenv("DEFAULT_AI_LANGUAGE", "en"),
        prompt=os.getenv("DEFAULT_BUSINESS_PROMPT", ""),
        system_prompt=os.getenv("DEFAULT_SYSTEM_PROMPT", ""),
        greeting_message=os.getenv("DEFAULT_GREETING_MESSAGE", "Hi, how can I help you today?"),
        quick_replies=_env_list("DEFAULT_QUICK_REPLIES"),
        conversation_behaviours=[
            {"rule": rule, "is_active": True}
            for rule in _env_list("DEFAULT_CONVERSATION_RULES")
        ],
        lead_collection=[
            {"field_name": field, "is_active": True}
            for field in _env_list("DEFAULT_LEAD_FIELDS")
        ],
        faqs=[],
        websites=[
            {"url": url}
            for url in _env_list("DEFAULT_KNOWLEDGE_URLS")
        ],
    )


def fetch_tenant_ai_config(tenant_id: str | None) -> AIConfig | None:
    if not tenant_id:
        return None
    import requests
    saas_backend_url = os.getenv("SAAS_BACKEND_URL", "http://localhost:8001").rstrip("/")
    try:
        resp = requests.get(f"{saas_backend_url}/whatsapp/ai-config/?tenant={tenant_id}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return AIConfig(
                assistant_name=data.get("assistant_name") or os.getenv("DEFAULT_ASSISTANT_NAME", "AI Assistant"),
                business_name=data.get("business_name") or os.getenv("DEFAULT_BUSINESS_NAME", "Enterprise"),
                personality=data.get("personality") or "Support",
                tone=data.get("tone") or "Friendly and Professional",
                primary_language=data.get("primary_language") or "en",
                prompt=data.get("prompt") or "",
                system_prompt=data.get("system_prompt") or "",
                greeting_message=data.get("greeting_message") or "Hi, how can I help you today?",
                quick_replies=data.get("quick_replies") or [],
                conversation_behaviours=[
                    {"rule": b.get("name") or b.get("rule") or "", "is_active": b.get("active", b.get("is_active", True))}
                    for b in data.get("conversation_behaviours", [])
                ],
                lead_collection=[
                    {"field_name": f.get("name") or f.get("field_name") or "", "is_active": f.get("active", f.get("is_active", True))}
                    for f in data.get("lead_collection", [])
                ],
                faqs=data.get("faqs") or [],
                websites=data.get("websites") or [],
                categories=data.get("categories") or [],
                domain_keywords=data.get("domain_keywords") or {},
                out_of_scope_message=data.get("out_of_scope_message"),
                registration_url_template=data.get("registration_url_template"),
                catalog_api_url=data.get("catalog_api_url"),
                llm_provider=data.get("llm_provider") or "openai",
                model_name=data.get("model_name") or "gpt-4o-mini",
                api_key=data.get("api_key") or None,
            )
    except Exception as exc:
        print(f"Failed to fetch dynamic AI Config for tenant '{tenant_id}':", exc)
    return None


def resolve_ai_config(ai_config: AIConfig | dict[str, Any] | None, tenant_id: str | None = None) -> AIConfig:
    if isinstance(ai_config, AIConfig):
        return ai_config
    if isinstance(ai_config, dict):
        return AIConfig(**ai_config)
    
    dynamic_cfg = fetch_tenant_ai_config(tenant_id)
    if dynamic_cfg:
        return dynamic_cfg

    if tenant_id:
        import json
        from pathlib import Path
        clean_tenant = os.path.basename(tenant_id.strip())
        tenant_file = Path(__file__).resolve().parent.parent.parent / "data" / "tenants" / f"{clean_tenant}.json"
        if tenant_file.exists():
            try:
                data = json.loads(tenant_file.read_text(encoding="utf-8"))
                return AIConfig(**data)
            except Exception as err:
                print(f"Failed to load tenant json config for {tenant_id}:", err)

    return get_default_ai_config()

