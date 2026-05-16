"""Unsupervised ML support for risk and confidence analysis."""

from __future__ import annotations

from functools import lru_cache
from statistics import median

try:
    from sklearn.ensemble import IsolationForest as SklearnIsolationForest
    ML_BACKEND = "sklearn"
except ModuleNotFoundError:  # pragma: no cover - exercised in constrained local environments
    SklearnIsolationForest = None
    ML_BACKEND = "fallback"

from ..config import (
    ML_ANOMALY_PERCENTILE_THRESHOLD,
    ML_ANOMALY_SEVERITY_THRESHOLDS,
    ML_FEATURE_NAMES,
    ML_ISOLATION_FOREST_CONTAMINATION,
    ML_ISOLATION_FOREST_ESTIMATORS,
    ML_RANDOM_STATE,
    ML_REFERENCE_CORPUS_SIZE,
    ML_REFERENCE_PERTURBATIONS,
    ML_REFERENCE_PROFILE_SEEDS,
    ML_REFERENCE_VERSION,
)
from ..metrics.utils import clamp
from ..models import MlAnomalyResult, MlFeatureDelta


def extract_ml_features(metrics: dict) -> dict[str, float]:
    return {
        "evidence_depth_score": float(metrics.get("evidence_depth_score", 0.0)),
        "activity_continuity_score": float(metrics.get("activity_continuity_score", 0.0)),
        "record_coherence_score": float(metrics.get("record_coherence_score", 0.0)),
        "payment_integrity_score": float(metrics.get("payment_integrity_score", 0.0)),
        "fulfilled_or_completed_order_ratio": float(metrics.get("fulfilled_or_completed_order_ratio", 0.0)),
        "cashflow_stability_proxy": float(_cashflow_stability_proxy(metrics)),
        "customer_diversity_score": float(metrics.get("customer_diversity_score", 0.0)),
        "growth_momentum_proxy": float(_growth_momentum_proxy(metrics)),
        "document_discipline_score": float(metrics.get("document_discipline_score", 0.0)),
        "operational_maturity_proxy": float(_operational_maturity_proxy(metrics)),
        "audit_integrity_score": float(metrics.get("audit_integrity_score", 0.0)),
        "deleted_record_ratio": float(metrics.get("deleted_record_ratio", 0.0)),
    }


def build_reference_feature_corpus() -> list[dict[str, float]]:
    corpus: list[dict[str, float]] = []
    for seed in ML_REFERENCE_PROFILE_SEEDS:
        base_profile = dict(seed["profile"])
        for perturbation in ML_REFERENCE_PERTURBATIONS:
            profile = {
                name: clamp(base_profile[name] + perturbation.get(name, 0.0))
                for name in ML_FEATURE_NAMES
            }
            corpus.append(profile)
    return corpus[:ML_REFERENCE_CORPUS_SIZE]


class MlAnomalyAnalyzer:
    """Isolation Forest-based anomaly analyzer over derived business metrics."""

    def analyze(self, metrics: dict) -> MlAnomalyResult:
        feature_vector = extract_ml_features(metrics)
        feature_rows = build_reference_feature_corpus()
        feature_matrix = [_to_vector(row) for row in feature_rows]
        model = _build_model()
        model.fit(feature_matrix)

        raw_reference_scores = [-float(score) for score in model.decision_function(feature_matrix)]
        sample_vector = _to_vector(feature_vector)
        raw_sample_score = -float(model.decision_function([sample_vector])[0])
        anomaly_percentile = _percentile_rank(raw_reference_scores, raw_sample_score)
        anomaly_score = _normalize_percentile_to_score(anomaly_percentile)
        severity = _severity_for(anomaly_score)
        top_feature_deltas = _top_feature_deltas(feature_rows, feature_vector)

        return MlAnomalyResult(
            anomaly_score=anomaly_score,
            anomaly_percentile=anomaly_percentile,
            is_anomalous=anomaly_percentile >= ML_ANOMALY_PERCENTILE_THRESHOLD,
            severity=severity,
            feature_vector=feature_vector,
            reference_version=ML_REFERENCE_VERSION,
            top_feature_deltas=top_feature_deltas,
            reference_profile_summary={
                "reference_version": ML_REFERENCE_VERSION,
                "reference_corpus_size": len(feature_rows),
                "feature_names": list(ML_FEATURE_NAMES),
                "contamination": ML_ISOLATION_FOREST_CONTAMINATION,
                "estimators": ML_ISOLATION_FOREST_ESTIMATORS,
                "backend": ML_BACKEND,
            },
        )


def _cashflow_stability_proxy(metrics: dict) -> float:
    parts = (
        float(metrics.get("income_regularity_score", 0.0)),
        float(metrics.get("expense_regularity_score", 0.0)),
        float(metrics.get("low_income_volatility_score", 0.0)),
        float(metrics.get("low_gap_score", 0.0)),
    )
    return clamp(sum(parts) / len(parts))


def _growth_momentum_proxy(metrics: dict) -> float:
    parts = (
        float(metrics.get("order_activity_trend_score", 0.0)),
        float(metrics.get("cashbook_income_trend_score", 0.0)),
        float(metrics.get("verified_payment_trend_score", 0.0)),
        float(metrics.get("customer_growth_trend_score", 0.0)),
        float(metrics.get("growth_naturalness_score", 0.0)),
    )
    return clamp(sum(parts) / len(parts))


def _operational_maturity_proxy(metrics: dict) -> float:
    parts = (
        float(metrics.get("product_setup_quality", 0.0)),
        float(metrics.get("record_linkage_score", 0.0)),
        float(metrics.get("cashbook_discipline_score", 0.0)),
        float(metrics.get("fladov_activity_consistency", 0.0)),
        float(metrics.get("purchase_or_expense_reality", 0.0)),
    )
    return clamp(sum(parts) / len(parts))


@lru_cache(maxsize=1)
def _build_model():
    if SklearnIsolationForest is not None:
        return SklearnIsolationForest(
            n_estimators=ML_ISOLATION_FOREST_ESTIMATORS,
            contamination=ML_ISOLATION_FOREST_CONTAMINATION,
            random_state=ML_RANDOM_STATE,
        )
    return _FallbackIsolationForest(
        contamination=ML_ISOLATION_FOREST_CONTAMINATION,
    )


def _to_vector(feature_map: dict[str, float]) -> list[float]:
    return [float(feature_map[name]) for name in ML_FEATURE_NAMES]


def _percentile_rank(reference_scores: list[float], sample_score: float) -> float:
    if not reference_scores:
        return 0.5
    less_or_equal = sum(1 for value in reference_scores if value <= sample_score)
    return clamp(less_or_equal / len(reference_scores))


def _normalize_percentile_to_score(percentile: float) -> float:
    if percentile <= 0.50:
        return 0.0
    return clamp((percentile - 0.50) / 0.50)


def _severity_for(anomaly_score: float) -> str:
    for threshold, label in ML_ANOMALY_SEVERITY_THRESHOLDS:
        if anomaly_score <= threshold:
            return label
    return "high"


def _top_feature_deltas(reference_rows: list[dict[str, float]], feature_vector: dict[str, float]) -> list[MlFeatureDelta]:
    deltas: list[MlFeatureDelta] = []
    for feature_name in ML_FEATURE_NAMES:
        reference_values = sorted(row[feature_name] for row in reference_rows)
        reference_median = median(reference_values)
        q1 = reference_values[len(reference_values) // 4]
        q3 = reference_values[(len(reference_values) * 3) // 4]
        scale = max(q3 - q1, 0.08)
        observed = feature_vector[feature_name]
        normalized_distance = abs(observed - reference_median) / scale
        deltas.append(
            MlFeatureDelta(
                feature_name=feature_name,
                observed_value=round(observed, 4),
                reference_median=round(reference_median, 4),
                normalized_distance=round(normalized_distance, 4),
            )
        )
    return sorted(deltas, key=lambda item: item.normalized_distance, reverse=True)[:3]


class _FallbackIsolationForest:
    """Small compatibility fallback when scikit-learn is unavailable locally.

    The project is designed to use sklearn's IsolationForest. This fallback keeps
    the engine runnable in constrained environments by scoring distance from the
    reference corpus median and spread through a compatible interface.
    """

    def __init__(self, contamination: float) -> None:
        self.contamination = contamination
        self.medians: list[float] = []
        self.scales: list[float] = []

    def fit(self, rows: list[list[float]]) -> "_FallbackIsolationForest":
        columns = list(zip(*rows))
        self.medians = [median(column) for column in columns]
        self.scales = []
        for column in columns:
            ordered = sorted(column)
            q1 = ordered[len(ordered) // 4]
            q3 = ordered[(len(ordered) * 3) // 4]
            self.scales.append(max(q3 - q1, 0.08))
        return self

    def decision_function(self, rows: list[list[float]]) -> list[float]:
        scores: list[float] = []
        for row in rows:
            normalized_distances = [
                abs(value - self.medians[index]) / self.scales[index]
                for index, value in enumerate(row)
            ]
            average_distance = sum(normalized_distances) / max(len(normalized_distances), 1)
            scores.append(0.5 - average_distance)
        return scores
