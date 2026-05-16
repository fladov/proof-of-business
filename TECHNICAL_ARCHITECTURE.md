# Technical Architecture

This document explains how the Proof of Business by Fladov codebase is organized, which files matter most, and how the main application flows move through the system.

It is written as an engineering guide for someone onboarding into the repository.

## Top-Level Structure

```text
app/
  api/
  core/
    rank_engine/
  fladov/
  payments/
  reports/
  static/
  templates/
  main.py
  settings.py
tests/
  fixtures/
  unit/
runtime/
README.md
TECHNICAL_ARCHITECTURE.md
pyproject.toml
```

## Application Entry Layer

### [app/main.py](</C:/Users/HP/Documents/New project/app/main.py>)

This is the FastAPI application entrypoint.

Responsibilities:

- builds the app
- mounts static assets
- includes the API router
- renders the homepage
- renders business pages
- renders passport pages
- handles query-driven payment prefill and invoice-backed passport rendering
- exposes `/health`

The most important internal helpers are:

- `render_passport_page(...)`
- `render_business_profile_page(...)`

The passport helper is where:

- the Fladov business export is fetched
- optional `pay_invoice` is resolved
- payment summary is loaded
- the report service is called
- the final template context is assembled

### [app/settings.py](</C:/Users/HP/Documents/New project/app/settings.py>)

This is the runtime configuration layer.

Responsibilities:

- loads `.env` from the project root
- defines the immutable `Settings` dataclass
- normalizes the API route prefix
- resolves environment variables into one cached settings object

Key design detail:

- it supports both `POB_*` names and some plain fallback env names for payment credentials and webhook config

## API Layer

### [app/api/routes.py](</C:/Users/HP/Documents/New project/app/api/routes.py>)

This builds the top-level API router under `settings.api_route_prefix`.

Responsibilities:

- mounts the Fladov API router
- mounts the payments API router
- exposes `POST /passport/generate`

### [app/api/models.py](</C:/Users/HP/Documents/New project/app/api/models.py>)

Small Pydantic request/response models for the passport generation API.

## Fladov Data Layer

The Fladov subsystem is the business-data backbone of the app.

### [app/fladov/contracts.py](</C:/Users/HP/Documents/New project/app/fladov/contracts.py>)

Defines the shared typed contracts for Fladov data:

- `FladovBusinessSummary`
- `FladovInvoiceLineItem`
- `FladovInvoice`
- `FladovBusinessExport`
- `FladovRepositoryManifest`

These types are the central contract between:

- the demo repository
- the future live Fladov repository
- the passport/report layer
- the payment metadata layer

Important detail:

- `FladovBusinessExport` includes both the PoB payload used by the scoring engine and a list of Fladov invoices.

### [app/fladov/demo_data.py](</C:/Users/HP/Documents/New project/app/fladov/demo_data.py>)

This is the complete demo data generator.

Responsibilities:

- generates the top-level Fladov manifest
- seeds 10 demo businesses
- builds PoB-schema-compatible record bundles
- seeds one invoice per demo business
- provides the global invoice preview template
- generates business avatar URLs and placeholder SVG fallbacks

This file is large because it contains the main deterministic demo world for the product.

### [app/fladov/repository.py](</C:/Users/HP/Documents/New project/app/fladov/repository.py>)

This is the repository abstraction layer.

Main parts:

- `FladovRepository` protocol
- `MockFladovRepository`
- `LiveFladovRepository`
- `build_fladov_repository(settings)`

Responsibilities:

- list searchable businesses
- fetch one business export by slug
- return the full manifest
- fetch one business-scoped invoice
- return the invoice preview template

Design intent:

- demo mode reads in-repo data
- live mode reads Fladov API data
- both implementations produce the same internal contracts

### [app/fladov/service.py](</C:/Users/HP/Documents/New project/app/fladov/service.py>)

Thin service layer around the repository.

Responsibilities:

- hide repository instantiation
- expose the most common operations the rest of the app needs
- keep `main.py`, payments, and reports from directly dealing with repository implementation details

### [app/fladov/routes.py](</C:/Users/HP/Documents/New project/app/fladov/routes.py>)

Fladov-facing API endpoints.

Current endpoints:

- `GET /fladov/businesses`
- `GET /fladov/businesses/{slug}`
- `GET /fladov/businesses/{slug}/invoices/{invoice_id}`
- `POST /fladov/webhooks/post-payment`

Notes:

- business search returns no businesses until a query is provided
- search results are capped to 10
- the top-level response also includes `enabled_business_count`
- the demo post-payment webhook is currently a simple echo/ack route

## Rank Engine

The rank engine lives in [app/core/rank_engine](</C:/Users/HP/Documents/New project/app/core/rank_engine>).

### [app/core/rank_engine/engine.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/engine.py>)

This is the public orchestration entrypoint.

Main exported functions:

- `rank_business`
- `score_fladov_business`
- `generate_fladov_pob_report`

Pipeline:

1. validate payload
2. normalize payload
3. build evidence graph
4. compute shared metrics
5. run rule-based anomaly detection
6. run ML anomaly analysis
7. calculate final result

### [app/core/rank_engine/schema](</C:/Users/HP/Documents/New project/app/core/rank_engine/schema>)

Validation layer for the PoB payload contract.

### [app/core/rank_engine/normalization](</C:/Users/HP/Documents/New project/app/core/rank_engine/normalization>)

Normalization layer that cleans and derives normalized values before scoring.

### [app/core/rank_engine/evidence](</C:/Users/HP/Documents/New project/app/core/rank_engine/evidence>)

Builds the evidence graph across records such as orders, cashbook entries, verified payments, documents, and logs.

### [app/core/rank_engine/metrics](</C:/Users/HP/Documents/New project/app/core/rank_engine/metrics>)

Computes the shared business metrics that later feed scoring and anomaly analysis.

### [app/core/rank_engine/risk](</C:/Users/HP/Documents/New project/app/core/rank_engine/risk>)

Rule-based anomaly detection and flag generation.

### [app/core/rank_engine/ml/analyzer.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/ml/analyzer.py>)

ML-assisted anomaly layer.

Responsibilities:

- extract ML features from computed metrics
- build a reference corpus
- run `IsolationForest` when `scikit-learn` is available
- fall back to a deterministic compatibility analyzer when it is not
- produce an `MlAnomalyResult` with:
  - anomaly score
  - percentile
  - severity
  - top feature deltas
  - backend metadata

This layer is intended to support risk and confidence, not replace deterministic scoring.

### [app/core/rank_engine/scoring](</C:/Users/HP/Documents/New project/app/core/rank_engine/scoring>)

Final score composition and result assembly.

### [app/core/rank_engine/models.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/models.py>)

Typed result models for the engine, including ML analysis structures.

### [app/core/rank_engine/config.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/config.py>)

Central configuration for thresholds, weights, feature names, ML parameters, and score behavior.

## Report Composition Layer

The report layer converts raw engine output into a UI-facing passport payload.

### [app/reports/service.py](</C:/Users/HP/Documents/New project/app/reports/service.py>)

Thin service wrapper that:

- fetches the Fladov business export
- calls the composer
- returns a serializable passport dict

### [app/reports/models.py](</C:/Users/HP/Documents/New project/app/reports/models.py>)

Defines UI-facing view models:

- `SubScoreItem`
- `PassportTab`
- `PassportInvoicePreview`
- `PassportView`

### [app/reports/composer.py](</C:/Users/HP/Documents/New project/app/reports/composer.py>)

This is the key bridge between raw engine output and the rendered passport.

Responsibilities:

- call the engine
- build confidence presentation
- build payment-aware passport state
- build customer, investor, and lender tabs
- derive risk notes
- derive improvement notes
- build invoice preview HTML from Fladov invoice data plus the global invoice template

Important detail:

- invoice preview rendering is server-side token substitution into trusted Fladov-owned template HTML

### [app/reports/presentation.py](</C:/Users/HP/Documents/New project/app/reports/presentation.py>)

Converts score values and confidence levels into UI-facing presentation objects such as percentage formatting and band labels.

## Payment Layer

The payment subsystem lives in [app/payments](</C:/Users/HP/Documents/New project/app/payments>).

### [app/payments/models.py](</C:/Users/HP/Documents/New project/app/payments/models.py>)

Core payment domain models:

- `PaymentIntent`
- `PaymentSummary`

`PaymentIntent.metadata` is important because it holds extended Fladov context such as:

- business identifiers
- business profile URL
- Fladov post-payment webhook URL
- invoice identifiers and totals when payment came from `pay_invoice`

### [app/payments/api_models.py](</C:/Users/HP/Documents/New project/app/payments/api_models.py>)

Pydantic models for payment API requests and responses.

### [app/payments/service.py](</C:/Users/HP/Documents/New project/app/payments/service.py>)

This is the payment orchestration core.

Responsibilities:

- load current payment summary
- create payment intents
- fetch payment intents
- verify and process Squad webhook payloads
- verify payment status on return
- build redirect URLs
- append alert query params
- dispatch post-payment success notifications

Important invoice behavior:

- if `invoice_id` is provided during intent creation, the service resolves the invoice from Fladov
- it uses the invoice total as the authoritative payment amount
- it stores invoice metadata into the payment intent

### [app/payments/store.py](</C:/Users/HP/Documents/New project/app/payments/store.py>)

Simple JSON-backed persistence for payment intents.

Storage file:

- `runtime/payments.json`

### [app/payments/registry.py](</C:/Users/HP/Documents/New project/app/payments/registry.py>)

Resolves the configured payment provider.

### [app/payments/providers/base.py](</C:/Users/HP/Documents/New project/app/payments/providers/base.py>)

Base payment provider structures such as `PaymentInitiation`.

### [app/payments/providers/squad.py](</C:/Users/HP/Documents/New project/app/payments/providers/squad.py>)

The active payment provider adapter.

Responsibilities:

- create Squad payment sessions
- verify transactions
- verify webhook signatures

### [app/payments/notifications.py](</C:/Users/HP/Documents/New project/app/payments/notifications.py>)

Outbound webhook dispatcher for successful payments.

Responsibilities:

- build the outbound payload
- sign it when configured
- post it to Fladov or another configured receiver
- record delivery success or failure metadata

### [app/payments/routes.py](</C:/Users/HP/Documents/New project/app/payments/routes.py>)

Payment API endpoints:

- `POST /payments/intents`
- `GET /payments/intents/{intent_id}`
- `GET /payments/return/{intent_id}`
- `POST /payments/webhooks/squad`

## Frontend Layer

### Templates

The Jinja templates live in [app/templates](</C:/Users/HP/Documents/New project/app/templates>):

- `base.html`
- `index.html`
- `business.html`
- `report.html`

Roles:

- `index.html`
  - homepage live search
- `business.html`
  - Fladov public business profile
- `report.html`
  - full passport page, tabs, payment block, invoice preview, risk notes, improvement notes

### Static assets

Assets live in [app/static](</C:/Users/HP/Documents/New project/app/static>):

- `app.js`
- `styles.css`
- `logo.svg`

`app.js` handles:

- theme toggle
- audience menu behavior
- live Fladov search
- sub-score expand/collapse
- payment intent creation
- payment alert rendering
- auto-scroll to payment

## Test Suite

Tests live in [tests/unit](</C:/Users/HP/Documents/New project/tests/unit>).

Main files:

- [tests/unit/test_rank_engine.py](</C:/Users/HP/Documents/New project/tests/unit/test_rank_engine.py>)
  - scoring, ordering, validation, ML behavior
- [tests/unit/test_fladov_repository.py](</C:/Users/HP/Documents/New project/tests/unit/test_fladov_repository.py>)
  - repository contracts, demo data, invoice access
- [tests/unit/test_payments.py](</C:/Users/HP/Documents/New project/tests/unit/test_payments.py>)
  - payment initiation, redirects, webhook validation, outbound notifications
- [tests/unit/test_web_app.py](</C:/Users/HP/Documents/New project/tests/unit/test_web_app.py>)
  - homepage, business page, passport page, invoice-backed passport behavior

Fixtures also exist under [tests/fixtures](</C:/Users/HP/Documents/New project/tests/fixtures>).

## Key Runtime Flows

### Homepage search flow

1. Browser loads `/`
2. `index.html` renders the total enabled-business count
3. `app.js` waits until the user types
4. Search calls `GET /api/fladov/businesses?query=...&limit=10`
5. Results render as passport/profile cards

### Passport flow

1. Browser loads `/passport/{slug}`
2. `main.py` resolves the Fladov business export
3. Optional `pay_invoice` is resolved here too
4. Payment summary is loaded from `PaymentService`
5. `generate_fladov_passport(...)` builds the passport payload
6. `report.html` renders the UI

### Invoice-backed payment flow

1. Browser loads `/passport/{slug}?pay_invoice={invoice_id}`
2. `main.py` fetches the invoice from `FladovRepositoryService`
3. Composer builds `PassportInvoicePreview`
4. Template renders invoice preview and locks payment amount
5. Frontend submits `invoice_id` with the payment intent request
6. `PaymentService` resolves the invoice again and enforces the invoice total server-side

### Payment completion flow

1. Frontend calls `POST /api/payments/intents`
2. `PaymentService` creates and stores a `PaymentIntent`
3. Squad checkout is opened
4. Squad sends webhook and/or browser returns through `/api/payments/return/{intent_id}`
5. `PaymentService` verifies final status
6. `PaymentSuccessWebhookDispatcher` optionally posts the result back to Fladov

## Demo vs Live Boundaries

The main boundary to understand is:

- the web app, rank engine, report layer, and payment orchestration are real application code
- the Fladov upstream business-data layer is still demo-backed unless `POB_FLADOV_DEMO_MODE=false` is combined with a real Fladov API

That means the codebase is already structured for a live Fladov connection, but the repository data source remains the main mocked infrastructure seam.

## Legacy / placeholder directories

There are a few lightweight directories that currently act more as structure placeholders than active feature areas:

- `app/integrations/`
- `app/services/`
- `app/ui/`

The active business logic today is concentrated in:

- `app/fladov`
- `app/core/rank_engine`
- `app/reports`
- `app/payments`
- `app/main.py`

## Practical onboarding order

If a new engineer is joining the project, the fastest understanding path is:

1. Read [README.md](</C:/Users/HP/Documents/New project/README.md>)
2. Read [app/main.py](</C:/Users/HP/Documents/New project/app/main.py>)
3. Read [app/fladov/contracts.py](</C:/Users/HP/Documents/New project/app/fladov/contracts.py>) and [app/fladov/repository.py](</C:/Users/HP/Documents/New project/app/fladov/repository.py>)
4. Read [app/reports/composer.py](</C:/Users/HP/Documents/New project/app/reports/composer.py>)
5. Read [app/core/rank_engine/engine.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/engine.py>)
6. Read [app/payments/service.py](</C:/Users/HP/Documents/New project/app/payments/service.py>)
7. Run [tests/unit/test_web_app.py](</C:/Users/HP/Documents/New project/tests/unit/test_web_app.py>) and [tests/unit/test_payments.py](</C:/Users/HP/Documents/New project/tests/unit/test_payments.py>)

That path gives the clearest end-to-end understanding of how the app works.
