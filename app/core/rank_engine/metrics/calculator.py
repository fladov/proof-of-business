"""Compute reusable shared metrics from normalized business evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from statistics import mean

from ..config import DIMINISHING_SCALES, EVIDENCE_DEPTH_WEIGHTS, STATUS_GROUPS
from ..evidence.graph import EvidenceGraph
from ..normalization.pipeline import NormalizedPayload
from .utils import clamp, diminishing, linear_score, months_between, safe_ratio


def compute_shared_metrics(normalized: NormalizedPayload, graph: EvidenceGraph) -> dict[str, float | int | str | dict | list]:
    records = normalized.active_records
    all_timestamps = _collect_activity_timestamps(records)
    revenue_series, expense_series = _build_cashflow_series(records["cashbook_entries"])
    order_dates = [item["order_date"] for item in records["orders"] if item.get("order_date")]
    verified_payment_dates = [item.get("verified_at") or item.get("paid_at") or item.get("created_at") for item in records["verified_payments"]]

    evidence_depth_score = _evidence_depth(records)
    activity = _activity_continuity(all_timestamps, normalized.payload.business.joined_at, normalized.generated_at)
    coherence = _record_coherence(records, graph)
    payment = _payment_integrity(records, graph)
    fulfillment = _fulfillment(records, graph)
    cashflow = _cashflow_stability(revenue_series, expense_series, activity["longest_gap_days"])
    customer = _customer_quality(records["orders"], order_dates)
    growth = _growth(records, order_dates, revenue_series, verified_payment_dates)
    document = _document_discipline(records["transaction_documents"], graph)
    operational = _operational_maturity(records, graph, document["document_discipline_score"])
    audit = _audit_integrity(records["operation_logs"], graph)
    history_length_score = clamp(months_between(normalized.payload.business.joined_at, normalized.generated_at) / 12.0)
    coverage = _evidence_category_coverage(records)
    deleted_ratio = _deleted_record_ratio(normalized)
    expense_pressure = _expense_pressure(revenue_series, expense_series)
    product_presence = 1.0 if records["products"] else 0.3 if records["orders"] else 0.0

    metrics: dict[str, float | int | str | dict | list] = {
        "evidence_depth_score": evidence_depth_score,
        "activity_continuity_score": activity["activity_continuity_score"],
        "active_month_ratio": activity["active_month_ratio"],
        "recency_score": activity["recency_score"],
        "burst_concentration_score": activity["burst_concentration_score"],
        "longest_gap_days": activity["longest_gap_days"],
        "record_coherence_score": coherence["record_coherence_score"],
        "orphan_record_ratio": coherence["orphan_record_ratio"],
        "payment_integrity_score": payment["payment_integrity_score"],
        "completed_cashbook_ratio": payment["completed_cashbook_ratio"],
        "verified_payment_coverage_ratio": payment["verified_payment_coverage_ratio"],
        "successful_verified_payment_ratio": payment["successful_verified_payment_ratio"],
        "payment_operation_match_score": payment["payment_operation_match_score"],
        "payment_timing_consistency": payment["payment_timing_consistency"],
        "failed_payment_ratio": payment["failed_payment_ratio"],
        "low_failed_payment_score": 1.0 - payment["failed_payment_ratio"],
        "fulfillment_reliability_components": fulfillment,
        "fulfilled_or_completed_order_ratio": fulfillment["fulfilled_or_completed_order_ratio"],
        "fulfilled_and_paid_ratio": fulfillment["fulfilled_and_paid_ratio"],
        "canceled_order_ratio": fulfillment["canceled_order_ratio"],
        "paid_unfulfilled_ratio": fulfillment["paid_unfulfilled_ratio"],
        "document_support_score": fulfillment["document_support_score"],
        "cashflow_stability_components": cashflow,
        "income_regularity_score": cashflow["income_regularity_score"],
        "expense_regularity_score": cashflow["expense_regularity_score"],
        "low_income_volatility_score": cashflow["low_income_volatility_score"],
        "low_gap_score": cashflow["low_gap_score"],
        "customer_quality_components": customer,
        "customer_diversity_score": customer["customer_diversity_score"],
        "repeat_customer_signal": customer["repeat_customer_signal"],
        "customer_concentration_ratio": customer["customer_concentration_ratio"],
        "low_customer_concentration": 1.0 - customer["customer_concentration_ratio"],
        "customer_activity_continuity": customer["customer_activity_continuity"],
        "growth_components": growth,
        "order_activity_trend_score": growth["order_activity_trend_score"],
        "cashbook_income_trend_score": growth["cashbook_income_trend_score"],
        "verified_payment_trend_score": growth["verified_payment_trend_score"],
        "customer_growth_trend_score": growth["customer_growth_trend_score"],
        "document_usage_trend_score": growth["document_usage_trend_score"],
        "product_catalog_growth_score": growth["product_catalog_growth_score"],
        "growth_naturalness_score": growth["growth_naturalness_score"],
        "document_discipline_score": document["document_discipline_score"],
        "non_preview_document_ratio": document["non_preview_document_ratio"],
        "linked_document_ratio": document["linked_document_ratio"],
        "document_amount_match_ratio": document["document_amount_match_ratio"],
        "file_presence_ratio": document["file_presence_ratio"],
        "document_type_diversity_score": document["document_type_diversity_score"],
        "operational_maturity_score_component": operational["operational_maturity_score_component"],
        "product_setup_quality": operational["product_setup_quality"],
        "record_linkage_score": operational["record_linkage_score"],
        "cashbook_discipline_score": operational["cashbook_discipline_score"],
        "fladov_activity_consistency": operational["fladov_activity_consistency"],
        "purchase_or_expense_reality": operational["purchase_or_expense_reality"],
        "low_orphan_record_score": operational["low_orphan_record_score"],
        "audit_integrity_score": audit["audit_integrity_score"],
        "operation_log_success_ratio": audit["operation_log_success_ratio"],
        "operation_source_distribution": audit["operation_source_distribution"],
        "history_length_score": history_length_score,
        "evidence_category_coverage": coverage,
        "verified_payment_coverage": payment["verified_payment_coverage_ratio"],
        "product_or_service_presence": product_presence,
        "reputation_signal": 0.5,
        "payment_supported_demand": safe_ratio(payment["verified_payment_coverage_ratio"] + payment["payment_operation_match_score"], 2.0),
        "low_expense_pressure_score": 1.0 - expense_pressure,
        "deleted_record_ratio": deleted_ratio,
        "counts": {group: len(items) for group, items in records.items()},
    }
    return metrics


def _evidence_depth(records: dict[str, list[dict]]) -> float:
    total = 0.0
    for group, weight in EVIDENCE_DEPTH_WEIGHTS.items():
        total += diminishing(len(records[group]), DIMINISHING_SCALES[group]) * weight
    return clamp(total)


def _activity_continuity(activity_dates: list[datetime], joined_at: datetime, generated_at: datetime) -> dict[str, float]:
    if not activity_dates:
        return {
            "activity_continuity_score": 0.0,
            "active_month_ratio": 0.0,
            "recency_score": 0.0,
            "burst_concentration_score": 1.0,
            "longest_gap_days": max(0, (generated_at - joined_at).days),
        }
    ordered = sorted(activity_dates)
    active_months = {(dt.year, dt.month) for dt in ordered}
    total_months = max(1.0, months_between(joined_at, generated_at) + 1.0)
    active_month_ratio = clamp(len(active_months) / total_months)
    recency_days = max(0.0, (generated_at - ordered[-1]).days)
    recency_score = clamp(1.0 - (recency_days / 180.0))

    gaps = [(right - left).days for left, right in zip(ordered, ordered[1:])]
    longest_gap_days = max(gaps, default=max(0, (generated_at - ordered[-1]).days))
    gap_score = clamp(1.0 - (longest_gap_days / 180.0))

    month_counts = Counter((dt.year, dt.month) for dt in ordered)
    dominant_share = safe_ratio(max(month_counts.values(), default=0), len(ordered), default=1.0)
    burst_concentration_score = dominant_share
    anti_burst_score = 1.0 - dominant_share
    score = clamp((active_month_ratio * 0.35) + (recency_score * 0.25) + (gap_score * 0.25) + (anti_burst_score * 0.15))

    return {
        "activity_continuity_score": score,
        "active_month_ratio": active_month_ratio,
        "recency_score": recency_score,
        "burst_concentration_score": burst_concentration_score,
        "longest_gap_days": float(longest_gap_days),
    }


def _record_coherence(records: dict[str, list[dict]], graph: EvidenceGraph) -> dict[str, float]:
    order_agreement = []
    for order in records["orders"]:
        expected_balance = max(0.0, order.get("total_payable", 0.0) - order.get("total_paid", 0.0))
        paid_status = order.get("payment_status") in STATUS_GROUPS["paid"]
        balance_match = abs(expected_balance - order.get("balance_remaining", 0.0)) <= 1.0
        status_match = paid_status == (order.get("balance_remaining", 0.0) <= 1.0)
        order_agreement.append(1.0 if balance_match and status_match else 0.0)

    purchase_agreement = []
    for purchase in records["purchases"]:
        subtotal = purchase.get("items_subtotal", purchase.get("total_paid", 0.0))
        expected_balance = max(0.0, subtotal - purchase.get("total_paid", 0.0))
        balance_match = abs(expected_balance - purchase.get("balance_remaining", 0.0)) <= 1.0
        purchase_agreement.append(1.0 if balance_match else 0.0)

    valid_cashbook_links = sum(1 for item in graph.cashbook_links if item["operation"] is not None)
    valid_document_links = sum(1 for item in graph.document_links if item["operation"] is not None)
    valid_payment_links = sum(
        1 for item in graph.cashbook_links
        if item["verified_payment"] is not None and item["verified_payment"].get("status") in STATUS_GROUPS["successful_payment"]
    )
    orphan_ratio = safe_ratio(graph.orphan_record_count, graph.total_linkable_records, default=0.0)
    linkage_score = safe_ratio(
        valid_cashbook_links + valid_document_links + valid_payment_links,
        (len(graph.cashbook_links) * 2) + len(graph.document_links),
        default=0.0,
    )
    agreement_score = mean(order_agreement + purchase_agreement) if (order_agreement or purchase_agreement) else 0.5
    score = clamp((agreement_score * 0.45) + (linkage_score * 0.40) + ((1.0 - orphan_ratio) * 0.15))
    return {"record_coherence_score": score, "orphan_record_ratio": orphan_ratio}


def _payment_integrity(records: dict[str, list[dict]], graph: EvidenceGraph) -> dict[str, float]:
    cashbook_entries = records["cashbook_entries"]
    completed_cashbook_ratio = safe_ratio(
        sum(1 for item in cashbook_entries if item.get("status") in STATUS_GROUPS["paid"]),
        len(cashbook_entries),
        default=0.0,
    )
    linked_verified = [item for item in graph.cashbook_links if item["verified_payment"] is not None]
    verified_payment_coverage_ratio = safe_ratio(len(linked_verified), len(cashbook_entries), default=0.0)
    verified_payments = records["verified_payments"]
    successful_verified_payment_ratio = safe_ratio(
        sum(1 for item in verified_payments if item.get("status") in STATUS_GROUPS["successful_payment"]),
        len(verified_payments),
        default=0.0,
    )
    failed_payment_ratio = safe_ratio(
        sum(1 for item in verified_payments if item.get("status") in STATUS_GROUPS["failed_payment"]),
        len(verified_payments),
        default=0.0,
    )

    matches = []
    timing_matches = []
    for link in linked_verified:
        cashbook = link["cashbook_entry"]
        payment = link["verified_payment"]
        matches.append(1.0 if abs(cashbook.get("amount", 0.0) - payment.get("amount", 0.0)) <= 1.0 else 0.0)
        event_time = payment.get("paid_at") or payment.get("verified_at") or payment.get("created_at")
        if event_time:
            days = abs((event_time - cashbook.get("effective_date")).days)
            timing_matches.append(clamp(1.0 - (days / 14.0)))
    payment_operation_match_score = mean(matches) if matches else 0.0
    payment_timing_consistency = mean(timing_matches) if timing_matches else 0.0
    score = clamp(
        (completed_cashbook_ratio * 0.20)
        + (verified_payment_coverage_ratio * 0.25)
        + (successful_verified_payment_ratio * 0.20)
        + (payment_operation_match_score * 0.20)
        + (payment_timing_consistency * 0.10)
        + ((1.0 - failed_payment_ratio) * 0.05)
    )
    return {
        "payment_integrity_score": score,
        "completed_cashbook_ratio": completed_cashbook_ratio,
        "verified_payment_coverage_ratio": verified_payment_coverage_ratio,
        "successful_verified_payment_ratio": successful_verified_payment_ratio,
        "payment_operation_match_score": payment_operation_match_score,
        "payment_timing_consistency": payment_timing_consistency,
        "failed_payment_ratio": failed_payment_ratio,
    }


def _fulfillment(records: dict[str, list[dict]], graph: EvidenceGraph) -> dict[str, float]:
    orders = records["orders"]
    if not orders:
        return {
            "fulfilled_or_completed_order_ratio": 0.0,
            "fulfilled_and_paid_ratio": 0.0,
            "canceled_order_ratio": 0.0,
            "paid_unfulfilled_ratio": 0.0,
            "document_support_score": 0.0,
        }
    fulfilled = [item for item in orders if item.get("status") in STATUS_GROUPS["fulfilled"]]
    paid = [item for item in orders if item.get("payment_status") in STATUS_GROUPS["paid"] or item.get("total_paid", 0.0) >= item.get("total_payable", 0.0) - 1.0]
    canceled = [item for item in orders if item.get("status") in STATUS_GROUPS["canceled"]]
    paid_unfulfilled = [
        item for item in orders
        if item in paid and item not in fulfilled and item not in canceled
    ]
    order_ids_with_docs = {link["operation"]["id"] for link in graph.document_links if link["operation"] and link["operation"].get("id")}
    doc_support = safe_ratio(sum(1 for item in orders if item["id"] in order_ids_with_docs), len(orders), default=0.0)
    return {
        "fulfilled_or_completed_order_ratio": safe_ratio(len(fulfilled), len(orders), default=0.0),
        "fulfilled_and_paid_ratio": safe_ratio(sum(1 for item in fulfilled if item in paid), len(orders), default=0.0),
        "canceled_order_ratio": safe_ratio(len(canceled), len(orders), default=0.0),
        "paid_unfulfilled_ratio": safe_ratio(len(paid_unfulfilled), len(orders), default=0.0),
        "document_support_score": doc_support,
    }


def _cashflow_stability(revenue_series: list[float], expense_series: list[float], longest_gap_days: float) -> dict[str, float]:
    income_regularity_score = _regularity_score(revenue_series)
    expense_regularity_score = _regularity_score(expense_series)
    low_income_volatility_score = 1.0 - _volatility_score(revenue_series)
    low_gap_score = clamp(1.0 - (longest_gap_days / 180.0))
    return {
        "income_regularity_score": income_regularity_score,
        "expense_regularity_score": expense_regularity_score,
        "low_income_volatility_score": low_income_volatility_score,
        "low_gap_score": low_gap_score,
    }


def _customer_quality(orders: list[dict], order_dates: list[datetime]) -> dict[str, float]:
    customer_counts = Counter(order.get("customer_contact_id") for order in orders if order.get("customer_contact_id"))
    unique_customers = len(customer_counts)
    total_orders = len(orders)
    repeat_customers = sum(1 for count in customer_counts.values() if count > 1)
    concentration = safe_ratio(max(customer_counts.values(), default=0), total_orders, default=0.0)
    customer_diversity_score = clamp(unique_customers / max(total_orders, 1))
    repeat_signal = safe_ratio(repeat_customers, max(unique_customers, 1), default=0.0)
    activity = _activity_continuity(order_dates, min(order_dates, default=datetime.now(order_dates[0].tzinfo) if order_dates else datetime.now()), max(order_dates, default=datetime.now()))
    return {
        "customer_diversity_score": customer_diversity_score,
        "repeat_customer_signal": repeat_signal,
        "customer_concentration_ratio": concentration,
        "customer_activity_continuity": activity["active_month_ratio"] if order_dates else 0.0,
    }


def _growth(records: dict[str, list[dict]], order_dates: list[datetime], revenue_series: list[float], verified_payment_dates: list[datetime | None]) -> dict[str, float]:
    order_activity_trend_score = _trend_score_from_dates(order_dates)
    cashbook_income_trend_score = _trend_score_from_series(revenue_series)
    verified_payment_trend_score = _trend_score_from_dates([dt for dt in verified_payment_dates if dt])
    customer_growth_trend_score = _trend_score_from_dates(order_dates)
    document_usage_trend_score = _trend_score_from_dates([item["created_at"] for item in records["transaction_documents"] if item.get("created_at")])
    product_catalog_growth_score = _trend_score_from_dates([item["created_at"] for item in records["products"] if item.get("created_at")])
    burst_score = _activity_continuity(_collect_activity_timestamps(records), records["products"][0]["created_at"] if records["products"] else (order_dates[0] if order_dates else datetime.now()), datetime.now(order_dates[0].tzinfo) if order_dates else datetime.now())["burst_concentration_score"] if (records["products"] or order_dates) else 1.0
    growth_naturalness_score = clamp(1.0 - burst_score)
    return {
        "order_activity_trend_score": order_activity_trend_score,
        "cashbook_income_trend_score": cashbook_income_trend_score,
        "verified_payment_trend_score": verified_payment_trend_score,
        "customer_growth_trend_score": customer_growth_trend_score,
        "document_usage_trend_score": document_usage_trend_score,
        "product_catalog_growth_score": product_catalog_growth_score,
        "growth_naturalness_score": growth_naturalness_score,
    }


def _document_discipline(documents: list[dict], graph: EvidenceGraph) -> dict[str, float]:
    if not documents:
        return {
            "document_discipline_score": 0.0,
            "non_preview_document_ratio": 0.0,
            "linked_document_ratio": 0.0,
            "document_amount_match_ratio": 0.0,
            "file_presence_ratio": 0.0,
            "document_type_diversity_score": 0.0,
        }
    non_preview_ratio = safe_ratio(sum(1 for item in documents if not item.get("is_preview", False)), len(documents), default=0.0)
    linked_ratio = safe_ratio(sum(1 for item in graph.document_links if item["operation"] is not None), len(documents), default=0.0)
    amount_matches = []
    for link in graph.document_links:
        document = link["document"]
        operation = link["operation"]
        if operation is None:
            continue
        op_amount = operation.get("total_payable", operation.get("items_subtotal", operation.get("total_amount", 0.0)))
        amount_matches.append(1.0 if abs(document.get("document_total_amount", 0.0) - op_amount) <= 1.0 else 0.0)
    amount_match_ratio = mean(amount_matches) if amount_matches else 0.0
    file_presence_ratio = safe_ratio(sum(1 for item in documents if item.get("file_path_present")), len(documents), default=0.0)
    type_diversity = clamp(len({item.get("document_type") for item in documents}) / 4.0)
    score = clamp(
        (non_preview_ratio * 0.20)
        + (linked_ratio * 0.30)
        + (amount_match_ratio * 0.20)
        + (file_presence_ratio * 0.15)
        + (type_diversity * 0.15)
    )
    return {
        "document_discipline_score": score,
        "non_preview_document_ratio": non_preview_ratio,
        "linked_document_ratio": linked_ratio,
        "document_amount_match_ratio": amount_match_ratio,
        "file_presence_ratio": file_presence_ratio,
        "document_type_diversity_score": type_diversity,
    }


def _operational_maturity(records: dict[str, list[dict]], graph: EvidenceGraph, document_discipline_score: float) -> dict[str, float]:
    product_setup_quality = clamp(mean(
        [
            safe_ratio(item.get("media_count", 0.0), 3.0, default=0.0) * 0.4
            + (1.0 if item.get("primary_price", 0.0) > 0 else 0.0) * 0.4
            + (1.0 if item.get("current_stock_quantity") is not None else 0.0) * 0.2
            for item in records["products"]
        ]
    ) if records["products"] else 0.0)
    record_linkage_score = 1.0 - safe_ratio(graph.orphan_record_count, graph.total_linkable_records, default=0.0)
    cashbook_discipline_score = safe_ratio(
        sum(1 for item in graph.cashbook_links if item["operation"] is not None and item["cashbook_entry"].get("status") in STATUS_GROUPS["paid"]),
        len(graph.cashbook_links),
        default=0.0,
    )
    used_modules = sum(1 for group, items in records.items() if items)
    fladov_activity_consistency = clamp(used_modules / len(records))
    purchase_or_expense_reality = clamp(
        0.6 if records["purchases"] else 0.0
        + 0.4 if records["general_financial_operations"] else 0.0
    )
    low_orphan_record_score = record_linkage_score
    return {
        "operational_maturity_score_component": clamp(
            (product_setup_quality * 0.10)
            + (document_discipline_score * 0.15)
            + (record_linkage_score * 0.25)
            + (cashbook_discipline_score * 0.15)
            + (fladov_activity_consistency * 0.15)
            + (purchase_or_expense_reality * 0.10)
            + (low_orphan_record_score * 0.10)
        ),
        "product_setup_quality": product_setup_quality,
        "record_linkage_score": record_linkage_score,
        "cashbook_discipline_score": cashbook_discipline_score,
        "fladov_activity_consistency": fladov_activity_consistency,
        "purchase_or_expense_reality": purchase_or_expense_reality,
        "low_orphan_record_score": low_orphan_record_score,
    }


def _audit_integrity(operation_logs: list[dict], graph: EvidenceGraph) -> dict[str, float]:
    if not operation_logs:
        return {
            "audit_integrity_score": 0.0,
            "operation_log_success_ratio": 0.0,
            "operation_source_distribution": 0.0,
        }
    success_ratio = safe_ratio(sum(1 for log in operation_logs if log.get("is_successful")), len(operation_logs), default=0.0)
    sources = Counter(log.get("source") for log in operation_logs if log.get("source"))
    source_distribution = clamp(len(sources) / 3.0)
    orphan_ratio = safe_ratio(len(graph.orphan_log_ids), len(operation_logs), default=0.0)
    return {
        "audit_integrity_score": clamp((success_ratio * 0.6) + (source_distribution * 0.2) + ((1.0 - orphan_ratio) * 0.2)),
        "operation_log_success_ratio": success_ratio,
        "operation_source_distribution": source_distribution,
    }


def _evidence_category_coverage(records: dict[str, list[dict]]) -> float:
    covered = sum(1 for items in records.values() if items)
    return clamp(covered / len(records))


def _deleted_record_ratio(normalized: NormalizedPayload) -> float:
    active_count = sum(len(items) for items in normalized.active_records.values())
    deleted_count = sum(len(items) for items in normalized.deleted_records.values())
    return safe_ratio(deleted_count, active_count + deleted_count, default=0.0)


def _expense_pressure(revenue_series: list[float], expense_series: list[float]) -> float:
    return clamp(safe_ratio(sum(expense_series), sum(revenue_series), default=0.5))


def _collect_activity_timestamps(records: dict[str, list[dict]]) -> list[datetime]:
    timestamps: list[datetime] = []
    candidate_keys = ("created_at", "updated_at", "order_date", "purchase_date", "operation_date", "effective_date", "verified_at", "paid_at")
    for items in records.values():
        for item in items:
            for key in candidate_keys:
                value = item.get(key)
                if isinstance(value, datetime):
                    timestamps.append(value)
                    break
    return timestamps


def _build_cashflow_series(entries: list[dict]) -> tuple[list[float], list[float]]:
    income_buckets: dict[tuple[int, int], float] = defaultdict(float)
    expense_buckets: dict[tuple[int, int], float] = defaultdict(float)
    for entry in entries:
        date = entry.get("effective_date")
        if not isinstance(date, datetime):
            continue
        key = (date.year, date.month)
        if entry.get("type") in {"income", "credit", "inflow"}:
            income_buckets[key] += entry.get("amount", 0.0)
        else:
            expense_buckets[key] += abs(entry.get("amount", 0.0))
    ordered_keys = sorted(set(income_buckets) | set(expense_buckets))
    return [income_buckets[key] for key in ordered_keys], [expense_buckets[key] for key in ordered_keys]


def _regularity_score(series: list[float]) -> float:
    if not series:
        return 0.0
    active = sum(1 for value in series if value > 0)
    return clamp(active / len(series))


def _volatility_score(series: list[float]) -> float:
    if len(series) < 2:
        return 0.0 if series else 1.0
    average = sum(series) / len(series)
    if average <= 0:
        return 1.0
    variance = sum((value - average) ** 2 for value in series) / len(series)
    std_dev = variance ** 0.5
    return clamp(std_dev / average)


def _trend_score_from_series(series: list[float]) -> float:
    if len(series) < 2:
        return 0.5 if series else 0.0
    midpoint = len(series) // 2
    first = sum(series[:midpoint]) or 0.0
    second = sum(series[midpoint:]) or 0.0
    if first == 0 and second > 0:
        return 0.8
    if first == 0 and second == 0:
        return 0.0
    ratio = safe_ratio(second - first, abs(first), default=0.0)
    return clamp(0.5 + (ratio * 0.5))


def _trend_score_from_dates(dates: list[datetime]) -> float:
    if len(dates) < 2:
        return 0.5 if dates else 0.0
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for dt in dates:
        counts[(dt.year, dt.month)] += 1
    return _trend_score_from_series([counts[key] for key in sorted(counts)])
