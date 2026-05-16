"""Payment API routes."""

from __future__ import annotations

import json
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.fladov.service import FladovRepositoryService
from app.settings import Settings

from .api_models import CreatePaymentIntentRequest, CreatePaymentIntentResponse, PaymentStatusResponse
from .service import PaymentService


def build_payments_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/payments")

    @router.post("/intents", response_model=CreatePaymentIntentResponse)
    def create_intent(payload: CreatePaymentIntentRequest) -> CreatePaymentIntentResponse:
        service = PaymentService(settings)
        try:
            fladov_export = FladovRepositoryService(settings).get_business_export(payload.business_slug)
        except KeyError as exc:
            return Response(content=json.dumps({"success": False, "message": str(exc)}), status_code=404, media_type="application/json")
        business_name = fladov_export.display_name
        return_url = payload.return_url or service.build_passport_return_url(payload.business_slug, payload.theme, invoice_id=payload.invoice_id)
        try:
            payment = service.create_intent(
                business_slug=payload.business_slug,
                business_name=business_name,
                amount=payload.amount,
                currency=payload.currency,
                note=payload.note,
                return_url=return_url,
                invoice_id=payload.invoice_id,
            )
        except KeyError as exc:
            return Response(content=json.dumps({"success": False, "message": str(exc)}), status_code=404, media_type="application/json")
        except ValueError as exc:
            return Response(content=json.dumps({"success": False, "message": str(exc)}), status_code=502, media_type="application/json")
        checkout_url = payment.checkout_url or return_url
        return CreatePaymentIntentResponse(checkout_url=checkout_url, payment=payment.to_dict())

    @router.get("/intents/{intent_id}", response_model=PaymentStatusResponse)
    def get_intent(intent_id: str) -> PaymentStatusResponse:
        service = PaymentService(settings)
        intent = service.get_intent(intent_id)
        if intent is None:
            return PaymentStatusResponse(payment={})
        summary = service.get_summary(intent.business_slug, intent.business_name)
        return PaymentStatusResponse(payment=summary.to_dict())

    @router.get("/return/{intent_id}")
    def payment_return(intent_id: str, request: Request) -> RedirectResponse:
        service = PaymentService(settings)
        next_url = request.query_params.get("next")
        redirect_url = service.finalize_payment_return(intent_id, next_url=next_url)
        return RedirectResponse(url=redirect_url, status_code=303)

    @router.post("/webhooks/squad")
    async def squad_webhook(request: Request) -> Response:
        service = PaymentService(settings)
        raw_body = await request.body()
        headers = {key.lower(): value for key, value in request.headers.items()}
        try:
            payment = service.process_webhook(raw_body, headers)
        except ValueError:
            return Response(content=json.dumps({"success": False, "message": "Invalid signature"}), status_code=401, media_type="application/json")
        if payment is None:
            return Response(content=json.dumps({"success": True, "message": "No matching intent"}), media_type="application/json")
        return Response(content=json.dumps({"success": True, "payment": payment.to_dict()}), media_type="application/json")

    return router
