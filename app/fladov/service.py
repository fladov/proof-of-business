"""Fladov repository service for Proof of Business."""

from __future__ import annotations

from dataclasses import dataclass

from app.settings import Settings

from .contracts import FladovBusinessExport, FladovBusinessSummary, FladovInvoice, FladovRepositoryMeta
from .repository import FladovRepository, build_fladov_repository


@dataclass(slots=True)
class FladovRepositoryService:
    settings: Settings
    repository: FladovRepository | None = None

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = build_fladov_repository(self.settings)

    def list_businesses(self, query: str | None = None, limit: int = 10) -> list[FladovBusinessSummary]:
        return self.repository.list_businesses(query=query, limit=limit)

    def get_business_export(self, business_slug: str) -> FladovBusinessExport:
        return self.repository.get_business(business_slug)

    def get_business_summary(self, business_slug: str) -> FladovBusinessSummary:
        return self.get_business_export(business_slug).to_summary()

    def get_invoice(self, business_slug: str, invoice_id: str) -> FladovInvoice:
        return self.repository.get_invoice(business_slug, invoice_id)

    def get_invoice_preview_template(self) -> str:
        return self.repository.get_invoice_preview_template()

    def get_repository_meta(self) -> FladovRepositoryMeta:
        return self.repository.get_repository_meta()

    def count_businesses(self) -> int:
        return self.get_repository_meta().enabled_business_count or 0


def build_fladov_business_export(settings: Settings, business_slug: str) -> FladovBusinessExport:
    return FladovRepositoryService(settings).get_business_export(business_slug)
