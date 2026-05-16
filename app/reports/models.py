"""Report view models for the web app."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.payments.models import PaymentSummary

from .presentation import ConfidenceBadge, PresentedScore


@dataclass(slots=True)
class SubScoreItem:
    label: str
    value: float
    note: str
    presentation: PresentedScore | None = None


@dataclass(slots=True)
class PassportTab:
    key: str
    title: str
    main_score_label: str
    main_score_value: float
    main_score_presentation: PresentedScore | None = None
    summary: str = ""
    explanation: str = ""
    highlights: list[str] = field(default_factory=list)
    sub_scores: list[SubScoreItem] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    improvement_notes: list[str] = field(default_factory=list)
    visible_by_default: bool = False


@dataclass(slots=True)
class PassportInvoicePreview:
    id: str
    invoice_number: str
    invoice_type: str
    status: str
    customer_name: str
    currency: str
    total_amount: float
    balance_due: float
    issued_at: str
    expires_at: str | None
    invoice_url: str | None
    preview_html: str


@dataclass(slots=True)
class PassportView:
    business_id: str
    business_name: str
    business_slug: str
    business_primary_category: str | None
    business_avatar_url: str
    business_profile_url: str
    pob_schema_version: str
    post_payment_webhook_url: str
    theme: str
    default_tab: str
    confidence: ConfidenceBadge
    payment: PaymentSummary
    selected_invoice: PassportInvoicePreview | None
    tabs: list[PassportTab]
    engine_result: dict
    source_payload: dict

    def to_dict(self) -> dict:
        return asdict(self)
