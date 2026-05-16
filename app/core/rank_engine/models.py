"""Public result models for the rank engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class RiskFlag:
    code: str
    severity: str
    message: str


@dataclass(slots=True)
class AnomalyResult:
    anomaly_score: float
    flags: list[RiskFlag] = field(default_factory=list)
    details: dict[str, float | int | str | list[str] | dict] = field(default_factory=dict)


@dataclass(slots=True)
class MlFeatureDelta:
    feature_name: str
    observed_value: float
    reference_median: float
    normalized_distance: float


@dataclass(slots=True)
class MlAnomalyResult:
    anomaly_score: float
    anomaly_percentile: float
    is_anomalous: bool
    severity: str
    feature_vector: dict[str, float] = field(default_factory=dict)
    reference_version: str = ""
    top_feature_deltas: list[MlFeatureDelta] = field(default_factory=list)
    reference_profile_summary: dict[str, float | int | str | list[str]] = field(default_factory=dict)


@dataclass(slots=True)
class ConfidenceSummary:
    confidence_score: float
    confidence_level: str


@dataclass(slots=True)
class RiskSummary:
    risk_score: float
    risk_flags: list[RiskFlag]
    ml_signal: MlAnomalyResult | None = None


@dataclass(slots=True)
class RankResult:
    scores: dict[str, float]
    confidence: ConfidenceSummary
    risk: RiskSummary
    metrics: dict[str, float | int | str | dict | list]

    def to_dict(self) -> dict:
        return asdict(self)
