"""
Schema and record validation for the ingestion layer.

This module owns the canonical data contract: it declares the fields every
transaction must provide, the accepted channels, and the scalar rules
(text/number/bool/timestamp) that adapters use while building canonical records
and that the pipeline uses to reject records which break the contract.
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime
from typing import Any

import pandas as pd

from ..exceptions import IngestionError, SchemaError, ValidationError
from ..models.transaction import CanonicalTransaction

#: Fields every canonical transaction must provide.
REQUIRED_FIELDS: tuple[str, ...] = (
    "transaction_id",
    "customer_id",
    "channel",
    "amount",
    "currency",
    "timestamp",
)

#: Channels produced by the Phase 1 source adapters.
VALID_CHANNELS: frozenset[str] = frozenset({"POS", "ATM", "ONLINE_BANKING"})

#: Source timestamp layouts tried (in order) before falling back to ISO parsing.
TIMESTAMP_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)

#: Text values that mean "this cell is empty" in real world CSVs.
_MISSING_TOKENS = frozenset({"", "nan", "nat", "none", "null", "na", "n/a", "-"})

_TRUE_TOKENS = frozenset({"1", "true", "t", "yes", "y"})
_FALSE_TOKENS = frozenset({"0", "false", "f", "no", "n"})

_CURRENCY_SYMBOLS = ("$", "\u20ac", "\u00a3", "\u00a5")

_CARD_LAST4_PATTERN = re.compile(r"\d{4}")
_CURRENCY_PATTERN = re.compile(r"[A-Z]{3}")


def _is_missing(value: Any) -> bool:
    """True for ``None``/``NaN``/``NaT`` style missing scalars."""
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict, set)):
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return False if hasattr(missing, "__len__") else bool(missing)


def to_text(value: Any) -> str | None:
    """
    Convert a source scalar into clean text, or ``None`` when the cell is empty.

    Whole floats collapse to their integer form (``1234.0`` -> ``"1234"``) and the
    usual missing markers (``NaN``/``NaT``/``"n/a"``) become ``None``, so the
    canonical layer only ever sees ``str`` or ``None``.
    """
    if _is_missing(value):
        return None
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    if isinstance(value, str):
        text = value.strip()
        return None if text.lower() in _MISSING_TOKENS else text
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return None if text.lower() in _MISSING_TOKENS else text


def to_number(value: Any, *, field_name: str = "value") -> float:
    """
    Coerce a source scalar into a finite float.

    Numbers and text numbers are accepted; thousands separators and currency
    symbols (``"$1,234.50"``) are tolerated.

    Raises:
        ValidationError: If the value is missing, boolean or not numeric.
    """
    if isinstance(value, bool):
        raise ValidationError("Expected a number but got a boolean.", field=field_name, value=value)
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = to_text(value)
        if text is None:
            raise ValidationError("Expected a number but the value is empty.", field=field_name, value=value)
        cleaned = text
        for symbol in _CURRENCY_SYMBOLS:
            cleaned = cleaned.replace(symbol, "")
        cleaned = cleaned.replace(",", "").strip()
        try:
            number = float(cleaned)
        except ValueError as exc:
            raise ValidationError(f"Expected a number but got '{text}'.", field=field_name, value=text) from exc
    if math.isnan(number) or math.isinf(number):
        raise ValidationError("Expected a finite number.", field=field_name, value=value)
    return number


def to_bool(value: Any, *, field_name: str = "value") -> bool:
    """Coerce ``0/1``, ``true/false`` or ``yes/no`` style source values to a bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value)
        raise ValidationError(
            "Expected a boolean (0/1) but got a different number.", field=field_name, value=value
        )
    text = to_text(value)
    if text is None:
        raise ValidationError("Expected a boolean but the value is empty.", field=field_name, value=value)
    lowered = text.lower()
    if lowered in _TRUE_TOKENS:
        return True
    if lowered in _FALSE_TOKENS:
        return False
    raise ValidationError(f"Expected a boolean but got '{text}'.", field=field_name, value=text)


def normalize_channel(
    value: Any,
    *,
    allowed_channels: Collection[str] = VALID_CHANNELS,
    field_name: str = "channel",
) -> str:
    """
    Normalize a source channel label to its canonical form.

    ``"online banking"`` becomes ``"ONLINE_BANKING"``; anything outside
    ``allowed_channels`` is rejected so typos cannot reach downstream layers.

    Raises:
        ValidationError: If the channel is empty or not supported.
    """
    text = to_text(value)
    if text is None:
        raise ValidationError("Channel is empty.", field=field_name)
    channel = re.sub(r"[^A-Z0-9]+", "_", text.upper()).strip("_")
    if channel not in allowed_channels:
        raise ValidationError(
            f"Unsupported channel '{text}'. Expected one of: {', '.join(sorted(allowed_channels))}.",
            field=field_name,
            value=text,
        )
    return channel


def parse_timestamp(value: Any, *, field_name: str = "timestamp") -> datetime:
    """
    Parse a source timestamp into a ``datetime``.

    ISO 8601 values (with or without timezone, ``Z`` included) are handled first,
    then the common ``dd/mm/yyyy``-style layouts listed in ``TIMESTAMP_FORMATS``.

    Raises:
        ValidationError: If the value is empty or in an unknown format.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = to_text(value)
    if text is None:
        raise ValidationError("Timestamp is empty.", field=field_name, value=value)
    iso_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(iso_text)
    except ValueError:
        pass
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValidationError(f"Unrecognised timestamp format: '{text}'.", field=field_name, value=text)


def assert_required_columns(
    columns: Iterable[Any],
    required: Sequence[str],
    *,
    source: str | None = None,
) -> None:
    """
    Raise SchemaError when a source frame is missing required columns.

    The pipeline calls this before normalization so a bad file fails fast with a
    message naming exactly what is missing.

    Raises:
        SchemaError: If any required column is absent.
    """
    present = {str(column).strip() for column in columns}
    missing = [column for column in required if column not in present]
    if missing:
        raise SchemaError(
            f"Source data is missing required column(s): {', '.join(missing)}",
            expected_fields=list(required),
            missing_fields=missing,
            source=source,
        )


@dataclass(frozen=True)
class InvalidRecord:
    """One source record that failed canonical validation."""

    index: int
    message: str
    field: str | None = None
    value: Any | None = None
    record: Mapping[str, Any] | None = dc_field(default=None, compare=False)


@dataclass
class ValidationResult:
    """Outcome of validating every record of a single source."""

    source: str | None = None
    valid: list[CanonicalTransaction] = dc_field(default_factory=list)
    invalid: list[InvalidRecord] = dc_field(default_factory=list)

    @property
    def total(self) -> int:
        """Number of records seen (valid + invalid)."""
        return len(self.valid) + len(self.invalid)

    @property
    def is_valid(self) -> bool:
        """True when no record was rejected."""
        return not self.invalid

    @property
    def failure_rate(self) -> float:
        """Share of records that failed validation, between 0.0 and 1.0."""
        return 0.0 if not self.total else len(self.invalid) / self.total

    def invalid_field_counts(self) -> dict[str, int]:
        """Number of failures per field (``"<record>"`` for record level errors)."""
        counts: dict[str, int] = {}
        for record in self.invalid:
            key = record.field or "<record>"
            counts[key] = counts.get(key, 0) + 1
        return counts

    def summary(self) -> str:
        """One line summary suitable for logs and reports."""
        label = self.source or "source"
        return (
            f"{label}: {len(self.valid)}/{self.total} record(s) valid "
            f"({self.failure_rate:.2%} rejected)"
        )


def validate_record(
    record: Mapping[str, Any],
    *,
    source: str | None = None,
    allowed_channels: Collection[str] = VALID_CHANNELS,
    allow_negative_amount: bool = False,
    strict: bool = False,
) -> CanonicalTransaction:
    """
    Validate a single canonical record and return a ``CanonicalTransaction``.

    The input mapping may come straight from an adapter: required text fields are
    stripped, channel/currency are upper-cased, the timestamp is normalized to
    ISO 8601, and optional fields are checked when present.

    Args:
        record: Mapping of canonical fields; unknown keys are ignored unless strict.
        source: Label used in error messages and pipeline reports.
        allowed_channels: Channels accepted for the ``channel`` field.
        allow_negative_amount: Permit negative amounts (e.g. refunds).
        strict: Reject unknown fields instead of ignoring them.

    Returns:
        The validated ``CanonicalTransaction``.

    Raises:
        ValidationError: If the record is not a mapping or a field value is invalid.
        SchemaError: If required fields are missing.
    """
    if not isinstance(record, Mapping):
        raise ValidationError(f"Expected a mapping of canonical fields, got {type(record).__name__}.", source=source)

    missing = [name for name in REQUIRED_FIELDS if to_text(record.get(name)) is None]
    if missing:
        raise SchemaError(
            f"Record is missing required field(s): {', '.join(missing)}",
            expected_fields=list(REQUIRED_FIELDS),
            missing_fields=missing,
            source=source,
        )

    unknown = sorted(set(record) - set(CanonicalTransaction.field_names()))
    if unknown and strict:
        raise ValidationError(f"Unexpected field(s) for the canonical contract: {', '.join(unknown)}", source=source)

    currency_text = to_text(record.get("currency"))
    currency = (currency_text or "").upper()
    if not _CURRENCY_PATTERN.fullmatch(currency):
        raise ValidationError("Currency must be a three letter ISO-4217 code.", field="currency", value=currency_text)

    amount = to_number(record.get("amount"), field_name="amount")
    if amount < 0 and not allow_negative_amount:
        raise ValidationError(
            "Amount must not be negative (pass allow_negative_amount=True to permit refunds).",
            field="amount",
            value=amount,
        )

    validated: dict[str, Any] = {
        "transaction_id": to_text(record.get("transaction_id")),
        "customer_id": to_text(record.get("customer_id")),
        "channel": normalize_channel(record.get("channel"), allowed_channels=allowed_channels),
        "amount": amount,
        "currency": currency,
        "timestamp": parse_timestamp(record.get("timestamp")).isoformat(),
    }

    for name in (
        "location",
        "merchant_id",
        "terminal_id",
        "card_type",
        "payment_method",
        "authorization_code",
        "response_code",
    ):
        validated[name] = to_text(record.get(name))

    card_last4 = to_text(record.get("card_last4"))
    if card_last4 is not None and not _CARD_LAST4_PATTERN.fullmatch(card_last4):
        raise ValidationError("card_last4 must be exactly four digits.", field="card_last4", value=card_last4)
    validated["card_last4"] = card_last4

    if record.get("response_time_seconds") is not None:
        seconds = to_number(record["response_time_seconds"], field_name="response_time_seconds")
        if seconds < 0:
            raise ValidationError(
                "response_time_seconds must not be negative.",
                field="response_time_seconds",
                value=seconds,
            )
        validated["response_time_seconds"] = seconds

    if record.get("is_fraud") is not None:
        validated["is_fraud"] = to_bool(record["is_fraud"], field_name="is_fraud")

    raw_source_data = record.get("raw_source_data")
    if isinstance(raw_source_data, Mapping):
        validated["raw_source_data"] = dict(raw_source_data)

    return CanonicalTransaction.from_dict(validated)
def validate_records(
    records: Iterable[Mapping[str, Any]],
    *,
    source: str | None = None,
    allowed_channels: Collection[str] = VALID_CHANNELS,
    allow_negative_amount: bool = False,
    strict: bool = False,
    raise_on_error: bool = False,
) -> ValidationResult:
    """
    Validate a batch of records, collecting failures instead of stopping.

    Args:
        records: Iterable of canonical record mappings.
        source: Label used in reports and error messages.
        allowed_channels: Channels accepted for the ``channel`` field.
        allow_negative_amount: Permit negative amounts (e.g. refunds).
        strict: Reject unknown fields instead of ignoring them.
        raise_on_error: Raise the first error instead of collecting it.

    Returns:
        ValidationResult holding the accepted transactions and the rejections.
    """
    result = ValidationResult(source=source)
    for index, record in enumerate(records):
        try:
            result.valid.append(
                validate_record(
                    record,
                    source=source,
                    allowed_channels=allowed_channels,
                    allow_negative_amount=allow_negative_amount,
                    strict=strict,
                )
            )
        except IngestionError as exc:
            if raise_on_error:
                raise
            result.invalid.append(
                InvalidRecord(
                    index=index,
                    message=str(exc),
                    field=getattr(exc, "field", None),
                    value=getattr(exc, "value", None),
                    record=record if isinstance(record, Mapping) else None,
                )
            )
    return result


__all__ = [
    "REQUIRED_FIELDS",
    "VALID_CHANNELS",
    "TIMESTAMP_FORMATS",
    "InvalidRecord",
    "ValidationResult",
    "validate_record",
    "validate_records",
    "assert_required_columns",
    "normalize_channel",
    "parse_timestamp",
    "to_text",
    "to_number",
    "to_bool",
]