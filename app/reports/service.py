"""Service layer for generating Fladov passports."""

from __future__ import annotations

from app.fladov.service import FladovRepositoryService
from app.payments.models import PaymentSummary
from app.settings import Settings, get_settings
from app.reports.composer import build_passport_view


def generate_fladov_passport(
    business_slug: str,
    settings: Settings | None = None,
    theme: str = "light",
    payment_summary: PaymentSummary | None = None,
    selected_invoice=None,
    invoice_preview_template_html: str = "",
) -> dict:
    settings = settings or get_settings()
    export = FladovRepositoryService(settings).get_business_export(business_slug)
    passport = build_passport_view(
        export,
        theme=theme,
        payment_summary=payment_summary,
        selected_invoice=selected_invoice,
        invoice_preview_template_html=invoice_preview_template_html,
    )
    return passport.to_dict()
