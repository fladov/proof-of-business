"""FastAPI application entrypoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.fladov.service import FladovRepositoryService
from app.payments.service import PaymentService
from app.reports.service import generate_fladov_passport
from app.settings import Settings, get_settings

from .api.routes import build_api_router


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    app.include_router(build_api_router(settings))

    def render_passport_page(
        request: Request,
        business_slug: str,
        theme: str,
        prefill_amount: float | None = None,
        pay_invoice: str | None = None,
    ) -> HTMLResponse:
        fladov_service = FladovRepositoryService(settings)
        try:
            fladov_export = fladov_service.get_business_export(business_slug)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        selected_invoice = None
        invoice_preview_template_html = ""
        if pay_invoice:
            try:
                selected_invoice = fladov_service.get_invoice(business_slug, pay_invoice)
            except KeyError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            invoice_preview_template_html = fladov_service.get_invoice_preview_template()
            prefill_amount = selected_invoice.total_amount
        payment_service = PaymentService(settings)
        payment_summary = payment_service.get_summary(business_slug, fladov_export.display_name)
        passport = generate_fladov_passport(
            business_slug=business_slug,
            settings=settings,
            theme=theme,
            payment_summary=payment_summary,
            selected_invoice=selected_invoice,
            invoice_preview_template_html=invoice_preview_template_html,
        )
        return TEMPLATES.TemplateResponse(
            request,
            "report.html",
            {
                "request": request,
                "settings": settings,
                "passport": passport,
                "confidence": passport["confidence"],
                "payment": passport["payment"],
                "business": fladov_export,
                "theme": theme,
                "prefill_amount": prefill_amount,
                "scroll_to_payment": prefill_amount is not None,
                "pay_invoice": pay_invoice,
            },
        )

    def render_business_profile_page(request: Request, business_slug: str, theme: str) -> HTMLResponse:
        try:
            fladov_export = FladovRepositoryService(settings).get_business_export(business_slug)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        passport_url = f"{settings.public_base_url.rstrip('/')}/passport/{fladov_export.slug}?theme={theme}"
        payment_service = PaymentService(settings)
        payment_summary = payment_service.get_summary(business_slug, fladov_export.display_name)
        return TEMPLATES.TemplateResponse(
            request,
            "business.html",
            {
                "request": request,
                "settings": settings,
                "business": fladov_export,
                "passport_url": passport_url,
                "payment": payment_summary,
                "theme": theme,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        fladov_service = FladovRepositoryService(settings)
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "settings": settings,
                "payment_supported": True,
                "fladov_demo_mode": settings.fladov_demo_mode,
                "enabled_business_count": fladov_service.count_businesses(),
            },
        )

    @app.get("/passport/{business_slug}", response_class=HTMLResponse)
    def show_passport(
        request: Request,
        business_slug: str,
        theme: str = Query(default="light"),
        amount: float | None = Query(default=None),
        pay_amount: float | None = Query(default=None),
        pay_invoice: str | None = Query(default=None),
    ):
        prefill_amount = amount if amount is not None else pay_amount
        return render_passport_page(request, business_slug, theme, prefill_amount=prefill_amount, pay_invoice=pay_invoice)

    @app.get("/pob/{business_slug}", response_class=HTMLResponse)
    def show_pob_alias(
        request: Request,
        business_slug: str,
        theme: str = Query(default="light"),
        amount: float | None = Query(default=None),
        pay_amount: float | None = Query(default=None),
        pay_invoice: str | None = Query(default=None),
    ):
        prefill_amount = amount if amount is not None else pay_amount
        return render_passport_page(request, business_slug, theme, prefill_amount=prefill_amount, pay_invoice=pay_invoice)

    @app.get("/business/{business_slug}", response_class=HTMLResponse)
    def show_business_alias(
        request: Request,
        business_slug: str,
        theme: str = Query(default="light"),
    ):
        return render_business_profile_page(request, business_slug, theme)

    @app.post("/passport", response_class=HTMLResponse)
    def render_passport(
        request: Request,
        business_slug: str = Form(...),
        theme: str = Form(default="light"),
    ):
        return render_passport_page(request, business_slug, theme)

    @app.post("/pob", response_class=HTMLResponse)
    def render_pob_alias(
        request: Request,
        business_slug: str = Form(...),
        theme: str = Form(default="light"),
    ):
        return render_passport_page(request, business_slug, theme)

    @app.post("/business", response_class=HTMLResponse)
    def render_business_alias(
        request: Request,
        business_slug: str = Form(...),
        theme: str = Form(default="light"),
    ):
        return render_business_profile_page(request, business_slug, theme)

    @app.get("/payments/return/{intent_id}")
    def payment_return_alias(intent_id: str, request: Request):
        payment_service = PaymentService(settings)
        next_url = request.query_params.get("next")
        redirect_url = payment_service.finalize_payment_return(intent_id, next_url=next_url)
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url=redirect_url, status_code=303)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
