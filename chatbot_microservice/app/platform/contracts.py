from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import AIConfig, LeadData


ChannelType = Literal[
    "website",
    "whatsapp",
    "instagram",
    "messenger",
    "telegram",
    "slack",
    "teams",
    "crm",
    "mobile",
    "voice",
    "api",
]


class ChannelContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    channel: ChannelType = "api"
    channel_session_id: str | None = None
    source_url: str | None = None
    page_title: str | None = None
    locale: str | None = None
    timezone: str | None = None
    user_agent: str | None = None


class VisitorIdentity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    external_user_id: str | None = None


class PlatformMessageRequest(BaseModel):
    """Channel-neutral input accepted by the enterprise conversation platform."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: str = "default"
    brand_id: str | None = None
    agent_id: str = "default"
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)
    channel: ChannelContext = Field(default_factory=ChannelContext)
    identity: VisitorIdentity = Field(default_factory=VisitorIdentity)
    ai_config: AIConfig | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformAction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    required: bool = False


class PlatformMemoryPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile: dict[str, Any] = Field(default_factory=dict)
    facts: list[dict[str, Any]] = Field(default_factory=list)
    session: dict[str, Any] = Field(default_factory=dict)


class PlatformValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    confidence: int = Field(default=70, ge=0, le=100)
    knowledge_hit: bool = False
    citations: list[dict[str, Any]] = Field(default_factory=list)
    should_escalate: bool = False
    escalation_reason: str | None = None


class PlatformMessageResponse(BaseModel):
    """Channel-neutral output returned by the platform core."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    tenant_id: str
    agent_id: str
    answer: str
    lead_type: str = "Cold"
    lead_score: int = Field(default=0, ge=0, le=100)
    needs_callback: bool = False
    next_action: str | None = None
    summary: str = ""
    lead_data: LeadData
    quick_replies: list[str] = Field(default_factory=list)
    jobs: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[PlatformAction] = Field(default_factory=list)
    memory_patch: PlatformMemoryPatch = Field(default_factory=PlatformMemoryPatch)
    validation: PlatformValidationResult = Field(default_factory=PlatformValidationResult)

