from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.reports.service import generate_fladov_passport
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


def test_generate_passport_builds_three_tabs(tmp_path: Path):
    report = generate_fladov_passport("sades-cakes", settings=_settings(tmp_path), theme="dark")

    assert report["default_tab"] == "customer"
    assert report["business_name"] == "Sade's Cakes"
    assert report["business_avatar_url"].startswith("https://loremflickr.com/")
    assert report["business_profile_url"] == "https://fladov.com/biz/sades-cakes"
    assert [tab["key"] for tab in report["tabs"]] == ["customer", "investor", "lender"]
    assert report["tabs"][0]["visible_by_default"] is True
    assert report["tabs"][1]["visible_by_default"] is False
    assert report["tabs"][2]["visible_by_default"] is False
    assert report["confidence"]["label"] in {"Low", "Medium", "High"}
    assert report["tabs"][0]["main_score_presentation"]["percent"] >= 0.0
    assert report["payment"]["cta_label"] == "Make payment"
    assert report["payment"]["status"] == "not_started"
    assert report["post_payment_webhook_url"].endswith("/api/fladov/webhooks/post-payment")


def test_api_routes_use_configurable_prefix():
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/passport/generate", json={"business_slug": "sades-cakes", "theme": "dark"})

    assert response.status_code == 200
    body = response.json()
    assert body["business_slug"] == "sades-cakes"
    assert body["passport"]["default_tab"] == "customer"


def test_fladov_catalog_endpoint_returns_businesses():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/fladov/businesses", params={"query": "salon"})

    assert response.status_code == 200
    body = response.json()
    assert body["pob_schema_version"] == "1.0.0"
    assert body["enabled_business_count"] == 10
    assert body["pob_enabled_businesses"]
    item = body["pob_enabled_businesses"][0]
    assert item["display_name"] == "Glow Salon"
    assert item["avatar_url"].startswith("https://loremflickr.com/")
    assert item["profile_url"] == "https://fladov.com/biz/glow-salon"


def test_fladov_catalog_endpoint_stays_empty_until_searching():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/fladov/businesses")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled_business_count"] == 10
    assert body["pob_enabled_businesses"] == []


def test_fladov_meta_endpoint_returns_repository_metadata():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/fladov/meta")

    assert response.status_code == 200
    body = response.json()
    assert body["pob_schema_version"] == "1.0.0"
    assert body["post_payment_webhook_url"].endswith("/api/fladov/webhooks/post-payment")
    assert body["invoice_preview_template_html"]
    assert body["enabled_business_count"] == 10
    assert "pob_enabled_businesses" not in body


def test_fladov_business_detail_endpoint_returns_full_payload():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/fladov/businesses/sades-cakes")

    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "sades-cakes"
    assert body["display_name"] == "Sade's Cakes"
    assert body["post_payment_webhook_url"].endswith("/api/fladov/webhooks/post-payment")
    assert body["pob_payload"]["business"]["slug"] == "sades-cakes"
    assert body["pob_payload"]["records"]["orders"]
    assert "records" not in body
    assert body["invoices"]


def test_fladov_invoice_detail_endpoint_returns_invoice():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/fladov/businesses/sades-cakes/invoices/inv_sades_001")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "inv_sades_001"
    assert body["business_slug"] == "sades-cakes"
    assert body["invoice_number"] == "FLD-PRO-1001"


def test_passport_page_renders_tabs():
    app = create_app()
    client = TestClient(app)

    response = client.get("/passport/sades-cakes?theme=dark")

    assert response.status_code == 200
    html = response.text
    assert "Customer" in html
    assert "Investor" in html
    assert "Lender" in html
    assert "Make payment" in html
    assert "Show contributing sub scores" in html
    assert "Where this passport can improve" in html
    assert "data-payment-alert" in html
    assert "Proof of Business by Fladov" in html
    assert "Sade&#39;s Cakes" in html
    assert "business_avatar_url" not in html
    assert "data-fladov-search-input" not in html


def test_passport_page_prefills_payment_amount_and_scrolls():
    app = create_app()
    client = TestClient(app)

    response = client.get("/passport/sades-cakes?theme=dark&amount=8750")

    assert response.status_code == 200
    html = response.text
    assert 'value="8750.0"' in html
    assert 'data-scroll-into-view="true"' in html


def test_passport_page_renders_invoice_preview_and_locks_amount():
    app = create_app()
    client = TestClient(app)

    response = client.get("/passport/sades-cakes?theme=dark&pay_invoice=inv_sades_001")

    assert response.status_code == 200
    html = response.text
    assert "Pay this invoice" in html
    assert "FLD-PRO-1001" in html
    assert "View full invoice on Fladov" in html
    assert 'value="59500.0"' in html
    assert 'readonly' in html
    assert 'data-scroll-into-view="true"' in html
    assert 'data-report-invoice-id="inv_sades_001"' in html


def test_passport_page_returns_error_for_unknown_invoice():
    app = create_app()
    client = TestClient(app)

    response = client.get("/passport/sades-cakes?theme=dark&pay_invoice=missing-invoice")

    assert response.status_code == 404
    assert "Unknown Fladov invoice" in response.text


def test_business_profile_page_renders_cta():
    app = create_app()
    client = TestClient(app)

    response = client.get("/business/sades-cakes?theme=dark")

    assert response.status_code == 200
    html = response.text
    assert "Sade&#39;s Cakes" in html
    assert "This business is verified through Fladov activity." in html
    assert "View passport" in html
    assert "/passport/sades-cakes?theme=dark" in html


def test_homepage_mentions_payments_and_search():
    app = create_app()
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert "Proof of Business by Fladov" in html
    assert "Search Fladov businesses" in html
    assert "data-fladov-search-input" in html
    assert "PoB enabled businesses" in html
    assert "Start typing to search" in html
    assert "Business slug" not in html
