from __future__ import annotations

from pathlib import Path

import pytest

from app.core.rank_engine import rank_business
from app.core.rank_engine.exceptions import PayloadValidationError
from tests.fixtures.payloads import build_payload


def test_mature_legitimate_business_scores_above_suspicious_vendor():
    mature = rank_business(build_payload("mature_legitimate_bakery"))
    suspicious = rank_business(build_payload("suspicious_backfilled_vendor"))

    assert mature["scores"]["proof_of_business_score"] > suspicious["scores"]["proof_of_business_score"]
    assert mature["scores"]["vendor_trust_score"] > suspicious["scores"]["vendor_trust_score"]
    assert mature["confidence"]["confidence_score"] > suspicious["confidence"]["confidence_score"]


def test_new_business_has_lower_confidence_than_mature_business():
    mature = rank_business(build_payload("mature_legitimate_bakery"))
    new = rank_business(build_payload("new_legitimate_salon"))

    assert new["confidence"]["confidence_score"] < mature["confidence"]["confidence_score"]


def test_verified_payments_improve_payment_confidence():
    with_payments = rank_business(build_payload("mature_legitimate_bakery"))
    poor_payment = rank_business(build_payload("good_orders_poor_payment_evidence"))

    assert with_payments["scores"]["payment_confidence_score"] > poor_payment["scores"]["payment_confidence_score"]


def test_paid_but_unfulfilled_orders_reduce_fulfillment_reliability():
    healthy = rank_business(build_payload("mature_legitimate_bakery"))
    poor_fulfillment = rank_business(build_payload("verified_payments_poor_fulfillment"))

    assert poor_fulfillment["scores"]["fulfillment_reliability_score"] < healthy["scores"]["fulfillment_reliability_score"]
    assert poor_fulfillment["scores"]["vendor_trust_score"] < healthy["scores"]["vendor_trust_score"]


def test_orphan_documents_do_not_boost_maturity_much():
    suspicious = rank_business(build_payload("suspicious_backfilled_vendor"))

    assert suspicious["scores"]["operational_maturity_score"] < 0.45


def test_backfilled_records_trigger_risk_flags():
    suspicious = rank_business(build_payload("suspicious_backfilled_vendor"))
    flag_codes = {flag["code"] for flag in suspicious["risk"]["risk_flags"]}

    assert "SUSPICIOUS_BACKFILL_PATTERN" in flag_codes
    assert "HIGH_ORPHAN_RECORD_RATIO" in flag_codes


def test_growth_heavy_business_has_higher_growth_than_flat_business():
    volatile = rank_business(build_payload("growth_heavy_volatile_business"))
    flat = rank_business(build_payload("mature_flat_business"))

    assert volatile["scores"]["growth_momentum_score"] > flat["scores"]["growth_momentum_score"]
    assert volatile["scores"]["cashflow_stability_score"] < 1.0


def test_scores_are_clamped_between_zero_and_one():
    result = rank_business(build_payload("stable_lender_friendly_business"))

    for value in result["scores"].values():
        assert 0.0 <= value <= 1.0
    assert 0.0 <= result["confidence"]["confidence_score"] <= 1.0
    assert 0.0 <= result["risk"]["risk_score"] <= 1.0


def test_confidence_level_bands_are_valid():
    mature = rank_business(build_payload("mature_legitimate_bakery"))
    new = rank_business(build_payload("new_legitimate_salon"))

    assert mature["confidence"]["confidence_level"] in {"medium", "high"}
    assert new["confidence"]["confidence_level"] in {"low", "medium"}


def test_invalid_payload_raises_clear_validation_error():
    payload = build_payload("mature_legitimate_bakery")
    del payload["records"]["orders"][0]["status"]

    with pytest.raises(PayloadValidationError):
        rank_business(payload)


def test_ml_analysis_is_present_and_bounded():
    result = rank_business(build_payload("mature_legitimate_bakery"))
    ml_analysis = result["metrics"]["ml_analysis"]
    ml_signal = result["risk"]["ml_signal"]

    assert 0.0 <= ml_analysis["anomaly_score"] <= 1.0
    assert 0.0 <= ml_analysis["anomaly_percentile"] <= 1.0
    assert ml_signal["reference_version"]
    assert len(result["metrics"]["ml_features"]) >= 8


def test_suspicious_vendor_has_higher_ml_anomaly_than_mature_bakery():
    mature = rank_business(build_payload("mature_legitimate_bakery"))
    suspicious = rank_business(build_payload("suspicious_backfilled_vendor"))

    assert suspicious["risk"]["ml_signal"]["anomaly_score"] > mature["risk"]["ml_signal"]["anomaly_score"]
    assert suspicious["risk"]["risk_score"] > mature["risk"]["risk_score"]


def test_new_business_is_less_anomalous_than_suspicious_vendor():
    new = rank_business(build_payload("new_legitimate_salon"))
    suspicious = rank_business(build_payload("suspicious_backfilled_vendor"))

    assert new["risk"]["ml_signal"]["anomaly_score"] < suspicious["risk"]["ml_signal"]["anomaly_score"]


def test_mature_flat_business_is_not_strongly_anomalous():
    flat = rank_business(build_payload("mature_flat_business"))

    assert flat["risk"]["ml_signal"]["anomaly_score"] < 0.65
    assert flat["risk"]["ml_signal"]["severity"] in {"low", "medium"}


def test_growth_heavy_volatile_business_can_look_moderately_anomalous():
    volatile = rank_business(build_payload("growth_heavy_volatile_business"))

    assert volatile["risk"]["ml_signal"]["anomaly_score"] < 0.9
    assert volatile["risk"]["ml_signal"]["severity"] in {"medium", "high"}


def test_ml_signal_lowers_confidence_for_suspicious_businesses():
    mature = rank_business(build_payload("mature_legitimate_bakery"))
    suspicious = rank_business(build_payload("suspicious_backfilled_vendor"))

    assert suspicious["confidence"]["confidence_score"] < mature["confidence"]["confidence_score"]


def test_ml_penalty_is_light_relative_to_core_business_scores():
    mature = rank_business(build_payload("mature_legitimate_bakery"))
    volatile = rank_business(build_payload("growth_heavy_volatile_business"))

    assert mature["scores"]["proof_of_business_score"] > 0.45
    assert volatile["scores"]["growth_momentum_score"] > 0.45


def test_readme_documents_ml_assisted_pipeline():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "IsolationForest" in readme
    assert "ML-assisted anomaly analysis" in readme
    assert "deterministic metrics and rules remain the backbone" in readme
