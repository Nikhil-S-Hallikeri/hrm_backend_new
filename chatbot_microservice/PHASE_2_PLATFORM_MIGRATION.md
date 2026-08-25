# Phase 2: Enterprise Conversation AI Platform

## Implemented Slice

This service now exposes a headless conversation entry point:

```text
POST /platform/message
```

The endpoint accepts channel-neutral input and returns a channel-neutral response. Existing endpoints such as `/chat`, `/aria/message`, and `/chat/end` remain available for backward compatibility.

## Platform Boundary

The new platform layer lives under:

```text
app/platform/
  contracts.py        Normalized request/response contracts
  configuration.py    Environment/admin supplied default agent configuration
  orchestrator.py     Conversation orchestration compatibility layer
```

The orchestrator currently delegates to the proven legacy components:

- `app.chatbot.generate_answer`
- `app.storage`
- `app.lead_analyzer`
- `app.conversation`

This is intentional. It creates the enterprise API boundary first without breaking WhatsApp, CRM, or website clients.

## Normalized Request

Connectors should send:

```json
{
  "tenant_id": "tenant",
  "brand_id": "brand",
  "agent_id": "default",
  "session_id": "optional-existing-session",
  "message": "Hello",
  "channel": {
    "channel": "website",
    "channel_session_id": "browser-session-id",
    "source_url": "https://example.com/page",
    "page_title": "Page title"
  },
  "identity": {
    "name": null,
    "email": null,
    "phone": null,
    "external_user_id": null
  },
  "metadata": {}
}
```

## Normalized Response

The platform returns:

```json
{
  "session_id": "session-id",
  "tenant_id": "tenant",
  "agent_id": "default",
  "answer": "Assistant response",
  "lead_type": "Cold",
  "lead_score": 0,
  "needs_callback": false,
  "quick_replies": [],
  "actions": [],
  "memory_patch": {},
  "validation": {
    "confidence": 70,
    "knowledge_hit": true,
    "should_escalate": false
  }
}
```

## Configuration

Default agent behavior is loaded from environment variables when a request does not provide `ai_config`.

Supported variables include:

- `DEFAULT_ASSISTANT_NAME`
- `DEFAULT_BUSINESS_NAME`
- `DEFAULT_AI_PERSONALITY`
- `DEFAULT_AI_TONE`
- `DEFAULT_AI_LANGUAGE`
- `DEFAULT_BUSINESS_PROMPT`
- `DEFAULT_SYSTEM_PROMPT`
- `DEFAULT_GREETING_MESSAGE`
- `DEFAULT_QUICK_REPLIES`
- `DEFAULT_CONVERSATION_RULES`
- `DEFAULT_LEAD_FIELDS`
- `DEFAULT_KNOWLEDGE_URLS`

Admin-panel supplied `ai_config` still overrides these defaults.

## Website Widget Integration

The MeridaHR website now mounts a bottom-right widget from:

```text
MeridaHR/hrm1/src/Component/ChatWidget/
```

It calls `/platform/message` and passes website channel context including URL, page title, locale, timezone, browser session ID, and referrer metadata.

Runtime widget configuration can be supplied through:

```js
window.MERIDA_CHAT_WIDGET_CONFIG = {
  apiUrl: "https://your-ai-service/platform/message",
  tenantId: "meridahr",
  brandId: "website",
  agentId: "default",
  title: "AI Assistant",
  primaryColor: "#4f1f87"
}
```

or CRA environment variables:

- `REACT_APP_AI_PLATFORM_URL`
- `REACT_APP_AI_TENANT_ID`
- `REACT_APP_AI_BRAND_ID`
- `REACT_APP_AI_AGENT_ID`
- `REACT_APP_CHAT_WIDGET_TITLE`
- `REACT_APP_CHAT_WIDGET_SUBTITLE`
- `REACT_APP_CHAT_LAUNCHER_LABEL`
- `REACT_APP_CHAT_WELCOME_MESSAGE`
- `REACT_APP_CHAT_PRIMARY_COLOR`
- `REACT_APP_CHAT_SECONDARY_COLOR`
- `REACT_APP_CHAT_WIDGET_POSITION`

## Next Migration Phases

1. Move prompt assembly into persisted prompt blocks.
2. Replace SQLite session memory with tenant-scoped structured memory tables.
3. Replace file retrieval with knowledge source ingestion, embeddings, metadata, citations, and hybrid search.
4. Add tool registry and workflow execution.
5. Add validation pipeline with confidence, contradiction checks, and escalation policies.
6. Expand admin UI into the visual chatbot/platform builder.
7. Migrate WhatsApp and CRM connectors to `/platform/message`.

