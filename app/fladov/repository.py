"""Fladov repository implementations for demo and live modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.settings import Settings

from .contracts import FladovBusinessExport, FladovBusinessSummary, FladovInvoice, FladovRepositoryMeta
from .demo_data import build_mock_fladov_manifest, _avatar_placeholder_data_uri


class FladovRepository(Protocol):
    def list_businesses(self, query: str | None = None, limit: int = 10) -> list[FladovBusinessSummary]:
        """Return browseable Fladov businesses."""

    def get_business(self, slug: str) -> FladovBusinessExport:
        """Return the full Fladov export for a business."""

    def get_repository_meta(self) -> FladovRepositoryMeta:
        """Return top-level repository metadata without business records."""

    def get_invoice(self, business_slug: str, invoice_id: str) -> FladovInvoice:
        """Return a Fladov invoice for a specific business."""

    def get_invoice_preview_template(self) -> str:
        """Return the Fladov-owned invoice preview template."""


@dataclass(slots=True)
class MockFladovRepository:
    metadata: FladovRepositoryMeta
    businesses: list[FladovBusinessExport]

    def __init__(self, manifest: dict[str, Any] | None = None) -> None:
        raw_manifest = manifest or build_mock_fladov_manifest()
        self.businesses = [FladovBusinessExport.from_manifest_entry(entry) for entry in raw_manifest["pob_enabled_businesses"]]
        self.metadata = FladovRepositoryMeta(
            pob_schema_version=raw_manifest["pob_schema_version"],
            post_payment_webhook_url=raw_manifest["post_payment_webhook_url"],
            invoice_preview_template_html=raw_manifest.get("invoice_preview_template_html", ""),
            enabled_business_count=len(self.businesses),
        )

    def list_businesses(self, query: str | None = None, limit: int = 10) -> list[FladovBusinessSummary]:
        businesses = self.businesses
        if query:
            normalized = query.strip().lower()
            businesses = [
                business
                for business in businesses
                if normalized in business.display_name.lower() or normalized in business.slug.lower()
            ]
        return [business.to_summary() for business in businesses[: max(limit, 0)]]

    def get_business(self, slug: str) -> FladovBusinessExport:
        normalized = slug.strip().lower()
        for business in self.businesses:
            if business.slug.lower() == normalized:
                return business
        raise KeyError(f"Unknown Fladov business slug: {slug}")

    def get_repository_meta(self) -> FladovRepositoryMeta:
        return self.metadata

    def get_invoice(self, business_slug: str, invoice_id: str) -> FladovInvoice:
        business = self.get_business(business_slug)
        normalized = invoice_id.strip().lower()
        for invoice in business.invoices:
            if invoice.id.lower() == normalized:
                return invoice
        raise KeyError(f"Unknown Fladov invoice '{invoice_id}' for business '{business_slug}'.")

    def get_invoice_preview_template(self) -> str:
        return self.metadata.invoice_preview_template_html


@dataclass(slots=True)
class LiveFladovRepository:
    settings: Settings
    client: httpx.Client | None = None

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = httpx.Client(
                base_url=self.settings.fladov_api_base_url.rstrip("/"),
                timeout=self.settings.fladov_request_timeout_seconds,
            )

    def list_businesses(self, query: str | None = None, limit: int = 10) -> list[FladovBusinessSummary]:
        response = self.client.get("/api/fladov/businesses", params={"query": query or "", "limit": limit})
        response.raise_for_status()
        return [
            FladovBusinessExport.from_manifest_entry(entry).to_summary()
            for entry in self._extract_business_entries(response.json())[: max(limit, 0)]
        ]

    def get_business(self, slug: str) -> FladovBusinessExport:
        response = self.client.get(f"/api/fladov/businesses/{slug}")
        response.raise_for_status()
        payload = response.json()
        if "pob_payload" in payload:
            return FladovBusinessExport.from_manifest_entry(payload)
        if "business" in payload and "records" in payload:
            entry = self._entry_from_payload(payload)
            return FladovBusinessExport.from_manifest_entry(entry)
        entries = self._extract_business_entries(payload)
        if not entries:
            raise KeyError(f"Unknown Fladov business slug: {slug}")
        return FladovBusinessExport.from_manifest_entry(entries[0])

    def get_repository_meta(self) -> FladovRepositoryMeta:
        response = self.client.get("/api/fladov/meta")
        response.raise_for_status()
        payload = response.json()
        return FladovRepositoryMeta(
            pob_schema_version=payload.get("pob_schema_version", self.settings.fladov_schema_version),
            post_payment_webhook_url=payload.get("post_payment_webhook_url", ""),
            invoice_preview_template_html=payload.get("invoice_preview_template_html", ""),
            enabled_business_count=int(payload.get("enabled_business_count", 0)),
        )

    def get_invoice(self, business_slug: str, invoice_id: str) -> FladovInvoice:
        business = self.get_business(business_slug)
        normalized = invoice_id.strip().lower()
        for invoice in business.invoices:
            if invoice.id.lower() == normalized:
                return invoice
        raise KeyError(f"Unknown Fladov invoice '{invoice_id}' for business '{business_slug}'.")

    def get_invoice_preview_template(self) -> str:
        return self.get_repository_meta().invoice_preview_template_html

    @staticmethod
    def _extract_business_entries(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and "pob_enabled_businesses" in payload:
            businesses = payload.get("pob_enabled_businesses", [])
            return businesses if isinstance(businesses, list) else []
        if isinstance(payload, dict) and "business" in payload and "records" in payload:
            return [LiveFladovRepository._entry_from_payload(payload)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    @staticmethod
    def _entry_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
        business = payload["business"]
        pob_schema_version = payload.get("pob_schema_version", payload.get("schema_version", "1.0.0"))
        profile_url = business.get("profile_url") or f"https://fladov.com/biz/{business['slug']}"
        return {
            "id": business["id"],
            "slug": business["slug"],
            "display_name": business.get("display_name") or business["name"],
            "avatar_url": business.get("avatar_url", ""),
            "avatar_placeholder_url": business.get("avatar_placeholder_url") or _avatar_placeholder_data_uri(business.get("primary_category", "")),
            "profile_url": profile_url,
            "pob_schema_version": pob_schema_version,
            "post_payment_webhook_url": payload.get("post_payment_webhook_url", ""),
            "source": payload.get("export", {}),
            "invoices": payload.get("invoices", []),
            "business": business,
            "pob_payload": {
                "schema_version": pob_schema_version,
                "export": payload.get("export", {}),
                "business": business,
                "records": payload["records"],
            },
        }


def build_fladov_repository(settings: Settings) -> FladovRepository:
    if settings.fladov_demo_mode:
        return MockFladovRepository()
    return LiveFladovRepository(settings)
