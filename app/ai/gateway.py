"""
SAP Transformation Management Platform
LLM Gateway — Sprint 7 / S20 Performance Enhancements.

Provider-agnostic LLM router with:
    - Multi-provider support (Anthropic Claude, OpenAI, Gemini, local stub)
    - Auto-retry with exponential backoff
    - Token tracking & cost logging
    - Rate-limit handling
    - Audit logging
    - S20: Response caching (two-tier: memory + DB)
    - S20: Smart model selector (purpose → tier routing)
    - S20: Provider fallback chain on failure
    - S20: Token budget enforcement (per-program/user)

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

        # S19 — Doc Gen stubs
        if "steering" in lower or "committee" in lower or "briefing" in lower:
            return json.dumps({
                "title": "Steering Committee Pack — Weekly Update",
                "executive_summary": "Program is on track with 85% backlog completion. "
                                     "Two medium risks require attention.",
                "workstream_status": [
                    {"name": "FI/CO", "status": "on_track", "progress_pct": 90,
                     "highlights": "Month-end close tested", "blockers": "None"},
                ],
                "kpi_highlights": [
                    {"kpi": "Backlog Completion", "value": "85%", "target": "80%", "trend": "improving"},
                ],
                "risk_escalations": [
                    {"risk": "Resource availability", "severity": "medium",
                     "impact": "Potential 1-week delay", "mitigation": "Cross-training plan"},
                ],
                "decisions_needed": [
                    {"decision": "Go-live date confirmation", "context": "All gates passed",
                     "recommendation": "Proceed as planned", "deadline": "Next week"},
                ],
                "next_steps": [
                    {"action": "Complete UAT sign-off", "owner": "Test Lead", "due_date": "2026-02-20"},
                ],
                "confidence": 0.82,
            })

        if "wricef" in lower or "specification" in lower or "spec" in lower:
            return json.dumps({
                "title": "WRICEF Functional Specification",
                "overview": "Custom enhancement for vendor payment processing "
                            "with local regulatory compliance.",
                "functional_requirements": [
                    {"id": "FR-001", "description": "Auto-calculate withholding tax",
                     "priority": "high", "acceptance_criteria": "Tax calculated per local rules"},
                ],
                "technical_details": "BADI implementation in ME21N with custom logic.",
                "integration_points": [
                    {"system": "SAP FI", "direction": "outbound",
                     "protocol": "RFC", "description": "Post accounting document"},
                ],
                "data_mapping": [
                    {"source_field": "LIFNR", "target_field": "vendor_id",
                     "transformation": "direct", "notes": "1:1 mapping"},
                ],
                "test_approach": "Unit test BADI logic, integration test with FI posting.",
                "assumptions": ["SAP ECC 6.0 EHP8", "Local tax rates configured"],
                "confidence": 0.78,
            })

        if "data quality" in lower or "completeness" in lower or "cleansing" in lower:
            return json.dumps({
                "quality_score": 72.5,
                "completeness_pct": 85.0,
                "issues": [
                    {"category": "missing_data", "description": "15% vendor records lack tax ID",
                     "severity": "high", "affected_records": 1250},
                ],
                "recommendations": [
                    {"action": "Enrich vendor master tax IDs", "priority": "high",
                     "estimated_effort": "3 days"},
                ],
                "cleansing_actions": [
                    {"rule": "Remove duplicate vendors", "description": "Merge by tax ID + name",
                     "auto_fixable": True},
                ],
                "migration_readiness": "needs_cleansing",
                "confidence": 0.75,
            })

        # S21 — Data Migration stubs
        if "migration" in lower or "wave" in lower or "reconcil" in lower:
            return json.dumps({
                "strategy": "Big-bang migration with 3 parallel waves",
                "wave_sequence": [
                    {"wave": 1, "objects": ["Vendor Master", "Customer Master"], "parallel": True},
                    {"wave": 2, "objects": ["Open PO", "Open SO"], "parallel": True},
                    {"wave": 3, "objects": ["GL Balances", "Asset Master"], "parallel": False},
                ],
                "data_objects": ["Vendor Master", "Customer Master", "Open PO",
                                 "Open SO", "GL Balances", "Asset Master"],
                "risk_areas": [
                    "Data volume exceeds 100M records",
                    "Currency conversion for legacy data",
                ],
                "recommendations": [
                    "Run trial migration 2 weeks before cutover",
                    "Validate reconciliation totals per wave",
                ],
                "estimated_duration_hours": 48,
                "confidence": 0.76,
            })

        # S21 — Integration Analyst stubs
        if "integration" in lower or "dependency" in lower or "switch" in lower or "interface" in lower:
            return json.dumps({
                "dependency_map": {
                    "SAP_to_Bank": {"direction": "outbound", "protocol": "SFTP",
                                    "criticality": "high"},
                    "EDI_Supplier": {"direction": "inbound", "protocol": "IDOC",
                                     "criticality": "medium"},
                },
                "critical_interfaces": ["SAP_to_Bank", "EDI_Supplier"],
                "coverage_gaps": ["No failover for bank interface"],
                "risks": ["Single point of failure on bank SFTP"],
                "recommendations": [
                    "Add redundant SFTP endpoint",
                    "Test IDOC retry logic",
                ],
                "validation_status": "needs_review",
                "confidence": 0.74,
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

        # S20 performance services — lazily initialised
        self._cache = None
        self._model_selector = None
        self._budget_service = None
        self._init_perf_services()

    # ── S20 Performance Service Initialisation ────────────────────────────

    def _init_perf_services(self):
        """Set up cache, model-selector, and budget service."""
        try:
            from app.ai.cache import ResponseCacheService
            self._cache = ResponseCacheService()
        except Exception as e:
            logger.debug("ResponseCacheService not available: %s", e)

        try:
            from app.ai.model_selector import ModelSelector
            self._model_selector = ModelSelector(
                available_providers=set(self._providers.keys()),
            )
        except Exception as e:
            logger.debug("ModelSelector not available: %s", e)

        try:
            from app.ai.budget import TokenBudgetService
            self._budget_service = TokenBudgetService()
        except Exception as e:
            logger.debug("TokenBudgetService not available: %s", e)

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
        skip_cache: bool = False,
        skip_budget: bool = False,
        **kwargs,
    ) -> dict:
        """
        Send a chat completion request with retry, caching, budget & fallback.

        S20 enhancements:
            - Cache lookup/store (two-tier)
            - Budget enforcement (token + cost limits)
            - Smart model selection by purpose
            - Fallback chain on provider failure

        Args:
            messages: Chat messages.
            model: Model identifier (defaults selected by purpose or DEFAULT_CHAT_MODEL).
            purpose: What the call is for (e.g. "requirement_analyst").
            user: Who triggered the call.
            program_id: Associated program.
            max_retries: Number of retries on failure.
            skip_cache: Bypass cache even for cacheable purposes.
            skip_budget: Bypass budget enforcement.
            **kwargs: temperature, max_tokens passed to provider.

        Returns:
            dict: {content, prompt_tokens, completion_tokens, model, cost_usd, latency_ms,
                   provider, cache_hit, fallback_provider}
        """
        # ── S20: Smart model selection ────────────────────────────────────
        if model is None and self._model_selector:
            model = self._model_selector.select(purpose=purpose)
        if model is None:
            model = self.DEFAULT_CHAT_MODEL

        # ── S20: Cache lookup ─────────────────────────────────────────────
        cache_hit = False
        if (not skip_cache
                and self._cache
                and self._cache.should_cache(purpose)):
            prompt_hash_cache = self._cache.compute_hash(messages, model)
            cached = self._cache.get(prompt_hash_cache)
            if cached is not None:
                cache_hit = True
                # cached is the raw response value (str or dict) stored via set()
                if isinstance(cached, dict):
                    content = cached.get("content", str(cached))
                    p_tok = cached.get("prompt_tokens", 0)
                    c_tok = cached.get("completion_tokens", 0)
                    c_model = cached.get("model", model)
                else:
                    content = str(cached)
                    p_tok = 0
                    c_tok = 0
                    c_model = model
                result = {
                    "content": content,
                    "prompt_tokens": p_tok,
                    "completion_tokens": c_tok,
                    "model": c_model,
                    "cost_usd": 0.0,
                    "latency_ms": 0,
                    "provider": "cache",
                    "cache_hit": True,
                    "fallback_provider": None,
                }
                self._log_usage(
                    provider="cache", model=model,
                    prompt_tokens=0, completion_tokens=0,
                    cost_usd=0.0, latency_ms=0,
                    user=user, purpose=purpose, program_id=program_id,
                    success=True, cache_hit=True,
                )
                return result

        # ── S20: Budget check ─────────────────────────────────────────────
        if not skip_budget and self._budget_service:
            budget_check = self._budget_service.check_budget(
                program_id=program_id, user=user,
            )
            if not budget_check["allowed"]:
                raise RuntimeError(f"Budget exceeded: {budget_check['reason']}")

        # ── Build provider chain (primary + fallbacks) ────────────────────
        provider, provider_name = self._get_provider(model)
        prompt_hash = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
        prompt_summary = messages[-1]["content"][:500] if messages else ""

        fallback_chain: list[tuple[str, str]] = []  # (model, provider_name)
        if self._model_selector:
            for fb_model in self._model_selector.get_fallback_chain(model):
                fb_prov = self.PROVIDER_MAP.get(fb_model, "local")
                if fb_prov in self._providers:
                    fallback_chain.append((fb_model, fb_prov))

        # ── Primary attempt with retries ──────────────────────────────────
        last_error = None
        fallback_provider_used = None

        for attempt in range(1, max_retries + 1):
            start_time = time.time()
            try:
                result = provider.chat(messages, model, **kwargs)
                latency_ms = int((time.time() - start_time) * 1000)

                cost = calculate_cost(model, result["prompt_tokens"], result["completion_tokens"])
                result["cost_usd"] = cost
                result["latency_ms"] = latency_ms
                result["provider"] = provider_name
                result["cache_hit"] = False
                result["fallback_provider"] = fallback_provider_used

                # S20: Store in cache
                if (not skip_cache
                        and self._cache
                        and self._cache.should_cache(purpose)):
                    self._cache.set(
                        prompt_hash=self._cache.compute_hash(messages, model),
                        response={
                            "content": result["content"],
                            "model": model,
                            "prompt_tokens": result["prompt_tokens"],
                            "completion_tokens": result["completion_tokens"],
                        },
                        model=model,
                        purpose=purpose,
                        prompt_tokens=result["prompt_tokens"],
                        completion_tokens=result["completion_tokens"],
                    )

                # S20: Record budget usage
                if not skip_budget and self._budget_service:
                    total_tokens = result["prompt_tokens"] + result["completion_tokens"]
                    self._budget_service.record_usage(
                        program_id=program_id, user=user,
                        tokens=total_tokens, cost_usd=cost,
                    )

                # Log usage + audit
                self._log_usage(
                    provider=provider_name, model=model,
                    prompt_tokens=result["prompt_tokens"],
                    completion_tokens=result["completion_tokens"],
                    cost_usd=cost, latency_ms=latency_ms,
                    user=user, purpose=purpose, program_id=program_id,
                    success=True, cache_hit=False,
                    fallback_provider=fallback_provider_used,
                )
                self._log_audit(
                    action="llm_call", provider=provider_name, model=model,
                    user=user, program_id=program_id,
                    prompt_hash=prompt_hash, prompt_summary=prompt_summary,
                    tokens_used=result["prompt_tokens"] + result["completion_tokens"],
                    cost_usd=cost, latency_ms=latency_ms,
                    response_summary=result["content"][:500],
                    success=True, cache_hit=False,
                    fallback_used=fallback_provider_used is not None,
                )

                return result

            except Exception as e:
                last_error = e
                latency_ms = int((time.time() - start_time) * 1000)
                logger.warning("LLM call attempt %d/%d failed: %s", attempt, max_retries, e)

                if attempt < max_retries:
                    backoff = min(2 ** (attempt - 1), 4)
                    import threading as _threading
                    _threading.Event().wait(backoff)

        # ── S20: Fallback chain after primary exhausted ───────────────────
        for fb_model, fb_prov_name in fallback_chain:
            fb_provider = self._providers[fb_prov_name]
            logger.info("Trying fallback: model=%s provider=%s", fb_model, fb_prov_name)
            start_time = time.time()
            try:
                result = fb_provider.chat(messages, fb_model, **kwargs)
                latency_ms = int((time.time() - start_time) * 1000)
                cost = calculate_cost(fb_model, result["prompt_tokens"], result["completion_tokens"])

                fallback_provider_used = fb_prov_name
                result["cost_usd"] = cost
                result["latency_ms"] = latency_ms
                result["provider"] = fb_prov_name
                result["cache_hit"] = False
                result["fallback_provider"] = fallback_provider_used

                # Cache the fallback result too
                if (not skip_cache
                        and self._cache
                        and self._cache.should_cache(purpose)):
                    self._cache.set(
                        prompt_hash=self._cache.compute_hash(messages, model),
                        response={
                            "content": result["content"],
                            "model": fb_model,
                            "prompt_tokens": result["prompt_tokens"],
                            "completion_tokens": result["completion_tokens"],
                        },
                        model=fb_model,
                        purpose=purpose,
                        prompt_tokens=result["prompt_tokens"],
                        completion_tokens=result["completion_tokens"],
                    )

                # Budget recording
                if not skip_budget and self._budget_service:
                    total_tokens = result["prompt_tokens"] + result["completion_tokens"]
                    self._budget_service.record_usage(
                        program_id=program_id, user=user,
                        tokens=total_tokens, cost_usd=cost,
                    )

                self._log_usage(
                    provider=fb_prov_name, model=fb_model,
                    prompt_tokens=result["prompt_tokens"],
                    completion_tokens=result["completion_tokens"],
                    cost_usd=cost, latency_ms=latency_ms,
                    user=user, purpose=purpose, program_id=program_id,
                    success=True, cache_hit=False,
                    fallback_provider=fallback_provider_used,
                )
                self._log_audit(
                    action="llm_call", provider=fb_prov_name, model=fb_model,
                    user=user, program_id=program_id,
                    prompt_hash=prompt_hash, prompt_summary=prompt_summary,
                    tokens_used=result["prompt_tokens"] + result["completion_tokens"],
                    cost_usd=cost, latency_ms=latency_ms,
                    response_summary=result["content"][:500],
                    success=True, cache_hit=False, fallback_used=True,
                )

                return result

            except Exception as fb_err:
                logger.warning("Fallback %s/%s failed: %s", fb_prov_name, fb_model, fb_err)
                last_error = fb_err

        # All retries + fallbacks exhausted
        self._log_usage(
            provider=provider_name, model=model,
            prompt_tokens=0, completion_tokens=0,
            cost_usd=0.0, latency_ms=0,
            user=user, purpose=purpose, program_id=program_id,
            success=False, error_message=str(last_error),
            cache_hit=False, fallback_provider=None,
        )
        self._log_audit(
            action="llm_call", provider=provider_name, model=model,
            user=user, program_id=program_id,
            prompt_hash=prompt_hash, prompt_summary=prompt_summary,
            tokens_used=0, cost_usd=0.0, latency_ms=0,
            response_summary="", success=False, error_message=str(last_error),
            cache_hit=False, fallback_used=len(fallback_chain) > 0,
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
                   success, error_message=None,
                   cache_hit=False, fallback_provider=None):
        """Persist a usage log record using a savepoint to avoid interfering with caller's transaction."""
        try:
            log = AIUsageLog(
                provider=provider, model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost_usd, latency_ms=latency_ms,
                user=user, purpose=purpose, program_id=program_id,
                success=success, error_message=error_message,
                cache_hit=cache_hit,
                fallback_provider=fallback_provider,
            )
            db.session.add(log)
            # Use nested transaction (savepoint) so we don't commit/rollback the caller's work
            db.session.flush()
        except Exception as e:
            logger.error("Failed to log AI usage: %s", e)
            try:
                db.session.rollback()
            except Exception:
                pass

    @staticmethod
    def _log_audit(*, action, provider, model, user, program_id,
                   prompt_hash, prompt_summary, tokens_used, cost_usd,
                   latency_ms, response_summary, success, error_message=None,
                   cache_hit=False, fallback_used=False):
        """Persist an audit log record using flush (savepoint-safe)."""
        try:
            log = AIAuditLog(
                action=action, provider=provider, model=model,
                user=user, program_id=program_id,
                prompt_hash=prompt_hash, prompt_summary=prompt_summary,
                tokens_used=tokens_used, cost_usd=cost_usd,
                latency_ms=latency_ms, response_summary=response_summary,
                success=success, error_message=error_message,
                cache_hit=cache_hit,
                fallback_used=fallback_used,
            )
            db.session.add(log)
            # Use flush instead of commit to avoid interfering with caller's transaction
            db.session.flush()

            # WR-2.3: Also write to general audit_logs table
            from app.models.audit import write_audit as _write_general
            _write_general(
                entity_type="ai_call",
                entity_id=str(log.id),
                action=f"ai.{action}",
                actor=user,
                program_id=program_id,
                diff={
                    "prompt_name": action,
                    "provider": provider,
                    "model": model,
                    "tokens_used": tokens_used,
                    "cost_usd": round(cost_usd, 6),
                    "latency_ms": latency_ms,
                    "success": success,
                    "error": error_message,
                },
            )
        except Exception as e:
            logger.error("Failed to log AI audit: %s", e)
            try:
                db.session.rollback()
            except Exception:
                pass
