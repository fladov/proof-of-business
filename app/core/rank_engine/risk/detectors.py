"""Pluggable anomaly detection for the PoB engine."""

from __future__ import annotations

from ..config import FLAG_SEVERITY_WEIGHTS
from ..evidence.graph import EvidenceGraph
from ..models import AnomalyResult, RiskFlag
from ..normalization.pipeline import NormalizedPayload
from ..schema.models import PoBPayload
from ..metrics.utils import clamp


class AnomalyDetector:
    """Base anomaly detector interface."""

    def detect(self, payload: PoBPayload, metrics: dict, evidence_graph: EvidenceGraph, normalized: NormalizedPayload) -> AnomalyResult:
        raise NotImplementedError


class RuleBasedAnomalyDetector(AnomalyDetector):
    """Deterministic anomaly detector for v1 scoring."""

    def detect(self, payload: PoBPayload, metrics: dict, evidence_graph: EvidenceGraph, normalized: NormalizedPayload) -> AnomalyResult:
        flags: list[RiskFlag] = []

        self._maybe_add(flags, metrics["evidence_depth_score"] < 0.25, "LOW_EVIDENCE_DEPTH", "high", "Business has very little usable evidence across core records.")
        self._maybe_add(flags, metrics["activity_continuity_score"] < 0.30, "LOW_ACTIVITY_CONTINUITY", "high", "Business activity is sparse or inconsistent across time.")
        self._maybe_add(flags, metrics["burst_concentration_score"] > 0.55, "HIGH_ACTIVITY_BURST_CONCENTRATION", "medium", "Activity is overly concentrated in a narrow time window.")
        self._maybe_add(flags, metrics["longest_gap_days"] > 120, "LONG_DORMANCY_GAP", "medium", "Business shows a long inactivity gap in the record trail.")
        self._maybe_add(flags, metrics["orphan_record_ratio"] > 0.20, "HIGH_ORPHAN_RECORD_RATIO", "high", "Many records do not link to valid supporting business operations.")
        self._maybe_add(flags, metrics["payment_operation_match_score"] < 0.60, "PAYMENT_OPERATION_MISMATCH", "high", "Cashbook and verified payment evidence do not align cleanly.")
        self._maybe_add(flags, metrics["verified_payment_coverage_ratio"] < 0.30 and metrics["counts"]["cashbook_entries"] >= 4, "LOW_VERIFIED_PAYMENT_COVERAGE", "medium", "Too few cashbook entries are backed by verified payments.")
        self._maybe_add(flags, metrics["failed_payment_ratio"] > 0.25, "HIGH_FAILED_PAYMENT_RATIO", "medium", "A large share of verified payments failed, expired, or reversed.")
        self._maybe_add(flags, metrics["canceled_order_ratio"] > 0.25, "HIGH_CANCELED_ORDER_RATIO", "medium", "A large share of customer orders are canceled or voided.")
        self._maybe_add(flags, metrics["paid_unfulfilled_ratio"] > 0.15, "HIGH_PAID_UNFULFILLED_RATIO", "high", "Paid orders remain unresolved or unfulfilled too often.")
        self._maybe_add(flags, metrics["customer_concentration_ratio"] > 0.55 and metrics["counts"]["orders"] >= 5, "HIGH_CUSTOMER_CONCENTRATION", "medium", "Too much customer activity depends on one customer profile.")
        self._maybe_add(flags, metrics["document_discipline_score"] < 0.35 and metrics["counts"]["transaction_documents"] >= 3, "DOCUMENTS_MOSTLY_PREVIEW_OR_UNLINKED", "medium", "Documents are mostly previews, unlinked, or weakly supported.")
        self._maybe_add(flags, metrics["burst_concentration_score"] > 0.65 and metrics["growth_naturalness_score"] < 0.30, "SUSPICIOUS_BACKFILL_PATTERN", "high", "The evidence pattern looks heavily backfilled rather than naturally accumulated.")
        self._maybe_add(flags, metrics["operation_log_success_ratio"] < 0.70 and metrics["counts"]["operation_logs"] >= 3, "HIGH_OPERATION_FAILURE_RATIO", "medium", "Operation logs show too many failed actions.")
        self._maybe_add(flags, metrics["deleted_record_ratio"] > 0.20, "EXCESSIVE_DELETED_RECORDS", "medium", "Deleted records represent an unusually large share of the evidence set.")

        anomaly_score = clamp(sum(FLAG_SEVERITY_WEIGHTS[flag.severity] for flag in flags))
        return AnomalyResult(
            anomaly_score=anomaly_score,
            flags=flags,
            details={
                "orphan_cashbook_ids": evidence_graph.orphan_cashbook_ids,
                "orphan_document_ids": evidence_graph.orphan_document_ids,
                "orphan_log_ids": evidence_graph.orphan_log_ids,
            },
        )

    @staticmethod
    def _maybe_add(flags: list[RiskFlag], condition: bool, code: str, severity: str, message: str) -> None:
        if condition:
            flags.append(RiskFlag(code=code, severity=severity, message=message))
