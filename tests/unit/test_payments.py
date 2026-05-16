from __future__ import annotations

import hmac
import json
from hashlib import sha512
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
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


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str | None = None):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else json.dumps(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://example.test")
            response = httpx.Response(self.status_code, text=self.text, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


@pytest.fixture()
def squad_api(monkeypatch):
    requests: list[tuple[str, str, dict]] = []

    def fake_post(url, *args, **kwargs):
        requests.append(("POST", url, kwargs))
        if url.endswith("/transaction/initiate"):
            return _FakeResponse(
                {
                    "data": {
                        "checkout_url": "https://sandbox.squad.co/checkout/tx_123",
                        "transaction_ref": "pob_pay_test123",
                        "transaction_status": "Pending",
                    }
                }
            )
        if url in {"https://listener.example/payment-recorded", "http://127.0.0.1:8000/api/fladov/webhooks/post-payment"}:
            return _FakeResponse({"ok": True}, text="ok")
        raise AssertionError(f"Unexpected POST request: {url}")

    def fake_get(url, *args, **kwargs):
        requests.append(("GET", url, kwargs))
        if "/transaction/verify/" in url:
            return _FakeResponse(
                {
                    "status": 200,
                    "success": True,
                    "message": "Success",
                    "data": {
                        "transaction_status": "Success",
                        "transaction_ref": url.rsplit("/", 1)[-1],
                        "transaction_amount": 250000,
                        "transaction_currency_id": "NGN",
                    },
                }
            )
        raise AssertionError(f"Unexpected GET request: {url}")

    monkeypatch.setattr("app.payments.providers.squad.httpx.post", fake_post)
    monkeypatch.setattr("app.payments.providers.squad.httpx.get", fake_get)
    monkeypatch.setattr("app.payments.notifications.httpx.post", fake_post)
    return requests


def test_create_payment_intent_returns_checkout_url(tmp_path: Path, squad_api):
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.post(
        "/api/payments/intents",
        json={
            "business_slug": "sades-cakes",
            "business_name": "Sade's Cakes",
            "amount": 2500,
            "currency": "NGN",
            "theme": "dark",
            "note": "Report payment",
            "return_url": "http://testserver/passport/sades-cakes?theme=dark",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["payment"]["status"] == "pending"
    assert body["payment"]["cta_label"] == "Make payment"
    assert body["checkout_url"] == "https://sandbox.squad.co/checkout/tx_123"
    assert body["payment"]["return_url"] == "http://testserver/passport/sades-cakes?theme=dark"


def test_create_payment_intent_uses_invoice_total_and_preserves_metadata(tmp_path: Path, squad_api):
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.post(
        "/api/payments/intents",
        json={
            "business_slug": "sades-cakes",
            "business_name": "Sade's Cakes",
            "amount": 1,
            "currency": "NGN",
            "theme": "dark",
            "invoice_id": "inv_sades_001",
            "return_url": "http://testserver/passport/sades-cakes?theme=dark&pay_invoice=inv_sades_001",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["payment"]["amount"] == 59500.0

    create_call = next(entry for entry in squad_api if entry[0] == "POST" and entry[1].endswith("/transaction/initiate"))
    assert create_call[2]["json"]["amount"] == 5950000

    payment_store = Path(tmp_path / "payments.json")
    stored = json.loads(payment_store.read_text(encoding="utf-8"))
    intent = stored["intents"][0]
    assert intent["metadata"]["fladov_invoice_id"] == "inv_sades_001"
    assert intent["metadata"]["fladov_invoice_number"] == "FLD-PRO-1001"
    assert intent["metadata"]["fladov_invoice_total_amount"] == 59500.0


def test_payment_return_redirects_with_alert(tmp_path: Path, squad_api):
    client = TestClient(create_app(_settings(tmp_path)))
    create_response = client.post(
        "/api/payments/intents",
        json={
            "business_slug": "sades-cakes",
            "business_name": "Sade's Cakes",
            "amount": 2500,
            "currency": "NGN",
            "theme": "dark",
            "return_url": "http://testserver/passport/sades-cakes?theme=dark",
        },
    )
    intent_id = create_response.json()["payment"]["intent_id"]

    response = client.get(
        f"/api/payments/return/{intent_id}",
        params={"next": "http://testserver/passport/sades-cakes?theme=dark"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    assert query["payment_result"] == ["succeeded"]
    assert query["payment_intent"] == [intent_id]
    assert query["payment_status"] == ["succeeded"]
    assert query["payment_notice"] == ["Payment confirmed and recorded."]


def test_squad_webhook_verification_rejects_bad_signature(tmp_path: Path, squad_api):
    client = TestClient(create_app(_settings(tmp_path)))

    response = client.post(
        "/api/payments/webhooks/squad",
        content=json.dumps({"intent_id": "missing", "transaction_status": "Success"}).encode("utf-8"),
        headers={"X-Squad-Encrypted-Body": "wrong"},
    )

    assert response.status_code == 401


def test_squad_webhook_verification_accepts_good_signature(tmp_path: Path, squad_api):
    settings = _settings(tmp_path)
    client = TestClient(create_app(settings))

    create_response = client.post(
        "/api/payments/intents",
        json={
            "business_slug": "sades-cakes",
            "business_name": "Sade's Cakes",
            "amount": 2500,
            "currency": "NGN",
            "theme": "dark",
            "return_url": "http://testserver/passport/sades-cakes?theme=dark",
        },
    )
    intent_id = create_response.json()["payment"]["intent_id"]
    payload = {"intent_id": intent_id, "transaction_status": "Success", "metadata": {"intent_id": intent_id}}
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(settings.squad_webhook_secret.encode("utf-8"), raw_body, sha512).hexdigest()

    response = client.post(
        "/api/payments/webhooks/squad",
        content=raw_body,
        headers={"X-Squad-Encrypted-Body": signature},
    )

    assert response.status_code == 200
    assert response.json()["payment"]["status"] == "succeeded"


def test_successful_webhook_dispatches_post_payment_notification(tmp_path: Path, squad_api):
    settings = _settings(
        tmp_path,
        payment_success_webhook_secret="notify-secret",
    )
    client = TestClient(create_app(settings))

    create_response = client.post(
        "/api/payments/intents",
        json={
            "business_slug": "sades-cakes",
            "business_name": "Sade's Cakes",
            "amount": 2500,
            "currency": "NGN",
            "theme": "dark",
            "return_url": "http://testserver/passport/sades-cakes?theme=dark",
        },
    )
    intent_id = create_response.json()["payment"]["intent_id"]
    payload = {"intent_id": intent_id, "transaction_status": "Success", "metadata": {"intent_id": intent_id}}
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(settings.squad_webhook_secret.encode("utf-8"), raw_body, sha512).hexdigest()

    response = client.post(
        "/api/payments/webhooks/squad",
        content=raw_body,
        headers={"X-Squad-Encrypted-Body": signature},
    )

    assert response.status_code == 200
    assert response.json()["payment"]["status"] == "succeeded"

    outbound_posts = [entry for entry in squad_api if entry[0] == "POST" and entry[1] == "http://127.0.0.1:8000/api/fladov/webhooks/post-payment"]
    assert outbound_posts, "Expected success notification to be sent."
    sent_body = json.loads(outbound_posts[0][2]["content"].decode("utf-8"))
    assert sent_body["event"] == "payment.succeeded"
    assert sent_body["payment"]["intent_id"] == intent_id
    assert sent_body["verification_payload"]["transaction_status"] == "Success"


def test_successful_webhook_dispatch_includes_invoice_payload(tmp_path: Path, squad_api):
    settings = _settings(
        tmp_path,
        payment_success_webhook_secret="notify-secret",
    )
    client = TestClient(create_app(settings))

    create_response = client.post(
        "/api/payments/intents",
        json={
            "business_slug": "sades-cakes",
            "business_name": "Sade's Cakes",
            "amount": 10,
            "currency": "NGN",
            "theme": "dark",
            "invoice_id": "inv_sades_001",
            "return_url": "http://testserver/passport/sades-cakes?theme=dark&pay_invoice=inv_sades_001",
        },
    )
    intent_id = create_response.json()["payment"]["intent_id"]
    payload = {"intent_id": intent_id, "transaction_status": "Success", "metadata": {"intent_id": intent_id}}
    raw_body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(settings.squad_webhook_secret.encode("utf-8"), raw_body, sha512).hexdigest()

    response = client.post(
        "/api/payments/webhooks/squad",
        content=raw_body,
        headers={"X-Squad-Encrypted-Body": signature},
    )

    assert response.status_code == 200

    outbound_posts = [entry for entry in squad_api if entry[0] == "POST" and entry[1] == "http://127.0.0.1:8000/api/fladov/webhooks/post-payment"]
    sent_body = json.loads(outbound_posts[-1][2]["content"].decode("utf-8"))
    assert sent_body["invoice"]["id"] == "inv_sades_001"
    assert sent_body["invoice"]["invoice_number"] == "FLD-PRO-1001"
    assert sent_body["invoice"]["total_amount"] == 59500.0
