"""Tests for pipeline orchestration: read -> normalize -> validate -> dedupe."""

import pandas as pd
import pytest

from ingestion.adapters import POSAdapter
from ingestion.exceptions import AdapterError
from ingestion.models import CanonicalTransaction
from ingestion.pipeline import (
    DEFAULT_ADAPTERS,
    IngestionPipeline,
    SourceSpec,
    canonical_frame,
    detect_adapter,
    run_ingestion,
    write_canonical_csv,
)


def test_default_registry_and_adapter_detection(pos_csv, atm_csv, online_csv):
    assert set(DEFAULT_ADAPTERS) == {"pos", "atm", "online"}
    assert detect_adapter(pos_csv) == "pos"
    assert detect_adapter(atm_csv) == "atm"
    assert detect_adapter(online_csv) == "online"
    with pytest.raises(AdapterError, match="Could not determine an adapter"):
        detect_adapter("transactions.csv")


def test_source_spec_defaults_its_reporting_name(tmp_path):
    spec = SourceSpec.from_path(tmp_path / "pos_march.csv")
    assert spec.name == "pos_march"
    assert spec.adapter is None

    forced = SourceSpec.from_path(tmp_path / "pos_march.csv", adapter="atm", name="custom")
    assert forced.adapter == "atm"
    assert forced.name == "custom"


def test_ingest_single_source_produces_canonical_records(pos_csv):
    result = IngestionPipeline().ingest(pos_csv)

    assert result.ok is True
    assert result.adapter == "pos"
    assert result.rows_read == 1
    assert len(result.valid) == 1
    txn = result.valid[0]
    assert isinstance(txn, CanonicalTransaction)
    assert txn.channel == "POS"
    assert txn.currency == "USD"
    assert txn.timestamp == "2026-01-02T03:04:05"
    assert txn.card_last4 == "0123"
    assert "pos_transactions (pos): ok" in result.summary()


def test_run_merges_sources_and_reports(pos_csv, atm_csv, online_csv):
    report = run_ingestion({"pos": pos_csv, "atm": atm_csv, "online": online_csv})

    assert [source.adapter for source in report.sources] == ["pos", "atm", "online"]
    assert len(report.records) == 3
    assert report.total_read == 3
    assert {record.channel for record in report.records} == {"POS", "ATM", "ONLINE_BANKING"}
    assert report.ok is True
    assert report.duplicates_removed == 0
    assert "Ingestion report: 3 canonical record(s)" in report.summary()


def test_run_accepts_paths_specs_and_tuples(pos_csv, atm_csv):
    report = IngestionPipeline().run([pos_csv, (atm_csv, "atm"), SourceSpec.from_path(pos_csv)])

    assert [source.adapter for source in report.sources] == ["pos", "atm", "pos"]
    assert len(report.records) == 2  # the third file repeats pos-1
    assert report.duplicates_removed == 1


def test_unsupported_source_specification_raises():
    with pytest.raises(AdapterError, match="Unsupported source specification"):
        IngestionPipeline().run([1234])


def test_duplicates_are_dropped_by_transaction_id(pos_csv, pos_duplicate_csv):
    report = IngestionPipeline().run([pos_csv, pos_duplicate_csv])

    assert len(report.records) == 1
    assert report.duplicates_removed == 1
    assert report.sources[1].duplicates_removed == 1
    assert report.records[0].amount == pytest.approx(42.5)  # first occurrence wins


def test_dedupe_can_be_disabled(pos_csv, pos_duplicate_csv):
    report = IngestionPipeline(dedupe=False).run([pos_csv, pos_duplicate_csv])

    assert len(report.records) == 2
    assert report.duplicates_removed == 0