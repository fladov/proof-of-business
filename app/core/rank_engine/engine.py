"""Public orchestration entrypoint for the PoB rank engine."""

from __future__ import annotations

from .evidence import build_evidence_graph
from .ml import MlAnomalyAnalyzer
from .metrics import compute_shared_metrics
from .normalization import normalize_payload
from .risk import RuleBasedAnomalyDetector
from .scoring import calculate_result
from .schema import validate_payload


def rank_business(payload):
    """Validate, normalize, score, and summarize a single PoB business payload."""

    typed_payload = validate_payload(payload)
    normalized = normalize_payload(typed_payload)
    evidence_graph = build_evidence_graph(normalized)
    metrics = compute_shared_metrics(normalized, evidence_graph)
    anomaly_result = RuleBasedAnomalyDetector().detect(typed_payload, metrics, evidence_graph, normalized)
    ml_result = MlAnomalyAnalyzer().analyze(metrics)
    return calculate_result(metrics, anomaly_result, ml_result).to_dict()


def score_fladov_business(payload):
    """Fladov-native alias for scoring a business payload."""

    return rank_business(payload)


def generate_fladov_pob_report(payload):
    """Fladov-native alias for generating a PoB passport report."""

    return rank_business(payload)
