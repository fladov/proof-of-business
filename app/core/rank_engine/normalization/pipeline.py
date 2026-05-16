"""Normalize validated payload data for downstream scoring."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..schema.models import PoBPayload


@dataclass(slots=True)
class NormalizedPayload:
    payload: PoBPayload
    records: dict[str, list[dict[str, Any]]]
    active_records: dict[str, list[dict[str, Any]]]
    deleted_records: dict[str, list[dict[str, Any]]]
    generated_at: datetime


def normalize_payload(payload: PoBPayload) -> NormalizedPayload:
    records = deepcopy(payload.records)
    active_records: dict[str, list[dict[str, Any]]] = {}
    deleted_records: dict[str, list[dict[str, Any]]] = {}

    for group, items in records.items():
        active: list[dict[str, Any]] = []
        deleted: list[dict[str, Any]] = []
        for item in items:
            normalized = _normalize_record(item)
            if normalized.get("deleted_at"):
                deleted.append(normalized)
            else:
                active.append(normalized)
        active_records[group] = active
        deleted_records[group] = deleted

    return NormalizedPayload(
        payload=payload,
        records=records,
        active_records=active_records,
        deleted_records=deleted_records,
        generated_at=payload.export.exported_at.astimezone(timezone.utc),
    )


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    for key, value in list(normalized.items()):
        if isinstance(value, str):
            if key in {"status", "payment_status", "financial_operation_type", "parent_entity_type", "document_type", "operation_name", "source", "type", "provider"}:
                normalized[key] = value.strip().lower()
            else:
                normalized[key] = value.strip()
        elif isinstance(value, datetime) and value.tzinfo is None:
            normalized[key] = value.replace(tzinfo=timezone.utc)
    return normalized
