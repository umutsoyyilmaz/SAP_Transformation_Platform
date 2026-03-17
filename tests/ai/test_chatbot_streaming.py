"""
Comprehensive tests for the floating chatbot widget's streaming backend.

Covers:
    - SSE endpoint validation (missing fields, too long message)
    - Conversation create → stream → done lifecycle
    - Intent detection (general_chat vs nl_query) for many input patterns
    - General chat streaming path (LocalStub word-by-word)
    - NL query path (supported + unsupported entities)
    - Closed conversation rejection
    - Non-existent conversation handling
    - ConversationManager.send_message_stream() unit tests
    - ChatAssistant system prompt injection
    - Gateway.stream() with LocalStub provider
"""

import json

import pytest

from app.ai.conversation import ConversationManager, _detect_intent
from app.models import db
from app.models.ai import AIConversation, AIConversationMessage


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_sse(response_data: bytes) -> list[dict]:
    """Parse SSE response data into list of event dicts."""
    events = []
    text = response_data.decode("utf-8", errors="replace")
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def _create_conversation(client, assistant_type="general", program_id=None):
    """Create a conversation session via the API."""
    payload = {"assistant_type": assistant_type}
    if program_id:
        payload["program_id"] = program_id
    res = client.post("/api/v1/ai/conversations", json=payload)
    assert res.status_code == 201, f"Failed to create conversation: {res.get_json()}"
    return res.get_json()


def _stream_message(client, conversation_id, message, program_id=None):
    """Send a streaming message and return parsed SSE events."""
    payload = {"conversation_id": conversation_id, "message": message}
    if program_id:
        payload["program_id"] = program_id
    res = client.post("/api/v1/ai/chat/stream", json=payload)
    assert res.status_code == 200, f"Stream returned {res.status_code}: {res.data}"
    assert res.content_type.startswith("text/event-stream")
    return _parse_sse(res.data)


# ═══════════════════════════════════════════════════════════════════════════
# 1. INTENT DETECTION UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestIntentDetection:
    """Test _detect_intent() regex-based routing."""

    @pytest.mark.parametrize("msg", [
        "how many requirements do we have",
        "count of open defects",
        "count all test cases",
        "list all test cases",
        "show me all risks",
        "show all backlog items",
        "total number of requirements",
        "average of defect priority",
        "top 10 requirements",
        "requirements by status",
        "open defects in SD module",
        "pending risks",
        "give me a list of wricef objects",
        "get all requirements",
        "fetch all backlog items",
        "How Many Requirements Are There?",
    ])
    def test_nl_query_detected(self, msg):
        """Messages with data keywords should route to nl_query."""
        assert _detect_intent(msg) == "nl_query"

    @pytest.mark.parametrize("msg", [
        "hello",
        "what is SAP Activate?",
        "explain fit gap analysis",
        "how does cutover planning work?",
        "what are the SAP Activate phases?",
        "help me understand WRICEF",
        "tell me about program governance",
        "what should I do for UAT?",
        "merhaba, nasılsın?",
        "SAP S/4HANA nedir?",
        "can you help me with my project?",
        "what is the best practice for data migration?",
        "explain requirements management",
        "what are test cases used for?",
        "",
    ])
    def test_general_chat_detected(self, msg):
        """Messages without data keywords should route to general_chat."""
        assert _detect_intent(msg) == "general_chat"


# ═══════════════════════════════════════════════════════════════════════════
# 2. SSE ENDPOINT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

class TestChatStreamValidation:
    """Test input validation on POST /api/v1/ai/chat/stream."""

    def test_missing_conversation_id(self, client):
        """Should return 400 when conversation_id is missing."""
        res = client.post("/api/v1/ai/chat/stream", json={"message": "hi"})
        assert res.status_code == 400
        data = res.get_json()
        assert "conversation_id" in data["error"]

    def test_missing_message(self, client):
        """Should return 400 when message is empty."""
        res = client.post(
            "/api/v1/ai/chat/stream",
            json={"conversation_id": 1, "message": ""},
        )
        assert res.status_code == 400
        assert "message" in res.get_json()["error"]

    def test_missing_message_key(self, client):
        """Should return 400 when message key is absent."""
        res = client.post(
            "/api/v1/ai/chat/stream",
            json={"conversation_id": 1},
        )
        assert res.status_code == 400

    def test_message_too_long(self, client):
        """Should return 400 when message exceeds 4000 chars."""
        res = client.post(
            "/api/v1/ai/chat/stream",
            json={"conversation_id": 1, "message": "x" * 4001},
        )
        assert res.status_code == 400
        assert "too long" in res.get_json()["error"]

    def test_whitespace_only_message(self, client):
        """Should return 400 for whitespace-only message."""
        res = client.post(
            "/api/v1/ai/chat/stream",
            json={"conversation_id": 1, "message": "   "},
        )
        assert res.status_code == 400

    def test_no_json_body(self, client):
        """Should return 400 or 415 when no JSON body is sent."""
        res = client.post("/api/v1/ai/chat/stream", data="not json")
        assert res.status_code in (400, 415)

    def test_response_headers(self, client):
        """SSE response should have correct headers."""
        conv = _create_conversation(client)
        res = client.post(
            "/api/v1/ai/chat/stream",
            json={"conversation_id": conv["id"], "message": "hello"},
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.content_type
        assert res.headers.get("Cache-Control") == "no-cache"


# ═══════════════════════════════════════════════════════════════════════════
# 3. GENERAL CHAT STREAMING (full lifecycle)
# ═══════════════════════════════════════════════════════════════════════════

class TestGeneralChatStreaming:
    """Test general_chat path end-to-end with LocalStub provider."""

    def test_simple_greeting(self, client):
        """Basic greeting should stream a general chat response."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "hello")

        # Should have: intent → chunk(s) → done
        types = [e["type"] for e in events]
        assert "intent" in types
        assert "done" in types

        intent_event = next(e for e in events if e["type"] == "intent")
        assert intent_event["value"] == "general_chat"

        # Should have at least one chunk
        chunks = [e for e in events if e["type"] == "chunk"]
        assert len(chunks) > 0, "Expected streaming chunks for general chat"

        # Concatenated chunks should form meaningful text
        full_text = "".join(c["content"] for c in chunks)
        assert len(full_text) > 0

        # Done event should have message_id
        done_event = next(e for e in events if e["type"] == "done")
        assert "message_id" in done_event

    def test_sap_topic_question(self, client):
        """SAP methodology question should trigger general_chat."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "What is SAP Activate methodology?")

        intent = next(e for e in events if e["type"] == "intent")
        assert intent["value"] == "general_chat"
        assert any(e["type"] == "chunk" for e in events)
        assert any(e["type"] == "done" for e in events)

    def test_turkish_message(self, client):
        """Turkish language message should work for general chat."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "SAP Activate nedir?")

        intent = next(e for e in events if e["type"] == "intent")
        assert intent["value"] == "general_chat"
        assert any(e["type"] == "done" for e in events)

    def test_multi_turn_conversation(self, client):
        """Multiple messages in same conversation should work."""
        conv = _create_conversation(client)

        # First message
        events1 = _stream_message(client, conv["id"], "hello")
        assert any(e["type"] == "done" for e in events1)

        # Second message
        events2 = _stream_message(client, conv["id"], "tell me about fit gap analysis")
        assert any(e["type"] == "done" for e in events2)

        # Verify conversation state in DB
        db_conv = db.session.get(AIConversation, conv["id"])
        assert db_conv is not None
        # 2 user messages + 2 assistant messages = 4
        assert db_conv.message_count >= 4

    def test_message_persisted_in_db(self, client):
        """User and assistant messages should be saved to DB."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "explain RACI matrix")

        done_event = next(e for e in events if e["type"] == "done")
        msg_id = done_event["message_id"]

        # Check assistant message exists
        asst_msg = db.session.get(AIConversationMessage, msg_id)
        assert asst_msg is not None
        assert asst_msg.role == "assistant"
        assert len(asst_msg.content) > 0

        # Check user message exists
        user_msgs = AIConversationMessage.query.filter_by(
            conversation_id=conv["id"], role="user"
        ).all()
        assert len(user_msgs) >= 1
        assert user_msgs[0].content == "explain RACI matrix"


# ═══════════════════════════════════════════════════════════════════════════
# 4. NL QUERY PATH
# ═══════════════════════════════════════════════════════════════════════════

class TestNLQueryPath:
    """Test nl_query path with various data questions."""

    def test_count_requirements(self, client):
        """'how many requirements' should trigger nl_query intent."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "how many requirements do we have?")

        intent = next(e for e in events if e["type"] == "intent")
        assert intent["value"] == "nl_query"

        # Should have either nl_result or done (no chunks for NL query)
        types = [e["type"] for e in events]
        assert "done" in types
        # NL query should NOT produce chunks (it's sync)
        chunks = [e for e in events if e["type"] == "chunk"]
        assert len(chunks) == 0, "NL query path should not produce streaming chunks"

    def test_list_test_cases(self, client):
        """'list test cases' should trigger nl_query."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "list all test cases")

        intent = next(e for e in events if e["type"] == "intent")
        assert intent["value"] == "nl_query"
        assert any(e["type"] == "done" for e in events)

    def test_count_by_status(self, client):
        """'requirements by status' should trigger nl_query."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "show requirements by status")

        intent = next(e for e in events if e["type"] == "intent")
        assert intent["value"] == "nl_query"

    def test_open_defects(self, client):
        """'open defects' should trigger nl_query."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "show me open defects")

        intent = next(e for e in events if e["type"] == "intent")
        assert intent["value"] == "nl_query"

    def test_nl_query_with_empty_db(self, client):
        """NL query on empty DB should not error — just return 0 results."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "how many requirements do we have?")

        # Should complete without error
        types = [e["type"] for e in events]
        assert "done" in types
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 0, f"Unexpected errors: {error_events}"

    def test_nl_result_event_structure(self, client):
        """nl_result event should have data field when NL query succeeds."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "count requirements")

        nl_results = [e for e in events if e["type"] == "nl_result"]
        # NL result may or may not be present depending on whether query engine
        # can map the entity. Either way, no error should occur.
        if nl_results:
            assert "data" in nl_results[0]

    def test_nl_query_persists_to_db(self, client):
        """NL query result should be persisted as assistant message."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "how many requirements?")

        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1
        msg_id = done_events[0]["message_id"]

        asst_msg = db.session.get(AIConversationMessage, msg_id)
        assert asst_msg is not None
        assert asst_msg.role == "assistant"


# ═══════════════════════════════════════════════════════════════════════════
# 5. ERROR / EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════

class TestChatStreamEdgeCases:
    """Test error scenarios and edge cases."""

    def test_nonexistent_conversation(self, client):
        """Streaming to a non-existent conversation should return error event."""
        events = _stream_message(client, 99999, "hello")

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) > 0, "Should get error for non-existent conversation"

    def test_closed_conversation(self, client):
        """Streaming to a closed conversation should return error event."""
        conv = _create_conversation(client)
        # Close it
        client.post(f"/api/v1/ai/conversations/{conv['id']}/close")

        events = _stream_message(client, conv["id"], "hello")
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) > 0, "Should get error for closed conversation"

    def test_message_at_max_length(self, client):
        """Message at exactly 4000 chars should be accepted."""
        conv = _create_conversation(client)
        msg = "a" * 4000
        res = client.post(
            "/api/v1/ai/chat/stream",
            json={"conversation_id": conv["id"], "message": msg},
        )
        assert res.status_code == 200

    def test_special_characters_in_message(self, client):
        """Messages with special chars should not break streaming."""
        conv = _create_conversation(client)
        events = _stream_message(
            client, conv["id"],
            'Hello! <script>alert("xss")</script> & "quotes" \'single\''
        )
        assert any(e["type"] == "done" for e in events)

    def test_unicode_message(self, client):
        """Unicode characters should be handled correctly."""
        conv = _create_conversation(client)
        events = _stream_message(client, conv["id"], "日本語のテスト 🎉 ñoño")
        assert any(e["type"] == "done" for e in events)

    def test_newlines_in_message(self, client):
        """Multi-line messages should work."""
        conv = _create_conversation(client)
        events = _stream_message(
            client, conv["id"],
            "Line 1\nLine 2\nLine 3"
        )
        assert any(e["type"] == "done" for e in events)


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONVERSATION LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════

class TestConversationLifecycle:
    """Test conversation create → stream → close lifecycle."""

    def test_create_general_conversation(self, client):
        """Creating a 'general' conversation should succeed."""
        conv = _create_conversation(client, assistant_type="general")
        assert conv["id"] is not None
        assert conv["status"] == "active"
        assert conv["assistant_type"] == "general"

    def test_create_nl_query_conversation(self, client):
        """Creating an 'nl_query' conversation should succeed."""
        conv = _create_conversation(client, assistant_type="nl_query")
        assert conv["status"] == "active"
        assert conv["assistant_type"] == "nl_query"

    def test_conversation_message_count_increases(self, client):
        """Message count should increment with each exchange."""
        conv = _create_conversation(client)
        _stream_message(client, conv["id"], "hello")

        db_conv = db.session.get(AIConversation, conv["id"])
        initial_count = db_conv.message_count

        _stream_message(client, conv["id"], "how are you?")

        db.session.expire(db_conv)
        assert db_conv.message_count > initial_count

    def test_close_conversation(self, client):
        """Closing a conversation should change its status."""
        conv = _create_conversation(client)
        res = client.post(f"/api/v1/ai/conversations/{conv['id']}/close")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "closed"

    def test_list_conversations(self, client):
        """Listing conversations should return created ones."""
        _create_conversation(client)
        _create_conversation(client)

        res = client.get("/api/v1/ai/conversations")
        assert res.status_code == 200
        convs = res.get_json()
        assert len(convs) >= 2

    def test_get_conversation_with_messages(self, client):
        """Getting a conversation should include messages after streaming."""
        conv = _create_conversation(client)
        _stream_message(client, conv["id"], "hello world")

        res = client.get(f"/api/v1/ai/conversations/{conv['id']}?include_messages=true")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data.get("messages", [])) >= 2  # user + assistant


# ═══════════════════════════════════════════════════════════════════════════
# 7. ConversationManager UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestConversationManagerUnit:
    """Direct unit tests for ConversationManager.send_message_stream()."""

    def test_stream_without_gateway(self):
        """Streaming without gateway should yield error event."""
        mgr = ConversationManager(gateway=None)
        # Create a conversation directly
        conv = AIConversation(
            title="Test", assistant_type="general",
            status="active", user="test",
        )
        db.session.add(conv)
        db.session.commit()

        events = list(mgr.send_message_stream(conv.id, "hello"))
        assert any(e["type"] == "error" for e in events)

    def test_stream_empty_message(self):
        """Empty message should yield error event."""
        mgr = ConversationManager(gateway=None)
        conv = AIConversation(
            title="Test", assistant_type="general",
            status="active", user="test",
        )
        db.session.add(conv)
        db.session.commit()

        events = list(mgr.send_message_stream(conv.id, ""))
        assert any(e["type"] == "error" for e in events)

    def test_stream_nonexistent_conversation(self):
        """Non-existent conversation ID should yield error event."""
        mgr = ConversationManager(gateway=None)
        events = list(mgr.send_message_stream(99999, "hello"))
        assert any(e["type"] == "error" for e in events)


# ═══════════════════════════════════════════════════════════════════════════
# 8. ChatAssistant UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestChatAssistantUnit:
    """Test ChatAssistant in isolation."""

    def test_system_prompt_prepended(self):
        """System prompt should be prepended when not present."""
        from app.ai.assistants.chat_assistant import ChatAssistant

        class FakeGateway:
            def stream(self, messages, **kwargs):
                # Verify system prompt is first
                assert messages[0]["role"] == "system"
                assert "Perga Copilot" in messages[0]["content"]
                yield {"type": "chunk", "content": "test"}
                yield {"type": "done", "usage": {}}

        asst = ChatAssistant(gateway=FakeGateway())
        events = list(asst.generate_response_stream(
            [{"role": "user", "content": "hi"}]
        ))
        assert len(events) == 2

    def test_existing_system_prompt_preserved(self):
        """If system prompt already exists, don't add another."""
        from app.ai.assistants.chat_assistant import ChatAssistant

        class FakeGateway:
            def stream(self, messages, **kwargs):
                # Should have exactly one system message
                system_msgs = [m for m in messages if m["role"] == "system"]
                assert len(system_msgs) == 1
                assert system_msgs[0]["content"] == "custom prompt"
                yield {"type": "done", "usage": {}}

        asst = ChatAssistant(gateway=FakeGateway())
        events = list(asst.generate_response_stream([
            {"role": "system", "content": "custom prompt"},
            {"role": "user", "content": "hi"},
        ]))
        assert len(events) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 9. GATEWAY STREAM UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestGatewayStreamUnit:
    """Test LLMGateway.stream() with LocalStub provider."""

    def test_local_stub_stream_produces_chunks(self, app):
        """LocalStub provider should yield word-by-word chunks."""
        from app.ai.gateway import LLMGateway

        gw = LLMGateway()
        messages = [{"role": "user", "content": "hello"}]

        events = list(gw.stream(messages, model="local-stub", purpose="test"))

        chunks = [e for e in events if e["type"] == "chunk"]
        assert len(chunks) > 0, "LocalStub should produce streaming chunks"

        done_events = [e for e in events if e["type"] == "done"]
        assert len(done_events) == 1

    def test_local_stub_stream_no_errors(self, app):
        """Stream should complete without error events."""
        from app.ai.gateway import LLMGateway

        gw = LLMGateway()
        messages = [{"role": "user", "content": "explain SAP"}]

        events = list(gw.stream(messages, model="local-stub"))
        errors = [e for e in events if e["type"] == "error"]
        assert len(errors) == 0, f"Unexpected errors: {errors}"
