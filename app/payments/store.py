"""Simple JSON-backed payment intent store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
from threading import Lock
from typing import Any

from .models import PaymentIntent


@dataclass(slots=True)
class PaymentStore:
    path: Path
    _lock: Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lock = Lock()

    def save_intent(self, intent: PaymentIntent) -> PaymentIntent:
        with self._lock:
            data = self._load()
            intents = [item for item in data.get("intents", []) if item.get("intent_id") != intent.intent_id]
            intents.append(intent.to_dict())
            data["intents"] = intents
            self._write(data)
        return intent

    def get_intent(self, intent_id: str) -> PaymentIntent | None:
        with self._lock:
            data = self._load()
            for item in data.get("intents", []):
                if item.get("intent_id") == intent_id:
                    return self._from_dict(item)
        return None

    def latest_for_business(self, business_slug: str) -> PaymentIntent | None:
        with self._lock:
            data = self._load()
            items = [
                self._from_dict(item)
                for item in data.get("intents", [])
                if item.get("business_slug") == business_slug
            ]
            if not items:
                return None
            items.sort(key=lambda item: item.updated_at, reverse=True)
            return items[0]

    def find_by_provider_reference(self, provider_reference: str) -> PaymentIntent | None:
        with self._lock:
            data = self._load()
            for item in data.get("intents", []):
                if item.get("provider_reference") == provider_reference:
                    return self._from_dict(item)
        return None

    def update_intent_status(self, intent_id: str, status: str, webhook_payload: dict[str, Any] | None = None) -> PaymentIntent | None:
        with self._lock:
            data = self._load()
            intents = data.get("intents", [])
            updated = None
            for item in intents:
                if item.get("intent_id") == intent_id:
                    item["status"] = status
                    item["updated_at"] = datetime.now(timezone.utc).isoformat()
                    if webhook_payload is not None:
                        item["webhook_payload"] = webhook_payload
                    updated = self._from_dict(item)
                    break
            if updated is not None:
                self._write(data)
            return updated

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"intents": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"intents": []}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")

    def _from_dict(self, item: dict[str, Any]) -> PaymentIntent:
        return PaymentIntent(
            intent_id=item["intent_id"],
            business_slug=item["business_slug"],
            business_name=item["business_name"],
            provider=item["provider"],
            amount=float(item["amount"]),
            currency=item["currency"],
            status=item["status"],
            checkout_url=item["checkout_url"],
            provider_reference=item["provider_reference"],
            return_url=item.get("return_url", ""),
            note=item.get("note"),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            metadata=item.get("metadata", {}),
            raw_provider_response=item.get("raw_provider_response", {}),
            webhook_payload=item.get("webhook_payload"),
        )
