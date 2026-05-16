"""Payload validation and typed parsing."""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from typing import Any

from ..exceptions import PayloadValidationError
from .models import BusinessInfo, FladovExport, PoBPayload

REQUIRED_RECORD_GROUPS = (
    "products",
    "orders",
    "purchases",
    "general_financial_operations",
    "cashbook_entries",
    "transaction_documents",
    "operation_logs",
    "verified_payments",
)

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "business": ("id", "slug", "name", "joined_at"),
    "export": ("source_system", "exported_at", "export_id", "mode"),
    "products": ("id", "created_at"),
    "orders": ("id", "status", "payment_status", "order_date", "total_payable", "total_paid", "balance_remaining"),
    "purchases": ("id", "status", "purchase_date", "total_paid", "balance_remaining"),
    "general_financial_operations": ("id", "operation_category", "operation_date", "total_amount"),
    "cashbook_entries": ("id", "amount", "effective_date", "status", "type"),
    "transaction_documents": ("id", "financial_operation_type", "financial_operation_id", "document_type", "created_at"),
    "operation_logs": ("id", "parent_entity_type", "parent_entity_id", "operation_name", "is_successful", "created_at"),
    "verified_payments": ("id", "status", "amount", "created_at"),
}

DATE_SUFFIXES = ("_at", "_date")


def validate_payload(payload: dict[str, Any] | PoBPayload) -> PoBPayload:
    if isinstance(payload, PoBPayload):
        return payload
    if not isinstance(payload, dict):
        raise PayloadValidationError("Payload must be a dictionary or PoBPayload instance.")

    schema_version = _require_str(payload, "schema_version")
    export = _parse_export(_require_dict(payload, "export"))
    business = _parse_business(_require_dict(payload, "business"))
    records = _parse_records(_require_dict(payload, "records"))
    return PoBPayload(schema_version=schema_version, export=export, business=business, records=records)


def _parse_export(data: dict[str, Any]) -> FladovExport:
    _require_fields("export", data)
    return FladovExport(
        source_system=_require_str(data, "source_system"),
        exported_at=_parse_datetime(data.get("exported_at"), "export.exported_at"),
        export_id=_require_str(data, "export_id"),
        mode=_require_str(data, "mode"),
    )


def _parse_business(data: dict[str, Any]) -> BusinessInfo:
    _require_fields("business", data)
    secondary_categories = data.get("secondary_categories") or []
    if not isinstance(secondary_categories, list):
        raise PayloadValidationError("business.secondary_categories must be a list when present.")
    return BusinessInfo(
        id=_require_str(data, "id"),
        slug=_require_str(data, "slug"),
        name=_require_str(data, "name"),
        joined_at=_parse_datetime(data.get("joined_at"), "business.joined_at"),
        pob_enabled_at=_parse_datetime(data.get("pob_enabled_at"), "business.pob_enabled_at", required=False),
        primary_category=_optional_str(data.get("primary_category")),
        secondary_categories=[str(item) for item in secondary_categories],
        business_type=_optional_str(data.get("business_type")),
        profile_url=_optional_str(data.get("profile_url")),
    )


def _parse_records(data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    missing = [group for group in REQUIRED_RECORD_GROUPS if group not in data]
    if missing:
        raise PayloadValidationError(f"records is missing required groups: {', '.join(missing)}")

    parsed: dict[str, list[dict[str, Any]]] = {}
    for group in REQUIRED_RECORD_GROUPS:
        records = data.get(group)
        if not isinstance(records, list):
            raise PayloadValidationError(f"records.{group} must be a list.")
        parsed[group] = [_parse_record(group, record, index) for index, record in enumerate(records)]
    return parsed


def _parse_record(group: str, record: Any, index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise PayloadValidationError(f"records.{group}[{index}] must be an object.")
    _require_fields(group, record, prefix=f"records.{group}[{index}]")

    parsed: dict[str, Any] = dict(record)
    for key, value in list(parsed.items()):
        if key.endswith(DATE_SUFFIXES) and value is not None:
            parsed[key] = _parse_datetime(value, f"records.{group}[{index}].{key}")
    for key in ("amount", "primary_price", "min_price", "max_price", "average_cost", "latest_cost", "current_stock_quantity",
                "amount_paid", "items_subtotal", "adjustments_total", "total_payable", "total_paid", "balance_remaining",
                "item_count", "total_quantity", "total_cost", "gross_profit", "entry_count", "total_amount",
                "document_total_amount", "media_count"):
        if key in parsed and parsed[key] is not None:
            parsed[key] = _coerce_float(parsed[key], f"records.{group}[{index}].{key}")
    return parsed


def _require_fields(group: str, data: dict[str, Any], prefix: str | None = None) -> None:
    prefix = prefix or group
    missing = [field_name for field_name in REQUIRED_FIELDS[group] if field_name not in data]
    if missing:
        raise PayloadValidationError(f"{prefix} is missing required fields: {', '.join(missing)}")


def _require_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise PayloadValidationError(f"{key} must be an object.")
    return value


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PayloadValidationError(f"{key} must be a non-empty string.")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PayloadValidationError("Optional string field must be a string when present.")
    return value


def _parse_datetime(value: Any, field_name: str, required: bool = True) -> datetime | None:
    if value is None:
        if required:
            raise PayloadValidationError(f"{field_name} is required.")
        return None
    if not isinstance(value, str):
        raise PayloadValidationError(f"{field_name} must be an ISO-8601 string.")
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PayloadValidationError(f"{field_name} must be a valid ISO-8601 timestamp.") from exc


def _coerce_float(value: Any, field_name: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raise PayloadValidationError(f"{field_name} must be numeric.")
