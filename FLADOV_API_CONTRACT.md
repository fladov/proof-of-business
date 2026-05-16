# Fladov API Contract for Proof of Business

This document defines the exact Fladov-side HTTP contract PoB currently expects for a live integration.

It is based on the code as it exists now, not on a future or idealized version.

The goal is simple:

- PoB should be able to switch `POB_FLADOV_DEMO_MODE=false`
- point to a live Fladov base URL
- and work correctly without changing PoB code

## Important Design Rule

No Fladov endpoint should ever expose a raw dump of all PoB-enabled businesses.

The live contract is intentionally split into:

- one metadata endpoint
- one query-limited search endpoint
- one full business export endpoint
- one invoice detail endpoint
- one post-payment webhook receiver

Blank search must return zero businesses.

## Transport And Auth

PoB expects server-to-server integration.

Recommended requirements:

- HTTPS only
- server-side authentication such as `Authorization: Bearer <token>`
- no browser-exposed Fladov credentials
- short-lived or scoped credentials where possible

PoB does not currently enforce one specific auth scheme in code. Fladov can choose the auth mechanism, but the live PoB deployment must be able to call these routes successfully.

## Endpoint Summary

PoB expects these live Fladov endpoints:

- `GET /api/fladov/meta`
- `GET /api/fladov/businesses`
- `GET /api/fladov/businesses/{slug}`
- `GET /api/fladov/businesses/{slug}/invoices/{invoice_id}`
- `POST /api/fladov/webhooks/post-payment`

## 1. Repository Metadata

### Request

```http
GET /api/fladov/meta
Authorization: Bearer <server-token>
```

### Response shape

This route returns only repository metadata. It must not include business arrays.

```json
{
  "pob_schema_version": "1.0.0",
  "post_payment_webhook_url": "https://fladov.example/api/pob/webhooks/post-payment",
  "invoice_preview_template_html": "<section>...</section>",
  "enabled_business_count": 1234
}
```

### Field definitions

- `pob_schema_version`
  - string
  - the PoB schema version Fladov exports into
- `post_payment_webhook_url`
  - string
  - the Fladov endpoint PoB should notify after successful payment
- `invoice_preview_template_html`
  - string
  - one global HTML fragment template used for invoice preview rendering
- `enabled_business_count`
  - integer
  - total number of PoB-enabled businesses available in Fladov

## 2. Search PoB-Enabled Businesses

### Request

```http
GET /api/fladov/businesses?query=salon&limit=10
Authorization: Bearer <server-token>
```

### Query parameters

- `query`
  - optional string
  - PoB sends this from homepage live search
- `limit`
  - optional integer
  - PoB currently sends `10`
  - maximum should be `10`

### Required behavior

- if `query` is blank or missing, return an empty `pob_enabled_businesses` array
- do not return the full business catalog for blank search
- return at most `limit` items
- include `enabled_business_count`
- do not include `post_payment_webhook_url` or `invoice_preview_template_html` here

### Response shape

```json
{
  "pob_schema_version": "1.0.0",
  "enabled_business_count": 1234,
  "pob_enabled_businesses": [
    {
      "id": "biz_123",
      "slug": "glow-salon",
      "display_name": "Glow Salon",
      "avatar_url": "https://cdn.fladov.example/avatars/glow-salon.jpg",
      "avatar_placeholder_url": "data:image/svg+xml;utf8,...",
      "profile_url": "https://fladov.com/biz/glow-salon",
      "pob_schema_version": "1.0.0"
    }
  ]
}
```

### Business summary object

Each item inside `pob_enabled_businesses` must match:

```json
{
  "id": "biz_123",
  "slug": "glow-salon",
  "display_name": "Glow Salon",
  "avatar_url": "https://cdn.fladov.example/avatars/glow-salon.jpg",
  "avatar_placeholder_url": "data:image/svg+xml;utf8,...",
  "profile_url": "https://fladov.com/biz/glow-salon",
  "pob_schema_version": "1.0.0"
}
```

## 3. Fetch One Business Export

### Request

```http
GET /api/fladov/businesses/sades-cakes
Authorization: Bearer <server-token>
```

### Required behavior

- return `404` if the business slug does not exist
- return the full canonical export object
- include the exact `pob_payload` PoB can send into the rank engine without transformation
- include `invoices` for that business

### Response shape

PoB is designed around this canonical export shape:

```json
{
  "id": "biz_123",
  "slug": "sades-cakes",
  "display_name": "Sade's Cakes",
  "avatar_url": "https://cdn.fladov.example/avatars/sades-cakes.jpg",
  "avatar_placeholder_url": "data:image/svg+xml;utf8,...",
  "profile_url": "https://fladov.com/biz/sades-cakes",
  "pob_schema_version": "1.0.0",
  "post_payment_webhook_url": "https://fladov.example/api/pob/webhooks/post-payment",
  "source": {
    "source_system": "fladov",
    "repository_mode": "live",
    "pob_schema_version": "1.0.0"
  },
  "pob_payload": {
    "schema_version": "1.0.0",
    "export": {
      "source_system": "fladov",
      "exported_at": "2026-05-15T10:30:00Z",
      "export_id": "export_01",
      "mode": "full_refresh"
    },
    "business": {
      "id": "biz_123",
      "slug": "sades-cakes",
      "name": "Sade's Cakes",
      "joined_at": "2025-03-21T10:30:00Z",
      "pob_enabled_at": "2026-04-15T10:30:00Z",
      "primary_category": "Bakery",
      "secondary_categories": ["Catering"],
      "business_type": "hybrid",
      "profile_url": "https://fladov.com/biz/sades-cakes"
    },
    "records": {
      "products": [],
      "orders": [],
      "purchases": [],
      "general_financial_operations": [],
      "cashbook_entries": [],
      "transaction_documents": [],
      "operation_logs": [],
      "verified_payments": []
    }
  },
  "invoices": []
}
```

### Notes on this shape

- `business` details live inside `pob_payload.business`
- `pob_payload.records` is the canonical record bundle used by the rank engine
- `post_payment_webhook_url` is business-export-level metadata PoB uses for successful payment callbacks
- `invoices` must be included even if the array is empty

## 4. Fetch One Invoice

### Request

```http
GET /api/fladov/businesses/sades-cakes/invoices/inv_sades_001
Authorization: Bearer <server-token>
```

### Required behavior

- invoice lookup is business-scoped
- return `404` if the invoice does not exist
- return `404` if the invoice does not belong to the business in the URL
- the returned invoice must match the same shape used inside the business export `invoices` array

### Response shape

```json
{
  "id": "inv_sades_001",
  "business_slug": "sades-cakes",
  "invoice_type": "proforma_invoice",
  "invoice_number": "FLD-PRO-1001",
  "status": "open",
  "issued_at": "2026-05-11T10:30:00Z",
  "expires_at": "2026-05-21T10:30:00Z",
  "customer_name": "Kemi Johnson",
  "customer_email": "kemi@example.com",
  "currency": "NGN",
  "subtotal": 61500.0,
  "discount_total": 2000.0,
  "tax_total": 0.0,
  "total_amount": 59500.0,
  "balance_due": 59500.0,
  "line_items": [
    {
      "description": "Celebration cake",
      "quantity": 1.0,
      "unit_price": 42000.0,
      "total_amount": 42000.0
    },
    {
      "description": "Cupcake box",
      "quantity": 3.0,
      "unit_price": 6500.0,
      "total_amount": 19500.0
    }
  ],
  "note": "Collection is available from 9am after payment clears.",
  "invoice_url": "https://fladov.com/biz/sades-cakes/invoice/inv_sades_001"
}
```

### Invoice fields

- `id`
  - string
- `business_slug`
  - string
- `invoice_type`
  - string
  - examples: `proforma_invoice`, `quotation`
- `invoice_number`
  - string
- `status`
  - string
- `issued_at`
  - ISO 8601 string
- `expires_at`
  - ISO 8601 string or `null`
- `customer_name`
  - string
- `customer_email`
  - string or `null`
- `currency`
  - string
- `subtotal`
  - number
- `discount_total`
  - number
- `tax_total`
  - number
- `total_amount`
  - number
- `balance_due`
  - number
- `line_items`
  - array of line items
- `note`
  - string or `null`
- `invoice_url`
  - string or `null`

### Invoice line item shape

```json
{
  "description": "Celebration cake",
  "quantity": 1.0,
  "unit_price": 42000.0,
  "total_amount": 42000.0
}
```

## 5. Receive Post-Payment Success Webhook

### Request

```http
POST /api/fladov/webhooks/post-payment
Content-Type: application/json
X-PoB-Event: payment.succeeded
X-PoB-Intent-ID: pay_123abc
X-PoB-Source: payment_return
X-PoB-Signature: <optional-hmac-sha256>
```

### Request body shape

This is the exact top-level structure PoB currently sends:

```json
{
  "event": "payment.succeeded",
  "source": "payment_return",
  "app_name": "Proof of Business by Fladov",
  "public_base_url": "https://pob.example",
  "recorded_at": "2026-05-15T10:30:00+00:00",
  "payment": {
    "intent_id": "pay_123abc",
    "business_slug": "sades-cakes",
    "business_name": "Sade's Cakes",
    "provider": "squad",
    "amount": 59500.0,
    "currency": "NGN",
    "status": "succeeded",
    "checkout_url": "https://sandbox.squad.co/checkout/tx_123",
    "provider_reference": "pob_pay_123abc",
    "return_url": "https://pob.example/passport/sades-cakes?theme=light&pay_invoice=inv_sades_001",
    "note": null,
    "created_at": "2026-05-15T10:30:00+00:00",
    "updated_at": "2026-05-15T10:32:00+00:00",
    "metadata": {
      "payment_provider": "squad",
      "payment_callback_url": "https://pob.example/api/payments/return/pay_123abc?next=...",
      "fladov_business_id": "biz_123",
      "fladov_business_slug": "sades-cakes",
      "fladov_business_display_name": "Sade's Cakes",
      "fladov_business_profile_url": "https://fladov.com/biz/sades-cakes",
      "fladov_post_payment_webhook_url": "https://fladov.example/api/pob/webhooks/post-payment",
      "fladov_pob_schema_version": "1.0.0",
      "fladov_invoice_id": "inv_sades_001",
      "fladov_invoice_number": "FLD-PRO-1001",
      "fladov_invoice_type": "proforma_invoice",
      "fladov_invoice_total_amount": 59500.0,
      "fladov_invoice_balance_due": 59500.0
    },
    "raw_provider_response": {},
    "webhook_payload": {}
  },
  "invoice": {
    "id": "inv_sades_001",
    "invoice_number": "FLD-PRO-1001",
    "invoice_type": "proforma_invoice",
    "total_amount": 59500.0,
    "balance_due": 59500.0
  },
  "verification_payload": {}
}
```

### Required behavior

- respond with `2xx` when accepted
- parse and preserve the invoice block when present
- parse and preserve the `payment.metadata` object
- validate `X-PoB-Signature` if Fladov and PoB share a webhook secret

### Suggested success response

```json
{
  "success": true,
  "message": "Fladov post-payment webhook received."
}
```

## Invoice Preview Template Contract

Fladov must provide one global HTML fragment in the `invoice_preview_template_html` field returned by `GET /api/fladov/meta`.

PoB performs server-side token substitution with these exact placeholders:

- `$invoice_type_label`
- `$invoice_number`
- `$status_label`
- `$customer_name`
- `$customer_email_html`
- `$issued_at_label`
- `$expires_at_html`
- `$items_html`
- `$note_html`
- `$invoice_link_html`
- `$subtotal_label`
- `$discount_total_label`
- `$tax_total_label`
- `$total_amount_label`
- `$balance_due_label`

Rules:

- return a fragment, not a complete HTML document
- PoB escapes values before substitution
- do not assume browser-side rendering
- `invoice_url` is optional, but if present PoB will render a `View full invoice on Fladov` link

## PoB Payload Requirements

PoB sends `pob_payload` directly into the rank engine. That payload must be complete and internally consistent.

At minimum, PoB expects these record groups:

- `products`
- `orders`
- `purchases`
- `general_financial_operations`
- `cashbook_entries`
- `transaction_documents`
- `operation_logs`
- `verified_payments`

The current demo system uses that exact group list, and the engine expects those names.

## Error Responses

PoB is tolerant of standard JSON error bodies, but the status codes matter.

Use:

- `404` for unknown business slug
- `404` for unknown invoice ID
- `404` when an invoice does not belong to the business in the URL
- `401` or `403` for auth failures
- `5xx` for Fladov-side failures

Suggested error shape:

```json
{
  "detail": "Unknown Fladov invoice 'inv_missing' for business 'sades-cakes'."
}
```

## What Fladov Must Implement

For PoB live mode to work correctly today, Fladov must implement:

1. `GET /api/fladov/meta`
2. `GET /api/fladov/businesses`
3. `GET /api/fladov/businesses/{slug}`
4. `GET /api/fladov/businesses/{slug}/invoices/{invoice_id}`
5. `POST /api/fladov/webhooks/post-payment`

And the following behavioral rules:

- never return all businesses for blank search
- cap business search results to 10
- return exact canonical business export objects
- keep invoice lookup business-scoped
- provide one global invoice preview template
- accept PoB payment success webhooks

If Fladov implements these routes and shapes as written, PoB can switch out of demo mode and the current codebase should work without further contract changes.
