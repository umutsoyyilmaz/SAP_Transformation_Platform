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
from datetime import datetime, timezone

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
