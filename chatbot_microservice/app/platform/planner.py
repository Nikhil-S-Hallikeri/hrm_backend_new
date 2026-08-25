from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.schemas import AIConfig
from .contracts import PlatformAction, PlatformMessageRequest, PlatformValidationResult
from .job_engine import build_candidate_registration_url, fetch_active_departments, fetch_active_jobs, filter_jobs, format_job_card, is_internal_company
from .state_machine import BUILTIN_WORKFLOWS, StateContext


class PlanDecision(BaseModel):
    action_type: str  # "respond", "ask_slot", "escalate", "resume_workflow", "show_jobs", "ask_hiring_type", "out_of_scope", "apply_now"
    target_slot: str | None = None
    override_answer: str | None = None
    suggested_quick_replies: list[str] = Field(default_factory=list)
    actions: list[PlatformAction] = Field(default_factory=list)
    jobs: list[dict[str, Any]] = Field(default_factory=list)
    validation: PlatformValidationResult = Field(default_factory=PlatformValidationResult)


def plan_conversation_step(
    request: PlatformMessageRequest,
    state: StateContext,
    ai_config: AIConfig,
    confidence_score: int = 70,
    knowledge_hit: bool = True,
) -> PlanDecision:
    """Evaluates conversation intent, out-of-scope requests, job search requests, slot completeness, and workflow actions."""

    message_lower = request.message.lower().strip()
    actions: list[PlatformAction] = []
    quick_replies: list[str] = list(ai_config.quick_replies or [])

        # 0. Candidate Application & Campaign Opt-In Workflow
    is_opt_in_response = message_lower in ("yes", "no") and (
        state.collected_slots.get("pending_opt_in") or request.metadata.get("pending_opt_in")
    )

    if is_opt_in_response:
        opt_in_choice = message_lower == "yes"
        state.collected_slots["email_campaign_opt_in"] = opt_in_choice
        state.collected_slots["pending_opt_in"] = False

        candidate_name = (
            state.collected_slots.get("name")
            or request.metadata.get("name")
            or (request.metadata.get("form_data") and request.metadata["form_data"].get("name"))
            or request.identity.name
            or "there"
        )
        job_title = state.collected_slots.get("selected_job_title") or request.metadata.get("job_title") or "Graphic Designer Intern"
        job_id = state.collected_slots.get("selected_job_id") or request.metadata.get("job_id") or 9
        is_unlisted = state.collected_slots.get("is_unlisted") or request.metadata.get("is_unlisted") or bool(state.collected_slots.get("unlisted_job_requested"))

        if is_unlisted:
            unlisted_role = state.collected_slots.get("unlisted_job_requested") or job_title
            state.collected_slots["interest"] = unlisted_role

            apply_url = build_candidate_registration_url("Others", 0)

            actions.append(
                PlatformAction(
                    type="redirect_button",
                    payload={"label": "Apply Now", "url": apply_url, "job_title": "Others", "job_id": 0},
                    required=True,
                )
            )

            return PlanDecision(
                action_type="apply_now",
                override_answer=(
                    f"Thank you, {candidate_name}!\n\n"
                    f"We have saved your preference for the **{unlisted_role}** role. "
                    f"You can also complete your formal application by clicking the **Apply Now** button below (select 'Others' if prompted for designation). "
                    f"Our recruitment team will look for the best opportunity for you based on the job you are interested in ({unlisted_role}) and will send you an update soon!"
                ),
                suggested_quick_replies=["View All Openings", "HR Consulting"],
                actions=actions,
                jobs=[],
                validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
            )

        apply_url = build_candidate_registration_url(job_title, job_id)

        actions.append(
            PlatformAction(
                type="redirect_button",
                payload={"label": "Apply Now", "url": apply_url, "job_title": job_title, "job_id": job_id},
                required=True,
            )
        )

        return PlanDecision(
            action_type="apply_now",
            override_answer=f"Perfect!\n\nThank you for showing interest in this job, {candidate_name}. The next step is to submit your application.",
            suggested_quick_replies=[],
            actions=actions,
            jobs=[],
            validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
        )

    # Candidate Quick Form Payload Submission
    is_form_submission = (
        "candidate details submitted" in message_lower
        or "name:" in message_lower
        or request.metadata.get("form_type") == "candidate_quick_form"
    )

    if is_form_submission:
        form_data = request.metadata.get("form_data", {})
        c_name = form_data.get("name")
        c_phone = form_data.get("phone")
        c_email = form_data.get("email")

        if not (c_name and c_phone and c_email) and "name:" in message_lower:
            import re
            m_name = re.search(r"name:\s*([^|]+)", request.message, re.IGNORECASE)
            m_phone = re.search(r"phone:\s*([^|]+)", request.message, re.IGNORECASE)
            m_email = re.search(r"email:\s*([^|]+)", request.message, re.IGNORECASE)
            if m_name:
                c_name = m_name.group(1).strip()
            if m_phone:
                c_phone = m_phone.group(1).strip()
            if m_email:
                c_email = m_email.group(1).strip()

        if c_name:
            state.collected_slots["name"] = c_name
        if c_phone:
            state.collected_slots["phone"] = c_phone
        if c_email:
            state.collected_slots["email"] = c_email

        job_title = form_data.get("job_title") or request.metadata.get("job_title") or state.collected_slots.get("selected_job_title") or "Position"
        job_id = form_data.get("job_id") or request.metadata.get("job_id") or state.collected_slots.get("selected_job_id") or 1

        state.collected_slots["selected_job_title"] = job_title
        state.collected_slots["selected_job_id"] = job_id
        state.collected_slots["pending_opt_in"] = True

        return PlanDecision(
            action_type="ask_opt_in",
            override_answer="Do you want to opt in to receive job-related email campaigns and direct messages from us?",
            suggested_quick_replies=["Yes", "No"],
            jobs=[],
            validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
        )

    # Job Interest Click Handler ("I'm interested in {job_title}")
    is_job_interest_click = (
        message_lower.startswith("i'm interested")
        or message_lower.startswith("interested in")
        or (request.metadata.get("job_title") and not is_opt_in_response and not is_form_submission)
    )

    if is_job_interest_click and not is_opt_in_response:
        job_title = request.metadata.get("job_title") or state.collected_slots.get("selected_job_title") or "Position"
        job_id = request.metadata.get("job_id") or state.collected_slots.get("selected_job_id") or 1
        is_unlisted = request.metadata.get("is_unlisted") or False

        state.collected_slots["selected_job_title"] = job_title
        state.collected_slots["selected_job_id"] = job_id
        state.collected_slots["is_unlisted"] = is_unlisted
        state.collected_slots["pending_opt_in"] = True

        return PlanDecision(
            action_type="ask_opt_in",
            override_answer="Do you want to opt in to receive job-related email campaigns and direct messages from us?",
            suggested_quick_replies=["Yes", "No"],
            jobs=[],
            validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
        )

    biz_name = getattr(request.ai_config, "business_name", None) or "Company"
    tenant_quick_replies = getattr(request.ai_config, "quick_replies", None) or []
    tenant_categories = getattr(request.ai_config, "categories", None) or []
    custom_out_of_scope = getattr(request.ai_config, "out_of_scope_message", None)
    url_template = getattr(request.ai_config, "registration_url_template", None)
    catalog_api_url = getattr(request.ai_config, "catalog_api_url", None)
    tenant_domain_keywords = getattr(request.ai_config, "domain_keywords", None) or {}

    # 1. Out-of-Scope Topic Protection (Food, Biryani, Non-Business Orders, etc.)
    out_of_scope_keywords = (
        "biryani", "pizza", "burger", "food", "restaurant", "order food",
        "movie ticket", "flight ticket", "hotel booking", "car repair",
        "cricket score", "weather forecast", "laundry", "taxi", "cab", "grocery"
    )
    if any(kw in message_lower for kw in out_of_scope_keywords):
        fallback_msg = custom_out_of_scope or (
            f"I am an AI assistant specialized in {biz_name} services and support. "
            f"I cannot assist with food or unrelated order requests. How can I help you with your needs today?"
        )
        return PlanDecision(
            action_type="out_of_scope",
            override_answer=fallback_msg,
            suggested_quick_replies=tenant_quick_replies or ["View All Openings"],
            jobs=[],
            validation=PlatformValidationResult(
                confidence=95,
                knowledge_hit=False,
                should_escalate=False,
            ),
        )

    # 2. Check for explicit escalation triggers
    escalation_keywords = ("human", "talk to human", "speak to agent", "agent", "support representative", "escalate")
    if any(kw in message_lower for kw in escalation_keywords):
        actions.append(
            PlatformAction(
                type="trigger_handoff",
                payload={"reason": "user_requested_agent", "conversation_id": request.session_id},
                required=True,
            )
        )
        return PlanDecision(
            action_type="escalate",
            suggested_quick_replies=["Connect to Agent", "Cancel Handoff"],
            actions=actions,
            validation=PlatformValidationResult(
                confidence=95,
                knowledge_hit=True,
                should_escalate=True,
                escalation_reason="user_requested_human_agent",
            ),
        )

    # 3. Catalog / Job Search / Service Intent Handling (Dynamically enabled via tenant ai_config)
    has_job_catalog = bool(catalog_api_url or url_template or tenant_domain_keywords)
    personality_lower = (getattr(request.ai_config, "personality", "") or "").lower()
    is_job_tenant = has_job_catalog or any(k in personality_lower for k in ("recruiter", "hiring", "talent", "recruitment"))

    is_explicit_all_jobs = is_job_tenant and any(kw in message_lower for kw in ("all openings", "all jobs", "view all openings", "show all jobs", "show me all openings", "see all jobs", "show all openings", "all options"))
    generic_keywords = (
        "job", "hiring", "opening", "vacancy", "career", "work", "position", "apply", "intern",
        "service", "product", "consultancy", "consulting", "external", "catalog", "option"
    )
    is_job_query = is_job_tenant and (is_explicit_all_jobs or any(kw in message_lower for kw in generic_keywords) or any(k in message_lower for k_list in tenant_domain_keywords.values() for k in k_list))

    if is_job_query:
        all_raw_jobs = fetch_active_jobs(catalog_api_url=getattr(request.ai_config, "catalog_api_url", None))

        # PRIORITY 1: Explicit request for ALL openings/jobs (clears past domain/fallback context)
        if is_explicit_all_jobs:
            state.collected_slots.pop("requested_domain", None)
            state.collected_slots.pop("unlisted_job_requested", None)
            formatted_all = [format_job_card(j, url_template=url_template, brand_keyword=biz_name) for j in all_raw_jobs]
            return PlanDecision(
                action_type="show_jobs",
                override_answer=f"Here are all available active offerings and openings for {biz_name}:",
                suggested_quick_replies=tenant_quick_replies or ["Internal Openings", "Partner Network"],
                jobs=formatted_all,
                validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
            )

        # PRIORITY 2: Check for explicit job role in current message
        import re
        detected_domain = None
        m_role = re.search(r"(?:looking for|looking|find|want|apply for|need)\s+(?:a|an)?\s*([a-zA-Z\s]+?)(?:\s+(?:job|opening|role|vacancy|service)|$)", message_lower, re.IGNORECASE)
        if m_role:
            custom_role = m_role.group(1).strip()
            invalid_stop_words = {
                "good", "new", "great", "any", "external", "high paying", "entry level", "there",
                "for", "for me", "me", "best", "a", "the", "something", "what", "which", "what is",
                "a job", "the best", "best for me", "what is best", "what is best for me", "is best",
                "is best for", "is best for me", "which is", "which is best", "suitable", "best suitable",
                "some", "more", "my", "your", "our", "their"
            }
            if len(custom_role) > 2 and custom_role.lower() not in invalid_stop_words and not custom_role.lower().startswith("for"):
                detected_domain = custom_role

        if not detected_domain:
            domain_keywords = tenant_domain_keywords or {
                "business development": ["bde", "business development", "biz dev", "sales"],
                "digital marketing": ["digital marketing", "marketing", "seo", "social media"],
                "network engineer": ["network engineer", "network", "sysadmin", "system engineer"],
                "sde": ["sde", "software", "developer", "software engineer", "coding", "fullstack", "backend", "frontend"],
                "ai": ["ai", "ml", "artificial intelligence", "data science", "machine learning"],
                "graphic designer": ["graphic", "designer", "design", "ui", "ux", "animator"],
                "nursing": ["nurse", "nursing", "medical", "healthcare"],
                "hr": ["hr", "recruiter", "talent", "hiring manager"],
            }
            for domain_name, kw_tuple in domain_keywords.items():
                if domain_name == "hr" and ("consultancy" in message_lower or "consulting" in message_lower):
                    continue
                if any(kw in message_lower for kw in kw_tuple):
                    detected_domain = domain_name
                    break

        if "consultancy" in message_lower or "consulting" in message_lower or "partner" in message_lower:
            if state.collected_slots.get("requested_domain") == "hr":
                state.collected_slots.pop("requested_domain", None)
                if detected_domain == "hr":
                    detected_domain = None

        if detected_domain:
            state.collected_slots["requested_domain"] = detected_domain

        requested_domain = detected_domain or state.collected_slots.get("requested_domain")
        matching_domain_jobs = filter_jobs(all_raw_jobs, query=requested_domain, custom_domain_keywords=tenant_domain_keywords, brand_keyword=biz_name) if requested_domain else []

        is_education_tenant = any(kw in biz_name.lower() for kw in ("skill", "learning", "academy", "sla", "education", "training"))

        # Selection A: Internal / Primary Brand Openings
        is_internal_click = biz_name.lower() in message_lower or "internal" in message_lower or "in this company" in message_lower
        if is_internal_click:
            m_jobs = filter_jobs(all_raw_jobs, hiring_type="internal", query=requested_domain, custom_domain_keywords=tenant_domain_keywords, brand_keyword=biz_name)
            if not m_jobs and requested_domain:
                ext_jobs = filter_jobs(all_raw_jobs, hiring_type="external", query=requested_domain, custom_domain_keywords=tenant_domain_keywords, brand_keyword=biz_name)
                if ext_jobs:
                    formatted_ext = [format_job_card(j, url_template=url_template, brand_keyword=biz_name) for j in ext_jobs]
                    domain_label = f"{requested_domain.upper()} "
                    return PlanDecision(
                        action_type="show_jobs",
                        override_answer=f"We don't have active {domain_label}openings directly in {biz_name}, but here are matching partner openings:",
                        suggested_quick_replies=tenant_quick_replies or ["View All Openings"],
                        jobs=formatted_ext,
                        validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
                    )
                elif not is_education_tenant:
                    unlisted_title = requested_domain.title()
                    state.collected_slots["unlisted_job_requested"] = unlisted_title
                    actions.append(
                        PlatformAction(
                            type="open_unlisted_form",
                            payload={"job_title": unlisted_title, "job_id": 0, "is_unlisted": True},
                            required=True,
                        )
                    )
                    return PlanDecision(
                        action_type="show_unlisted_job_form",
                        override_answer=(
                            f"We currently don't have an active opening listed for **{unlisted_title}**. "
                            f"However, we would love to match your profile!\n\n"
                            f"Please submit your details below. We will look for the best opportunity for you based on the **{unlisted_title}** role and send you an update soon."
                        ),
                        suggested_quick_replies=[f"Submit Details for {unlisted_title}", "View All Openings"],
                        actions=actions,
                        jobs=[],
                        validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
                    )

            formatted_m_jobs = [format_job_card(j, url_template=url_template, brand_keyword=biz_name) for j in m_jobs] if m_jobs else [format_job_card(j, url_template=url_template, brand_keyword=biz_name) for j in all_raw_jobs if is_internal_company(j.get("company_inrto") or j.get("company"), biz_name)]
            domain_label = f"{requested_domain.upper()} " if requested_domain and m_jobs else ""
            dept_count = len(set(j["department"] for j in formatted_m_jobs))
            return PlanDecision(
                action_type="show_jobs",
                override_answer=f"Here are the active {domain_label}openings for {biz_name} across {dept_count} department(s):",
                suggested_quick_replies=tenant_quick_replies or ["Partner Network", "View All Openings"],
                jobs=formatted_m_jobs,
                validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
            )

        # Selection B: Partner Network / External Hiring
        elif "external" in message_lower or "consultancy" in message_lower or "consulting" in message_lower or "partner" in message_lower:
            ext_jobs = filter_jobs(all_raw_jobs, hiring_type="external", query=requested_domain, custom_domain_keywords=tenant_domain_keywords, brand_keyword=biz_name)
            if not ext_jobs:
                ext_jobs = [dict(j, company_inrto="Partner Network") for j in all_raw_jobs]
            formatted_ext_jobs = [format_job_card(j, url_template=url_template, brand_keyword=biz_name) for j in ext_jobs]
            domain_label = f"{requested_domain.upper()} " if requested_domain else ""
            return PlanDecision(
                action_type="show_jobs",
                override_answer=f"Here are the active {domain_label}openings available through our Partner Network. How can I help you today?",
                suggested_quick_replies=tenant_quick_replies or [f"{biz_name} Openings", "View All Openings"],
                jobs=formatted_ext_jobs,
                validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
            )

        if is_education_tenant:
            return PlanDecision(
                action_type="respond",
                suggested_quick_replies=tenant_quick_replies or ["On-Job Training (OJT)", "Career Certification Courses", "Talk to a Counselor"],
                validation=PlatformValidationResult(confidence=85, knowledge_hit=True, should_escalate=False),
            )

        if matching_domain_jobs:
            formatted_domain_jobs = [format_job_card(j, url_template=url_template, brand_keyword=biz_name) for j in matching_domain_jobs]
            domain_label = f"**{requested_domain.title()}** " if requested_domain else ""
            return PlanDecision(
                action_type="show_jobs",
                override_answer=f"Here are the active opportunities in {domain_label}:",
                suggested_quick_replies=tenant_quick_replies or ["View All Openings"],
                jobs=formatted_domain_jobs,
                validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
            )

        # If user specified a domain (e.g. "HR", "Blockchain Developer") and there are NO matching active jobs in the DB:
        if requested_domain and not matching_domain_jobs:
            unlisted_title = requested_domain.title()
            state.collected_slots["unlisted_job_requested"] = unlisted_title

            actions.append(
                PlatformAction(
                    type="open_unlisted_form",
                    payload={"job_title": unlisted_title, "job_id": 0, "is_unlisted": True},
                    required=True,
                )
            )

            return PlanDecision(
                action_type="show_unlisted_job_form",
                override_answer=(
                    f"We currently don't have an active opening listed for **{unlisted_title}**. "
                    f"However, we would love to match your profile!\n\n"
                    f"Please submit your details below. We will look for the best opportunity for you based on the **{unlisted_title}** role and send you an update soon."
                ),
                suggested_quick_replies=[f"Submit Details for {unlisted_title}", "View All Openings"],
                actions=actions,
                jobs=[],
                validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
            )

        # Domain/Job query without specific company selection -> Ask for hiring category preference
        domain_text = f"a {requested_domain.upper()}" if requested_domain else "a"
        active_deps = fetch_active_departments()
        return PlanDecision(
            action_type="ask_hiring_type",
            override_answer=f"We'd be happy to help you find {domain_text} job. What type of position or department are you interested in?",
            suggested_quick_replies=active_deps or ["Merida Hiring", "HR Consultancy"],
            validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
        )

    # 3.1 Affirmative acknowledgment ("Yes", "Sure", "Show me") when jobs or details were offered
    is_affirmative = message_lower in ("yes", "sure", "ok", "yep", "yeah", "show me", "share them", "please share", "yes please")
    if is_affirmative:
        all_raw_jobs = fetch_active_jobs()
        requested_domain = state.collected_slots.get("requested_domain")
        m_jobs = filter_jobs(all_raw_jobs, query=requested_domain) if requested_domain else all_raw_jobs
        if not m_jobs:
            m_jobs = all_raw_jobs
        formatted_jobs = [format_job_card(j) for j in m_jobs]
        domain_label = f" {requested_domain.upper()}" if requested_domain else ""
        return PlanDecision(
            action_type="show_jobs",
            override_answer=f"Here are the active{domain_label} job openings available for you:",
            suggested_quick_replies=["Merida Hiring", "HR Consultancy", "View All Openings"],
            jobs=formatted_jobs,
            validation=PlatformValidationResult(confidence=95, knowledge_hit=True, should_escalate=False),
        )

    # 4. Check for workflow resumption if stack is populated and query is simple acknowledgment
    if state.workflow_stack and message_lower in ("yes", "sure", "ok", "continue", "resume"):
        resumed = state.pop_interrupted_workflow()
        if resumed:
            state.current_workflow_id = resumed.workflow_id
            state.current_step_id = resumed.step_id
            return PlanDecision(
                action_type="resume_workflow",
                suggested_quick_replies=quick_replies,
                actions=actions,
                validation=PlatformValidationResult(
                    confidence=85,
                    knowledge_hit=True,
                    should_escalate=False,
                ),
            )

    # 5. Check for workflow slot collection
    if state.current_workflow_id and state.current_workflow_id in BUILTIN_WORKFLOWS:
        workflow = BUILTIN_WORKFLOWS[state.current_workflow_id]
        for step in workflow.steps:
            if step.required_slot and not state.collected_slots.get(step.required_slot):
                state.current_step_id = step.id
                return PlanDecision(
                    action_type="ask_slot",
                    target_slot=step.required_slot,
                    suggested_quick_replies=quick_replies,
                    actions=actions,
                    validation=PlatformValidationResult(
                        confidence=80,
                        knowledge_hit=True,
                        should_escalate=False,
                    ),
                )

    # 6. Low confidence knowledge fallback check
    if confidence_score < 50:
        return PlanDecision(
            action_type="escalate",
            suggested_quick_replies=["Connect with Support Team", "Try another question"],
            actions=actions,
            validation=PlatformValidationResult(
                confidence=confidence_score,
                knowledge_hit=False,
                should_escalate=True,
                escalation_reason="low_confidence_fallback",
            ),
        )

    return PlanDecision(
        action_type="respond",
        suggested_quick_replies=quick_replies,
        actions=actions,
        validation=PlatformValidationResult(
            confidence=confidence_score,
            knowledge_hit=knowledge_hit,
            should_escalate=False,
        ),
    )
