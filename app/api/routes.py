"""FastAPI routes for the Fladov Proof of Business app."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.fladov.routes import build_fladov_router
from app.payments.routes import build_payments_router
from app.reports.service import generate_fladov_passport
from app.settings import Settings

from .models import GeneratePassportRequest, GeneratePassportResponse


def build_api_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix=settings.api_route_prefix)
    router.include_router(build_fladov_router(settings))
    router.include_router(build_payments_router(settings))

    @router.post("/passport/generate", response_model=GeneratePassportResponse)
    def create_passport(payload: GeneratePassportRequest) -> GeneratePassportResponse:
        try:
            passport = generate_fladov_passport(
                business_slug=payload.business_slug,
                settings=settings,
                theme=payload.theme,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return GeneratePassportResponse(
            api_route_prefix=settings.api_route_prefix,
            business_slug=payload.business_slug,
            passport=passport,
        )

    return router
