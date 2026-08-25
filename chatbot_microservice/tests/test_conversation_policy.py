import os
from unittest.mock import patch
from app.chatbot import generate_answer
from app.contact_extractor import extract_contact_details
from app.conversation import (
    calculate_lead_score,
    has_sufficient_recommendation_data,
    lead_type_from_score,
    normalize_lead_data,
    recommend_courses,
    update_profile_memory,
)

def test_generic_investment_interest_is_remembered_without_name():
    assert extract_contact_details("Hey, I'm looking for property investment") == {}

    # Mock llm_extracted to simulate extraction
    lead_data = update_profile_memory(
        normalize_lead_data({}), 
        "Hey, I'm looking for property investment",
        ai_config=None,
        llm_extracted={"interest": "Real Estate Investment"}
    )

    assert lead_data["name"] is None
    assert lead_data["interest"] == "Real Estate Investment"
    assert has_sufficient_recommendation_data(lead_data, None)
    assert calculate_lead_score(lead_data, None) == 0

def test_investor_budget_and_timeline_are_captured():
    mock_config = {
        "lead_collection": [
            {"field_name": "investment_amount", "is_active": True},
            {"field_name": "investment_timeline", "is_active": True}
        ]
    }
    lead_data = update_profile_memory(
        normalize_lead_data({}),
        "I want to invest 25 lakhs this month. Can someone call me?",
        ai_config=mock_config,
        llm_extracted={
            "interest": "Real Estate Investment",
            "investment_amount": "25 lakhs",
            "investment_timeline": "This month"
        }
    )

    assert lead_data["interest"] == "Real Estate Investment"
    assert lead_data["investment_amount"] == "25 lakhs"
    assert lead_data["investment_timeline"] == "This month"
    assert lead_data["advisor_requested"] is True
    # HIGH_INTENT matches "Can someone call me?" and score >= 5
    score = calculate_lead_score(lead_data, mock_config)
    assert lead_type_from_score(score, "I want to invest 25 lakhs") == "Hot"

@patch("app.chatbot._llm_generate_answer")
def test_current_projects_are_routed_to_advisor_handoff(mock_llm):
    mock_llm.return_value = (
        "I'd be happy to connect you with one of our investment advisors who can provide the latest project-specific details.",
        {},
        "LEAD_CAPTURE"
    )

    lead_data = update_profile_memory(
        normalize_lead_data({}), 
        "What current projects are available?",
        ai_config=None,
        llm_extracted={
            "course_title": "Current JPM Property Flipping Projects",
            "course_category": "Project Availability",
            "advisor_requested": True
        }
    )

    assert lead_data["course_title"] == "Current JPM Property Flipping Projects"
    assert lead_data["course_category"] == "Project Availability"
    assert lead_data["advisor_requested"] is True

    answer, _ = generate_answer(
        [{"role": "user", "content": "What current projects are available?"}],
        lead_data,
    )
    assert "investment advisor" in answer.lower()
    assert "latest project-specific details" in answer.lower()

def test_recommendations_are_investment_next_steps_not_courses():
    lead_data = update_profile_memory(
        normalize_lead_data({}),
        "I am an experienced investor interested in ROI and short-term returns",
        ai_config=None,
        llm_extracted={"interest": "Real Estate Investment"}
    )

    recommendations = recommend_courses(lead_data)
    assert recommendations
    assert all("Course" not in item["title"] for item in recommendations)

@patch("app.chatbot._llm_generate_answer")
def test_roi_answer_does_not_invent_returns(mock_llm):
    mock_llm.return_value = (
        "ROI depends on the specific project. We do not want to quote a number.",
        {},
        "DISCOVERY"
    )
    answer, _ = generate_answer(
        [{"role": "user", "content": "What ROI do you offer?"}],
        normalize_lead_data({}),
    )

    assert "depends" in answer.lower()
    assert "do not want to quote a number" in answer.lower()

def test_aria_identity_refused_email_normalization():
    from app.schemas import AriaIdentity
    identity = AriaIdentity(email="refused")
    assert identity.email is None

def test_append_knowledge_source():
    from app.ingestion.build_knowledge_base import append_knowledge_source, KNOWLEDGE_FILE
    import shutil
    
    # Backup knowledge base if exists
    backup_path = KNOWLEDGE_FILE.with_suffix(".bak_test")
    existed = KNOWLEDGE_FILE.exists()
    if existed:
        shutil.copyfile(KNOWLEDGE_FILE, backup_path)
        KNOWLEDGE_FILE.unlink()
        
    try:
        # 1. Test FAQ Q&A append
        append_knowledge_source(faq_q="What are working hours?", faq_a="9 AM to 6 PM.")
        content = KNOWLEDGE_FILE.read_text(encoding="utf-8")
        assert "What are working hours?" in content
        assert "9 AM to 6 PM." in content
        
        # 2. Test append mode preserves existing content
        append_knowledge_source(faq_q="Where are you located?", faq_a="New York.")
        content_after = KNOWLEDGE_FILE.read_text(encoding="utf-8")
        assert "What are working hours?" in content_after
        assert "Where are you located?" in content_after
        
        # 3. Test CSV FAQ parsing
        csv_bytes = b"Is support 24/7?,Yes it is.\nWhat is price?,Starts at 10k."
        append_knowledge_source(file_name="faq.csv", file_bytes=csv_bytes)
        content_csv = KNOWLEDGE_FILE.read_text(encoding="utf-8")
        assert "Is support 24/7?" in content_csv
        assert "Yes it is." in content_csv
        assert "What is price?" in content_csv
    finally:
        # Cleanup uploaded test files
        from app.ingestion.build_knowledge_base import DOCS_DIR
        test_file = DOCS_DIR / "faq.csv"
        if test_file.exists():
            try:
                test_file.unlink()
            except Exception:
                pass
                
        # Restore backup
        if existed:
            shutil.copyfile(backup_path, KNOWLEDGE_FILE)
            try:
                backup_path.unlink()
            except Exception:
                pass
        elif KNOWLEDGE_FILE.exists():
            KNOWLEDGE_FILE.unlink()
