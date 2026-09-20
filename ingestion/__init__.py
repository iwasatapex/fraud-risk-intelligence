"""Ingestion layer: source adapters, canonical contract, validation and pipeline."""

from __future__ import annotations

from .exceptions import (
    AdapterError,
    IngestionError,
    NormalizationError,
    SchemaError,
    ValidationError,
)
from .models.transaction import CanonicalTransaction
from .validation import (
    REQUIRED_FIELDS,
    VALID_CHANNELS,
    InvalidRecord,
    ValidationResult,
    assert_required_columns,
    validate_record,
    validate_records,
)
from .adapters import (
    ATMAdapter,
    BaseSourceAdapter,
    OnlineBankingAdapter,
    POSAdapter,
    SourceAdapter,
)
from .pipeline import (
    DEFAULT_ADAPTERS,
    IngestionPipeline,
    IngestionReport,
    SourceResult,
    SourceSpec,
    canonical_frame,
    detect_adapter,
    run_ingestion,
    write_canonical_csv,
)

__all__ = [
    # Canonical contract
    "CanonicalTransaction",
    "REQUIRED_FIELDS",
    "VALID_CHANNELS",
    # Errors
    "IngestionError",
    "ValidationError",
    "AdapterError",
    "SchemaError",
    "NormalizationError",
    # Adapters
    "BaseSourceAdapter",
    "SourceAdapter",
    "POSAdapter",
    "ATMAdapter",
    "OnlineBankingAdapter",
    # Validation
    "validate_record",
    "validate_records",
    "assert_required_columns",
    "InvalidRecord",
    "ValidationResult",
    # Pipeline
    "IngestionPipeline",
    "IngestionReport",
    "SourceResult",
    "SourceSpec",
    "DEFAULT_ADAPTERS",
    "detect_adapter",
    "run_ingestion",
    "canonical_frame",
    "write_canonical_csv",
]