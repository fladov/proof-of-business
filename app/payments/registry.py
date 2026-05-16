"""Payment provider registry."""

from __future__ import annotations

from dataclasses import dataclass

from app.settings import Settings

from .providers.squad import SquadPaymentProvider


@dataclass(slots=True)
class PaymentProviderRegistry:
    settings: Settings

    def list_providers(self) -> list[dict[str, str]]:
        return [{"key": "squad", "display_name": "Squad", "description": "PoB-hosted payment flow powered by Squad."}]

    def resolve(self, provider_key: str):
        normalized = provider_key.strip().lower()
        if normalized == "squad":
            return SquadPaymentProvider(self.settings)
        raise KeyError(f"Unsupported payment provider: {provider_key}")
