from app.main import _build_crm_payload

def test_missing_mandatory_fields_returns_error():
    session = {
        "lead_data": {
            "name": None,
            "phone": None,
            "email": None
        }
    }
    messages = []
    payload = _build_crm_payload("session-1", session, messages)
    assert payload == {
        "status": "lead_not_created",
        "reason": "Mandatory fields missing"
    }

def test_investor_lead_generation():
    session = {
        "lead_data": {
            "name": "Ayush Srivastava",
            "phone": "9621293445",
            "email": "ayushsriavstava@gmail.com",
            "current_status": "Experienced Investor",
            "interest": "Current Projects",
            "course_title": "Current JPM Property Flipping Projects",
            "investment_amount": "25 lakhs",
            "investment_timeline": "This month",
            "callback_time": "tomorrow evening",
        }
    }
    messages = [
        {"role": "user", "content": "I want to invest 25 lakhs in current JPM projects"},
        {"role": "assistant", "content": "I can connect you with an investment advisor."},
        {"role": "user", "content": "Ayush Srivastava, 9621293445, ayushsriavstava@gmail.com"}
    ]
    payload = _build_crm_payload("test-111910", session, messages)
    assert payload["name"] == "Ayush Srivastava"
    assert payload["contact_number"] == "9621293445"
    assert payload["email"] == "ayushsriavstava@gmail.com"
    assert "lead_id" in payload
    assert payload["source"] == "JPM Property Flipping AI Chatbot"
    assert payload["priority"] == "High"
    assert payload["level_lead"] == "newlead"
    assert payload["investment_amount"] == "25 lakhs"
    assert payload["preferred_callback_time"] == "tomorrow evening"
