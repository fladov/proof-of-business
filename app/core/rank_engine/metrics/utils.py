"""Reusable metric helpers."""

from __future__ import annotations

from datetime import datetime


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def safe_ratio(numerator: float, denominator: float, default: float = 0.0) -> float:
    return default if denominator == 0 else numerator / denominator


def diminishing(value: float, scale: float) -> float:
    return 0.0 if value <= 0 else value / (value + scale)


def linear_score(value: float, start: float, end: float) -> float:
    if end == start:
        return 1.0 if value >= end else 0.0
    if value <= start:
        return 0.0
    if value >= end:
        return 1.0
    return (value - start) / (end - start)


def months_between(start: datetime, end: datetime) -> float:
    delta_days = max(0.0, (end - start).days)
    return max(delta_days / 30.0, 0.0)
