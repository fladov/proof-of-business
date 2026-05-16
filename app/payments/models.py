"""Domain models for payment intents and payment summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .presentation import PAYMENT_CTA_LABEL, present_payment_status


@dataclass(slots=True)
class PaymentIntent:
    intent_id: str
    business_slug: str
    business_name: str
    provider: str
    amount: float
    currency: str
    status: str
    checkout_url: str
    provider_reference: str
    return_url: str
    note: str | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_provider_response: dict[str, Any] = field(default_factory=dict)
    webhook_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return payload


@dataclass(slots=True)
class PaymentSummary:
    enabled: bool
    cta_label: str
    status: str
    status_label: str
    status_class_name: str
    status_message: str
    provider: str
    amount: float
    currency: str
    business_slug: str
    business_name: str
    intent_id: str | None = None
    checkout_url: str | None = None
    return_url: str | None = None
    note: str | None = None
    updated_at: str | None = None

    @classmethod
    def default(cls, business_slug: str, business_name: str, provider: str, amount: float, currency: str) -> "PaymentSummary":
        badge = present_payment_status("not_started")
        return cls(
            enabled=True,
            cta_label=PAYMENT_CTA_LABEL,
            status=badge.status,
            status_label=badge.label,
            status_class_name=badge.class_name,
            status_message=badge.message,
            provider=provider,
            amount=amount,
            currency=currency,
            business_slug=business_slug,
            business_name=business_name,
        )

    @classmethod
    def from_intent(cls, intent: PaymentIntent) -> "PaymentSummary":
        badge = present_payment_status(intent.status)
        return cls(
            enabled=True,
            cta_label=PAYMENT_CTA_LABEL,
            status=badge.status,
            status_label=badge.label,
            status_class_name=badge.class_name,
            status_message=badge.message,
            provider=intent.provider,
            amount=float(intent.amount),
            currency=intent.currency,
            business_slug=intent.business_slug,
            business_name=intent.business_name,
            intent_id=intent.intent_id,
            checkout_url=intent.checkout_url,
            return_url=intent.return_url,
            note=intent.note,
            updated_at=intent.updated_at.isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
