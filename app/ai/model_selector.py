"""
SAP Transformation Management Platform
Smart Model Selector — Sprint 20 (Performance).

Routes AI requests to the optimal model based on:
    1. Purpose/assistant type (fast vs strong model)
    2. Provider availability (fallback chain)
    3. Explicit model override from caller

Model tiers:
    fast     — classification, triage, simple Q&A  (cheapest/fastest)
    balanced — moderate reasoning, multi-turn       (price/quality balance)
    strong   — doc gen, complex analysis, cutover   (best quality)
"""

import logging
import os

from app.models.ai import PURPOSE_MODEL_MAP, MODEL_TIERS

logger = logging.getLogger(__name__)


class ModelSelector:
    """
    Selects the optimal model for a given purpose.

    Priority:
        1. Explicit model from caller (passthrough)
        2. Purpose → tier → first available provider model
        3. Default fallback (gateway's DEFAULT_CHAT_MODEL)
    """

    def __init__(self, available_providers: set[str] | None = None):
        """
        Args:
            available_providers: Set of provider names with active API keys.
                e.g. {"gemini", "anthropic", "local"}
        """
        self.available_providers = available_providers or set()

    # Provider name for each model prefix
    _MODEL_PROVIDER = {
        "gemini": "gemini",
        "gpt": "openai",
        "claude": "anthropic",
        "local": "local",
    }

    def select(self, purpose: str, explicit_model: str | None = None,
               default_model: str = "gemini-2.5-flash") -> str:
        """
        Select the best model for the given purpose.

        Args:
            purpose: e.g. "defect_triage", "steering_pack"
            explicit_model: If set, use this model directly
            default_model: Fallback if no tier match

        Returns:
            Model name string
        """
        # 1. Explicit override — always honour
        if explicit_model:
            return explicit_model

        # 2. Look up purpose → tier → model list
        tier_name = PURPOSE_MODEL_MAP.get(purpose, "balanced")
        candidates = MODEL_TIERS.get(tier_name, MODEL_TIERS["balanced"])

        # 3. Pick first model whose provider is available
        for model in candidates:
            provider = self._model_to_provider(model)
            if provider in self.available_providers:
                logger.debug(
                    "ModelSelector: purpose=%s tier=%s → model=%s (provider=%s)",
                    purpose, tier_name, model, provider,
                )
                return model

        # 4. If no real provider available, use default (may be local-stub)
        logger.debug(
            "ModelSelector: no provider available for tier=%s, using default=%s",
            tier_name, default_model,
        )
        return default_model

    def get_fallback_chain(self, model: str) -> list[str]:
        """
        Build a fallback chain for a model.
        If primary model fails, try next models in the same tier,
        then try models from lower tiers.

        Returns:
            Ordered list of fallback models (excluding the primary).
        """
        primary_tier = None
        for tier_name, models in MODEL_TIERS.items():
            if model in models:
                primary_tier = tier_name
                break

        fallbacks = []
        tier_order = ["fast", "balanced", "strong"]

        if primary_tier:
            # Same tier first (excluding primary)
            for m in MODEL_TIERS[primary_tier]:
                if m != model and self._is_available(m):
                    fallbacks.append(m)

            # Then lower tiers
            primary_idx = tier_order.index(primary_tier) if primary_tier in tier_order else 1
            for i in range(primary_idx - 1, -1, -1):
                for m in MODEL_TIERS[tier_order[i]]:
                    if m not in fallbacks and m != model and self._is_available(m):
                        fallbacks.append(m)

        # Always include local-stub as last resort
        if "local" in self.available_providers and "local-stub" not in fallbacks:
            fallbacks.append("local-stub")

        return fallbacks

    def _is_available(self, model: str) -> bool:
        """Check if a model's provider is available."""
        provider = self._model_to_provider(model)
        return provider in self.available_providers

    @staticmethod
    def _model_to_provider(model: str) -> str:
        """Map model name to provider name."""
        for prefix, provider in ModelSelector._MODEL_PROVIDER.items():
            if model.startswith(prefix):
                return provider
        return "local"
