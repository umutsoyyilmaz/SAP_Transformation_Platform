"""
SAP Transformation Platform
General SAP-aware conversational assistant with streaming support.

This assistant handles free-form conversation about the SAP transformation
methodology, platform features, and project context. Data queries (counts,
lists, DB summaries) are automatically routed to NLQueryAssistant by
ConversationManager's intent detection.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ai.gateway import LLMGateway

logger = logging.getLogger(__name__)


class ChatAssistant:
    """
    General SAP-aware conversational assistant with streaming support.

    Provides free-form conversation about SAP Activate methodology,
    platform features, RAID/WRICEF/fit-gap concepts, and project context.
    Does NOT execute SQL — data questions are routed by ConversationManager.
    """

    SYSTEM_PROMPT = (
        "You are Perga Copilot, an AI assistant embedded in the Perga SAP "
        "Transformation Management Platform. You help program managers, functional "
        "consultants, and technical leads navigate their SAP implementations.\n\n"
        "You are knowledgeable about:\n"
        "- SAP Activate methodology (Discover, Prepare, Explore, Realize, Deploy, Run)\n"
        "- Fit/Gap analysis (Standard Fit, Partial Fit, Gap, Out of Scope)\n"
        "- WRICEF objects (Workflows, Reports, Interfaces, Conversions, Enhancements, Forms)\n"
        "- RAID log management (Risks, Actions, Issues, Decisions)\n"
        "- Test management (test plans, test cases, defects, UAT sign-off)\n"
        "- Cutover planning and hypercare monitoring\n"
        "- Program governance, RACI matrices, and change management\n"
        "- SAP modules: FI, CO, MM, SD, PP, QM, PM, HCM, BASIS, BTP\n\n"
        "For data questions (counts, lists, summaries of records in the system), "
        "the system will automatically detect and route those to the query engine — "
        "you do not need to handle them yourself.\n\n"
        "Be concise, practical, and focused on SAP transformation delivery. "
        "Avoid unnecessary filler. Answer in the same language the user writes in."
    )

    def __init__(self, gateway: "LLMGateway") -> None:
        self.gateway = gateway

    def generate_response_stream(
        self,
        messages: list[dict],
        *,
        program_id: int | None = None,
        tenant_id: int | None = None,
    ) -> Generator[dict, None, None]:
        """
        Yield SSE-compatible events for a general chat response.

        Args:
            messages: Full conversation history (role/content dicts).
                      System prompt is prepended if not already present.
            program_id: Active program for budget tracking and context.
            tenant_id: Owning tenant (passed through to gateway for audit).

        Yields:
            {"type": "chunk", "content": str}
            {"type": "done",  "usage": dict}
            {"type": "error", "message": str}
        """
        full_messages = self._build_messages(messages)
        yield from self.gateway.stream(
            full_messages,
            purpose="conversation_general",
            program_id=program_id,
        )

    def _build_messages(self, messages: list[dict]) -> list[dict]:
        """
        Prepend system prompt to messages if not already present.

        Args:
            messages: Existing conversation history.

        Returns:
            Messages list with system prompt as first entry.
        """
        if any(m.get("role") == "system" for m in messages):
            return messages
        return [{"role": "system", "content": self.SYSTEM_PROMPT}] + messages
