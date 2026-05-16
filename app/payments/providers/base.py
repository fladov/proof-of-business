"""Contracts for payment providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PaymentInitiation:
    provider: str
    checkout_url: str
    provider_reference: str
    status: str
    raw_response: dict


class PaymentProvider(Protocol):
    provider_key: str

    def create_payment(self, *, intent_id: str, business_slug: str, business_name: str, amount: float, currency: str, note: str | None, return_url: str) -> PaymentInitiation:
        raise NotImplementedError

    def verify_transaction(self, transaction_ref: str) -> dict:
        raise NotImplementedError

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> dict:
        raise NotImplementedError
