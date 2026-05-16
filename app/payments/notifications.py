"""Outbound payment notifications for PoB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import logging

import httpx

from app.settings import Settings

from .models import PaymentIntent


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PaymentNotificationResult:
    delivered: bool
    webhook_url: str | None
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    sent_at: str | None = None

    def to_dict(self) -> dict[str, str | bool | int | None]:
        return {
            "delivered": self.delivered,
            "webhook_url": self.webhook_url,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "error": self.error,
            "sent_at": self.sent_at,
        }


@dataclass(slots=True)
class PaymentSuccessWebhookDispatcher:
    settings: Settings

    def dispatch(
        self,
        intent: PaymentIntent,
        source: str,
        verification_payload: dict[str, object] | None = None,
        webhook_url: str | None = None,
    ) -> PaymentNotificationResult:
        webhook_url = (webhook_url or self.settings.payment_success_webhook_url).strip()
        if not webhook_url:
            result = PaymentNotificationResult(
                delivered=False,
                webhook_url=None,
                error="No payment success webhook configured.",
                sent_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info("Payment success webhook skipped for %s: %s", intent.intent_id, result.error)
            return result

        payload = {
            "event": "payment.succeeded",
            "source": source,
            "app_name": self.settings.app_name,
            "public_base_url": self.settings.public_base_url,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "payment": intent.to_dict(),
            "invoice": self._build_invoice_payload(intent),
            "verification_payload": verification_payload or {},
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-PoB-Event": "payment.succeeded",
            "X-PoB-Intent-ID": intent.intent_id,
            "X-PoB-Source": source,
        }
        if self.settings.payment_success_webhook_secret:
            signature = hmac.new(self.settings.payment_success_webhook_secret.encode("utf-8"), body, sha256).hexdigest()
            headers["X-PoB-Signature"] = signature

        try:
            response = httpx.post(
                webhook_url,
                content=body,
                headers=headers,
                timeout=self.settings.payment_success_webhook_timeout_seconds,
            )
            response.raise_for_status()
            result = PaymentNotificationResult(
                delivered=True,
                webhook_url=webhook_url,
                status_code=response.status_code,
                response_body=response.text,
                sent_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info(
                "Payment success webhook delivered for %s to %s with status %s",
                intent.intent_id,
                webhook_url,
                response.status_code,
            )
            return result
        except Exception as exc:  # noqa: BLE001 - log and preserve state for auditability
            result = PaymentNotificationResult(
                delivered=False,
                webhook_url=webhook_url,
                error=str(exc),
                sent_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.exception("Payment success webhook failed for %s to %s", intent.intent_id, webhook_url)
            return result

    @staticmethod
    def _build_invoice_payload(intent: PaymentIntent) -> dict[str, object] | None:
        invoice_id = intent.metadata.get("fladov_invoice_id")
        if not invoice_id:
            return None
        return {
            "id": invoice_id,
            "invoice_number": intent.metadata.get("fladov_invoice_number"),
            "invoice_type": intent.metadata.get("fladov_invoice_type"),
            "total_amount": intent.metadata.get("fladov_invoice_total_amount"),
            "balance_due": intent.metadata.get("fladov_invoice_balance_due"),
        }
