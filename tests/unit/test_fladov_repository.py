from __future__ import annotations

from pathlib import Path

import httpx

from app.fladov.demo_data import build_mock_fladov_manifest
from app.fladov.repository import LiveFladovRepository, MockFladovRepository, build_fladov_repository
from app.settings import Settings


def _settings(tmp_path: Path, **overrides) -> Settings:
    base = dict(
        api_route_prefix="/api",
        app_name="Proof of Business by Fladov",
        public_base_url="http://testserver",
        fladov_demo_mode=True,
        fladov_api_base_url="http://fladov.test",
        fladov_request_timeout_seconds=10.0,
        fladov_schema_version="1.0.0",
        payment_provider="squad",
        payment_currency="NGN",
        payment_default_amount=5000.0,
        payment_store_path=str(tmp_path / "payments.json"),
        payment_success_webhook_url="",
        payment_success_webhook_secret="",
        payment_success_webhook_timeout_seconds=10.0,
        squad_base_url="https://sandbox-api-d.squadco.com",
        squad_public_key="sandbox_pk",
        squad_secret_key="sandbox_sk",
        squad_webhook_secret="webhook-secret",
        squad_beneficiary_account="",
    )
    base.update(overrides)
    return Settings(**base)


def test_mock_repository_meta_contains_only_repository_metadata(tmp_path: Path):
    repository = MockFladovRepository()

    metadata = repository.get_repository_meta()
    assert metadata.pob_schema_version == "1.0.0"
    assert metadata.post_payment_webhook_url.endswith("/api/fladov/webhooks/post-payment")
    assert metadata.invoice_preview_template_html
    assert metadata.enabled_business_count == 10

    results = repository.list_businesses(query="salon")
    assert len(results) == 1
    assert results[0].display_name == "Glow Salon"
    assert results[0].avatar_url.startswith("https://loremflickr.com/")
    assert results[0].profile_url == "https://fladov.com/biz/glow-salon"

    export = repository.get_business("sades-cakes")
    assert export.display_name == "Sade's Cakes"
    assert export.pob_payload["business"]["slug"] == "sades-cakes"
    assert export.pob_payload["records"]["orders"]
    assert export.invoices
    assert "records" not in export.to_dict()

    invoice = repository.get_invoice("sades-cakes", "inv_sades_001")
    assert invoice.business_slug == "sades-cakes"
    assert invoice.invoice_number == "FLD-PRO-1001"


def test_live_repository_matches_meta_and_business_contracts(tmp_path: Path):
    manifest = build_mock_fladov_manifest()
    meta = {
        "pob_schema_version": manifest["pob_schema_version"],
        "post_payment_webhook_url": manifest["post_payment_webhook_url"],
        "invoice_preview_template_html": manifest["invoice_preview_template_html"],
        "enabled_business_count": len(manifest["pob_enabled_businesses"]),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/fladov/meta":
            return httpx.Response(200, json=meta)
        if request.url.path == "/api/fladov/businesses":
            query = request.url.params.get("query", "")
            businesses = [item for item in manifest["pob_enabled_businesses"] if query.lower() in item["slug"].lower() or query.lower() in item["display_name"].lower()]
            return httpx.Response(
                200,
                json={
                    "pob_schema_version": meta["pob_schema_version"],
                    "enabled_business_count": meta["enabled_business_count"],
                    "pob_enabled_businesses": businesses[: int(request.url.params.get("limit", "10"))],
                },
            )
        if request.url.path == "/api/fladov/businesses/sades-cakes":
            return httpx.Response(200, json=manifest["pob_enabled_businesses"][0])
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://fladov.test")
    repository = LiveFladovRepository(_settings(tmp_path, fladov_demo_mode=False, fladov_api_base_url="http://fladov.test"), client=client)

    metadata_result = repository.get_repository_meta()
    assert metadata_result.pob_schema_version == "1.0.0"
    assert metadata_result.enabled_business_count == 10

    businesses = repository.list_businesses(query="cakes")
    assert businesses
    assert businesses[0].display_name == "Sade's Cakes"

    export = repository.get_business("sades-cakes")
    assert export.slug == "sades-cakes"
    assert export.post_payment_webhook_url.endswith("/api/fladov/webhooks/post-payment")
    assert repository.get_invoice_preview_template()
    assert repository.get_invoice("sades-cakes", "inv_sades_001").business_slug == "sades-cakes"
    assert "records" not in export.to_dict()


def test_build_fladov_repository_switches_mode(tmp_path: Path):
    demo_repo = build_fladov_repository(_settings(tmp_path, fladov_demo_mode=True))
    live_repo = build_fladov_repository(_settings(tmp_path, fladov_demo_mode=False, fladov_api_base_url="http://fladov.test"))

    assert isinstance(demo_repo, MockFladovRepository)
    assert isinstance(live_repo, LiveFladovRepository)
