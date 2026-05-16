"""Pydantic models for payment API routes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreatePaymentIntentRequest(BaseModel):
    business_slug: str
    business_name: str | None = None
    amount: float = Field(gt=0)
    currency: str = Field(default="NGN")
    theme: str = Field(default="light")
    note: str | None = None
    return_url: str | None = None
    invoice_id: str | None = None


class CreatePaymentIntentResponse(BaseModel):
    checkout_url: str
    payment: dict


class PaymentStatusResponse(BaseModel):
    payment: dict
