"""Deterministic mock Fladov repository data for Proof of Business."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from typing import Any


DEMO_POB_SCHEMA_VERSION = "1.0.0"
DEMO_POST_PAYMENT_WEBHOOK_URL = "http://127.0.0.1:8000/api/fladov/webhooks/post-payment"
DEMO_INVOICE_PREVIEW_TEMPLATE_HTML = """
<section class="rounded-lg border border-slate-200/80 bg-white/95 p-5 dark:border-white/10 dark:bg-slate-950/30">
  <div class="flex flex-wrap items-start justify-between gap-4">
    <div>
      <p class="text-xs font-medium uppercase tracking-[0.24em] text-slate-400 dark:text-slate-500">$invoice_type_label</p>
      <h3 class="mt-2 font-display text-xl font-bold tracking-tight text-slate-950 dark:text-white">$invoice_number</h3>
      <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">$customer_name</p>
      $customer_email_html
    </div>
    <div class="text-right">
      <span class="inline-flex items-center rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 dark:border-brand-400/20 dark:bg-brand-500/10 dark:text-brand-200">$status_label</span>
      <p class="mt-3 text-sm text-slate-500 dark:text-slate-400">Issued $issued_at_label</p>
      $expires_at_html
    </div>
  </div>
  <div class="mt-5 overflow-hidden rounded-lg border border-slate-200/80 dark:border-white/10">
    <table class="min-w-full divide-y divide-slate-200/80 text-sm dark:divide-white/10">
      <thead class="bg-slate-50/80 dark:bg-white/5">
        <tr>
          <th class="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400">Item</th>
          <th class="px-4 py-3 text-right font-medium text-slate-500 dark:text-slate-400">Qty</th>
          <th class="px-4 py-3 text-right font-medium text-slate-500 dark:text-slate-400">Unit</th>
          <th class="px-4 py-3 text-right font-medium text-slate-500 dark:text-slate-400">Total</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-200/80 bg-white dark:divide-white/10 dark:bg-slate-950/20">
        $items_html
      </tbody>
    </table>
  </div>
  <div class="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
    <div class="space-y-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
      $note_html
      $invoice_link_html
    </div>
    <dl class="space-y-2 text-sm">
      <div class="flex items-center justify-between gap-4"><dt class="text-slate-500 dark:text-slate-400">Subtotal</dt><dd class="font-medium text-slate-900 dark:text-white">$subtotal_label</dd></div>
      <div class="flex items-center justify-between gap-4"><dt class="text-slate-500 dark:text-slate-400">Discount</dt><dd class="font-medium text-slate-900 dark:text-white">$discount_total_label</dd></div>
      <div class="flex items-center justify-between gap-4"><dt class="text-slate-500 dark:text-slate-400">Tax</dt><dd class="font-medium text-slate-900 dark:text-white">$tax_total_label</dd></div>
      <div class="flex items-center justify-between gap-4 border-t border-slate-200/80 pt-3 text-base dark:border-white/10"><dt class="font-semibold text-slate-900 dark:text-white">Total</dt><dd class="font-semibold text-slate-950 dark:text-white">$total_amount_label</dd></div>
      <div class="flex items-center justify-between gap-4"><dt class="text-slate-500 dark:text-slate-400">Balance due</dt><dd class="font-medium text-brand-700 dark:text-brand-300">$balance_due_label</dd></div>
    </dl>
  </div>
</section>
""".strip()


def build_payload(kind: str) -> dict[str, Any]:
    builders = {
        "mature_legitimate_bakery": _mature_legitimate_bakery,
        "new_legitimate_salon": _new_legitimate_salon,
        "suspicious_backfilled_vendor": _suspicious_backfilled_vendor,
        "good_orders_poor_payment_evidence": _good_orders_poor_payment_evidence,
        "verified_payments_poor_fulfillment": _verified_payments_poor_fulfillment,
        "stable_lender_friendly_business": _stable_lender_friendly_business,
        "growth_heavy_volatile_business": _growth_heavy_volatile_business,
        "mature_flat_business": _mature_flat_business,
        "artisan_tailor_studio": _artisan_tailor_studio,
        "seasonal_cafe": _seasonal_cafe,
    }
    return builders[kind]()


def build_mock_fladov_manifest() -> dict[str, Any]:
    business_specs = [
        ("sades-cakes", "Sade's Cakes", "mature_legitimate_bakery", "Bakery", "#0f766e"),
        ("glow-salon", "Glow Salon", "new_legitimate_salon", "Salon", "#10b981"),
        ("quick-mart", "Quick Mart", "suspicious_backfilled_vendor", "Retail", "#ef4444"),
        ("steady-foods", "Steady Foods", "stable_lender_friendly_business", "Catering", "#0ea5e9"),
        ("prime-bites", "Prime Bites", "good_orders_poor_payment_evidence", "Bakery", "#f59e0b"),
        ("verified-delight", "Verified Delight", "verified_payments_poor_fulfillment", "Retail", "#8b5cf6"),
        ("bloom-studio", "Bloom Studio", "growth_heavy_volatile_business", "Fashion", "#14b8a6"),
        ("flatline-goods", "Flatline Goods", "mature_flat_business", "Wholesale", "#475569"),
        ("urban-tailor", "Urban Tailor", "artisan_tailor_studio", "Fashion", "#2563eb"),
        ("sunrise-cafe", "Sunrise Cafe", "seasonal_cafe", "Cafe", "#f97316"),
    ]

    return {
        "pob_schema_version": DEMO_POB_SCHEMA_VERSION,
        "post_payment_webhook_url": DEMO_POST_PAYMENT_WEBHOOK_URL,
        "invoice_preview_template_html": DEMO_INVOICE_PREVIEW_TEMPLATE_HTML,
        "pob_enabled_businesses": [
            _build_manifest_business(slug, display_name, kind, category, avatar_color)
            for slug, display_name, kind, category, avatar_color in business_specs
        ],
    }


def _build_manifest_business(slug: str, display_name: str, kind: str, primary_category: str, avatar_color: str) -> dict[str, Any]:
    payload = deepcopy(build_payload(kind))
    payload["business"]["slug"] = slug
    payload["business"]["name"] = display_name
    payload["business"]["primary_category"] = primary_category
    payload["business"]["profile_url"] = _profile_url(slug)

    return {
        "id": payload["business"]["id"],
        "slug": slug,
        "display_name": display_name,
        "avatar_url": _avatar_image_url(slug, primary_category),
        "avatar_placeholder_url": _avatar_placeholder_data_uri(primary_category),
        "profile_url": _profile_url(slug),
        "pob_schema_version": DEMO_POB_SCHEMA_VERSION,
        "post_payment_webhook_url": DEMO_POST_PAYMENT_WEBHOOK_URL,
        "source": {
            "source_system": "fladov",
            "repository_mode": "demo",
            "pob_schema_version": DEMO_POB_SCHEMA_VERSION,
        },
        "invoices": _build_invoices(slug, display_name, primary_category),
        "business": payload["business"],
        "pob_payload": payload,
    }


def _profile_url(slug: str) -> str:
    return f"https://fladov.com/biz/{slug}"


def _invoice_url(slug: str, invoice_id: str) -> str:
    return f"https://fladov.com/biz/{slug}/invoice/{invoice_id}"


def _avatar_image_url(slug: str, primary_category: str) -> str:
    query_map = {
        "Bakery": ("bakery", "cake", 101),
        "Salon": ("salon", "hair", 102),
        "Retail": ("grocery", "shop", 103),
        "Catering": ("catering", "food", 104),
        "Fashion": ("fashion", "boutique", 105),
        "Wholesale": ("warehouse", "boxes", 106),
        "Cafe": ("coffee", "cafe", 107),
        "Floristry": ("flowers", "bouquet", 108),
        "Studio": ("workspace", "studio", 109),
    }
    tag_one, tag_two, lock = query_map.get(primary_category, ("storefront", "business", 110))
    return f"https://loremflickr.com/320/320/{tag_one},{tag_two}?lock={lock}"


def _avatar_placeholder_data_uri(primary_category: str) -> str:
    color_map = {
        "Bakery": "#f59e0b",
        "Salon": "#10b981",
        "Retail": "#0ea5e9",
        "Catering": "#14b8a6",
        "Fashion": "#8b5cf6",
        "Wholesale": "#64748b",
        "Cafe": "#f97316",
        "Floristry": "#ec4899",
        "Studio": "#2563eb",
    }
    icon_map = {
        "Bakery": """
          <rect x="42" y="84" width="76" height="38" rx="10" fill="#fff" opacity="0.92" />
          <path d="M52 84c4-14 14-22 28-22s24 8 28 22" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" />
          <circle cx="60" cy="104" r="4" fill="{accent}" />
          <circle cx="76" cy="104" r="4" fill="{accent}" />
          <circle cx="92" cy="104" r="4" fill="{accent}" />
          <circle cx="108" cy="104" r="4" fill="{accent}" />
        """,
        "Salon": """
          <path d="M50 92l28-18 12 12-18 28-22 8 8-22Z" fill="#fff" opacity="0.92" />
          <path d="M76 68l18 18" stroke="{accent}" stroke-width="6" stroke-linecap="round" />
          <path d="M90 54l16-16" stroke="{accent}" stroke-width="6" stroke-linecap="round" />
        """,
        "Retail": """
          <path d="M52 66h56l8 16H44l8-16Z" fill="#fff" opacity="0.92" />
          <path d="M48 82h64v34H48V82Z" fill="#fff" opacity="0.82" />
          <path d="M62 92h16" stroke="{accent}" stroke-width="6" stroke-linecap="round" />
          <path d="M86 92h16" stroke="{accent}" stroke-width="6" stroke-linecap="round" />
        """,
        "Catering": """
          <path d="M46 96c0-16 14-30 34-30s34 14 34 30H46Z" fill="#fff" opacity="0.92" />
          <path d="M60 66c4-8 12-14 20-14s16 6 20 14" fill="none" stroke="{accent}" stroke-width="6" stroke-linecap="round" />
        """,
        "Fashion": """
          <path d="M62 58l18-10 18 10-8 12 10 34H60l10-34-8-12Z" fill="#fff" opacity="0.92" />
        """,
        "Wholesale": """
          <rect x="48" y="72" width="30" height="30" rx="5" fill="#fff" opacity="0.92" />
          <rect x="78" y="72" width="30" height="30" rx="5" fill="#fff" opacity="0.82" />
          <rect x="63" y="46" width="30" height="30" rx="5" fill="#fff" opacity="0.72" />
        """,
        "Cafe": """
          <path d="M50 82h48c0 18-12 30-24 30s-24-12-24-30Z" fill="#fff" opacity="0.92" />
          <path d="M98 86h10c0 8-4 14-10 14" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" />
          <path d="M66 56c0 6 4 8 4 14" fill="none" stroke="{accent}" stroke-width="5" stroke-linecap="round" />
          <path d="M82 56c0 6 4 8 4 14" fill="none" stroke="{accent}" stroke-width="5" stroke-linecap="round" />
        """,
        "Floristry": """
          <circle cx="80" cy="82" r="12" fill="{accent}" />
          <circle cx="80" cy="58" r="12" fill="#fff" opacity="0.88" />
          <circle cx="64" cy="70" r="12" fill="#fff" opacity="0.82" />
          <circle cx="96" cy="70" r="12" fill="#fff" opacity="0.82" />
          <circle cx="68" cy="94" r="12" fill="#fff" opacity="0.82" />
          <circle cx="92" cy="94" r="12" fill="#fff" opacity="0.82" />
        """,
        "Studio": """
          <rect x="46" y="68" width="68" height="38" rx="10" fill="#fff" opacity="0.92" />
          <circle cx="80" cy="87" r="11" fill="{accent}" />
          <rect x="68" y="52" width="24" height="12" rx="4" fill="#fff" opacity="0.82" />
        """,
    }
    color = color_map.get(primary_category, "#0f766e")
    icon = icon_map.get(
        primary_category,
        """
          <rect x="48" y="72" width="64" height="40" rx="12" fill="#fff" opacity="0.9" />
          <path d="M58 72c4-12 12-18 22-18s18 6 22 18" fill="none" stroke="#fff" stroke-width="8" stroke-linecap="round" />
        """,
    ).format(accent=color)
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 160 160">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="{color}" />
          <stop offset="100%" stop-color="#0f172a" />
        </linearGradient>
      </defs>
      <rect width="160" height="160" rx="28" fill="url(#g)" />
      <circle cx="122" cy="40" r="18" fill="#fff" opacity="0.08" />
      <circle cx="38" cy="118" r="24" fill="#fff" opacity="0.06" />
      <g transform="translate(0 4)">
        {icon}
      </g>
    </svg>
    """.strip()
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def _build_invoices(slug: str, display_name: str, primary_category: str) -> list[dict[str, Any]]:
    invoice_specs = {
        "sades-cakes": {
            "invoice_id": "inv_sades_001",
            "invoice_type": "proforma_invoice",
            "invoice_number": "FLD-PRO-1001",
            "status": "open",
            "issued_days_ago": 4,
            "expires_days_ago": -10,
            "customer_name": "Kemi Johnson",
            "customer_email": "kemi@example.com",
            "line_items": [
                ("Celebration cake", 1, 42000),
                ("Cupcake box", 3, 6500),
            ],
            "discount_total": 2000,
            "tax_total": 0,
            "note": "Collection is available from 9am after payment clears.",
        },
        "glow-salon": {
            "invoice_id": "inv_glow_001",
            "invoice_type": "quotation",
            "invoice_number": "FLD-QUO-2027",
            "status": "draft",
            "issued_days_ago": 2,
            "expires_days_ago": -5,
            "customer_name": "Amara Obi",
            "customer_email": "amara@example.com",
            "line_items": [
                ("Braiding session", 1, 18000),
                ("Hair treatment add-on", 1, 4500),
            ],
            "discount_total": 0,
            "tax_total": 0,
            "note": "Appointment slot is reserved for 48 hours after confirmation.",
        },
        "quick-mart": {
            "invoice_id": "inv_quick_001",
            "invoice_type": "proforma_invoice",
            "invoice_number": "FLD-PRO-3042",
            "status": "open",
            "issued_days_ago": 1,
            "expires_days_ago": -7,
            "customer_name": "Nedu Okafor",
            "customer_email": "nedu@example.com",
            "line_items": [
                ("Household restock bundle", 1, 25000),
                ("Delivery fee", 1, 2500),
            ],
            "discount_total": 0,
            "tax_total": 0,
            "note": "Delivery timeline depends on stock confirmation.",
        },
        "steady-foods": {
            "invoice_id": "inv_steady_001",
            "invoice_type": "quotation",
            "invoice_number": "FLD-QUO-4108",
            "status": "open",
            "issued_days_ago": 6,
            "expires_days_ago": -12,
            "customer_name": "The Brix Offices",
            "customer_email": "ops@brix.example",
            "line_items": [
                ("Corporate lunch trays", 8, 16500),
                ("Service logistics", 1, 18000),
            ],
            "discount_total": 6000,
            "tax_total": 0,
            "note": "Menus can still be adjusted before final confirmation.",
        },
        "prime-bites": {
            "invoice_id": "inv_prime_001",
            "invoice_type": "proforma_invoice",
            "invoice_number": "FLD-PRO-5190",
            "status": "open",
            "issued_days_ago": 3,
            "expires_days_ago": -8,
            "customer_name": "Tolu Aina",
            "customer_email": "tolu@example.com",
            "line_items": [
                ("Signature small chops tray", 2, 14000),
                ("Mocktail set", 1, 12000),
            ],
            "discount_total": 1500,
            "tax_total": 0,
            "note": "Payment confirms prep slot for the event date.",
        },
        "verified-delight": {
            "invoice_id": "inv_verified_001",
            "invoice_type": "quotation",
            "invoice_number": "FLD-QUO-6204",
            "status": "open",
            "issued_days_ago": 5,
            "expires_days_ago": -9,
            "customer_name": "Ayo Peters",
            "customer_email": "ayo@example.com",
            "line_items": [
                ("Retail gift hamper", 4, 9800),
                ("Packaging", 1, 3200),
            ],
            "discount_total": 0,
            "tax_total": 0,
            "note": "Packaging is included in the quoted amount.",
        },
        "bloom-studio": {
            "invoice_id": "inv_bloom_001",
            "invoice_type": "proforma_invoice",
            "invoice_number": "FLD-PRO-7317",
            "status": "open",
            "issued_days_ago": 2,
            "expires_days_ago": -6,
            "customer_name": "Mia Styles",
            "customer_email": "mia@example.com",
            "line_items": [
                ("Custom outfit deposit", 1, 55000),
                ("Fabric sourcing", 1, 18000),
            ],
            "discount_total": 0,
            "tax_total": 0,
            "note": "Fabric sourcing starts immediately after payment.",
        },
        "flatline-goods": {
            "invoice_id": "inv_flatline_001",
            "invoice_type": "quotation",
            "invoice_number": "FLD-QUO-8450",
            "status": "open",
            "issued_days_ago": 7,
            "expires_days_ago": -14,
            "customer_name": "Northlink Traders",
            "customer_email": "purchasing@northlink.example",
            "line_items": [
                ("Bulk pantry cartons", 12, 11200),
                ("Interstate dispatch", 1, 24000),
            ],
            "discount_total": 8000,
            "tax_total": 0,
            "note": "Lead time shortens once payment is confirmed.",
        },
        "urban-tailor": {
            "invoice_id": "inv_tailor_001",
            "invoice_type": "proforma_invoice",
            "invoice_number": "FLD-PRO-9501",
            "status": "open",
            "issued_days_ago": 1,
            "expires_days_ago": -5,
            "customer_name": "Linda Eze",
            "customer_email": "linda@example.com",
            "line_items": [
                ("Two-piece outfit", 1, 38000),
                ("Alteration package", 1, 8500),
            ],
            "discount_total": 0,
            "tax_total": 0,
            "note": "Measurements are confirmed and ready for production.",
        },
        "sunrise-cafe": {
            "invoice_id": "inv_sunrise_001",
            "invoice_type": "quotation",
            "invoice_number": "FLD-QUO-1068",
            "status": "open",
            "issued_days_ago": 4,
            "expires_days_ago": -7,
            "customer_name": "Rita James",
            "customer_email": "rita@example.com",
            "line_items": [
                ("Breakfast platter", 6, 8500),
                ("Coffee flask set", 2, 7000),
            ],
            "discount_total": 2500,
            "tax_total": 0,
            "note": "Morning delivery window is held once payment is made.",
        },
    }
    spec = invoice_specs[slug]
    return [
        _invoice(
            invoice_id=spec["invoice_id"],
            business_slug=slug,
            business_display_name=display_name,
            primary_category=primary_category,
            invoice_type=spec["invoice_type"],
            invoice_number=spec["invoice_number"],
            status=spec["status"],
            issued_days_ago=spec["issued_days_ago"],
            expires_days_ago=spec["expires_days_ago"],
            customer_name=spec["customer_name"],
            customer_email=spec["customer_email"],
            line_items=spec["line_items"],
            discount_total=spec["discount_total"],
            tax_total=spec["tax_total"],
            note=spec["note"],
        )
    ]


def _invoice(
    *,
    invoice_id: str,
    business_slug: str,
    business_display_name: str,
    primary_category: str,
    invoice_type: str,
    invoice_number: str,
    status: str,
    issued_days_ago: int,
    expires_days_ago: int | None,
    customer_name: str,
    customer_email: str | None,
    line_items: list[tuple[str, float, float]],
    discount_total: float,
    tax_total: float,
    note: str | None,
) -> dict[str, Any]:
    normalized_items = []
    subtotal = 0.0
    for description, quantity, unit_price in line_items:
        total_amount = float(quantity) * float(unit_price)
        subtotal += total_amount
        normalized_items.append(
            {
                "description": description,
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "total_amount": total_amount,
            }
        )
    total_amount = subtotal - float(discount_total) + float(tax_total)
    return {
        "id": invoice_id,
        "business_slug": business_slug,
        "invoice_type": invoice_type,
        "invoice_number": invoice_number,
        "status": status,
        "issued_at": _iso(issued_days_ago),
        "expires_at": _iso(expires_days_ago) if expires_days_ago is not None else None,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "currency": "NGN",
        "subtotal": subtotal,
        "discount_total": float(discount_total),
        "tax_total": float(tax_total),
        "total_amount": total_amount,
        "balance_due": total_amount,
        "line_items": normalized_items,
        "note": note or f"{business_display_name} will begin fulfilment once payment is confirmed in Fladov.",
        "invoice_url": _invoice_url(business_slug, invoice_id),
        "business_display_name": business_display_name,
        "primary_category": primary_category,
    }


def _base_payload(joined_days_ago: int = 360, exported_days_ago: int = 0) -> dict[str, Any]:
    exported_at = _dt(exported_days_ago)
    joined_at = exported_at - timedelta(days=joined_days_ago)
    return {
        "schema_version": DEMO_POB_SCHEMA_VERSION,
        "export": {
            "source_system": "fladov",
            "exported_at": exported_at.isoformat().replace("+00:00", "Z"),
            "export_id": "export_01",
            "mode": "full_refresh",
        },
        "business": {
            "id": "biz_123",
            "slug": "sample-biz",
            "name": "Sample Biz",
            "joined_at": joined_at.isoformat().replace("+00:00", "Z"),
            "pob_enabled_at": (exported_at - timedelta(days=30)).isoformat().replace("+00:00", "Z"),
            "primary_category": "Bakery",
            "secondary_categories": ["Catering"],
            "business_type": "hybrid",
            "profile_url": _profile_url("sample-biz"),
        },
        "records": {
            "products": [],
            "orders": [],
            "purchases": [],
            "general_financial_operations": [],
            "cashbook_entries": [],
            "transaction_documents": [],
            "operation_logs": [],
            "verified_payments": [],
        },
    }


def _mature_legitimate_bakery() -> dict[str, Any]:
    payload = _base_payload(joined_days_ago=420)
    payload["business"]["slug"] = "sades-cakes"
    payload["business"]["name"] = "Sade's Cakes"
    payload["business"]["primary_category"] = "Bakery"
    payload["records"]["products"] = [
        _product("prod_cake", 380, 3, 5500, 12),
        _product("prod_pastry", 240, 2, 2200, 35),
        _product("prod_catering", 120, 4, 18000, 5),
    ]
    orders = []
    purchases = []
    cashbook = []
    verified = []
    docs = []
    logs = []
    gen_ops = []
    customer_ids = ["cust_a", "cust_b", "cust_c", "cust_d", "cust_e", "cust_f"]
    for index, days_ago in enumerate([360, 330, 300, 270, 240, 210, 180, 150, 120, 90, 60, 30]):
        order_id = f"ord_{index}"
        payment_id = f"pay_{index}"
        orders.append(_order(order_id, days_ago, customer_ids[index % len(customer_ids)], "completed", "paid", 10000 + (index * 500), 9800 + (index * 450)))
        purchases.append(_purchase(f"pur_{index}", days_ago + 4, 4500 + (index * 100), 0.0))
        gen_ops.append(_gfo(f"gfo_{index}", days_ago + 2, 1500 + index * 20))
        cashbook.append(_cashbook(f"cb_{index}", days_ago, "income", 10000 + (index * 500), "paid", "order", order_id, payment_id))
        cashbook.append(_cashbook(f"cbx_{index}", days_ago + 5, "expense", 4200 + (index * 80), "paid", "purchase", f"pur_{index}", None))
        verified.append(_verified_payment(payment_id, days_ago, 10000 + (index * 500), "successful"))
        docs.append(_document(f"doc_{index}", "order", order_id, days_ago, 10000 + (index * 500), "invoice", preview=False))
        logs.append(_log(f"log_{index}", "order", order_id, days_ago, success=True, source="web"))
    payload["records"]["orders"] = orders
    payload["records"]["purchases"] = purchases
    payload["records"]["general_financial_operations"] = gen_ops
    payload["records"]["cashbook_entries"] = cashbook
    payload["records"]["verified_payments"] = verified
    payload["records"]["transaction_documents"] = docs
    payload["records"]["operation_logs"] = logs
    return payload


def _new_legitimate_salon() -> dict[str, Any]:
    payload = _base_payload(joined_days_ago=50)
    payload["business"]["slug"] = "glow-salon"
    payload["business"]["name"] = "Glow Salon"
    payload["business"]["primary_category"] = "Salon"
    payload["records"]["products"] = [_product("svc_braids", 40, 1, 15000, None)]
    payload["records"]["orders"] = [
        _order("ord_1", 35, "cust_1", "completed", "paid", 15000, 14000),
        _order("ord_2", 18, "cust_2", "completed", "paid", 18000, 16000),
        _order("ord_3", 7, "cust_1", "confirmed", "partial", 12000, 6000),
    ]
    payload["records"]["cashbook_entries"] = [
        _cashbook("cb_1", 35, "income", 14000, "paid", "order", "ord_1", "pay_1"),
        _cashbook("cb_2", 18, "income", 16000, "paid", "order", "ord_2", None),
        _cashbook("cb_3", 10, "expense", 5000, "paid", "general_financial_operation", "gfo_1", None),
    ]
    payload["records"]["verified_payments"] = [_verified_payment("pay_1", 35, 14000, "successful")]
    payload["records"]["general_financial_operations"] = [_gfo("gfo_1", 10, 5000)]
    payload["records"]["transaction_documents"] = [_document("doc_1", "order", "ord_1", 35, 15000, "invoice", preview=False)]
    payload["records"]["operation_logs"] = [
        _log("log_1", "order", "ord_1", 35, success=True, source="web"),
        _log("log_2", "order", "ord_2", 18, success=True, source="bica"),
        _log("log_3", "cashbook_entry", "cb_2", 18, success=True, source="web"),
    ]
    return payload


def _suspicious_backfilled_vendor() -> dict[str, Any]:
    payload = _base_payload(joined_days_ago=200)
    payload["business"]["slug"] = "quick-mart"
    payload["business"]["name"] = "Quick Mart"
    payload["business"]["primary_category"] = "Retail"
    payload["records"]["products"] = [_product("prod_1", 5, 0, 5000, 1)]
    for index in range(10):
        payload["records"]["orders"].append(_order(f"ord_{index}", 4, "cust_big", "confirmed", "paid", 5000, 5000))
        payload["records"]["cashbook_entries"].append(_cashbook(f"cb_{index}", 4, "income", 5000, "pending", "order", f"missing_{index}", None))
        payload["records"]["transaction_documents"].append(_document(f"doc_{index}", "order", f"missing_{index}", 4, 5000, "invoice", preview=True, file_present=False))
    payload["records"]["verified_payments"] = [
        _verified_payment("pay_1", 4, 5000, "failed"),
        _verified_payment("pay_2", 4, 5000, "refunded"),
    ]
    payload["records"]["operation_logs"] = [
        _log("log_1", "order", "missing_1", 4, success=False, source="web"),
        _log("log_2", "order", "missing_2", 4, success=False, source="web"),
    ]
    payload["records"]["purchases"] = [_purchase("pur_1", 3, 2000, 1800, deleted_days_ago=1)]
    return payload


def _good_orders_poor_payment_evidence() -> dict[str, Any]:
    payload = deepcopy(_mature_legitimate_bakery())
    payload["business"]["slug"] = "prime-bites"
    payload["business"]["name"] = "Prime Bites"
    payload["business"]["primary_category"] = "Bakery"
    payload["records"]["verified_payments"] = []
    for entry in payload["records"]["cashbook_entries"]:
        if entry["type"] == "income":
            entry["verified_payment_id"] = None
    return payload


def _verified_payments_poor_fulfillment() -> dict[str, Any]:
    payload = deepcopy(_mature_legitimate_bakery())
    payload["business"]["slug"] = "verified-delight"
    payload["business"]["name"] = "Verified Delight"
    payload["business"]["primary_category"] = "Retail"
    for order in payload["records"]["orders"][:5]:
        order["status"] = "confirmed"
        order["payment_status"] = "paid"
        order["balance_remaining"] = 0.0
    return payload


def _stable_lender_friendly_business() -> dict[str, Any]:
    payload = deepcopy(_mature_legitimate_bakery())
    payload["business"]["slug"] = "steady-foods"
    payload["business"]["name"] = "Steady Foods"
    payload["business"]["primary_category"] = "Catering"
    return payload


def _growth_heavy_volatile_business() -> dict[str, Any]:
    payload = _base_payload(joined_days_ago=240)
    payload["business"]["slug"] = "bloom-studio"
    payload["business"]["name"] = "Bloom Studio"
    payload["business"]["primary_category"] = "Fashion"
    payload["records"]["products"] = [_product("prod_1", 200, 1, 4000, 2), _product("prod_2", 30, 2, 7000, 4)]
    for index, days_ago in enumerate([210, 180, 150, 90, 60, 45, 30, 20, 15, 10, 7, 3]):
        amount = 3000 if index < 4 else 15000 + (index * 3000)
        order_id = f"ord_{index}"
        payment_id = f"pay_{index}"
        payload["records"]["orders"].append(_order(order_id, days_ago, f"cust_{index}", "completed", "paid", amount, amount))
        payload["records"]["cashbook_entries"].append(_cashbook(f"cb_{index}", days_ago, "income", amount, "paid", "order", order_id, payment_id))
        payload["records"]["verified_payments"].append(_verified_payment(payment_id, days_ago, amount, "successful"))
        payload["records"]["transaction_documents"].append(_document(f"doc_{index}", "order", order_id, days_ago, amount, "receipt", preview=False))
    payload["records"]["cashbook_entries"] += [
        _cashbook("cb_exp_1", 61, "expense", 4000, "paid", "general_financial_operation", "gfo_1", None),
        _cashbook("cb_exp_2", 9, "expense", 20000, "paid", "general_financial_operation", "gfo_2", None),
    ]
    payload["records"]["general_financial_operations"] = [_gfo("gfo_1", 61, 4000), _gfo("gfo_2", 9, 20000)]
    payload["records"]["operation_logs"] = [_log(f"log_{idx}", "order", f"ord_{idx}", days, success=True, source="web") for idx, days in enumerate([210, 180, 150, 90, 60, 45, 30, 20, 15, 10, 7, 3])]
    return payload


def _mature_flat_business() -> dict[str, Any]:
    payload = deepcopy(_mature_legitimate_bakery())
    payload["business"]["slug"] = "flatline-goods"
    payload["business"]["name"] = "Flatline Goods"
    payload["business"]["primary_category"] = "Wholesale"
    for index, order in enumerate(payload["records"]["orders"]):
        order["total_payable"] = 10000
        order["total_paid"] = 10000
        order["gross_profit"] = 2500
        payment_id = payload["records"]["cashbook_entries"][index * 2]["verified_payment_id"]
        payload["records"]["verified_payments"][index]["amount"] = 10000
        payload["records"]["cashbook_entries"][index * 2]["amount"] = 10000
        payload["records"]["transaction_documents"][index]["document_total_amount"] = 10000
        payload["records"]["orders"][index]["id"] = f"flat_{index}"
        payload["records"]["cashbook_entries"][index * 2]["financial_operation_id"] = f"flat_{index}"
        payload["records"]["transaction_documents"][index]["financial_operation_id"] = f"flat_{index}"
        if payment_id:
            payload["records"]["verified_payments"][index]["id"] = payment_id
    return payload


def _artisan_tailor_studio() -> dict[str, Any]:
    payload = deepcopy(_new_legitimate_salon())
    payload["business"]["slug"] = "urban-tailor"
    payload["business"]["name"] = "Urban Tailor"
    payload["business"]["primary_category"] = "Fashion"
    payload["business"]["secondary_categories"] = ["Alterations", "Retail"]
    return payload


def _seasonal_cafe() -> dict[str, Any]:
    payload = deepcopy(_mature_legitimate_bakery())
    payload["business"]["slug"] = "sunrise-cafe"
    payload["business"]["name"] = "Sunrise Cafe"
    payload["business"]["primary_category"] = "Cafe"
    payload["business"]["secondary_categories"] = ["Brunch", "Events"]
    payload["records"]["products"][0]["primary_name"] = "coffee_box"
    payload["records"]["products"][1]["primary_name"] = "pastry_box"
    return payload


def _product(product_id: str, created_days_ago: int, media_count: int, price: float, stock: float | None) -> dict[str, Any]:
    return {
        "id": product_id,
        "product_type": "product",
        "primary_name": product_id,
        "is_inventory_item": stock is not None,
        "tags": ["popular"],
        "primary_price": price,
        "min_price": price,
        "max_price": price,
        "currency": "NGN",
        "average_cost": price * 0.55,
        "latest_cost": price * 0.6,
        "current_stock_quantity": stock,
        "media_count": media_count,
        "created_at": _iso(created_days_ago),
        "updated_at": _iso(max(created_days_ago - 2, 0)),
        "deleted_at": None,
    }


def _order(order_id: str, days_ago: int, customer_id: str, status: str, payment_status: str, total_payable: float, total_paid: float) -> dict[str, Any]:
    return {
        "id": order_id,
        "order_type": "order",
        "customer_contact_id": customer_id,
        "status": status,
        "currency": "NGN",
        "payment_status": payment_status,
        "amount_paid": total_paid,
        "order_date": _iso(days_ago),
        "items_subtotal": total_payable,
        "adjustments_total": 0.0,
        "total_payable": total_payable,
        "total_paid": total_paid,
        "balance_remaining": max(0.0, total_payable - total_paid),
        "item_count": 1,
        "total_quantity": 1,
        "total_cost": total_payable * 0.62,
        "gross_profit": total_paid - (total_payable * 0.62),
        "created_at": _iso(days_ago),
        "updated_at": _iso(max(days_ago - 1, 0)),
        "deleted_at": None,
    }


def _purchase(purchase_id: str, days_ago: int, subtotal: float, balance_remaining: float, deleted_days_ago: int | None = None) -> dict[str, Any]:
    return {
        "id": purchase_id,
        "vendor_contact_id": "vendor_1",
        "status": "completed",
        "currency": "NGN",
        "purchase_date": _iso(days_ago),
        "items_subtotal": subtotal,
        "total_paid": subtotal - balance_remaining,
        "balance_remaining": balance_remaining,
        "item_count": 1,
        "total_quantity": 1,
        "created_at": _iso(days_ago),
        "updated_at": _iso(max(days_ago - 1, 0)),
        "deleted_at": _iso(deleted_days_ago) if deleted_days_ago is not None else None,
    }


def _gfo(operation_id: str, days_ago: int, total_amount: float) -> dict[str, Any]:
    return {
        "id": operation_id,
        "operation_category": "expense",
        "operation_date": _iso(days_ago),
        "currency": "NGN",
        "total_amount": total_amount,
        "entry_count": 1,
        "created_at": _iso(days_ago),
        "updated_at": _iso(max(days_ago - 1, 0)),
        "deleted_at": None,
    }


def _cashbook(entry_id: str, days_ago: int, entry_type: str, amount: float, status: str, operation_type: str, operation_id: str, payment_id: str | None) -> dict[str, Any]:
    return {
        "id": entry_id,
        "amount": amount,
        "currency": "NGN",
        "effective_date": _iso(days_ago),
        "payment_method_id": "pm_1",
        "verified_payment_id": payment_id,
        "financial_operation_type": operation_type,
        "financial_operation_id": operation_id,
        "status": status,
        "type": entry_type,
        "created_at": _iso(days_ago),
        "updated_at": _iso(max(days_ago - 1, 0)),
        "deleted_at": None,
    }


def _document(doc_id: str, operation_type: str, operation_id: str, days_ago: int, amount: float, doc_type: str, preview: bool, file_present: bool = True) -> dict[str, Any]:
    return {
        "id": doc_id,
        "reference_id": f"ref_{doc_id}",
        "slug": doc_id,
        "financial_operation_type": operation_type,
        "financial_operation_id": operation_id,
        "document_type": doc_type,
        "document_total_amount": amount,
        "file_path_present": file_present,
        "is_preview": preview,
        "created_at": _iso(days_ago),
        "updated_at": _iso(max(days_ago - 1, 0)),
        "deleted_at": None,
    }


def _log(log_id: str, entity_type: str, entity_id: str, days_ago: int, success: bool, source: str) -> dict[str, Any]:
    return {
        "id": log_id,
        "user_id": "user_1",
        "parent_entity_type": entity_type,
        "parent_entity_id": entity_id,
        "source": source,
        "operation_name": "create",
        "is_successful": success,
        "created_at": _iso(days_ago),
    }


def _verified_payment(payment_id: str, days_ago: int, amount: float, status: str) -> dict[str, Any]:
    return {
        "id": payment_id,
        "provider": "squad",
        "provider_reference": f"pref_{payment_id}",
        "provider_transaction_id": f"ptx_{payment_id}",
        "status": status,
        "amount": amount,
        "currency": "NGN",
        "payment_channel": "transfer",
        "requested_at": _iso(days_ago),
        "verified_at": _iso(days_ago),
        "paid_at": _iso(days_ago),
        "expires_at": _iso(max(days_ago - 2, 0)),
        "created_at": _iso(days_ago),
        "updated_at": _iso(max(days_ago - 1, 0)),
        "deleted_at": None,
    }


def _dt(days_ago: int) -> datetime:
    return datetime(2026, 5, 13, 10, 30, tzinfo=timezone.utc) - timedelta(days=days_ago)


def _iso(days_ago: int) -> str:
    return _dt(days_ago).isoformat().replace("+00:00", "Z")
