"""Compose user-facing passport payloads from Fladov output."""

from __future__ import annotations

from datetime import datetime
from html import escape
from string import Template

from app.core.rank_engine import generate_fladov_pob_report
from app.fladov.contracts import FladovInvoice
from app.payments.models import PaymentSummary

from .models import PassportInvoicePreview, PassportTab, PassportView, SubScoreItem
from .presentation import confidence_to_badge, score_to_presented


def build_passport_view(
    fladov_export,
    theme: str = "light",
    payment_summary: PaymentSummary | None = None,
    selected_invoice: FladovInvoice | None = None,
    invoice_preview_template_html: str = "",
) -> PassportView:
    result = generate_fladov_pob_report(fladov_export.pob_payload)
    confidence = confidence_to_badge(
        result["confidence"]["confidence_score"],
        result["confidence"]["confidence_level"],
    )
    payment = payment_summary or PaymentSummary.default(
        business_slug=fladov_export.slug,
        business_name=fladov_export.display_name,
        provider="squad",
        amount=selected_invoice.total_amount if selected_invoice is not None else 5000.0,
        currency="NGN",
    )
    invoice_preview = _build_invoice_preview(selected_invoice, invoice_preview_template_html)
    tabs = [
        _customer_tab(result),
        _investor_tab(result),
        _lender_tab(result),
    ]
    tabs[0].visible_by_default = True
    return PassportView(
        business_id=fladov_export.id,
        business_name=fladov_export.display_name,
        business_slug=fladov_export.slug,
        business_primary_category=fladov_export.pob_payload["business"].get("primary_category"),
        business_avatar_url=fladov_export.avatar_url,
        business_profile_url=fladov_export.profile_url,
        pob_schema_version=fladov_export.pob_schema_version,
        post_payment_webhook_url=fladov_export.post_payment_webhook_url,
        theme=theme,
        default_tab="customer",
        confidence=confidence,
        payment=payment,
        selected_invoice=invoice_preview,
        tabs=tabs,
        engine_result=result,
        source_payload=fladov_export.source,
    )


def _build_invoice_preview(invoice: FladovInvoice | None, template_html: str) -> PassportInvoicePreview | None:
    if invoice is None or not template_html:
        return None
    items_html = "".join(
        [
            (
                "<tr>"
                f"<td class=\"px-4 py-3 text-slate-700 dark:text-slate-200\">{escape(item.description)}</td>"
                f"<td class=\"px-4 py-3 text-right text-slate-500 dark:text-slate-400\">{_format_quantity(item.quantity)}</td>"
                f"<td class=\"px-4 py-3 text-right text-slate-500 dark:text-slate-400\">{_format_money(invoice.currency, item.unit_price)}</td>"
                f"<td class=\"px-4 py-3 text-right font-medium text-slate-900 dark:text-white\">{_format_money(invoice.currency, item.total_amount)}</td>"
                "</tr>"
            )
            for item in invoice.line_items
        ]
    )
    preview_html = Template(template_html).safe_substitute(
        invoice_type_label=escape(invoice.invoice_type.replace("_", " ").title()),
        invoice_number=escape(invoice.invoice_number),
        status_label=escape(invoice.status.replace("_", " ").title()),
        customer_name=escape(invoice.customer_name),
        customer_email_html=(
            f"<p class=\"mt-1 text-sm text-slate-500 dark:text-slate-400\">{escape(invoice.customer_email)}</p>"
            if invoice.customer_email
            else ""
        ),
        issued_at_label=escape(_format_date(invoice.issued_at)),
        expires_at_html=(
            f"<p class=\"mt-1 text-sm text-slate-500 dark:text-slate-400\">Expires {_format_date(invoice.expires_at)}</p>"
            if invoice.expires_at
            else ""
        ),
        items_html=items_html,
        note_html=(
            f"<p>{escape(invoice.note)}</p>"
            if invoice.note
            else "<p>This invoice can be paid directly from this Fladov passport.</p>"
        ),
        invoice_link_html=(
            f"<a href=\"{escape(invoice.invoice_url)}\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"inline-flex items-center gap-1.5 font-medium text-brand-700 transition hover:text-brand-600 dark:text-brand-300 dark:hover:text-brand-200\">View full invoice on Fladov</a>"
            if invoice.invoice_url
            else ""
        ),
        subtotal_label=escape(_format_money(invoice.currency, invoice.subtotal)),
        discount_total_label=escape(_format_money(invoice.currency, invoice.discount_total)),
        tax_total_label=escape(_format_money(invoice.currency, invoice.tax_total)),
        total_amount_label=escape(_format_money(invoice.currency, invoice.total_amount)),
        balance_due_label=escape(_format_money(invoice.currency, invoice.balance_due)),
    )
    return PassportInvoicePreview(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        invoice_type=invoice.invoice_type,
        status=invoice.status,
        customer_name=invoice.customer_name,
        currency=invoice.currency,
        total_amount=invoice.total_amount,
        balance_due=invoice.balance_due,
        issued_at=invoice.issued_at,
        expires_at=invoice.expires_at,
        invoice_url=invoice.invoice_url,
        preview_html=preview_html,
    )


def _format_money(currency: str, value: float) -> str:
    return f"{currency} {value:,.2f}"


def _format_quantity(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y")
    except ValueError:
        return value


def _customer_tab(result: dict) -> PassportTab:
    scores = result["scores"]
    main_score = score_to_presented(scores["vendor_trust_score"])
    risk_flags = result["risk"]["risk_flags"]
    risk_notes = [flag["message"] for flag in risk_flags]
    sub_scores = [
        _subscore("Fulfillment reliability", scores["fulfillment_reliability_score"], "How consistently accepted orders end in completion or delivery."),
        _subscore("Payment confidence", scores["payment_confidence_score"], "How much of the payment trail is verified and aligned with the cashbook."),
        _subscore("Proof of business", scores["proof_of_business_score"], "Overall credibility from the evidence trail, activity history, and record coherence."),
    ]
    return PassportTab(
        key="customer",
        title="Customer",
        main_score_label="Vendor trust score",
        main_score_value=scores["vendor_trust_score"],
        main_score_presentation=main_score,
        summary="How safe and reliable the Fladov business appears for a customer-facing transaction.",
        explanation="It centers on order fulfillment, verified payment evidence, and how well the records agree inside Fladov.",
        highlights=[
            "Order completion is the primary trust signal in this view.",
            "Verified payments strengthen the credibility of the cash trail.",
            "Tighter record agreement raises confidence for customers.",
        ],
        sub_scores=sub_scores,
        risk_notes=risk_notes,
        improvement_notes=_improvement_notes("customer", sub_scores, risk_flags),
        visible_by_default=True,
    )


def _investor_tab(result: dict) -> PassportTab:
    scores = result["scores"]
    main_score = score_to_presented(scores["growth_momentum_score"])
    risk_flags = result["risk"]["risk_flags"]
    risk_notes = [flag["message"] for flag in risk_flags]
    sub_scores = [
        _subscore("Proof of business", scores["proof_of_business_score"], "How strong the full evidence trail is across records and linked activity."),
        _subscore("Operational maturity", scores["operational_maturity_score"], "How well the Fladov business uses the activity trail in a structured, repeatable way."),
        _subscore("Customer quality", scores["customer_quality_signal"], "Whether demand looks broad, repeatable, and not overly concentrated."),
    ]
    return PassportTab(
        key="investor",
        title="Investor",
        main_score_label="Growth momentum score",
        main_score_value=scores["growth_momentum_score"],
        main_score_presentation=main_score,
        summary="How strongly the Fladov business appears to be expanding without looking artificial.",
        explanation="It checks for steady traction, broader demand, and growth that does not look backfilled.",
        highlights=[
            "Growth must look steady rather than artificially compressed.",
            "Broader customer spread supports a stronger investor view.",
            "Operational maturity keeps growth from looking inflated.",
        ],
        sub_scores=sub_scores,
        risk_notes=risk_notes,
        improvement_notes=_improvement_notes("investor", sub_scores, risk_flags),
    )


def _lender_tab(result: dict) -> PassportTab:
    scores = result["scores"]
    main_score = score_to_presented(scores["credit_readiness_score"])
    risk_flags = result["risk"]["risk_flags"]
    risk_notes = [flag["message"] for flag in risk_flags]
    sub_scores = [
        _subscore("Cashflow stability", scores["cashflow_stability_score"], "How steady income and expense activity looks across the record history."),
        _subscore("Repayment capacity", scores["repayment_capacity_signal"], "How comfortably the business appears able to support a recurring obligation."),
        _subscore("Payment confidence", scores["payment_confidence_score"], "How reliable the payment evidence is when matched back to cashbook records."),
    ]
    return PassportTab(
        key="lender",
        title="Lender",
        main_score_label="Credit readiness score",
        main_score_value=scores["credit_readiness_score"],
        main_score_presentation=main_score,
        summary="How ready the Fladov business appears to support obligations without overreaching.",
        explanation="It combines cash rhythm, payment reliability, continuity, and operational structure into a lender-facing signal.",
        highlights=[
            "Cashflow stability matters more than one-off spikes.",
            "Verified payment history helps repayment confidence.",
            "Repeated activity over time supports lender readiness.",
        ],
        sub_scores=sub_scores,
        risk_notes=risk_notes,
        improvement_notes=_improvement_notes("lender", sub_scores, risk_flags),
    )


def _improvement_notes(tab_key: str, sub_scores: list[SubScoreItem], risk_flags: list[dict]) -> list[str]:
    score_actions = {
        "Fulfillment reliability": "Improve handoffs from order confirmation to delivery so paid or accepted orders are completed faster and with fewer drop-offs.",
        "Payment confidence": "Push more customer payments through verifiable channels and reconcile them promptly after each sale.",
        "Proof of business": "Capture business activity as it happens so sales, cash movement, and supporting documents leave a clearer operating trail over time.",
        "Operational maturity": "Standardize the day-to-day workflow so orders, logs, inventory movement, and cash updates are recorded the same way each time.",
        "Customer quality": "Grow demand across a wider customer base so the business depends less on a few repeat buyers.",
        "Cashflow stability": "Reduce sharp swings in cash movement by keeping inflows and operating expenses more predictable week to week.",
        "Repayment capacity": "Create more buffer between operating costs and incoming revenue so recurring obligations feel easier to carry.",
        "Growth momentum": "Aim for steadier month-to-month growth instead of sudden spikes that are hard to sustain.",
    }
    flag_actions = {
        "LOW_EVIDENCE_DEPTH": "Run more of the business through Fladov consistently so there is a deeper trail of real operating activity to assess.",
        "LOW_ACTIVITY_CONTINUITY": "Keep activity flowing more consistently across the year so the business does not look dormant for long stretches.",
        "HIGH_ACTIVITY_BURST_CONCENTRATION": "Spread activity more naturally over time instead of clustering too much business into a short period.",
        "LONG_DORMANCY_GAP": "Reduce long inactive gaps by keeping the business active and recording routine operations even in slower periods.",
        "HIGH_ORPHAN_RECORD_RATIO": "Make sure each major sale, payment, and document is created from a real business workflow so fewer records sit in isolation.",
        "PAYMENT_OPERATION_MISMATCH": "Tighten the checkout and reconciliation process so payments, cashbook entries, and underlying sales all point to the same transaction.",
        "LOW_VERIFIED_PAYMENT_COVERAGE": "Encourage more customers to pay through channels that produce verified payment evidence inside the business flow.",
        "HIGH_FAILED_PAYMENT_RATIO": "Reduce failed and reversed payments by confirming customer payment intent earlier and removing friction at checkout.",
        "HIGH_CANCELED_ORDER_RATIO": "Lower order cancellations by improving stock certainty, response times, and expectation setting before confirming an order.",
        "HIGH_PAID_UNFULFILLED_RATIO": "Prioritize fulfillment after payment so customers receive what they paid for without long unresolved delays.",
        "HIGH_CUSTOMER_CONCENTRATION": "Broaden the customer mix so revenue does not rely too heavily on one buyer or a narrow circle.",
        "DOCUMENTS_MOSTLY_PREVIEW_OR_UNLINKED": "Use final supporting documents more consistently as part of the live workflow, not just previews or loose uploads.",
        "SUSPICIOUS_BACKFILL_PATTERN": "Let the activity trail build naturally over time instead of trying to compress too much visible activity into a short window.",
        "HIGH_OPERATION_FAILURE_RATIO": "Reduce failed operational actions by tightening internal processes and resolving issues before they recur.",
        "EXCESSIVE_DELETED_RECORDS": "Reduce cleanup churn by confirming details before entries are created, then correcting issues through cleaner workflows.",
    }

    notes: list[str] = []
    ordered = sorted(sub_scores, key=lambda item: item.value)
    for sub_score in ordered:
        action = score_actions.get(sub_score.label)
        if not action:
            continue
        if sub_score.value < 0.78 or not notes:
            notes.append(action)
        if len(notes) == 2:
            break

    for flag in risk_flags:
        action = flag_actions.get(flag.get("code"))
        if action and action not in notes:
            notes.append(action)
        if len(notes) == 3:
            break

    if not notes:
        notes.append(
            "Keep building a steady operating trail in Fladov so stronger business habits and cleaner evidence continue to reinforce each other."
        )

    if tab_key == "customer" and all("customer" not in note.lower() for note in notes):
        notes.append("Make the customer journey more predictable from payment through delivery so trust improves naturally with each completed order.")
    if tab_key == "investor" and all("growth" not in note.lower() for note in notes):
        notes.append("Show repeatable growth by pairing new demand with disciplined execution, not just higher transaction volume.")
    if tab_key == "lender" and all("cash" not in note.lower() and "obligation" not in note.lower() for note in notes):
        notes.append("Strengthen lender confidence by showing steadier cash discipline and more reliable follow-through after each payment event.")

    deduped: list[str] = []
    for note in notes:
        if note not in deduped:
            deduped.append(note)
    return deduped[:3]
def _subscore(label: str, value: float, note: str) -> SubScoreItem:
    return SubScoreItem(label=label, value=value, note=note, presentation=score_to_presented(value))
