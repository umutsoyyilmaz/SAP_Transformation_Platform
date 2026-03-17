"""
SAP Transformation Management Platform
Conversation Manager — Sprint 19 (AI Phase 4).

Multi-turn conversation support:
    - Create / continue / close / list sessions
    - Message history management with context window trimming
    - LLM call delegation through gateway
    - Token/cost aggregation per conversation
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from app.models import db
from app.models.ai import (
    AIConversation,
    AIConversationMessage,
    CONVERSATION_STATUSES,
    ASSISTANT_TYPES,
)

logger = logging.getLogger(__name__)

# Maximum messages to send to LLM (context window management)
MAX_HISTORY_MESSAGES = 20

# ── Intent detection ──────────────────────────────────────────────────────────

_NL_QUERY_RE = re.compile(
    r"\b(how many|count of|count all|list all|show me all|show all|"
    r"total number|average of|top \d+|"
    r"by status|by module|by priority|open defects|pending risks|"
    r"give me a list|get all|fetch all)\b",
    re.IGNORECASE,
)


def _detect_intent(message: str) -> str:
    """
    Detect whether a message is a data query or general conversation.

    Args:
        message: Raw user message text.

    Returns:
        "nl_query" if the message appears to be a data/SQL query request,
        "general_chat" otherwise.
    """
    return "nl_query" if _NL_QUERY_RE.search(message) else "general_chat"


class ConversationManager:
    """Manages multi-turn AI conversations with history and context."""

    def __init__(self, gateway=None, prompt_registry=None):
        self.gateway = gateway
        self.prompt_registry = prompt_registry

    # ── Session lifecycle ─────────────────────────────────────────────────

    def create_session(
        self,
        *,
        assistant_type: str = "general",
        title: str = "",
        program_id: int | None = None,
        user: str = "system",
        context: dict | None = None,
        system_prompt: str | None = None,
    ) -> dict:
        """Create a new conversation session."""
        if assistant_type not in ASSISTANT_TYPES:
            return {"error": f"Invalid assistant_type: {assistant_type}"}

        conv = AIConversation(
            title=title or f"Conversation — {assistant_type}",
            assistant_type=assistant_type,
            status="active",
            program_id=program_id,
            user=user,
            context_json=json.dumps(context or {}),
        )
        db.session.add(conv)
        db.session.flush()

        # Optionally add a system message
        if system_prompt:
            msg = AIConversationMessage(
                conversation_id=conv.id,
                seq=1,
                role="system",
                content=system_prompt,
            )
            db.session.add(msg)
            conv.message_count = 1

        db.session.commit()
        return conv.to_dict(include_messages=True)

    def send_message(
        self,
        conversation_id: int,
        user_message: str,
        *,
        model: str | None = None,
    ) -> dict:
        """
        Append a user message, call LLM with full history, append assistant reply.

        Returns the assistant's response message dict.
        """
        conv = db.session.get(AIConversation, conversation_id)
        if not conv:
            return {"error": "Conversation not found"}
        if conv.status != "active":
            return {"error": f"Conversation is {conv.status}, cannot send messages"}

        if not user_message or not user_message.strip():
            return {"error": "Message content is required"}

        # 1. Append user message
        next_seq = conv.message_count + 1
        user_msg = AIConversationMessage(
            conversation_id=conv.id,
            seq=next_seq,
            role="user",
            content=user_message.strip(),
        )
        db.session.add(user_msg)
        conv.message_count = next_seq
        db.session.flush()

        # 2. Build LLM messages from history
        messages = self._build_llm_messages(conv)

        # 3. Call LLM
        if not self.gateway:
            return {"error": "LLM gateway not configured"}

        llm_result = self.gateway.chat(
            messages=messages,
            model=model,
            purpose=f"conversation_{conv.assistant_type}",
            user=conv.user,
            program_id=conv.program_id,
        )

        content = llm_result.get("content", "")
        prompt_tokens = llm_result.get("prompt_tokens", 0)
        completion_tokens = llm_result.get("completion_tokens", 0)
        cost = llm_result.get("cost_usd", 0.0)
        latency = llm_result.get("latency_ms", 0)
        llm_model = llm_result.get("model", "unknown")

        # 4. Append assistant response
        asst_seq = conv.message_count + 1
        asst_msg = AIConversationMessage(
            conversation_id=conv.id,
            seq=asst_seq,
            role="assistant",
            content=content,
            model=llm_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency,
        )
        db.session.add(asst_msg)

        # 5. Update conversation stats
        conv.message_count = asst_seq
        conv.total_tokens = (conv.total_tokens or 0) + prompt_tokens + completion_tokens
        conv.total_cost_usd = (conv.total_cost_usd or 0) + cost

        db.session.commit()
        return asst_msg.to_dict()

    def close_session(self, conversation_id: int) -> dict:
        """Close a conversation session."""
        conv = db.session.get(AIConversation, conversation_id)
        if not conv:
            return {"error": "Conversation not found"}
        conv.status = "closed"
        db.session.commit()
        return conv.to_dict()

    def list_sessions(
        self,
        *,
        program_id: int | None = None,
        assistant_type: str | None = None,
        status: str | None = None,
        user: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """List conversation sessions with optional filters."""
        q = AIConversation.query
        if program_id is not None:
            q = q.filter_by(program_id=program_id)
        if assistant_type:
            q = q.filter_by(assistant_type=assistant_type)
        if status:
            q = q.filter_by(status=status)
        if user:
            q = q.filter_by(user=user)
        convs = q.order_by(AIConversation.updated_at.desc()).limit(limit).all()
        return [c.to_dict() for c in convs]

    def get_session(self, conversation_id: int, *, include_messages: bool = True) -> dict | None:
        """Get a single conversation with optional messages."""
        conv = db.session.get(AIConversation, conversation_id)
        if not conv:
            return None
        return conv.to_dict(include_messages=include_messages)

    def append_structured_exchange(
        self,
        conversation_id: int,
        *,
        user_message: str,
        assistant_payload: dict[str, Any],
        title: str | None = None,
    ) -> dict:
        """Append a user/assistant exchange produced by another assistant flow."""
        conv = db.session.get(AIConversation, conversation_id)
        if not conv:
            return {"error": "Conversation not found"}
        if conv.status != "active":
            return {"error": f"Conversation is {conv.status}, cannot append messages"}
        if not user_message or not user_message.strip():
            return {"error": "user_message is required"}

        user_seq = conv.message_count + 1
        user_msg = AIConversationMessage(
            conversation_id=conv.id,
            seq=user_seq,
            role="user",
            content=user_message.strip(),
        )
        db.session.add(user_msg)

        assistant_seq = user_seq + 1
        assistant_msg = AIConversationMessage(
            conversation_id=conv.id,
            seq=assistant_seq,
            role="assistant",
            content=json.dumps(assistant_payload, ensure_ascii=True),
            model=assistant_payload.get("model"),
            prompt_tokens=int(assistant_payload.get("prompt_tokens") or 0),
            completion_tokens=int(assistant_payload.get("completion_tokens") or 0),
            cost_usd=float(assistant_payload.get("cost_usd") or 0.0),
            latency_ms=int(assistant_payload.get("latency_ms") or 0),
        )
        db.session.add(assistant_msg)

        conv.message_count = assistant_seq
        conv.total_tokens = (conv.total_tokens or 0) + assistant_msg.prompt_tokens + assistant_msg.completion_tokens
        conv.total_cost_usd = (conv.total_cost_usd or 0.0) + assistant_msg.cost_usd
        if title and (not conv.title or conv.title.startswith("Conversation")):
            conv.title = title

        db.session.commit()
        return {
            "conversation": conv.to_dict(),
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict(),
        }

    def send_message_stream(
        self,
        conversation_id: int,
        user_message: str,
        *,
        program_id: int | None = None,
        tenant_id: int | None = None,
    ) -> Generator[dict, None, None]:
        """
        Stream an AI response for a conversation message.

        Saves the user message to DB immediately, detects intent, routes to
        the appropriate assistant (NLQueryAssistant or ChatAssistant), yields
        SSE-compatible events as they arrive, then saves the completed assistant
        message to DB and commits.

        Args:
            conversation_id: Target conversation primary key.
            user_message: Raw user text (max 4000 chars enforced by caller).
            program_id: Active program for budget and context.
            tenant_id: Owning tenant (for audit logging in gateway).

        Yields:
            {"type": "intent",    "value": "general_chat" | "nl_query"}
            {"type": "chunk",     "content": str}            — general_chat only
            {"type": "nl_result", "data": dict}              — nl_query only
            {"type": "done",      "usage": dict, "message_id": int}
            {"type": "error",     "message": str}
        """
        if not self.gateway:
            yield {"type": "error", "message": "LLM gateway not configured"}
            return

        conv = db.session.get(AIConversation, conversation_id)
        if not conv or conv.status != "active":
            yield {"type": "error", "message": "Conversation not found or closed"}
            return

        if not user_message or not user_message.strip():
            yield {"type": "error", "message": "Message content is required"}
            return

        clean_message = user_message.strip()[:4000]

        # 1. Persist user message (flush only — keep session open)
        user_seq = conv.message_count + 1
        user_msg = AIConversationMessage(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            seq=user_seq,
            role="user",
            content=clean_message,
        )
        db.session.add(user_msg)
        conv.message_count = user_seq
        db.session.flush()

        # 2. Detect intent and broadcast immediately
        intent = _detect_intent(clean_message)
        yield {"type": "intent", "value": intent}

        full_content = ""
        usage: dict = {}
        t0 = time.time()

        try:
            if intent == "nl_query":
                # NL query runs synchronously; result sent as a single event
                from app.ai.assistants.nl_query import NLQueryAssistant
                nl_asst = NLQueryAssistant(gateway=self.gateway)
                nl_result = nl_asst.process_query(
                    clean_message,
                    program_id=program_id or conv.program_id,
                    auto_execute=True,
                )
                yield {"type": "nl_result", "data": nl_result}
                full_content = json.dumps(nl_result, ensure_ascii=True)
                usage = nl_result.get("usage", {})
            else:
                # General chat — true streaming
                from app.ai.assistants.chat_assistant import ChatAssistant
                chat_asst = ChatAssistant(gateway=self.gateway)
                llm_messages = self._build_llm_messages(conv)
                llm_messages.append({"role": "user", "content": clean_message})

                for event in chat_asst.generate_response_stream(
                    llm_messages,
                    program_id=program_id or conv.program_id,
                    tenant_id=tenant_id,
                ):
                    if event["type"] == "chunk":
                        full_content += event["content"]
                        yield event
                    elif event["type"] == "done":
                        usage = event.get("usage", {})
                    elif event["type"] == "error":
                        yield event
                        db.session.rollback()
                        return

            # 3. Persist assistant message + commit
            asst_seq = conv.message_count + 1
            asst_msg = AIConversationMessage(
                conversation_id=conv.id,
                tenant_id=tenant_id,
                seq=asst_seq,
                role="assistant",
                content=full_content,
                model=usage.get("model"),
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                cost_usd=float(usage.get("cost_usd") or 0.0),
                latency_ms=int((time.time() - t0) * 1000),
            )
            db.session.add(asst_msg)
            conv.message_count = asst_seq
            conv.total_tokens = (conv.total_tokens or 0) + asst_msg.prompt_tokens + asst_msg.completion_tokens
            conv.total_cost_usd = (conv.total_cost_usd or 0.0) + asst_msg.cost_usd
            db.session.commit()

            yield {"type": "done", "usage": usage, "message_id": asst_msg.id}

        except GeneratorExit:
            db.session.rollback()
            return
        except Exception:
            logger.exception("send_message_stream failed conversation_id=%s", conversation_id)
            db.session.rollback()
            yield {"type": "error", "message": "Stream processing failed"}

    # ── Internal helpers ──────────────────────────────────────────────────

    def _build_llm_messages(self, conv: AIConversation) -> list[dict]:
        """Build messages list for LLM from conversation history."""
        all_msgs = conv.messages.order_by(AIConversationMessage.seq.asc()).all()

        # Trim to last MAX_HISTORY_MESSAGES, always keeping system message if present
        system_msg = None
        history = []
        for m in all_msgs:
            if m.role == "system":
                system_msg = m
            else:
                history.append(m)

        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg.content})
        for m in history:
            messages.append({"role": m.role, "content": m.content})

        return messages
