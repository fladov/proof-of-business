"""Typed internal schema models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class FladovExport:
    source_system: str
    exported_at: datetime
    export_id: str
    mode: str


@dataclass(slots=True)
class BusinessInfo:
    id: str
    slug: str
    name: str
    joined_at: datetime
    pob_enabled_at: datetime | None
    primary_category: str | None
    secondary_categories: list[str] = field(default_factory=list)
    business_type: str | None = None
    profile_url: str | None = None


@dataclass(slots=True)
class PoBPayload:
    schema_version: str
    export: FladovExport
    business: BusinessInfo
    records: dict[str, list[dict[str, Any]]]
