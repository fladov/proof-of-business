"""Calculate final score outputs from shared metrics and anomalies."""

from __future__ import annotations

from ..config import (
    CONFIDENCE_LEVELS,
    FLAG_SCORE_RELEVANCE,
    FLAG_SEVERITY_WEIGHTS,
    ML_CONFIDENCE_PENALTY_MAX,
    ML_CONFIDENCE_PENALTY_THRESHOLD,
    ML_RISK_BLEND_WEIGHT,
    ML_SCORE_PENALTIES,
    ML_SCORE_PENALTY_THRESHOLD,
    RISK_PENALTIES,
    SCORE_WEIGHTS,
)
from ..models import AnomalyResult, ConfidenceSummary, MlAnomalyResult, RankResult, RiskSummary
from ..metrics.utils import clamp


def calculate_result(metrics: dict, anomaly_result: AnomalyResult, ml_result: MlAnomalyResult) -> RankResult:
    metrics_with_ml = {
        **metrics,
        "ml_features": ml_result.feature_vector,
        "ml_analysis": {
            "anomaly_score": ml_result.anomaly_score,
            "anomaly_percentile": ml_result.anomaly_percentile,
            "is_anomalous": ml_result.is_anomalous,
            "severity": ml_result.severity,
            "reference_version": ml_result.reference_version,
            "top_feature_deltas": [
                {
                    "feature_name": delta.feature_name,
                    "observed_value": delta.observed_value,
                    "reference_median": delta.reference_median,
                    "normalized_distance": delta.normalized_distance,
                }
                for delta in ml_result.top_feature_deltas
            ],
        },
        "reference_profile_summary": ml_result.reference_profile_summary,
    }
    scores: dict[str, float] = {}

    payment_confidence_score = _weighted_score("payment_confidence_score", metrics_with_ml, anomaly_result, ml_result)
    scores["payment_confidence_score"] = payment_confidence_score

    fulfillment_score = _compose_fulfillment_score(metrics_with_ml, anomaly_result, ml_result)
    scores["fulfillment_reliability_score"] = fulfillment_score

    operational_maturity_score = _weighted_score("operational_maturity_score", metrics_with_ml, anomaly_result, ml_result)
    scores["operational_maturity_score"] = operational_maturity_score

    scores["proof_of_business_score"] = _weighted_score(
        "proof_of_business_score",
        {**metrics_with_ml, "operational_maturity_score": operational_maturity_score},
        anomaly_result,
        ml_result,
    )
    scores["vendor_trust_score"] = _weighted_score(
        "vendor_trust_score",
        {
            **metrics_with_ml,
            "fulfillment_reliability_score": fulfillment_score,
            "payment_confidence_score": payment_confidence_score,
        },
        anomaly_result,
        ml_result,
    )
    cashflow_stability_score = _weighted_score("cashflow_stability_score", metrics_with_ml, anomaly_result, ml_result)
    scores["cashflow_stability_score"] = cashflow_stability_score
    scores["credit_readiness_score"] = _weighted_score(
        "credit_readiness_score",
        {
            **metrics_with_ml,
            "cashflow_stability_score": cashflow_stability_score,
            "payment_confidence_score": payment_confidence_score,
            "operational_maturity_score": operational_maturity_score,
        },
        anomaly_result,
        ml_result,
    )
    scores["repayment_capacity_signal"] = _weighted_score(
        "repayment_capacity_signal",
        {
            **metrics_with_ml,
            "cashflow_stability_score": cashflow_stability_score,
            "payment_confidence_score": payment_confidence_score,
            "fulfillment_reliability_score": fulfillment_score,
            "operational_maturity_score": operational_maturity_score,
        },
        anomaly_result,
        ml_result,
    )
    scores["growth_momentum_score"] = _weighted_score("growth_momentum_score", metrics_with_ml, anomaly_result, ml_result)
    scores["customer_quality_signal"] = _weighted_score("customer_quality_signal", metrics_with_ml, anomaly_result, ml_result)

    confidence_score = _weighted_score("confidence_score", metrics_with_ml, anomaly_result, ml_result)
    confidence_score = clamp(confidence_score - _ml_confidence_penalty(ml_result))
    confidence = ConfidenceSummary(
        confidence_score=confidence_score,
        confidence_level=_confidence_level(confidence_score),
    )
    risk = RiskSummary(
        risk_score=_blend_risk_score(anomaly_result.anomaly_score, ml_result.anomaly_score),
        risk_flags=anomaly_result.flags,
        ml_signal=ml_result,
    )

    return RankResult(scores=scores, confidence=confidence, risk=risk, metrics=metrics_with_ml)


def _compose_fulfillment_score(metrics: dict, anomaly_result: AnomalyResult, ml_result: MlAnomalyResult) -> float:
    derived_metrics = {
        **metrics,
        "low_cancellation_score": 1.0 - metrics["canceled_order_ratio"],
        "low_paid_unfulfilled_score": 1.0 - metrics["paid_unfulfilled_ratio"],
    }
    return _weighted_score("fulfillment_reliability_score", derived_metrics, anomaly_result, ml_result)


def _weighted_score(score_name: str, metrics: dict, anomaly_result: AnomalyResult, ml_result: MlAnomalyResult) -> float:
    total = 0.0
    for metric_name, weight in SCORE_WEIGHTS[score_name].items():
        total += float(metrics.get(metric_name, 0.0)) * weight
    return clamp(total - _risk_penalty_for_score(score_name, anomaly_result) - _ml_penalty_for_score(score_name, ml_result))


def _risk_penalty_for_score(score_name: str, anomaly_result: AnomalyResult) -> float:
    matched_weight = 0.0
    for flag in anomaly_result.flags:
        relevance = FLAG_SCORE_RELEVANCE.get(flag.code, {})
        if score_name == "confidence_score":
            include = bool(relevance.get("confidence"))
        else:
            include = score_name in relevance.get("scores", [])
        if include:
            matched_weight += FLAG_SEVERITY_WEIGHTS[flag.severity]
    if matched_weight <= 0:
        return 0.0
    return clamp(matched_weight * RISK_PENALTIES[score_name], maximum=0.6)


def _ml_penalty_for_score(score_name: str, ml_result: MlAnomalyResult) -> float:
    if score_name == "confidence_score" or ml_result.anomaly_score <= ML_SCORE_PENALTY_THRESHOLD:
        return 0.0
    penalty_strength = clamp(
        (ml_result.anomaly_score - ML_SCORE_PENALTY_THRESHOLD) / max(1e-9, (1.0 - ML_SCORE_PENALTY_THRESHOLD))
    )
    return clamp(penalty_strength * ML_SCORE_PENALTIES.get(score_name, 0.0), maximum=0.12)


def _ml_confidence_penalty(ml_result: MlAnomalyResult) -> float:
    if ml_result.anomaly_score <= ML_CONFIDENCE_PENALTY_THRESHOLD:
        return 0.0
    penalty_strength = clamp(
        (ml_result.anomaly_score - ML_CONFIDENCE_PENALTY_THRESHOLD) / max(1e-9, (1.0 - ML_CONFIDENCE_PENALTY_THRESHOLD))
    )
    return clamp(penalty_strength * ML_CONFIDENCE_PENALTY_MAX, maximum=ML_CONFIDENCE_PENALTY_MAX)


def _blend_risk_score(rule_risk_score: float, ml_risk_score: float) -> float:
    return clamp((rule_risk_score * (1.0 - ML_RISK_BLEND_WEIGHT)) + (ml_risk_score * ML_RISK_BLEND_WEIGHT))


def _confidence_level(score: float) -> str:
    for threshold, label in CONFIDENCE_LEVELS:
        if score <= threshold:
            return label
    return "high"
