from app.platform.contracts import PlatformMessageRequest
from app.platform.orchestrator import (
    chat_request_to_platform,
    platform_response_to_chat_response,
    process_platform_message,
)
from app.schemas import ChatRequest


def test_legacy_chat_request_maps_to_platform_contract():
    request = ChatRequest(message="Hello", session_id="platform-test-legacy")
    platform_request = chat_request_to_platform(request)

    assert platform_request.message == "Hello"
    assert platform_request.session_id == "platform-test-legacy"
    assert platform_request.channel.channel == "website"


def test_platform_message_returns_legacy_compatible_response():
    request = PlatformMessageRequest(
        tenant_id="test-tenant",
        agent_id="test-agent",
        session_id="platform-test-session",
        message="Hello",
        channel={"channel": "website", "source_url": "https://example.test"},
    )

    platform_response = process_platform_message(request)
    legacy_response = platform_response_to_chat_response(platform_response)

    assert platform_response.tenant_id == "test-tenant"
    assert platform_response.agent_id == "test-agent"
    assert platform_response.session_id == "platform-test-session"
    assert platform_response.answer
    assert legacy_response.answer == platform_response.answer
    assert legacy_response.session_id == platform_response.session_id

