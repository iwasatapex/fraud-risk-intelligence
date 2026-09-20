"""Tests for the POS/ATM/online banking source adapters."""

import pandas as pd
import pytest

from ingestion.adapters import ATMAdapter, OnlineBankingAdapter, POSAdapter
from ingestion.adapters.base import SourceAdapter
from ingestion.exceptions import AdapterError, NormalizationError, SchemaError


def test_adapters_satisfy_the_source_adapter_protocol():
    for adapter in (POSAdapter(), ATMAdapter(), OnlineBankingAdapter()):
        assert isinstance(adapter, SourceAdapter)
        assert adapter.required_columns == adapter.get_required_columns()
        assert adapter.name == adapter._source_name.upper()


def test_required_columns_returns_a_copy():
    adapter = POSAdapter()
    columns = adapter.required_columns
    columns.append("not_a_source_column")
    assert "not_a_source_column" not in adapter.required_columns
    assert "transaction_id" in adapter.required_columns


def test_read_keeps_leading_zeros_and_text_scalars(pos_csv):
    frame = POSAdapter().read(pos_csv)
    assert frame.iloc[0]["card_last4"] == "0123"
    assert frame.iloc[0]["response_code"] == "00"
    assert frame.iloc[0]["amount"] == "42.50"


def test_pos_normalize_maps_to_the_canonical_contract(pos_csv):
    adapter = POSAdapter()
    record = adapter.normalize(adapter.read(pos_csv))[0]
    assert record["channel"] == "POS"
    assert record["amount"] == pytest.approx(42.5)
    assert record["card_last4"] == "0123"
    assert record["authorization_code"] == "A1B2C3"
    assert record["merchant_id"] == "merch-9"
    assert record["location"] == "store-12"
    assert record["currency"] == "usd"  # case normalization is validation's job
    assert record.get("terminal_id") is None


def test_atm_normalize_sets_channel_and_leaves_authorization_empty(atm_csv):
    adapter = ATMAdapter()
    record = adapter.normalize(adapter.read(atm_csv))[0]
    assert record["channel"] == "ATM"
    assert record["terminal_id"] == "atm-77"
    assert record["payment_method"] == "CASH_WITHDRAWAL"
    assert record["authorization_code"] is None
    assert record["merchant_id"] is None
    assert record["amount"] == pytest.approx(100.0)


def test_online_normalize_maps_channel_and_status(online_csv):
    adapter = OnlineBankingAdapter()
    record = adapter.normalize(adapter.read(online_csv))[0]
    assert record["channel"] == "ONLINE_BANKING"
    assert record["payment_method"] == "MOBILE_APP"
    assert record["response_code"] == "APPROVED"
    assert record["location"] is None
    assert record["terminal_id"] is None
    assert record["merchant_id"] == "merch-3"
    assert record["amount"] == pytest.approx(1250.75)


def test_include_raw_attaches_the_source_row(pos_csv):
    adapter = POSAdapter(include_raw=True)
    record = adapter.normalize(adapter.read(pos_csv))[0]
    assert record["raw_source_data"]["transaction_id"] == "pos-1"
    assert record["raw_source_data"]["amount"] == "42.50"


def test_missing_columns_raise_schema_error(write_csv):
    broken = write_csv("pos_broken.csv", {"transaction_id": "t-1", "amount": "1.00"})
    adapter = POSAdapter()
    with pytest.raises(SchemaError) as excinfo:
        adapter.normalize(adapter.read(broken))
    assert "customer_id" in excinfo.value.missing_fields
    assert "timestamp" in excinfo.value.missing_fields


def test_non_numeric_amount_raises_normalization_error(write_csv, pos_row):
    broken = write_csv("pos_bad_amount.csv", {**pos_row, "amount": "not-a-number"})
    adapter = POSAdapter()
    with pytest.raises(NormalizationError, match="Row 0"):
        adapter.normalize(adapter.read(broken))


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="Source file not found"):
        POSAdapter().read(tmp_path / "does_not_exist.csv")


def test_directory_path_raises_adapter_error(tmp_path):
    folder = tmp_path / "not_a_file.csv"
    folder.mkdir()
    with pytest.raises(AdapterError, match="Expected a file"):
        POSAdapter().read(folder)


def test_unparseable_csv_raises_adapter_error(tmp_path):
    empty = tmp_path / "pos_empty.csv"
    empty.write_text("")
    with pytest.raises(AdapterError, match="Could not read CSV file"):
        POSAdapter().read(empty)


def test_base_adapter_without_source_name_raises():
    class Nameless(POSAdapter):
        _source_name = ""

    with pytest.raises(AdapterError, match="does not define a source name"):
        Nameless().name


def test_base_adapter_cannot_be_instantiated():
    from ingestion.adapters import BaseSourceAdapter

    with pytest.raises(TypeError):
        BaseSourceAdapter()