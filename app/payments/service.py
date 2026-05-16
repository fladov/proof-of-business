"""Payment orchestration service for PoB."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from app.fladov.service import FladovRepositoryService
from app.settings import Settings

from .models import PaymentIntent, PaymentSummary
from .notifications import PaymentSuccessWebhookDispatcher
from .registry import PaymentProviderRegistry
from .store import PaymentStore


@dataclass(slots=True)
class PaymentService:
    settings: Settings
    store: PaymentStore | None = None
    _notifier: PaymentSuccessWebhookDispatcher | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = PaymentStore(Path(self.settings.payment_store_path))
        self._notifier = PaymentSuccessWebhookDispatcher(self.settings)

    def get_summary(self, business_slug: str, business_name: str) -> PaymentSummary:
        latest = self.store.latest_for_business(business_slug)
        if latest is None:
            return PaymentSummary.default(
                business_slug=business_slug,
                business_name=business_name,
                provider=self.settings.payment_provider,
                amount=self.settings.payment_default_amount,
                currency=self.settings.payment_currency,
            )
        return PaymentSummary.from_intent(latest)

    def create_intent(
        self,
        *,
        business_slug: str,
        business_name: str,
        amount: float,
        currency: str,
        note: str | None,
        return_url: str,
        invoice_id: str | None = None,
    ) -> PaymentSummary:
        provider = PaymentProviderRegistry(self.settings).resolve(self.settings.payment_provider)
        fladov_service = FladovRepositoryService(self.settings)
        business_export = fladov_service.get_business_export(business_slug)
        business_name = business_name or business_export.display_name
        invoice = fladov_service.get_invoice(business_slug, invoice_id) if invoice_id else None
        resolved_amount = float(invoice.total_amount if invoice else amount)
        intent_id = f"pay_{uuid4().hex[:12]}"
        callback_url = self.build_payment_callback_url(intent_id, return_url)
        initiation = provider.create_payment(
            intent_id=intent_id,
            business_slug=business_slug,
            business_name=business_name,
            amount=resolved_amount,
            currency=currency,
            note=note,
            return_url=callback_url,
        )
        now = datetime.now(timezone.utc)
        intent = PaymentIntent(
            intent_id=intent_id,
            business_slug=business_slug,
            business_name=business_name,
            provider=initiation.provider,
            amount=resolved_amount,
            currency=currency,
            status=initiation.status,
            checkout_url=initiation.checkout_url,
            provider_reference=initiation.provider_reference,
            return_url=return_url,
            note=note,
            created_at=now,
            updated_at=now,
            metadata={
                "payment_provider": self.settings.payment_provider,
                "payment_callback_url": callback_url,
                "fladov_business_id": business_export.id,
                "fladov_business_slug": business_export.slug,
                "fladov_business_display_name": business_export.display_name,
                "fladov_business_profile_url": business_export.profile_url,
                "fladov_post_payment_webhook_url": business_export.post_payment_webhook_url,
                "fladov_pob_schema_version": business_export.pob_schema_version,
            },
            raw_provider_response=initiation.raw_response,
        )
        if invoice is not None:
            intent.metadata.update(
                {
                    "fladov_invoice_id": invoice.id,
                    "fladov_invoice_number": invoice.invoice_number,
                    "fladov_invoice_type": invoice.invoice_type,
                    "fladov_invoice_total_amount": invoice.total_amount,
                    "fladov_invoice_balance_due": invoice.balance_due,
                }
            )
        self.store.save_intent(intent)
        return PaymentSummary.from_intent(intent)

    def get_intent(self, intent_id: str) -> PaymentIntent | None:
        return self.store.get_intent(intent_id)

    def process_webhook(self, raw_body: bytes, headers: dict[str, str]) -> PaymentSummary | None:
        provider = PaymentProviderRegistry(self.settings).resolve(self.settings.payment_provider)
        payload = provider.verify_webhook(raw_body, headers)
        intent_id = payload.get("metadata", {}).get("intent_id") or payload.get("intent_id")
        transaction_ref = payload.get("transaction_ref") or payload.get("transactionRef")
        provider_status = self._normalize_status(payload.get("transaction_status") or payload.get("status") or "pending")
        intent = None
        if intent_id:
            intent = self.store.get_intent(intent_id)
        if intent is None and transaction_ref:
            intent = self.store.find_by_provider_reference(transaction_ref)
        if intent is not None:
            updated = self.store.update_intent_status(intent.intent_id, provider_status, webhook_payload=payload)
            if updated is not None:
                self._maybe_dispatch_success_notification(updated, source="squad_webhook", verification_payload=payload)
                return PaymentSummary.from_intent(updated)
        return None

    def build_passport_return_url(self, business_slug: str, theme: str, invoice_id: str | None = None) -> str:
        base = f"{self.settings.public_base_url.rstrip('/')}/passport/{business_slug}?theme={theme}"
        if invoice_id:
            return self._append_query_params(base, {"pay_invoice": invoice_id})
        return base

    def build_payment_callback_url(self, intent_id: str, final_return_url: str) -> str:
        encoded_return = quote(final_return_url, safe="")
        return f"{self.settings.public_base_url.rstrip('/')}{self.settings.api_route_prefix}/payments/return/{intent_id}?next={encoded_return}"

    def finalize_payment_return(self, intent_id: str, next_url: str | None = None) -> str:
        intent = self.store.get_intent(intent_id)
        if intent is None:
            return self._append_query_params(
                next_url or self.build_passport_return_url("", "light"),
                {
                    "payment_result": "error",
                    "payment_notice": "Payment session not found.",
                },
            )

        provider = PaymentProviderRegistry(self.settings).resolve(intent.provider)
        current = intent
        if current.status not in {"succeeded", "failed", "cancelled", "expired"} and current.provider_reference:
            try:
                verification = provider.verify_transaction(current.provider_reference)
                data = verification.get("data") or {}
                verified_status = self._normalize_status(data.get("transaction_status") or verification.get("status") or current.status)
                if verified_status and verified_status != current.status:
                    updated = self.store.update_intent_status(current.intent_id, verified_status, webhook_payload=data)
                    if updated is not None:
                        current = updated
            except ValueError:
                pass

        if current.status == "succeeded":
            self._maybe_dispatch_success_notification(
                current,
                source="payment_return",
                verification_payload=current.webhook_payload or current.raw_provider_response,
            )

        destination = self._resolve_redirect_destination(
            next_url,
            current.return_url or self.build_passport_return_url(current.business_slug, "light"),
        )
        return self._append_query_params(
            destination,
            {
                "payment_result": current.status,
                "payment_intent": current.intent_id,
                "payment_status": current.status,
                "payment_notice": self._payment_notice_for_status(current.status),
            },
        )

    def _maybe_dispatch_success_notification(self, intent: PaymentIntent, source: str, verification_payload: dict | None) -> None:
        notification_state = intent.metadata.get("post_payment_success_webhook")
        if notification_state:
            return
        notifier = self._notifier or PaymentSuccessWebhookDispatcher(self.settings)
        webhook_url = intent.metadata.get("fladov_post_payment_webhook_url") or self.settings.payment_success_webhook_url
        result = notifier.dispatch(intent, source=source, verification_payload=verification_payload, webhook_url=webhook_url)
        if result.webhook_url:
            intent.metadata["post_payment_success_webhook"] = result.to_dict()
            intent.metadata["post_payment_success_webhook"]["source"] = source
            self.store.save_intent(intent)

    @staticmethod
    def _normalize_status(status: str) -> str:
        normalized = status.strip().lower()
        if normalized in {"success", "successful", "paid", "completed"}:
            return "succeeded"
        if normalized in {"failed", "error", "reversed", "refunded"}:
            return "failed"
        if normalized in {"cancelled", "canceled"}:
            return "cancelled"
        if normalized == "expired":
            return "expired"
        return normalized or "pending"

    @staticmethod
    def _payment_notice_for_status(status: str) -> str:
        normalized = status.strip().lower()
        if normalized == "succeeded":
            return "Payment confirmed and recorded."
        if normalized in {"failed", "cancelled", "expired"}:
            return "Payment did not complete."
        return "Payment status is being confirmed."

    @staticmethod
    def _append_query_params(url: str, params: dict[str, str]) -> str:
        parsed = urlsplit(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update({key: value for key, value in params.items() if value is not None})
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    def _resolve_redirect_destination(self, next_url: str | None, fallback_url: str) -> str:
        if not next_url:
            return fallback_url
        parsed = urlsplit(next_url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            allowed = urlsplit(self.settings.public_base_url)
            if parsed.netloc.lower() == allowed.netloc.lower():
                return next_url
            return fallback_url
        if next_url.startswith("/"):
            return f"{self.settings.public_base_url.rstrip('/')}{next_url}"
        return fallback_url
