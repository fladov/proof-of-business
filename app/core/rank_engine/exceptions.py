"""Domain-specific exceptions for the rank engine."""


class RankEngineError(Exception):
    """Base error for rank engine failures."""


class PayloadValidationError(RankEngineError):
    """Raised when the PoB payload is structurally or semantically invalid."""
