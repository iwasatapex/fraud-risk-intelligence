from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
INGESTION_DIR = PROJECT_ROOT / "ingestion"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(ANALYSIS_DIR))
sys.path.insert(0, str(ANALYSIS_DIR / "core"))


# =============================================================================
# Ingestion Test Fixtures
# =============================================================================

POS_ROW = {
    "transaction_id": "pos-1",
    "customer_id": "cust-1",
    "amount": "42.50",
    "currency": "usd",
    "timestamp": "2026-01-02T03:04:05",
    "location": "store-12",
    "merchant_id": "merch-9",
    "card_last4": "0123",
    "card_type": "VISA",
    "payment_method": "CHIP",
    "authorization_code": "A1B2C3",
    "response_code": "00",
}

ATM_ROW = {
    "transaction_id": "atm-1",
    "customer_id": "cust-2",
    "amount": "100.00",
    "currency": "USD",
    "timestamp": "02/01/2026 10:00:00",
    "terminal_id": "atm-77",
    "card_last4": "5678",
    "card_type": "MASTERCARD",
    "transaction_type": "CASH_WITHDRAWAL",
    "response_code": "00",
}

ONLINE_ROW = {
    "transaction_id": "onl-1",
    "customer_id": "cust-3",
    "amount": "1,250.75",
    "currency": "eur",
    "timestamp": "2026-01-02 11:30:00",
    "merchant_id": "merch-3",
    "card_last4": "9999",
    "card_type": "VISA",
    "merchant_category": "electronics",
    "channel": "MOBILE_APP",
    "transaction_status": "APPROVED",
}


def _write_row(path: Path, row: dict) -> Path:
    """Write a single row to ``path`` as CSV."""
    pd.DataFrame([row]).to_csv(path, index=False)
    return path


@pytest.fixture
def write_csv(tmp_path):
    """Return a helper writing one raw source row to a named CSV file."""

    def _write_csv(name: str, row: dict) -> Path:
        return _write_row(tmp_path / name, row)

    return _write_csv


@pytest.fixture
def pos_row() -> dict:
    return dict(POS_ROW)


@pytest.fixture
def atm_row() -> dict:
    return dict(ATM_ROW)


@pytest.fixture
def online_row() -> dict:
    return dict(ONLINE_ROW)


@pytest.fixture
def pos_csv(write_csv):
    return write_csv("pos_transactions.csv", POS_ROW)


@pytest.fixture
def pos_duplicate_csv(write_csv):
    """Second POS file repeating ``pos-1`` with a different amount."""
    return write_csv("pos_duplicate.csv", {**POS_ROW, "amount": "99.99"})


@pytest.fixture
def atm_csv(write_csv):
    return write_csv("atm_transactions.csv", ATM_ROW)


@pytest.fixture
def online_csv(write_csv):
    return write_csv("online_transactions.csv", ONLINE_ROW)


@pytest.fixture
def canonical_record() -> dict:
    """A fully valid canonical record used by the validation tests."""
    return {
        "transaction_id": "txn-1",
        "customer_id": "cust-1",
        "channel": "POS",
        "amount": 10.5,
        "currency": "USD",
        "timestamp": "2026-01-02T03:04:05",
        "merchant_id": "merch-1",
        "card_last4": "1234",
    }


# =============================================================================
# Analysis Test Fixtures
# =============================================================================

@pytest.fixture
def write_csv_analysis(tmp_path):
    """Return a helper for writing CSV files in analysis tests."""
    def _write_csv(path, df):
        if isinstance(df, list):
            path.write_text("\n".join(df) + "\n")
        else:
            df.to_csv(path, index=False)
        return path

    return _write_csv


# =============================================================================
# Shared Utilities
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensure test environment is properly set up before each test."""
    # Add any shared setup here if needed
    pass
