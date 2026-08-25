from app.platform.contracts import PlatformMessageRequest
from app.platform.orchestrator import process_platform_message
from app.platform.planner import plan_conversation_step
from app.platform.prompt_builder import build_dynamic_system_prompt
from app.platform.state_machine import StateContext
from app.schemas import AIConfig


def test_state_machine_workflow_stack():
    state = StateContext(
        current_workflow_id="job_application",
        current_step_id="collect_role",
        collected_slots={"name": "Alice"},
    )
    state.push_interrupted_workflow(reason="asked_pricing")

    assert len(state.workflow_stack) == 1
    assert state.workflow_stack[0].workflow_id == "job_application"

    popped = state.pop_interrupted_workflow()
    assert popped is not None
    assert popped.workflow_id == "job_application"
    assert state.current_workflow_id == "job_application"


def test_dynamic_prompt_builder():
    config = AIConfig(
        assistant_name="Aria",
        business_name="Acme Corp",
        personality="Warm and empathetic",
        tone="Friendly",
        prompt="We sell enterprise software.",
    )
    state = StateContext(
        collected_slots={"name": "Bob", "email": "bob@example.com"},
        summary="User asked about enterprise licensing.",
    )

    prompt = build_dynamic_system_prompt(config, state, grounding_docs=["Licensing costs $99/mo."])

    assert "Aria" in prompt
    assert "Acme Corp" in prompt
    assert "Warm and empathetic" in prompt
    assert "bob@example.com" in prompt
    assert "Licensing costs $99/mo." in prompt


def test_planner_human_escalation():
    config = AIConfig(quick_replies=["FAQ", "Pricing"])
    state = StateContext()

    request = PlatformMessageRequest(
        tenant_id="tenant-1",
        message="I want to speak to a human agent please",
    )

    plan = plan_conversation_step(request, state, config)

    assert plan.action_type == "escalate"
    assert plan.validation.should_escalate is True
    assert len(plan.actions) == 1
    assert plan.actions[0].type == "trigger_handoff"


def test_planner_job_hiring_type_buttons():
    config = AIConfig()
    state = StateContext()

    request = PlatformMessageRequest(
        tenant_id="meridahr",
        message="Hey I'm looking for a Business Development Job",
    )

    plan = plan_conversation_step(request, state, config)

    assert plan.action_type == "ask_hiring_type"
    assert "What type of company are you interested in?" in plan.override_answer


def test_orchestrator_merida_hiring_selection():
    request = PlatformMessageRequest(
        tenant_id="meridahr",
        message="Internal Openings",
    )

    response = process_platform_message(request)

    assert "openings" in response.answer.lower()
    assert len(response.jobs) > 0


def test_orchestrator_external_hiring_selection():
    request = PlatformMessageRequest(
        tenant_id="meridahr",
        message="Partner Network",
    )

    response = process_platform_message(request)

    assert "partner network" in response.answer.lower()
    assert len(response.jobs) > 0


def test_out_of_scope_biryani_order_rejection():
    request = PlatformMessageRequest(
        tenant_id="meridahr",
        message="Biryani Order",
    )

    response = process_platform_message(request)

    assert "cannot assist with food or unrelated order requests" in response.answer.lower()
    assert response.lead_data.phone is None
    assert response.lead_data.email is None


def test_zero_code_tenant_onboarding_acme_corp():
    """Verifies that a brand new company (Acme Corp) can be onboarded 100% via AIConfig payload with zero microservice code changes."""
    acme_config = AIConfig(
        assistant_name="AcmeBot",
        business_name="Acme Corp Solutions",
        personality="Corporate and Efficient",
        tone="Professional",
        prompt="Assist clients with Acme cloud services and IT consulting.",
        out_of_scope_message="I am AcmeBot for Acme Corp Solutions. I only assist with cloud and IT consulting.",
        quick_replies=["Cloud Consulting", "Security Audit", "Contact Sales"],
        domain_keywords={
            "cloud": ["aws", "azure", "cloud", "devops"],
            "security": ["firewall", "cybersecurity", "audit"]
        }
    )

    request = PlatformMessageRequest(
        tenant_id="acmecorp_tenant_999",
        message="I need help with azure cloud migration",
        ai_config=acme_config,
    )

    response = process_platform_message(request)

    # 1. Microservice dynamically adapts assistant & business identity
    assert response.agent_id == "default"
    assert response.lead_type in ("Cold", "Warm", "Hot")
    
    # 2. Out of scope request test for Acme Corp
    request_oos = PlatformMessageRequest(
        tenant_id="acmecorp_tenant_999",
        message="Order 2 pizzas",
        ai_config=acme_config,
    )
    resp_oos = process_platform_message(request_oos)
    assert "acme corp solutions" in resp_oos.answer.lower()
    assert "Contact Sales" in resp_oos.quick_replies or "Cloud Consulting" in resp_oos.quick_replies


def test_candidate_quick_form_and_opt_in_flow():
    # Step 1: Submit Candidate Form
    request1 = PlatformMessageRequest(
        tenant_id="meridahr",
        message="Candidate details submitted",
        metadata={
            "form_type": "candidate_quick_form",
            "form_data": {
                "name": "Vinod Bajpayi",
                "phone": "+91 9876543210",
                "email": "vinod@example.com",
                "job_title": "Graphic Designer Intern",
                "job_id": 9,
            },
        },
    )

    resp1 = process_platform_message(request1)
    assert "opt in to receive job-related email campaigns" in resp1.answer
    assert "Yes" in resp1.quick_replies
    assert "No" in resp1.quick_replies
    assert resp1.lead_data.name == "Vinod Bajpayi"

    # Step 2: Opt-In Response
    request2 = PlatformMessageRequest(
        tenant_id="meridahr",
        session_id=resp1.session_id,
        message="Yes",
        metadata={
            "pending_opt_in": True,
            "name": "Vinod Bajpayi",
            "job_title": "Graphic Designer Intern",
            "job_id": 9,
        },
    )

    resp2 = process_platform_message(request2)
    assert len(resp2.actions) == 1
    assert resp2.actions[0].type == "redirect_button"
    assert resp2.actions[0].payload["label"] == "Apply Now"
    assert "desig=Graphic%20Designer%20Intern" in resp2.actions[0].payload["url"]
    assert "jobpk=9" in resp2.actions[0].payload["url"]


def test_unlisted_job_request_and_ai_confirmation_flow():
    # Step 1: User asks for an unlisted role (Blockchain Developer)
    request1 = PlatformMessageRequest(
        tenant_id="meridahr",
        message="I am looking for a Blockchain Developer job",
    )

    resp1 = process_platform_message(request1)
    assert "don't have an active opening listed for **Blockchain Developer**" in resp1.answer
    assert any(act.type == "open_unlisted_form" for act in resp1.actions)

    # Step 2: User submits Quick Form for unlisted job
    request2 = PlatformMessageRequest(
        tenant_id="meridahr",
        session_id=resp1.session_id,
        message="Name: Vinod | Phone: 9876543210 | Email: vinod@example.com",
        metadata={
            "form_type": "candidate_quick_form",
            "is_unlisted": True,
            "form_data": {
                "name": "Vinod",
                "phone": "9876543210",
                "email": "vinod@example.com",
                "job_title": "Blockchain Developer",
                "job_id": 0,
            },
        },
    )

    resp2 = process_platform_message(request2)
    assert "opt in to receive job-related email campaigns" in resp2.answer

    # Step 3: User answers Yes to Opt-In
    request3 = PlatformMessageRequest(
        tenant_id="meridahr",
        session_id=resp1.session_id,
        message="Yes",
        metadata={
            "pending_opt_in": True,
            "is_unlisted": True,
            "job_title": "Blockchain Developer",
        },
    )

    resp3 = process_platform_message(request3)
    assert "saved your preference for the **blockchain developer** role" in resp3.answer.lower()
    assert "look for the best opportunity" in resp3.answer.lower()
    assert "send you an update soon" in resp3.answer.lower()
    assert len(resp3.actions) == 1
    assert resp3.actions[0].type == "redirect_button"
    assert resp3.actions[0].payload["label"] == "Apply Now"
    assert "desig=Others" in resp3.actions[0].payload["url"]
    assert "jobpk=0" in resp3.actions[0].payload["url"]
