"""Tests for the canonical transaction contract."""

from ingestion.models import CanonicalTransaction


def test_field_names_are_the_phase_one_contract():
    names = CanonicalTransaction.field_names()
    assert names[:6] == (
        "transaction_id",
        "customer_id",
        "channel",
        "amount",
        "currency",
        "timestamp",
    )
    assert names[-1] == "raw_source_data"
    assert len(names) == len(set(names)) == 17


def test_optional_fields_default_to_none():
    txn = CanonicalTransaction(
        transaction_id="t1",
        customer_id="c1",
        channel="POS",
        amount=1.0,
        currency="USD",
        timestamp="2026-01-01T00:00:00",
    )
    assert txn.merchant_id is None
    assert txn.terminal_id is None
    assert txn.authorization_code is None
    assert txn.response_time_seconds is None
    assert txn.is_fraud is None
    assert txn.raw_source_data is None


def test_to_dict_uses_declaration_order():
    txn = CanonicalTransaction(
        transaction_id="t1",
        customer_id="c1",
        channel="ATM",
        amount=2.0,
        currency="EUR",
        timestamp="2026-01-01T00:00:00",
        terminal_id="atm-1",
    )
    as_dict = txn.to_dict()
    assert list(as_dict) == list(CanonicalTransaction.field_names())
    assert as_dict["channel"] == "ATM"
    assert as_dict["terminal_id"] == "atm-1"
    assert as_dict["merchant_id"] is None


def test_from_dict_ignores_unknown_keys():
    txn = CanonicalTransaction.from_dict(
        {
            "transaction_id": "t1",
            "customer_id": "c1",
            "channel": "ONLINE_BANKING",
            "amount": 3,
            "currency": "usd",
            "timestamp": "2026-01-01",
            "unexpected_source_column": "ignored",
        }
    )
    assert txn.channel == "ONLINE_BANKING"
    assert txn.amount == 3
    assert not hasattr(txn, "unexpected_source_column")