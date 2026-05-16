"""Build linkage-aware evidence graph from normalized records."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..normalization.pipeline import NormalizedPayload


@dataclass(slots=True)
class EvidenceGraph:
    operations_by_type: dict[str, dict[str, dict]]
    verified_payments_by_id: dict[str, dict]
    cashbook_links: list[dict] = field(default_factory=list)
    document_links: list[dict] = field(default_factory=list)
    operation_log_links: list[dict] = field(default_factory=list)
    orphan_cashbook_ids: list[str] = field(default_factory=list)
    orphan_document_ids: list[str] = field(default_factory=list)
    orphan_log_ids: list[str] = field(default_factory=list)
    orphan_record_count: int = 0
    total_linkable_records: int = 0


def build_evidence_graph(normalized: NormalizedPayload) -> EvidenceGraph:
    records = normalized.active_records
    operations_by_type = {
        "order": {item["id"]: item for item in records["orders"]},
        "purchase": {item["id"]: item for item in records["purchases"]},
        "generalfinancialoperation": {item["id"]: item for item in records["general_financial_operations"]},
        "general_financial_operation": {item["id"]: item for item in records["general_financial_operations"]},
        "general_financial_operations": {item["id"]: item for item in records["general_financial_operations"]},
    }
    verified_payments_by_id = {item["id"]: item for item in records["verified_payments"]}

    graph = EvidenceGraph(operations_by_type=operations_by_type, verified_payments_by_id=verified_payments_by_id)

    for entry in records["cashbook_entries"]:
        graph.total_linkable_records += 1
        operation = _resolve_operation(operations_by_type, entry.get("financial_operation_type"), entry.get("financial_operation_id"))
        verified_payment = verified_payments_by_id.get(entry.get("verified_payment_id")) if entry.get("verified_payment_id") else None
        graph.cashbook_links.append(
            {"cashbook_entry": entry, "operation": operation, "verified_payment": verified_payment}
        )
        if operation is None:
            graph.orphan_cashbook_ids.append(entry["id"])
            graph.orphan_record_count += 1

    for document in records["transaction_documents"]:
        graph.total_linkable_records += 1
        operation = _resolve_operation(
            operations_by_type,
            document.get("financial_operation_type"),
            document.get("financial_operation_id"),
        )
        graph.document_links.append({"document": document, "operation": operation})
        if operation is None:
            graph.orphan_document_ids.append(document["id"])
            graph.orphan_record_count += 1

    all_entities = _build_entity_lookup(records)
    for log in records["operation_logs"]:
        graph.total_linkable_records += 1
        entity_type = str(log.get("parent_entity_type", "")).replace("_", "").lower()
        linked = all_entities.get(entity_type, {}).get(log.get("parent_entity_id"))
        graph.operation_log_links.append({"log": log, "entity": linked})
        if linked is None:
            graph.orphan_log_ids.append(log["id"])
            graph.orphan_record_count += 1

    return graph


def _resolve_operation(operations_by_type: dict[str, dict[str, dict]], operation_type: str | None, operation_id: str | None) -> dict | None:
    if not operation_type or not operation_id:
        return None
    key = operation_type.replace("_", "").lower()
    return operations_by_type.get(key, {}).get(operation_id)


def _build_entity_lookup(records: dict[str, list[dict]]) -> dict[str, dict[str, dict]]:
    return {
        "product": {item["id"]: item for item in records["products"]},
        "order": {item["id"]: item for item in records["orders"]},
        "purchase": {item["id"]: item for item in records["purchases"]},
        "generalfinancialoperation": {item["id"]: item for item in records["general_financial_operations"]},
        "cashbookentry": {item["id"]: item for item in records["cashbook_entries"]},
        "transactiondocument": {item["id"]: item for item in records["transaction_documents"]},
        "verifiedpayment": {item["id"]: item for item in records["verified_payments"]},
    }
