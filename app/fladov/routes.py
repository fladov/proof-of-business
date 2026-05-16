"""Fladov repository API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.settings import Settings

from .service import FladovRepositoryService


def build_fladov_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/fladov")

    @router.get("/meta")
    def get_repository_meta() -> dict:
        service = FladovRepositoryService(settings)
        return service.get_repository_meta().to_dict()

    @router.get("/businesses")
    def list_businesses(
        query: str = Query(default=""),
        limit: int = Query(default=10, ge=1, le=10),
    ) -> dict:
        service = FladovRepositoryService(settings)
        metadata = service.get_repository_meta()
        businesses = [] if not query.strip() else service.list_businesses(query=query or None, limit=limit)
        return {
            "pob_schema_version": metadata.pob_schema_version,
            "enabled_business_count": metadata.enabled_business_count,
            "pob_enabled_businesses": [business.to_dict() for business in businesses],
        }

    @router.get("/businesses/{slug}")
    def get_business(slug: str) -> dict:
        service = FladovRepositoryService(settings)
        try:
            export = service.get_business_export(slug)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return export.to_dict()

    @router.get("/businesses/{slug}/invoices/{invoice_id}")
    def get_invoice(slug: str, invoice_id: str) -> dict:
        service = FladovRepositoryService(settings)
        try:
            invoice = service.get_invoice(slug, invoice_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return invoice.to_dict()

    @router.post("/webhooks/post-payment")
    async def post_payment_webhook(request: Request) -> dict:
        payload = await request.json()
        return {
            "success": True,
            "message": "Fladov post-payment webhook received.",
            "payload": payload,
        }

    return router
