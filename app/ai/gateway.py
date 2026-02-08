"""
SAP Transformation Management Platform
LLM Gateway — Sprint 7.

Provider-agnostic LLM router with:
    - Multi-provider support (Anthropic Claude, OpenAI, local stub)
    - Auto-retry with exponential backoff
    - Token tracking & cost logging
    - Rate-limit handling
    - Audit logging

Usage:
    from app.ai.gateway import LLMGateway
    gw = LLMGateway()
    result = gw.chat("Classify this requirement", model="claude-3-5-haiku-20241022")
"""

import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod

from app.models import db
from app.models.ai import AIUsageLog, AIAuditLog, calculate_cost

logger = logging.getLogger(__name__)


# ── Provider Abstract Base ────────────────────────────────────────────────────

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def chat(self, messages: list, model: str, **kwargs) -> dict:
        """
        Send a chat completion request.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            model: Model identifier string.
            **kwargs: temperature, max_tokens, etc.

        Returns:
            dict with keys: content, prompt_tokens, completion_tokens, model
        """
        ...

    @abstractmethod
    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Returns:
            List of float vectors (one per input text).
        """
        ...


# ── Anthropic Provider ────────────────────────────────────────────────────────

class AnthropicProvider(LLMProvider):
    """Claude API (Anthropic) provider."""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def chat(self, messages: list, model: str = "claude-3-5-haiku-20241022", **kwargs) -> dict:
        client = self._get_client()

        # Separate system message
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)

        params = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.3),
        }
        if system_msg:
            params["system"] = system_msg

        response = client.messages.create(**params)

        return {
            "content": response.content[0].text,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "model": model,
        }

    def embed(self, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        # Anthropic doesn't have embeddings, delegate to OpenAI
        raise NotImplementedError("Use OpenAI provider for embeddings")


# ── OpenAI Provider ───────────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """OpenAI GPT + Embedding provider."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    def chat(self, messages: list, model: str = "gpt-4o-mini", **kwargs) -> dict:
        client = self._get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.3),
        )
        choice = response.choices[0]
        return {
            "content": choice.message.content,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "model": model,
        }

    def embed(self, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        client = self._get_client()
        response = client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in response.data]


# ── Google Gemini Provider (free-tier demo) ──────────────────────────────────

class GeminiProvider(LLMProvider):
    """
    Google Gemini API provider (AI Studio free tier).

    Provides both chat and embeddings from a single free API key.
    Models:
        - gemini-2.5-flash  (fast classification/triage)
        - gemini-2.5-pro    (complex reasoning)
        - gemini-embedding-001 (3072-dim embeddings, configurable)

    Environment:
        GEMINI_API_KEY — obtain free at https://aistudio.google.com/apikey
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "google-genai package not installed. Run: pip install google-genai"
                )
        return self._client

    def chat(self, messages: list, model: str = "gemini-2.5-flash", **kwargs) -> dict:
        client = self._get_client()
        from google.genai import types

        # Separate system instruction from conversation messages
        system_parts = []
        contents = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                # Gemini uses "user" and "model" roles
                role = "model" if m["role"] == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=m["content"])],
                    )
                )

        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.3),
            max_output_tokens=kwargs.get("max_tokens", 4096),
        )
        if system_parts:
            config.system_instruction = "\n\n".join(system_parts)

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        return {
            "content": response.text or "",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "model": model,
        }

    def embed(self, texts: list[str], model: str = "gemini-embedding-001") -> list[list[float]]:
        client = self._get_client()
        from google.genai import types

        result = client.models.embed_content(
            model=model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=1536,  # good balance of quality vs storage
            ),
        )
        return [e.values for e in result.embeddings]


# ── Local Stub Provider (for dev/test without API keys) ──────────────────────

class LocalStubProvider(LLMProvider):
    """
    Local stub that returns deterministic responses for dev/testing.
    No API key required.
    """

    def chat(self, messages: list, model: str = "local-stub", **kwargs) -> dict:
        # Extract last user message
        user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                user_msg = m["content"]
                break

        # Generate a stub response based on context
        content = self._generate_stub_response(user_msg)

        return {
            "content": content,
            "prompt_tokens": len(user_msg.split()) * 2,  # rough estimate
            "completion_tokens": len(content.split()) * 2,
            "model": "local-stub",
        }

    def embed(self, texts: list[str], model: str = "local-stub") -> list[list[float]]:
        """Generate deterministic pseudo-embeddings for testing."""
        import hashlib
        embeddings = []
        for text in texts:
            # Use hash to generate reproducible 1536-dim vector
            h = hashlib.sha512(text.encode()).digest()
            # Repeat hash bytes to fill 1536 floats
            vec = []
            for i in range(1536):
                byte_val = h[i % len(h)]
                vec.append((byte_val - 128) / 256.0)  # normalize to [-0.5, 0.5]
            embeddings.append(vec)
        return embeddings

    @staticmethod
    def _generate_stub_response(user_msg: str) -> str:
        """Generate context-aware stub response."""
        lower = user_msg.lower()

        if "classify" in lower or "fit" in lower or "gap" in lower:
            return json.dumps({
                "classification": "partial_fit",
                "confidence": 0.78,
                "reasoning": "The requirement partially aligns with standard SAP functionality. "
                             "Minor customization needed for local regulatory compliance.",
                "recommended_actions": ["Review SAP standard config", "Check note 2345678"],
            })

        if "defect" in lower or "triage" in lower or "severity" in lower:
            return json.dumps({
                "severity": "P2",
                "module": "FI",
                "confidence": 0.85,
                "reasoning": "Financial posting error in month-end close. "
                             "Impacts reporting but has manual workaround.",
                "similar_defects": [101, 203],
            })

        if "risk" in lower or "assess" in lower:
            return json.dumps({
                "risk_level": "medium",
                "probability": 3,
                "impact": 4,
                "confidence": 0.72,
                "reasoning": "Resource constraints during peak testing phase. "
                             "Mitigation: cross-training and contingency staffing.",
            })

        if "test" in lower or "generate" in lower:
            return json.dumps({
                "test_cases": [
                    {"title": "Verify standard posting", "steps": "1. Open FB50\n2. Enter amounts\n3. Post",
                     "expected": "Document posted successfully"},
                ],
                "confidence": 0.80,
            })

        return json.dumps({
            "response": "Analysis complete. Based on the SAP transformation context, "
                        "the recommended approach aligns with SAP Activate best practices.",
            "confidence": 0.70,
        })


# ── LLM Gateway (Main Interface) ─────────────────────────────────────────────

class LLMGateway:
    """
    Central gateway for all LLM calls.

    Features:
        - Provider routing based on model name
        - Auto-retry with exponential backoff
        - Token/cost tracking (persisted to DB)
        - Audit logging
        - Fallback provider support

    Usage:
        gw = LLMGateway(app=flask_app)
        result = gw.chat(
            messages=[{"role": "user", "content": "Classify this..."}],
            model="claude-3-5-haiku-20241022",
            purpose="requirement_analyst",
        )
    """

    # Model → provider mapping
    PROVIDER_MAP = {
        # Anthropic
        "claude-3-5-haiku-20241022": "anthropic",
        "claude-3-5-sonnet-20241022": "anthropic",
        "claude-3-opus-20240229": "anthropic",
        # OpenAI
        "gpt-4o-mini": "openai",
        "gpt-4o": "openai",
        "gpt-4-turbo": "openai",
        "text-embedding-3-small": "openai",
        "text-embedding-3-large": "openai",
        # Google Gemini (free tier — demo default)
        "gemini-2.5-flash": "gemini",
        "gemini-2.5-pro": "gemini",
        "gemini-2.0-flash": "gemini",
        "gemini-embedding-001": "gemini",
        # Local stub (dev/test)
        "local-stub": "local",
    }

    # Default models — Gemini free tier for demo, override via env
    DEFAULT_CHAT_MODEL = os.getenv("LLM_DEFAULT_CHAT_MODEL", "gemini-2.5-flash")
    DEFAULT_EMBED_MODEL = os.getenv("LLM_DEFAULT_EMBED_MODEL", "gemini-embedding-001")

    def __init__(self, app=None):
        self._providers = {}
        self._app = app
        self._init_providers()

    def _init_providers(self):
        """Initialize available providers based on environment."""
        # Always register local stub
        self._providers["local"] = LocalStubProvider()

        # Register real providers if API keys present
        if os.getenv("GEMINI_API_KEY"):
            self._providers["gemini"] = GeminiProvider()
        if os.getenv("ANTHROPIC_API_KEY"):
            self._providers["anthropic"] = AnthropicProvider()
        if os.getenv("OPENAI_API_KEY"):
            self._providers["openai"] = OpenAIProvider()

    def _get_provider(self, model: str) -> tuple[LLMProvider, str]:
        """
        Resolve model to provider. Falls back to local stub if real provider unavailable.
        Returns (provider, provider_name).
        """
        provider_name = self.PROVIDER_MAP.get(model, "local")

        if provider_name in self._providers:
            return self._providers[provider_name], provider_name

        # Fallback: local stub
        logger.warning(
            "Provider '%s' not available (no API key?). Falling back to local stub for model '%s'.",
            provider_name, model,
        )
        return self._providers["local"], "local"

    def chat(
        self,
        messages: list,
        model: str | None = None,
        *,
        purpose: str = "",
        user: str = "system",
        program_id: int | None = None,
        max_retries: int = 3,
        **kwargs,
    ) -> dict:
        """
        Send a chat completion request with retry and logging.

        Args:
            messages: Chat messages.
            model: Model identifier (defaults to DEFAULT_CHAT_MODEL).
            purpose: What the call is for (e.g. "requirement_analyst").
            user: Who triggered the call.
            program_id: Associated program.
            max_retries: Number of retries on failure.
            **kwargs: temperature, max_tokens passed to provider.

        Returns:
            dict: {content, prompt_tokens, completion_tokens, model, cost_usd, latency_ms}
        """
        if model is None:
            model = self.DEFAULT_CHAT_MODEL

        provider, provider_name = self._get_provider(model)
        prompt_hash = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
        prompt_summary = messages[-1]["content"][:500] if messages else ""

        last_error = None
        for attempt in range(1, max_retries + 1):
            start_time = time.time()
            try:
                result = provider.chat(messages, model, **kwargs)
                latency_ms = int((time.time() - start_time) * 1000)

                # Calculate cost
                cost = calculate_cost(model, result["prompt_tokens"], result["completion_tokens"])
                result["cost_usd"] = cost
                result["latency_ms"] = latency_ms
                result["provider"] = provider_name

                # Log usage + audit
                self._log_usage(
                    provider=provider_name, model=model,
                    prompt_tokens=result["prompt_tokens"],
                    completion_tokens=result["completion_tokens"],
                    cost_usd=cost, latency_ms=latency_ms,
                    user=user, purpose=purpose, program_id=program_id,
                    success=True,
                )
                self._log_audit(
                    action="llm_call", provider=provider_name, model=model,
                    user=user, program_id=program_id,
                    prompt_hash=prompt_hash, prompt_summary=prompt_summary,
                    tokens_used=result["prompt_tokens"] + result["completion_tokens"],
                    cost_usd=cost, latency_ms=latency_ms,
                    response_summary=result["content"][:500],
                    success=True,
                )

                return result

            except Exception as e:
                last_error = e
                latency_ms = int((time.time() - start_time) * 1000)
                logger.warning("LLM call attempt %d/%d failed: %s", attempt, max_retries, e)

                if attempt < max_retries:
                    backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                    time.sleep(backoff)

        # All retries exhausted
        self._log_usage(
            provider=provider_name, model=model,
            prompt_tokens=0, completion_tokens=0,
            cost_usd=0.0, latency_ms=0,
            user=user, purpose=purpose, program_id=program_id,
            success=False, error_message=str(last_error),
        )
        self._log_audit(
            action="llm_call", provider=provider_name, model=model,
            user=user, program_id=program_id,
            prompt_hash=prompt_hash, prompt_summary=prompt_summary,
            tokens_used=0, cost_usd=0.0, latency_ms=0,
            response_summary="", success=False, error_message=str(last_error),
        )
        raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_error}")

    def embed(
        self,
        texts: list[str],
        model: str | None = None,
        *,
        purpose: str = "embedding",
        user: str = "system",
        program_id: int | None = None,
    ) -> list[list[float]]:
        """
        Generate embeddings with logging.

        Args:
            texts: List of strings to embed.
            model: Embedding model (defaults to DEFAULT_EMBED_MODEL).

        Returns:
            List of float vectors.
        """
        if model is None:
            model = self.DEFAULT_EMBED_MODEL

        provider, provider_name = self._get_provider(model)
        start_time = time.time()

        try:
            vectors = provider.embed(texts, model)
            latency_ms = int((time.time() - start_time) * 1000)

            total_tokens = sum(len(t.split()) * 2 for t in texts)  # rough estimate
            cost = calculate_cost(model, total_tokens, 0)

            self._log_usage(
                provider=provider_name, model=model,
                prompt_tokens=total_tokens, completion_tokens=0,
                cost_usd=cost, latency_ms=latency_ms,
                user=user, purpose=purpose, program_id=program_id,
                success=True,
            )
            self._log_audit(
                action="embedding_create", provider=provider_name, model=model,
                user=user, program_id=program_id,
                prompt_hash="", prompt_summary=f"Embedding {len(texts)} texts",
                tokens_used=total_tokens, cost_usd=cost, latency_ms=latency_ms,
                response_summary=f"{len(vectors)} vectors generated", success=True,
            )

            return vectors

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error("Embedding failed: %s", e)

            self._log_audit(
                action="embedding_create", provider=provider_name, model=model,
                user=user, program_id=program_id,
                prompt_hash="", prompt_summary=f"Embedding {len(texts)} texts",
                tokens_used=0, cost_usd=0.0, latency_ms=latency_ms,
                response_summary="", success=False, error_message=str(e),
            )
            raise

    # ── Internal Logging ──────────────────────────────────────────────────

    @staticmethod
    def _log_usage(*, provider, model, prompt_tokens, completion_tokens,
                   cost_usd, latency_ms, user, purpose, program_id,
                   success, error_message=None):
        """Persist a usage log record."""
        try:
            log = AIUsageLog(
                provider=provider, model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost_usd, latency_ms=latency_ms,
                user=user, purpose=purpose, program_id=program_id,
                success=success, error_message=error_message,
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error("Failed to log AI usage: %s", e)
            db.session.rollback()

    @staticmethod
    def _log_audit(*, action, provider, model, user, program_id,
                   prompt_hash, prompt_summary, tokens_used, cost_usd,
                   latency_ms, response_summary, success, error_message=None):
        """Persist an audit log record."""
        try:
            log = AIAuditLog(
                action=action, provider=provider, model=model,
                user=user, program_id=program_id,
                prompt_hash=prompt_hash, prompt_summary=prompt_summary,
                tokens_used=tokens_used, cost_usd=cost_usd,
                latency_ms=latency_ms, response_summary=response_summary,
                success=success, error_message=error_message,
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            logger.error("Failed to log AI audit: %s", e)
            db.session.rollback()
