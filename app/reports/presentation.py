"""Presentation helpers for score colors, percentages, and confidence badges.

The UI should not hardcode score thresholds. These values stay centralized so
the grading system can be tuned without touching templates or report assembly.
Percentage presentation is intentionally one-decimal-place so the UI tracks the
underlying score closely without rounding away signal.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.rank_engine.metrics.utils import clamp


SCORE_PERCENT_SCALE = 100.0
SCORE_PERCENT_DECIMALS = 1

SCORE_BANDS = (
    {"min": 0.0, "max": 0.399999999, "key": "low", "label": "Low", "class_name": "score-band-low"},
    {"min": 0.4, "max": 0.699999999, "key": "mid", "label": "Moderate", "class_name": "score-band-mid"},
    {"min": 0.7, "max": 1.0, "key": "high", "label": "Strong", "class_name": "score-band-high"},
)

CONFIDENCE_BADGE_CLASSES = {
    "low": "badge-low",
    "medium": "badge-medium",
    "high": "badge-high",
}


@dataclass(slots=True)
class PresentedScore:
    value: float
    percent: float
    band_key: str
    band_label: str
    class_name: str


@dataclass(slots=True)
class ConfidenceBadge:
    value: float
    percent: float
    level: str
    class_name: str
    label: str


def score_to_presented(value: float) -> PresentedScore:
    normalized = clamp(value)
    band = _band_for(normalized)
    return PresentedScore(
        value=normalized,
        percent=round(normalized * SCORE_PERCENT_SCALE, SCORE_PERCENT_DECIMALS),
        band_key=band["key"],
        band_label=band["label"],
        class_name=band["class_name"],
    )


def confidence_to_badge(value: float, level: str) -> ConfidenceBadge:
    normalized = clamp(value)
    safe_level = level.strip().lower()
    return ConfidenceBadge(
        value=normalized,
        percent=round(normalized * SCORE_PERCENT_SCALE, SCORE_PERCENT_DECIMALS),
        level=safe_level,
        class_name=CONFIDENCE_BADGE_CLASSES.get(safe_level, "badge-medium"),
        label=safe_level.title(),
    )


def _band_for(value: float) -> dict[str, str | float]:
    for band in SCORE_BANDS:
        if band["min"] <= value <= band["max"]:
            return band
    return SCORE_BANDS[-1]
