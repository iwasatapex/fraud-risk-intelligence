"""Tests for the canonical schema validation rules."""

from datetime import datetime

import pytest

from ingestion.exceptions import SchemaError, ValidationError
from ingestion.validation import (
    REQUIRED_FIELDS,
    VALID_CHANNELS,
    assert_required_columns,
    normalize_channel,
    parse_timestamp,
    to_bool,
    to_number,
    to_text,
    validate_record,
    validate_records,
)


def test_contract_constants():
    assert REQUIRED_FIELDS == (
        "transaction_id",
        "customer_id",
        "channel",
        "amount",
        "currency",
        "timestamp",
    )
    assert VALID_CHANNELS == frozenset({"POS", "ATM", "ONLINE_BANKING"})


def test_validate_record_normalizes_the_contract(canonical_record):
    txn = validate_record(canonical_record)
    assert txn.channel == "POS"
    assert txn.currency == "USD"
    assert txn.amount == pytest.approx(10.5)
    assert txn.card_last4 == "1234"
    assert txn.timestamp == "2026-01-02T03:04:05"
    assert txn.is_fraud is None
    assert txn.response_time_seconds is None


def test_validate_record_accepts_source_style_values(canonical_record):
    txn = validate_record(
        {
            **canonical_record,
            "channel": "online banking",
            "currency": "eur",
            "amount": "$1,250.75",
            "timestamp": "02/01/2026 10:00:00",
            "card_last4": 1234,
        }
    )
    assert txn.channel == "ONLINE_BANKING"
    assert txn.currency == "EUR"
    assert txn.amount == pytest.approx(1250.75)
    assert txn.timestamp == "2026-01-02T10:00:00"
    assert txn.card_last4 == "1234"


def test_missing_required_fields_raise_schema_error(canonical_record):
    record = {**canonical_record, "amount": None}
    del record["currency"]
    with pytest.raises(SchemaError) as excinfo:
        validate_record(record, source="POS")
    assert excinfo.value.missing_fields == ["amount", "currency"]
    assert excinfo.value.expected_fields == list(REQUIRED_FIELDS)
    assert "[POS]" in str(excinfo.value)


def test_invalid_field_values_raise_validation_error(canonical_record):
    with pytest.raises(ValidationError, match="Unsupported channel"):
        validate_record({**canonical_record, "channel": "telegraph"})
    with pytest.raises(ValidationError, match="ISO-4217"):
        validate_record({**canonical_record, "currency": "dollars"})
    with pytest.raises(ValidationError, match="Expected a number"):
        validate_record({**canonical_record, "amount": "abc"})
    with pytest.raises(ValidationError, match="four digits"):
        validate_record({**canonical_record, "card_last4": "12"})
    with pytest.raises(ValidationError, match="Unrecognised timestamp"):
        validate_record({**canonical_record, "timestamp": "not-a-date"})
    with pytest.raises(ValidationError, match="must not be negative"):
        validate_record({**canonical_record, "amount": -5})


def test_negative_amounts_can_be_allowed(canonical_record):
    txn = validate_record({**canonical_record, "amount": -5}, allow_negative_amount=True)
    assert txn.amount == pytest.approx(-5.0)


def test_strict_mode_rejects_unknown_fields(canonical_record):
    record = {**canonical_record, "unexpected": "x"}
    assert validate_record(record).transaction_id == "txn-1"
    with pytest.raises(ValidationError, match="Unexpected field"):
        validate_record(record, strict=True)


def test_optional_fields_are_checked_when_present(canonical_record):
    txn = validate_record(
        {
            **canonical_record,
            "response_time_seconds": "1.5",
            "is_fraud": "1",
            "raw_source_data": {"source_row": 1},
        }
    )
    assert txn.response_time_seconds == pytest.approx(1.5)
    assert txn.is_fraud is True
    assert txn.raw_source_data == {"source_row": 1}

    with pytest.raises(ValidationError, match="must not be negative"):
        validate_record({**canonical_record, "response_time_seconds": -1})
    with pytest.raises(ValidationError, match="Expected a boolean"):
        validate_record({**canonical_record, "is_fraud": "maybe"})


def test_validate_records_collects_failures(canonical_record):
    records = [
        canonical_record,
        {**canonical_record, "transaction_id": "txn-2", "amount": "oops"},
        {**canonical_record, "transaction_id": "txn-3", "channel": "telegraph"},
    ]
    result = validate_records(records, source="POS")

    assert len(result.valid) == 1
    assert len(result.invalid) == 2
    assert result.total == 3
    assert result.failure_rate == pytest.approx(2 / 3)
    assert result.is_valid is False
    assert result.invalid[0].index == 1
    assert result.invalid[0].field == "amount"
    assert result.invalid[0].record["transaction_id"] == "txn-2"
    assert result.invalid_field_counts() == {"amount": 1, "channel": 1}
    assert "POS: 1/3 record(s) valid" in result.summary()


def test_validate_records_can_raise_on_error(canonical_record):
    with pytest.raises(ValidationError):
        validate_records([{**canonical_record, "amount": "oops"}], raise_on_error=True)


def test_validate_records_handles_an_empty_batch():
    result = validate_records([])
    assert result.total == 0
    assert result.failure_rate == 0.0
    assert result.is_valid is True
    assert result.invalid_field_counts() == {}


def test_assert_required_columns():
    assert_required_columns(["transaction_id", " amount"], ["transaction_id", "amount"])
    with pytest.raises(SchemaError) as excinfo:
        assert_required_columns(["transaction_id"], ["transaction_id", "amount", "currency"], source="POS")
    assert excinfo.value.missing_fields == ["amount", "currency"]
    assert "[POS]" in str(excinfo.value)
def test_non_mapping_record_is_rejected():
    with pytest.raises(ValidationError, match="Expected a mapping"):
        validate_record(["not", "a", "mapping"])


def test_to_number_robust_string_cleaning():
    """Formatted numbers are cleaned; malformed strings are rejected."""
    assert to_number("$1,234.50", field_name="amount") == 1234.5
    assert to_number("\u20ac2,500.00", field_name="amount") == 2500.0
    assert to_number("- $5,000.00", field_name="amount") == -5000.0
    assert to_number("12345", field_name="amount") == 12345.0
    assert to_number("500", field_name="amount") == 500.0

    for malformed in ("12abc34", "abc123", "1.2.3", "1-2", "1,2,3", "abc-xyz", "nan", "inf"):
        with pytest.raises(ValidationError, match="could not be reliably converted to a number"):
            to_number(malformed, field_name="amount")

    with pytest.raises(ValidationError, match="Cannot convert empty string"):
        to_number("   ", field_name="amount")
