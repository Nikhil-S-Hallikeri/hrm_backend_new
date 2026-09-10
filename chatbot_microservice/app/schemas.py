from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ── Shared literals ────────────────────────────────────────────────────────────

LeadType = Literal["Hot", "Warm", "Cold", "Dead"]

CurrentStatus = Literal[
    "New Investor",
    "Experienced Investor",
    "NRI Investor",
    "Business Owner",
]

ConversationStateType = Literal[
    "DISCOVERY",
    "PROFILE_COLLECTION",
    "INTEREST_COLLECTION",
    "RECOMMENDATION",
    "COURSE_DISCUSSION",
    "LEAD_CAPTURE",
    "CALLBACK_REQUEST",
    "QUALIFIED",
]

Urgency = Literal["low", "medium", "high"]
BudgetSignal = Literal["unknown", "concern"]

# Max lead score your scoring function can produce — used for range validation
MAX_LEAD_SCORE = 100


# ── Sub-models ─────────────────────────────────────────────────────────────────

class CourseRecommendation(BaseModel):
    """A single course recommendation returned by the bot."""
    model_config = ConfigDict(extra="ignore")

    title: str
    category: str | None = None


class ChatMessage(BaseModel):
    """A single turn in the conversation transcript."""
    model_config = ConfigDict(extra="ignore")

    role: Literal["user", "assistant", "system"]
    content: str


# ── Request models ─────────────────────────────────────────────────────────────

class Behaviour(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rule: str
    is_active: bool = True

class LeadField(BaseModel):
    model_config = ConfigDict(extra="ignore")
    field_name: str
    is_active: bool = True

class AutoReplyRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    keyword: str
    reply: str
    active: bool = True

class WebsiteSource(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str

class FAQSource(BaseModel):
    model_config = ConfigDict(extra="ignore")
    q: str
    a: str | None = None

class AIConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    assistant_name: str = "Assistant"
    business_name: str = "Company"
    personality: str = "Support"
    tone: str = "Friendly and Professional"
    primary_language: str = "en"
    prompt: str = ""
    system_prompt: str = ""
    conversation_behaviours: list[Behaviour] = Field(default_factory=list)
    lead_collection: list[LeadField] = Field(default_factory=list)
    auto_replies: list[AutoReplyRule] = Field(default_factory=list)
    websites: list[WebsiteSource] = Field(default_factory=list)
    faqs: list[FAQSource] = Field(default_factory=list)
    categories: list[dict] = Field(default_factory=list)
    domain_keywords: dict[str, list[str]] = Field(default_factory=dict)
    out_of_scope_message: str | None = None
    registration_url_template: str | None = None
    catalog_api_url: str | None = None
    context_window_size: int = 15
    fallback_rule: str = "transfer"
    confidence_threshold: int = 70
    human_handoff_alert: bool = True
    llm_provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    api_key: str | None = None
    greeting_message: str = "Hi, how can I help you today?"
    quick_replies: list[str] = Field(default_factory=list)
    flow_definitions: dict = Field(default_factory=dict)

class ChatRequest(BaseModel):
    """Incoming chat message from the visitor."""
    model_config = ConfigDict(extra="ignore")

    ai_config: AIConfig | None = None
    # Keep max_length in sync with MAX_MESSAGE_LENGTH in main.py
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) != 10 or digits[0] not in "6789":
            raise ValueError("phone must be a valid 10-digit Indian mobile number")
        return digits


class EndChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    ai_config: AIConfig | None = None


# ── Data models ────────────────────────────────────────────────────────────────

class LeadData(BaseModel):
    """All collected lead profile fields for a session."""
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    interest: str | None = None
    course_title: str | None = None
    course_category: str | None = None
    current_status: CurrentStatus | None = None
    education: str | None = None
    current_domain: str | None = None
    career_goal: str | None = None
    email_refused: bool = False
    phone_refused: bool = False
    callback_deferred: bool = False
    conversation_state: ConversationStateType | None = None
    recommendations: list[CourseRecommendation] = Field(default_factory=list)
    investment_amount: str | None = None
    investment_timeline: str | None = None
    return_preference: str | None = None
    investment_experience: str | None = None
    investment_mode: str | None = None
    location: str | None = None
    callback_time: str | None = None
    advisor_requested: bool = False
    brochure_requested: bool = False
    company_name: str | None = None
    executive_name: str | None = None
    internship_duration: str | None = None
    profiling_answers: dict | None = None
    whatsapp_welcome_sent: bool = False


# ── Response models ────────────────────────────────────────────────────────────

class LeadAnalysis(BaseModel):
    """Internal lead qualification result — not exposed directly to frontend."""
    model_config = ConfigDict(extra="ignore")

    lead_type: LeadType = "Cold"
    interest: str | None = None
    urgency: Urgency = "low"
    budget_signal: BudgetSignal = "unknown"
    needs_callback: bool = False
    contact_collected: bool = False
    lead_score: int = Field(default=0, ge=0, le=MAX_LEAD_SCORE)
    summary: str = ""
    next_action: str = ""


class ChatResponse(BaseModel):
    """Response returned to the frontend after each chat turn."""
    model_config = ConfigDict(extra="ignore")

    answer: str
    session_id: str
    lead_type: LeadType
    lead_score: int = Field(ge=0, le=MAX_LEAD_SCORE)
    needs_callback: bool
    next_action: str | None = None
    interest: str | None = None
    summary: str = ""
    lead_data: LeadData
    crm_pushed: bool = False
    quick_replies: list[str] = Field(default_factory=list)


class AriaIdentity(BaseModel):
    """Identity signals supplied by a channel adapter."""
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    whatsapp_number: str | None = None

    @field_validator("name", "phone", "whatsapp_number", mode="before")
    @classmethod
    def normalize_optional_string(cls, v):
        if v is None:
            return None
        value = str(v).strip()
        return value or None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_optional_email(cls, v):
        if v is None:
            return None
        value = str(v).strip()
        if not value or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
            return None
        return value


class AriaMessageRequest(BaseModel):
    """Unified cross-channel message request for Aria Core."""
    model_config = ConfigDict(extra="ignore")

    ai_config: AIConfig | None = None
    channel: Literal["website", "whatsapp"] = "website"
    channel_session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=2000)
    identity: AriaIdentity = Field(default_factory=AriaIdentity)
    metadata: dict = Field(default_factory=dict)


class AriaJourneyState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_stage: str
    current_category: str | None = None
    flow_id: str | None = None
    last_completed_question: str | None = None
    next_question: str | None = None
    completed_questions: list[str] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    progress_percentage: int = Field(default=0, ge=0, le=100)
    is_complete: bool = False
    last_active_channel: str | None = None


class AriaLeadSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    lead_type: LeadType
    lead_score: int = Field(ge=0, le=MAX_LEAD_SCORE)
    needs_callback: bool = False
    next_action: str | None = None


class AriaAction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    template_name: str | None = None
    to: str | None = None
    required: bool = False


class AriaMessageResponse(BaseModel):
    """Unified cross-channel response returned by Aria Core."""
    model_config = ConfigDict(extra="ignore")

    aria_user_id: str
    session_id: str
    answer: str
    profile: LeadData
    journey_state: AriaJourneyState
    lead: AriaLeadSnapshot
    actions: list[AriaAction] = Field(default_factory=list)
    memory_summary: str = ""


class EndChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    crm_pushed: bool
    lead_type: LeadType
    lead_score: int = Field(ge=0, le=MAX_LEAD_SCORE)
    summary: str
    lead_data: LeadData


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: str
    lead_type: LeadType
    lead_score: int = Field(ge=0, le=MAX_LEAD_SCORE)
    summary: str = ""
    lead_data: LeadData
    messages: list[ChatMessage]


class KnowledgeRebuildResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str
    message: str
    crawl_website: bool
    knowledge_file: str
    file_size_bytes: int

class PromptGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    business_name: str
    tone: str = "friendly"

class PromptGenerateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    generated_prompt: str

class PromptImproveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prompt: str

class PromptImproveResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    improved_prompt: str
