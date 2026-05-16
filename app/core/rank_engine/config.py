"""Centralized thresholds, scales, and scoring weights."""

DIMINISHING_SCALES = {
    "products": 8.0,
    "orders": 20.0,
    "purchases": 12.0,
    "general_financial_operations": 10.0,
    "cashbook_entries": 24.0,
    "transaction_documents": 16.0,
    "operation_logs": 30.0,
    "verified_payments": 15.0,
}

EVIDENCE_DEPTH_WEIGHTS = {
    "products": 0.10,
    "orders": 0.18,
    "purchases": 0.12,
    "general_financial_operations": 0.10,
    "cashbook_entries": 0.16,
    "transaction_documents": 0.12,
    "operation_logs": 0.10,
    "verified_payments": 0.12,
}

SCORE_WEIGHTS = {
    "proof_of_business_score": {
        "evidence_depth_score": 0.20,
        "activity_continuity_score": 0.20,
        "record_coherence_score": 0.25,
        "payment_integrity_score": 0.15,
        "audit_integrity_score": 0.10,
        "operational_maturity_score": 0.10,
    },
    "vendor_trust_score": {
        "activity_continuity_score": 0.20,
        "product_or_service_presence": 0.10,
        "fulfillment_reliability_score": 0.20,
        "payment_confidence_score": 0.20,
        "record_coherence_score": 0.15,
        "reputation_signal": 0.05,
        "audit_integrity_score": 0.10,
    },
    "payment_confidence_score": {
        "completed_cashbook_ratio": 0.20,
        "verified_payment_coverage_ratio": 0.25,
        "successful_verified_payment_ratio": 0.20,
        "payment_operation_match_score": 0.20,
        "payment_timing_consistency": 0.10,
        "low_failed_payment_score": 0.05,
    },
    "fulfillment_reliability_score": {
        "fulfilled_or_completed_order_ratio": 0.35,
        "fulfilled_and_paid_ratio": 0.25,
        "low_cancellation_score": 0.15,
        "low_paid_unfulfilled_score": 0.15,
        "document_support_score": 0.10,
    },
    "credit_readiness_score": {
        "evidence_depth_score": 0.20,
        "cashflow_stability_score": 0.20,
        "payment_confidence_score": 0.20,
        "activity_continuity_score": 0.15,
        "operational_maturity_score": 0.15,
        "audit_integrity_score": 0.10,
    },
    "cashflow_stability_score": {
        "income_regularity_score": 0.25,
        "expense_regularity_score": 0.15,
        "low_income_volatility_score": 0.20,
        "activity_continuity_score": 0.15,
        "payment_integrity_score": 0.15,
        "low_gap_score": 0.10,
    },
    "repayment_capacity_signal": {
        "cashflow_stability_score": 0.30,
        "payment_confidence_score": 0.20,
        "activity_continuity_score": 0.15,
        "fulfillment_reliability_score": 0.15,
        "operational_maturity_score": 0.10,
        "low_expense_pressure_score": 0.10,
    },
    "growth_momentum_score": {
        "order_activity_trend_score": 0.25,
        "cashbook_income_trend_score": 0.20,
        "verified_payment_trend_score": 0.15,
        "customer_growth_trend_score": 0.15,
        "document_usage_trend_score": 0.10,
        "product_catalog_growth_score": 0.05,
        "growth_naturalness_score": 0.10,
    },
    "customer_quality_signal": {
        "customer_diversity_score": 0.25,
        "repeat_customer_signal": 0.20,
        "low_customer_concentration": 0.20,
        "customer_activity_continuity": 0.15,
        "reputation_signal": 0.10,
        "payment_supported_demand": 0.10,
    },
    "operational_maturity_score": {
        "product_setup_quality": 0.10,
        "document_discipline_score": 0.15,
        "record_linkage_score": 0.25,
        "cashbook_discipline_score": 0.15,
        "fladov_activity_consistency": 0.15,
        "purchase_or_expense_reality": 0.10,
        "low_orphan_record_score": 0.10,
    },
    "confidence_score": {
        "history_length_score": 0.25,
        "evidence_depth_score": 0.25,
        "evidence_category_coverage": 0.15,
        "activity_continuity_score": 0.15,
        "verified_payment_coverage": 0.10,
        "audit_integrity_score": 0.10,
    },
}

RISK_PENALTIES = {
    "proof_of_business_score": 0.35,
    "vendor_trust_score": 0.40,
    "payment_confidence_score": 0.55,
    "fulfillment_reliability_score": 0.55,
    "credit_readiness_score": 0.45,
    "cashflow_stability_score": 0.40,
    "repayment_capacity_signal": 0.40,
    "growth_momentum_score": 0.35,
    "customer_quality_signal": 0.40,
    "operational_maturity_score": 0.35,
    "confidence_score": 0.30,
}

FLAG_SEVERITY_WEIGHTS = {"low": 0.08, "medium": 0.16, "high": 0.26}

FLAG_SCORE_RELEVANCE = {
    "LOW_EVIDENCE_DEPTH": {
        "scores": ["proof_of_business_score", "credit_readiness_score", "operational_maturity_score"],
        "confidence": True,
    },
    "LOW_ACTIVITY_CONTINUITY": {
        "scores": ["proof_of_business_score", "vendor_trust_score", "credit_readiness_score", "cashflow_stability_score"],
        "confidence": True,
    },
    "HIGH_ACTIVITY_BURST_CONCENTRATION": {
        "scores": ["proof_of_business_score", "growth_momentum_score"],
        "confidence": True,
    },
    "LONG_DORMANCY_GAP": {
        "scores": ["proof_of_business_score", "vendor_trust_score", "cashflow_stability_score"],
        "confidence": True,
    },
    "HIGH_ORPHAN_RECORD_RATIO": {
        "scores": ["proof_of_business_score", "operational_maturity_score", "vendor_trust_score"],
        "confidence": True,
    },
    "PAYMENT_OPERATION_MISMATCH": {
        "scores": ["payment_confidence_score", "proof_of_business_score", "credit_readiness_score"],
        "confidence": False,
    },
    "LOW_VERIFIED_PAYMENT_COVERAGE": {
        "scores": ["payment_confidence_score", "credit_readiness_score", "customer_quality_signal"],
        "confidence": True,
    },
    "HIGH_FAILED_PAYMENT_RATIO": {
        "scores": ["payment_confidence_score", "vendor_trust_score"],
        "confidence": False,
    },
    "HIGH_CANCELED_ORDER_RATIO": {
        "scores": ["fulfillment_reliability_score", "vendor_trust_score"],
        "confidence": False,
    },
    "HIGH_PAID_UNFULFILLED_RATIO": {
        "scores": ["fulfillment_reliability_score", "vendor_trust_score", "repayment_capacity_signal"],
        "confidence": False,
    },
    "HIGH_CUSTOMER_CONCENTRATION": {
        "scores": ["customer_quality_signal", "growth_momentum_score"],
        "confidence": False,
    },
    "DOCUMENTS_MOSTLY_PREVIEW_OR_UNLINKED": {
        "scores": ["operational_maturity_score", "proof_of_business_score"],
        "confidence": False,
    },
    "SUSPICIOUS_BACKFILL_PATTERN": {
        "scores": ["proof_of_business_score", "growth_momentum_score", "vendor_trust_score"],
        "confidence": True,
    },
    "HIGH_OPERATION_FAILURE_RATIO": {
        "scores": ["proof_of_business_score", "operational_maturity_score"],
        "confidence": False,
    },
    "EXCESSIVE_DELETED_RECORDS": {
        "scores": ["proof_of_business_score", "operational_maturity_score"],
        "confidence": True,
    },
}

CONFIDENCE_LEVELS = (
    (0.39, "low"),
    (0.69, "medium"),
    (1.00, "high"),
)

STATUS_GROUPS = {
    "paid": {"paid", "completed", "settled", "success"},
    "fulfilled": {"fulfilled", "completed", "delivered", "closed"},
    "canceled": {"cancelled", "canceled", "voided"},
    "successful_payment": {"success", "successful", "paid", "completed", "verified"},
    "failed_payment": {"failed", "abandoned", "refunded", "expired", "reversed"},
}

ML_FEATURE_NAMES = (
    "evidence_depth_score",
    "activity_continuity_score",
    "record_coherence_score",
    "payment_integrity_score",
    "fulfilled_or_completed_order_ratio",
    "cashflow_stability_proxy",
    "customer_diversity_score",
    "growth_momentum_proxy",
    "document_discipline_score",
    "operational_maturity_proxy",
    "audit_integrity_score",
    "deleted_record_ratio",
)

ML_REFERENCE_VERSION = "2026.05.14.v1"
ML_REFERENCE_CORPUS_SIZE = 48
ML_RANDOM_STATE = 17
ML_ISOLATION_FOREST_CONTAMINATION = 0.16
ML_ISOLATION_FOREST_ESTIMATORS = 200

ML_REFERENCE_PROFILE_SEEDS = (
    {
        "name": "mature_legitimate_bakery",
        "profile": {
            "evidence_depth_score": 0.82,
            "activity_continuity_score": 0.78,
            "record_coherence_score": 0.86,
            "payment_integrity_score": 0.84,
            "fulfilled_or_completed_order_ratio": 0.88,
            "cashflow_stability_proxy": 0.76,
            "customer_diversity_score": 0.74,
            "growth_momentum_proxy": 0.63,
            "document_discipline_score": 0.82,
            "operational_maturity_proxy": 0.83,
            "audit_integrity_score": 0.80,
            "deleted_record_ratio": 0.03,
        },
    },
    {
        "name": "new_legitimate_salon",
        "profile": {
            "evidence_depth_score": 0.36,
            "activity_continuity_score": 0.47,
            "record_coherence_score": 0.70,
            "payment_integrity_score": 0.58,
            "fulfilled_or_completed_order_ratio": 0.64,
            "cashflow_stability_proxy": 0.42,
            "customer_diversity_score": 0.45,
            "growth_momentum_proxy": 0.56,
            "document_discipline_score": 0.50,
            "operational_maturity_proxy": 0.48,
            "audit_integrity_score": 0.57,
            "deleted_record_ratio": 0.04,
        },
    },
    {
        "name": "suspicious_backfilled_vendor",
        "profile": {
            "evidence_depth_score": 0.18,
            "activity_continuity_score": 0.16,
            "record_coherence_score": 0.24,
            "payment_integrity_score": 0.18,
            "fulfilled_or_completed_order_ratio": 0.12,
            "cashflow_stability_proxy": 0.22,
            "customer_diversity_score": 0.08,
            "growth_momentum_proxy": 0.20,
            "document_discipline_score": 0.10,
            "operational_maturity_proxy": 0.18,
            "audit_integrity_score": 0.14,
            "deleted_record_ratio": 0.22,
        },
    },
    {
        "name": "good_orders_poor_payment_evidence",
        "profile": {
            "evidence_depth_score": 0.72,
            "activity_continuity_score": 0.76,
            "record_coherence_score": 0.67,
            "payment_integrity_score": 0.26,
            "fulfilled_or_completed_order_ratio": 0.84,
            "cashflow_stability_proxy": 0.68,
            "customer_diversity_score": 0.70,
            "growth_momentum_proxy": 0.61,
            "document_discipline_score": 0.73,
            "operational_maturity_proxy": 0.69,
            "audit_integrity_score": 0.74,
            "deleted_record_ratio": 0.05,
        },
    },
    {
        "name": "verified_payments_poor_fulfillment",
        "profile": {
            "evidence_depth_score": 0.74,
            "activity_continuity_score": 0.73,
            "record_coherence_score": 0.70,
            "payment_integrity_score": 0.85,
            "fulfilled_or_completed_order_ratio": 0.38,
            "cashflow_stability_proxy": 0.69,
            "customer_diversity_score": 0.67,
            "growth_momentum_proxy": 0.60,
            "document_discipline_score": 0.75,
            "operational_maturity_proxy": 0.71,
            "audit_integrity_score": 0.73,
            "deleted_record_ratio": 0.05,
        },
    },
    {
        "name": "stable_lender_friendly_business",
        "profile": {
            "evidence_depth_score": 0.84,
            "activity_continuity_score": 0.80,
            "record_coherence_score": 0.87,
            "payment_integrity_score": 0.86,
            "fulfilled_or_completed_order_ratio": 0.86,
            "cashflow_stability_proxy": 0.82,
            "customer_diversity_score": 0.72,
            "growth_momentum_proxy": 0.57,
            "document_discipline_score": 0.83,
            "operational_maturity_proxy": 0.84,
            "audit_integrity_score": 0.81,
            "deleted_record_ratio": 0.02,
        },
    },
    {
        "name": "growth_heavy_volatile_business",
        "profile": {
            "evidence_depth_score": 0.66,
            "activity_continuity_score": 0.59,
            "record_coherence_score": 0.75,
            "payment_integrity_score": 0.80,
            "fulfilled_or_completed_order_ratio": 0.79,
            "cashflow_stability_proxy": 0.46,
            "customer_diversity_score": 0.71,
            "growth_momentum_proxy": 0.86,
            "document_discipline_score": 0.77,
            "operational_maturity_proxy": 0.69,
            "audit_integrity_score": 0.72,
            "deleted_record_ratio": 0.05,
        },
    },
    {
        "name": "mature_flat_business",
        "profile": {
            "evidence_depth_score": 0.80,
            "activity_continuity_score": 0.74,
            "record_coherence_score": 0.84,
            "payment_integrity_score": 0.84,
            "fulfilled_or_completed_order_ratio": 0.86,
            "cashflow_stability_proxy": 0.79,
            "customer_diversity_score": 0.69,
            "growth_momentum_proxy": 0.48,
            "document_discipline_score": 0.82,
            "operational_maturity_proxy": 0.81,
            "audit_integrity_score": 0.78,
            "deleted_record_ratio": 0.02,
        },
    },
)

ML_REFERENCE_PERTURBATIONS = (
    {
        "evidence_depth_score": 0.00,
        "activity_continuity_score": 0.00,
        "record_coherence_score": 0.00,
        "payment_integrity_score": 0.00,
        "fulfilled_or_completed_order_ratio": 0.00,
        "cashflow_stability_proxy": 0.00,
        "customer_diversity_score": 0.00,
        "growth_momentum_proxy": 0.00,
        "document_discipline_score": 0.00,
        "operational_maturity_proxy": 0.00,
        "audit_integrity_score": 0.00,
        "deleted_record_ratio": 0.00,
    },
    {
        "evidence_depth_score": 0.03,
        "activity_continuity_score": 0.04,
        "record_coherence_score": 0.02,
        "payment_integrity_score": 0.03,
        "fulfilled_or_completed_order_ratio": 0.03,
        "cashflow_stability_proxy": 0.02,
        "customer_diversity_score": 0.02,
        "growth_momentum_proxy": 0.05,
        "document_discipline_score": 0.02,
        "operational_maturity_proxy": 0.03,
        "audit_integrity_score": 0.03,
        "deleted_record_ratio": -0.01,
    },
    {
        "evidence_depth_score": -0.04,
        "activity_continuity_score": -0.03,
        "record_coherence_score": -0.03,
        "payment_integrity_score": -0.02,
        "fulfilled_or_completed_order_ratio": -0.04,
        "cashflow_stability_proxy": -0.03,
        "customer_diversity_score": -0.02,
        "growth_momentum_proxy": -0.03,
        "document_discipline_score": -0.03,
        "operational_maturity_proxy": -0.03,
        "audit_integrity_score": -0.03,
        "deleted_record_ratio": 0.01,
    },
    {
        "evidence_depth_score": 0.02,
        "activity_continuity_score": -0.02,
        "record_coherence_score": 0.03,
        "payment_integrity_score": -0.01,
        "fulfilled_or_completed_order_ratio": 0.01,
        "cashflow_stability_proxy": -0.04,
        "customer_diversity_score": 0.02,
        "growth_momentum_proxy": 0.06,
        "document_discipline_score": 0.01,
        "operational_maturity_proxy": 0.02,
        "audit_integrity_score": 0.01,
        "deleted_record_ratio": 0.00,
    },
    {
        "evidence_depth_score": -0.02,
        "activity_continuity_score": 0.03,
        "record_coherence_score": -0.01,
        "payment_integrity_score": 0.04,
        "fulfilled_or_completed_order_ratio": -0.02,
        "cashflow_stability_proxy": 0.04,
        "customer_diversity_score": 0.01,
        "growth_momentum_proxy": -0.04,
        "document_discipline_score": 0.02,
        "operational_maturity_proxy": 0.01,
        "audit_integrity_score": 0.03,
        "deleted_record_ratio": 0.01,
    },
    {
        "evidence_depth_score": 0.01,
        "activity_continuity_score": 0.01,
        "record_coherence_score": -0.04,
        "payment_integrity_score": -0.03,
        "fulfilled_or_completed_order_ratio": 0.02,
        "cashflow_stability_proxy": 0.01,
        "customer_diversity_score": -0.03,
        "growth_momentum_proxy": 0.03,
        "document_discipline_score": -0.02,
        "operational_maturity_proxy": -0.02,
        "audit_integrity_score": -0.03,
        "deleted_record_ratio": 0.02,
    },
)

ML_ANOMALY_PERCENTILE_THRESHOLD = 0.82
ML_ANOMALY_SEVERITY_THRESHOLDS = (
    (0.35, "low"),
    (0.65, "medium"),
    (1.00, "high"),
)

ML_RISK_BLEND_WEIGHT = 0.30
ML_CONFIDENCE_PENALTY_MAX = 0.18
ML_CONFIDENCE_PENALTY_THRESHOLD = 0.55
ML_SCORE_PENALTY_THRESHOLD = 0.65
ML_SCORE_PENALTIES = {
    "proof_of_business_score": 0.05,
    "vendor_trust_score": 0.06,
    "payment_confidence_score": 0.05,
    "fulfillment_reliability_score": 0.05,
    "credit_readiness_score": 0.06,
    "cashflow_stability_score": 0.05,
    "repayment_capacity_signal": 0.05,
    "growth_momentum_score": 0.04,
    "customer_quality_signal": 0.04,
    "operational_maturity_score": 0.04,
}
