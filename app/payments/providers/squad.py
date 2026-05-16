"""Squad payment adapter."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha512
import hmac
from uuid import uuid4

import httpx
from httpx import HTTPStatusError

from app.settings import Settings

from .base import PaymentInitiation


@dataclass(slots=True)
class SquadPaymentProvider:
    settings: Settings

    provider_key: str = "squad"

    def create_payment(self, *, intent_id: str, business_slug: str, business_name: str, amount: float, currency: str, note: str | None, return_url: str) -> PaymentInitiation:
        if not self.settings.squad_secret_key:
            raise ValueError("SQUAD_SECRET_KEY is required for live payment initiation.")

        payload = {
            "amount": int(round(amount * 100)),
            "currency": currency,
            "transaction_ref": f"pob_{intent_id}",
            "initiate_type": "inline",
            "email": self._synthetic_email(business_slug),
            "customer_name": business_name,
            "metadata": {
                "intent_id": intent_id,
                "business_slug": business_slug,
                "business_name": business_name,
                "note": note or "",
            },
            "callback_url": return_url,
        }

        headers = {"Authorization": f"Bearer {self.settings.squad_secret_key}"}
        response = httpx.post(f"{self.settings.squad_base_url.rstrip('/')}/transaction/initiate", json=payload, headers=headers, timeout=30.0)
        try:
            response.raise_for_status()
        except HTTPStatusError as exc:
            raise ValueError(f"Squad initiation failed: {exc.response.text}") from exc
        body = response.json()
        data = body.get("data") or {}
        checkout_url = data.get("checkout_url") or data.get("checkoutUrl") or body.get("checkout_url") or return_url
        provider_reference = data.get("transaction_ref") or data.get("transactionRef") or payload["transaction_ref"]
        return PaymentInitiation(
            provider=self.provider_key,
            checkout_url=checkout_url,
            provider_reference=provider_reference,
            status=(data.get("transaction_status") or "pending").lower(),
            raw_response=body,
        )

    def verify_transaction(self, transaction_ref: str) -> dict:
        if not self.settings.squad_secret_key:
            raise ValueError("SQUAD_SECRET_KEY is required for transaction verification.")

        headers = {"Authorization": f"Bearer {self.settings.squad_secret_key}"}
        response = httpx.get(
            f"{self.settings.squad_base_url.rstrip('/')}/transaction/verify/{transaction_ref}",
            headers=headers,
            timeout=30.0,
        )
        try:
            response.raise_for_status()
        except HTTPStatusError as exc:
            raise ValueError(f"Squad verification failed: {exc.response.text}") from exc
        return response.json()

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> dict:
        signature = (
            headers.get("x-squad-encrypted-body")
            or headers.get("x-squad-signature")
            or headers.get("x-squad-webhook-signature")
            or headers.get("x-webhook-signature")
            or ""
        )
        expected = hmac.new(self.settings.squad_webhook_secret.encode("utf-8"), raw_body, sha512).hexdigest()
        if not self.settings.squad_webhook_secret or signature.lower() != expected.lower():
            raise ValueError("Invalid Squad webhook signature.")
        return self._parse_json(raw_body)

    @staticmethod
    def _synthetic_email(business_slug: str) -> str:
        safe = business_slug.replace(" ", "").replace("/", "-").lower()
        return f"{safe}@example.com"

    @staticmethod
    def _parse_json(raw_body: bytes) -> dict:
        import json

        return json.loads(raw_body.decode("utf-8"))
