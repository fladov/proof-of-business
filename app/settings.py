"""Application settings for the Proof of Business web app."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_local_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ[key] = value


_load_local_env_file()


def _normalize_api_route_prefix(prefix: str) -> str:
    normalized = prefix.strip() or "/api"
    if normalized.endswith("/demo"):
        normalized = normalized[:-5]
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/") or "/api"


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True, slots=True)
class Settings:
    api_route_prefix: str = "/api"
    app_name: str = "Proof of Business by Fladov"
    public_base_url: str = "http://127.0.0.1:8000"
    fladov_demo_mode: bool = True
    fladov_api_base_url: str = "https://api.fladov.example"
    fladov_request_timeout_seconds: float = 10.0
    fladov_schema_version: str = "1.0.0"
    payment_provider: str = "squad"
    payment_currency: str = "NGN"
    payment_default_amount: float = 5000.0
    payment_store_path: str = str(PROJECT_ROOT / "runtime" / "payments.json")
    payment_success_webhook_url: str = ""
    payment_success_webhook_secret: str = ""
    payment_success_webhook_timeout_seconds: float = 10.0
    squad_base_url: str = "https://sandbox-api-d.squadco.com"
    squad_public_key: str = ""
    squad_secret_key: str = ""
    squad_webhook_secret: str = ""
    squad_beneficiary_account: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    def pick(*names: str, default: str = "") -> str:
        for name in names:
            value = os.getenv(name)
            if value is not None and value != "":
                return value
        return default

    return Settings(
        api_route_prefix=_normalize_api_route_prefix(os.getenv("POB_API_ROUTE_PREFIX", "/api")),
        app_name=os.getenv("POB_APP_NAME", "Proof of Business by Fladov"),
        public_base_url=os.getenv("POB_PUBLIC_BASE_URL", "http://127.0.0.1:8000"),
        fladov_demo_mode=_parse_bool(os.getenv("POB_FLADOV_DEMO_MODE"), default=True),
        fladov_api_base_url=os.getenv("POB_FLADOV_API_BASE_URL", "https://api.fladov.example"),
        fladov_request_timeout_seconds=float(os.getenv("POB_FLADOV_REQUEST_TIMEOUT_SECONDS", "10")),
        fladov_schema_version=os.getenv("POB_FLADOV_SCHEMA_VERSION", "1.0.0"),
        payment_provider=os.getenv("POB_PAYMENT_PROVIDER", "squad"),
        payment_currency=os.getenv("POB_PAYMENT_CURRENCY", "NGN"),
        payment_default_amount=float(os.getenv("POB_PAYMENT_DEFAULT_AMOUNT", "5000")),
        payment_store_path=os.getenv("POB_PAYMENT_STORE_PATH", str(PROJECT_ROOT / "runtime" / "payments.json")),
        payment_success_webhook_url=pick("POB_PAYMENT_SUCCESS_WEBHOOK_URL", "PAYMENT_SUCCESS_WEBHOOK_URL"),
        payment_success_webhook_secret=pick("POB_PAYMENT_SUCCESS_WEBHOOK_SECRET", "PAYMENT_SUCCESS_WEBHOOK_SECRET"),
        payment_success_webhook_timeout_seconds=float(os.getenv("POB_PAYMENT_SUCCESS_WEBHOOK_TIMEOUT_SECONDS", "10")),
        squad_base_url=pick("POB_SQUAD_BASE_URL", "SQUAD_BASE_URL", default="https://sandbox-api-d.squadco.com"),
        squad_public_key=pick("POB_SQUAD_PUBLIC_KEY", "SQUAD_PUBLIC_KEY"),
        squad_secret_key=pick("POB_SQUAD_SECRET_KEY", "SQUAD_SECRET_KEY"),
        squad_webhook_secret=pick("POB_SQUAD_WEBHOOK_SECRET", "SQUAD_WEBHOOK_SECRET"),
        squad_beneficiary_account=pick("POB_SQUAD_BENEFICIARY_ACCOUNT", "SQUAD_BENEFICIARY_ACCOUNT"),
    )
