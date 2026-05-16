"""Shared Fladov repository contracts for Proof of Business."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class FladovInvoiceLineItem:
    description: str
    quantity: float
    unit_price: float
    total_amount: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FladovInvoiceLineItem":
        return cls(
            description=payload["description"],
            quantity=float(payload["quantity"]),
            unit_price=float(payload["unit_price"]),
            total_amount=float(payload["total_amount"]),
        )


@dataclass(slots=True)
class FladovInvoice:
    id: str
    business_slug: str
    invoice_type: str
    invoice_number: str
    status: str
    issued_at: str
    expires_at: str | None
    customer_name: str
    customer_email: str | None
    currency: str
    subtotal: float
    discount_total: float
    tax_total: float
    total_amount: float
    balance_due: float
    line_items: list[FladovInvoiceLineItem] = field(default_factory=list)
    note: str | None = None
    invoice_url: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FladovInvoice":
        return cls(
            id=payload["id"],
            business_slug=payload["business_slug"],
            invoice_type=payload["invoice_type"],
            invoice_number=payload["invoice_number"],
            status=payload["status"],
            issued_at=payload["issued_at"],
            expires_at=payload.get("expires_at"),
            customer_name=payload["customer_name"],
            customer_email=payload.get("customer_email"),
            currency=payload["currency"],
            subtotal=float(payload["subtotal"]),
            discount_total=float(payload["discount_total"]),
            tax_total=float(payload["tax_total"]),
            total_amount=float(payload["total_amount"]),
            balance_due=float(payload["balance_due"]),
            line_items=[FladovInvoiceLineItem.from_dict(item) for item in payload.get("line_items", [])],
            note=payload.get("note"),
            invoice_url=payload.get("invoice_url"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FladovBusinessSummary:
    """Lightweight browseable business identity."""

    id: str
    slug: str
    display_name: str
    avatar_url: str
    avatar_placeholder_url: str
    profile_url: str
    pob_schema_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FladovBusinessExport:
    """Full Fladov-native export payload for a single business."""

    id: str
    slug: str
    display_name: str
    avatar_url: str
    avatar_placeholder_url: str
    profile_url: str
    pob_schema_version: str
    post_payment_webhook_url: str
    source: dict[str, Any]
    pob_payload: dict[str, Any]
    invoices: list[FladovInvoice] = field(default_factory=list)

    @classmethod
    def from_manifest_entry(cls, entry: dict[str, Any]) -> "FladovBusinessExport":
        return cls(
            id=entry["id"],
            slug=entry["slug"],
            display_name=entry["display_name"],
            avatar_url=entry["avatar_url"],
            avatar_placeholder_url=entry["avatar_placeholder_url"],
            profile_url=entry["profile_url"],
            pob_schema_version=entry["pob_schema_version"],
            post_payment_webhook_url=entry["post_payment_webhook_url"],
            source=dict(entry.get("source", {})),
            pob_payload=dict(entry["pob_payload"]),
            invoices=[FladovInvoice.from_dict(item) for item in entry.get("invoices", [])],
        )

    def to_summary(self) -> FladovBusinessSummary:
        return FladovBusinessSummary(
            id=self.id,
            slug=self.slug,
            display_name=self.display_name,
            avatar_url=self.avatar_url,
            avatar_placeholder_url=self.avatar_placeholder_url,
            profile_url=self.profile_url,
            pob_schema_version=self.pob_schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FladovRepositoryMeta:
    """Top-level Fladov repository metadata."""

    pob_schema_version: str
    post_payment_webhook_url: str
    invoice_preview_template_html: str = ""
    enabled_business_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
