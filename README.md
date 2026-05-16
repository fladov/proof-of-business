# Proof of Business by Fladov

Proof of Business by Fladov, or PoB, is a Fladov-native sub-app that turns real business activity recorded on Fladov into a public credibility passport.

Fladov helps small businesses run their operations. PoB reads that operational history, scores it, explains it, and presents it as a privacy-safe passport that helps customers, lenders, investors, and payers understand how credible a business looks from its actual Fladov trail.

Squad powers verified payments inside the passport experience. When a payment is made through PoB, the payment result strengthens the evidence trail and can be sent back to Fladov through a post-payment webhook.

## Product Story

The product story is deliberately Fladov-native:

- Fladov businesses record orders, products, cashbook entries, purchases, documents, logs, and verified payments.
- PoB converts that activity into credibility, payment confidence, operational maturity, growth, and credit-readiness signals.
- The result is a public Fladov credibility passport.
- Fake vendors ask people to trust them. Fladov businesses can prove themselves.

PoB is not presented here as a multi-provider trust layer. Business records are Fladov-only. Payment-provider flexibility still exists inside the verified payments layer, where Squad is the active provider today.

## What the App Does

- Searches PoB-enabled Fladov businesses from the homepage
- Opens a public business profile page and a public passport page
- Generates customer, investor, and lender views from the same Fladov business export
- Shows confidence and risk alongside score explanations
- Supports direct Squad-powered payment initiation from the passport page
- Supports invoice-backed payment flows with `?pay_invoice={invoice_id}`
- Sends post-payment success notifications back to the Fladov-side webhook
- Includes a lightweight ML anomaly layer to support risk and confidence analysis

## Main User Flows

### 1. Passport flow

1. A user searches for a Fladov business on the homepage.
2. The homepage calls the Fladov business search endpoint.
3. The user opens `/passport/{business_slug}`.
4. PoB fetches the full Fladov export for that business.
5. The PoB rank engine validates, normalizes, links, scores, and explains the business activity.
6. The report layer builds a passport payload for the web UI.
7. The passport page renders customer, investor, and lender views.

### 2. Direct payment flow

1. A user opens a passport.
2. The payment form is prefilled with the default payment amount or a query-driven amount.
3. PoB creates a payment intent through the Squad adapter.
4. Squad returns a checkout URL.
5. The user completes payment in Squad.
6. Squad webhook and return verification update the payment intent in PoB.
7. PoB sends a post-payment success notification to Fladov.

### 3. Invoice-backed payment flow

1. A user opens a passport with `?pay_invoice={invoice_id}`.
2. PoB fetches the business-scoped invoice from the Fladov repository.
3. The passport scrolls directly to the payment section.
4. A Fladov-owned invoice preview is rendered inside the payment panel.
5. The amount is set to the invoice total and locked.
6. Payment completes through the standard Squad flow.
7. The payment intent and the outbound Fladov webhook both carry invoice metadata.

## Demo System

The project ships with a complete in-repo demo system.

### Demo Fladov repository

In demo mode, Fladov data is not fetched from a live upstream API. Instead, the app reads from an in-code Fladov repository manifest in [app/fladov/demo_data.py](</C:/Users/HP/Documents/New project/app/fladov/demo_data.py>).

The demo repository includes:

- one top-level PoB schema version
- one Fladov post-payment webhook URL
- one global invoice preview HTML template
- 10 PoB-enabled demo businesses
- 10 demo invoices, one for each business
- complete PoB-schema-compatible record bundles for each business

### Demo businesses

The current demo businesses are:

- `sades-cakes`
- `glow-salon`
- `quick-mart`
- `steady-foods`
- `prime-bites`
- `verified-delight`
- `bloom-studio`
- `flatline-goods`
- `urban-tailor`
- `sunrise-cafe`

These are intentionally varied. The set includes mature businesses, newer businesses, suspicious businesses, payment-weak businesses, growth-volatile businesses, and lender-friendly businesses so the scoring engine has a believable range of scenarios to work with.

### Demo links

Assuming the app is running locally on `http://127.0.0.1:8000`, useful demo links include:

Business and passport examples:

- [Homepage](http://127.0.0.1:8000/)
- [Sade's Cakes passport](http://127.0.0.1:8000/passport/sades-cakes?theme=light)
- [Glow Salon passport](http://127.0.0.1:8000/passport/glow-salon?theme=light)
- [Sade's Cakes business profile](http://127.0.0.1:8000/business/sades-cakes?theme=light)

Invoice-backed passport examples:

- [Sade's Cakes invoice flow](http://127.0.0.1:8000/passport/sades-cakes?theme=light&pay_invoice=inv_sades_001)
- [Glow Salon invoice flow](http://127.0.0.1:8000/passport/glow-salon?theme=light&pay_invoice=inv_glow_001)
- [Steady Foods invoice flow](http://127.0.0.1:8000/passport/steady-foods?theme=light&pay_invoice=inv_steady_001)
- [Bloom Studio invoice flow](http://127.0.0.1:8000/passport/bloom-studio?theme=light&pay_invoice=inv_bloom_001)
- [Urban Tailor invoice flow](http://127.0.0.1:8000/passport/urban-tailor?theme=light&pay_invoice=inv_tailor_001)

API examples:

- [Search businesses API](http://127.0.0.1:8000/api/fladov/businesses?query=salon&limit=10)
- [Business export API](http://127.0.0.1:8000/api/fladov/businesses/sades-cakes)
- [Invoice API](http://127.0.0.1:8000/api/fladov/businesses/sades-cakes/invoices/inv_sades_001)

## How Scoring Works

PoB scoring is deterministic first and ML-assisted second.

The public rank-engine entrypoints are exposed from [app/core/rank_engine/__init__.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/__init__.py>):

- `rank_business(payload)`
- `score_fladov_business(payload)`
- `generate_fladov_pob_report(payload)`

All three currently resolve to the same core orchestration path in [app/core/rank_engine/engine.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/engine.py>).

### Rank engine pipeline

The engine performs these stages in order:

1. Schema validation
2. Payload normalization
3. Evidence graph construction
4. Shared metric computation
5. Rule-based anomaly detection
6. ML anomaly analysis
7. Final scoring, confidence, and risk composition

### PoB schema and business evidence

The Fladov export is converted into the PoB schema shape expected by the engine. The current payload includes:

- business metadata
- products
- orders
- purchases
- general financial operations
- cashbook entries
- transaction documents
- operation logs
- verified payments

The schema remains the contract between Fladov export logic and the engine, but in this repository it is described as the schema Fladov exports into PoB, not a generic multi-platform standard.

### Shared metrics

The engine computes a reusable metric layer before any final audience score is assembled. Examples include:

- evidence depth
- activity continuity
- record coherence
- payment integrity
- fulfillment reliability
- cashflow stability proxies
- customer diversity
- growth momentum proxies
- document discipline
- operational maturity
- audit integrity

### Rule-based anomaly detection

The rule-based risk layer identifies concrete explainable flags such as:

- low evidence depth
- low activity continuity
- burst concentration
- dormancy gaps
- orphan records
- payment-operation mismatches
- low verified payment coverage
- high failed payment ratio
- high canceled order ratio
- paid-but-unfulfilled patterns
- high customer concentration
- suspicious backfill patterns
- excessive deleted records

These remain the primary explicit explanation system for risk notes shown in the UI.

### ML-assisted risk and confidence analysis

This stage of the pipeline is the app's ML-assisted anomaly analysis layer.

PoB also includes a lightweight unsupervised ML layer in [app/core/rank_engine/ml/analyzer.py](</C:/Users/HP/Documents/New project/app/core/rank_engine/ml/analyzer.py>).

The ML layer:

- uses `IsolationForest` when `scikit-learn` is available
- falls back to a deterministic compatibility analyzer if `scikit-learn` is unavailable locally
- derives a compact feature vector from the shared metrics
- compares a business against a deterministic reference corpus built from realistic scenario seeds and perturbations
- contributes mainly to risk and confidence rather than replacing the core deterministic scoring system
- deterministic metrics and rules remain the backbone

Important positioning:

- this is not a trained predictive credit model
- this is not a custom learned weights system
- it is an anomaly-support layer designed to be reasonable, explainable, and hackathon-credible

### Final scores

The engine produces score outputs including:

- `proof_of_business_score`
- `vendor_trust_score`
- `payment_confidence_score`
- `fulfillment_reliability_score`
- `credit_readiness_score`
- `cashflow_stability_score`
- `repayment_capacity_signal`
- `growth_momentum_score`
- `customer_quality_signal`
- `operational_maturity_score`

The passport then organizes those into three audience views:

- `Customer`
- `Investor`
- `Lender`

Each tab contains:

- a main score
- a short summary
- a fuller explanation
- contributing sub-scores
- risk notes
- improvement notes

All scores are shown as percentages with one decimal place and are color-banded for readability.

## Payments

The payment subsystem lives under [app/payments](</C:/Users/HP/Documents/New project/app/payments>).

### Payment behavior

- PoB owns the payment UX
- Squad is the active payment rail
- Payment intents are stored locally in `runtime/payments.json`
- Successful payments can trigger an outbound success webhook
- Verified payment outcomes feed the evidence story

### Squad integration

The Squad adapter is implemented in [app/payments/providers/squad.py](</C:/Users/HP/Documents/New project/app/payments/providers/squad.py>).

It handles:

- payment initiation
- transaction verification
- webhook signature verification

The app uses:

- `POST /transaction/initiate`
- `GET /transaction/verify/{transaction_ref}`

against the configured Squad base URL.

### Post-payment Fladov notification

After a successful payment, PoB can notify Fladov through the configured post-payment success webhook. The notification includes:

- payment intent data
- verification payload
- Fladov business metadata
- invoice metadata when the payment came from `pay_invoice`

## Routes

### Web routes

- `GET /`
- `GET /passport/{business_slug}`
- `GET /pob/{business_slug}`
- `GET /business/{business_slug}`
- `POST /passport`
- `POST /pob`
- `POST /business`
- `GET /payments/return/{intent_id}`

### API routes

- `GET /api/fladov/businesses`
- `GET /api/fladov/businesses/{slug}`
- `GET /api/fladov/businesses/{slug}/invoices/{invoice_id}`
- `POST /api/fladov/webhooks/post-payment`
- `POST /api/passport/generate`
- `POST /api/payments/intents`
- `GET /api/payments/intents/{intent_id}`
- `GET /api/payments/return/{intent_id}`
- `POST /api/payments/webhooks/squad`

### Important query parameters

Passport pages support:

- `theme=light|dark`
- `amount={number}`
- `pay_amount={number}`
- `pay_invoice={invoice_id}`

Behavior:

- `amount` or `pay_amount` prefills the payment amount and scrolls to the payment section
- `pay_invoice` loads a Fladov invoice preview, sets the amount to the invoice total, locks the amount field, and scrolls to payment

## Directory Overview

High-level application areas:

- `app/main.py`
  - FastAPI app entrypoint and page routes
- `app/settings.py`
  - environment loading and runtime settings
- `app/fladov/`
  - Fladov repository contracts, demo data, adapters, API routes, and service helpers
- `app/core/rank_engine/`
  - scoring engine
- `app/reports/`
  - passport composition and presentation logic
- `app/payments/`
  - payment intents, providers, storage, notification dispatch, and payment API routes
- `app/templates/`
  - Jinja templates for the homepage, business page, and passport page
- `app/static/`
  - JavaScript, CSS, and logo asset
- `tests/unit/`
  - repository, web app, payments, and rank-engine tests

For a full codebase walkthrough, see [TECHNICAL_ARCHITECTURE.md](</C:/Users/HP/Documents/New project/TECHNICAL_ARCHITECTURE.md>).

## Setup

### Requirements

- Python `3.12+`
- PowerShell or another shell capable of setting environment variables
- internet access if you want to test real Squad sandbox calls

### Install

```powershell
python -m pip install -e ".[dev]"
```

### Environment

Create a local `.env` file in the project root.

Typical demo-mode configuration:

```env
POB_APP_NAME=Proof of Business by Fladov
POB_API_ROUTE_PREFIX=/api
POB_PUBLIC_BASE_URL=http://127.0.0.1:8000

POB_FLADOV_DEMO_MODE=true
POB_FLADOV_API_BASE_URL=https://api.fladov.example
POB_FLADOV_REQUEST_TIMEOUT_SECONDS=10
POB_FLADOV_SCHEMA_VERSION=1.0.0

POB_PAYMENT_PROVIDER=squad
POB_PAYMENT_CURRENCY=NGN
POB_PAYMENT_DEFAULT_AMOUNT=5000
POB_PAYMENT_STORE_PATH=runtime/payments.json

POB_SQUAD_BASE_URL=https://sandbox-api-d.squadco.com
POB_SQUAD_PUBLIC_KEY=your_sandbox_public_key
POB_SQUAD_SECRET_KEY=your_sandbox_secret_key
POB_SQUAD_WEBHOOK_SECRET=your_sandbox_secret_key

POB_PAYMENT_SUCCESS_WEBHOOK_URL=
POB_PAYMENT_SUCCESS_WEBHOOK_SECRET=
POB_PAYMENT_SUCCESS_WEBHOOK_TIMEOUT_SECONDS=10
```

The app also supports plain `SQUAD_*` and plain payment-success webhook env names as fallbacks, because [app/settings.py](</C:/Users/HP/Documents/New project/app/settings.py>) resolves both PoB-prefixed and plain names for key payment settings.

### Run locally

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open:

- [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### Local webhook testing with ngrok

If you want Squad sandbox callbacks to reach your local machine:

1. Run the app locally on port `8000`
2. Expose it with ngrok
3. Set `POB_PUBLIC_BASE_URL` to the ngrok URL
4. Configure Squad test redirect and webhook URLs to use the ngrok domain

## Demo Mode and Live Mode

PoB supports two Fladov data modes:

- `POB_FLADOV_DEMO_MODE=true`
  - uses the in-repo demo Fladov repository
- `POB_FLADOV_DEMO_MODE=false`
  - uses the live Fladov repository adapter and `POB_FLADOV_API_BASE_URL`

The same repository contract is used in both modes. That is the main seam intended for a future real Fladov integration.

For payments:

- the app already supports real Squad sandbox/live initiation
- the Fladov business-data side remains demo-backed until a live Fladov API is connected

## What Is Still Mocked

The project is feature-complete as a demo, but some infrastructure is still mocked:

- the Fladov upstream API itself
- the Fladov business search and full export backend
- the Fladov invoice source backend
- the live Fladov post-payment receiver
- long-term persistent storage beyond the local JSON payment store

## Testing

Run the full suite with:

```powershell
python -m pytest -q
```

The test suite covers:

- rank-engine scoring behavior
- ML anomaly signal behavior
- Fladov repository manifest behavior
- homepage search behavior
- passport rendering
- business profile rendering
- invoice-backed passport rendering
- payment intent creation
- Squad webhook verification
- outbound Fladov post-payment notification payloads

## Roadmap

The most natural next steps are:

1. Connect the live Fladov API and replace the demo repository in production mode
2. Back payment intents with a database instead of a local JSON store
3. Let Fladov mark invoices as settled after post-payment confirmation
4. Add richer analytics and trend views to the passport
5. Harden deployment and auth boundaries for production-grade Fladov access

## Security and deployment notes

- The repository is open source, but that does not imply public access to live Fladov business records.
- The intended production model is an authenticated server-to-server Fladov integration.
- Demo mode exists so the application can run safely without private Fladov data access.
- Payment-provider secrets belong in environment variables, not in committed files.
