"""Presentation helpers for payment status and CTAs."""

from __future__ import annotations

from dataclasses import dataclass


PAYMENT_CTA_LABEL = "Make payment"

PAYMENT_STATUS_STYLES = {
    "not_started": {"label": "Ready", "class_name": "badge-neutral", "message": "No payment has been started for this business yet."},
    "pending": {"label": "Pending", "class_name": "badge-medium", "message": "A payment session exists and is waiting for completion."},
    "processing": {"label": "Processing", "class_name": "badge-medium", "message": "The payment is currently being confirmed."},
    "requires_action": {"label": "Action needed", "class_name": "badge-medium", "message": "The customer still needs to complete the payment flow."},
    "succeeded": {"label": "Paid", "class_name": "badge-high", "message": "The most recent payment was completed successfully."},
    "failed": {"label": "Failed", "class_name": "badge-low", "message": "The most recent payment attempt did not complete."},
    "cancelled": {"label": "Cancelled", "class_name": "badge-low", "message": "The payment was cancelled before completion."},
    "expired": {"label": "Expired", "class_name": "badge-low", "message": "The payment session expired before completion."},
}


@dataclass(slots=True)
class PaymentBadge:
    status: str
    label: str
    class_name: str
    message: str


def present_payment_status(status: str) -> PaymentBadge:
    normalized = (status or "not_started").strip().lower()
    config = PAYMENT_STATUS_STYLES.get(normalized, PAYMENT_STATUS_STYLES["pending"])
    return PaymentBadge(status=normalized, label=config["label"], class_name=config["class_name"], message=config["message"])
