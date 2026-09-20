"""ATM (Automated Teller Machine) source adapter."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..exceptions import NormalizationError, ValidationError
from ..validation import to_number, to_text
from .base import BaseSourceAdapter


class ATMAdapter(BaseSourceAdapter):
    """
    Adapter for ATM transaction data.

    Expected source schema (CSV columns):
        transaction_id, customer_id, amount, currency, timestamp, terminal_id,
        card_last4, card_type, transaction_type, response_code
    """

    _source_name = "atm"
    _required_columns = [
        "transaction_id", "customer_id", "amount", "currency", "timestamp",
        "terminal_id", "card_last4", "card_type", "transaction_type", "response_code",
    ]

    def normalize(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Normalize ATM rows into canonical records (channel ``ATM``).

        ``transaction_type`` (e.g. CASH_WITHDRAWAL) maps to ``payment_method``;
        ATM data carries no authorization code, so that field stays ``None``.

        Raises:
            SchemaError: If required columns are missing.
            NormalizationError: If a row cannot be converted.
        """
        self.check_required_columns(df)

        records: list[dict[str, Any]] = []
        for index, row in df.iterrows():
            try:
                record = {
                    "transaction_id": to_text(row["transaction_id"]),
                    "customer_id": to_text(row["customer_id"]),
                    "channel": "ATM",
                    "amount": to_number(row["amount"], field_name="amount"),
                    "currency": to_text(row["currency"]),
                    "timestamp": to_text(row["timestamp"]),
                    "location": None,
                    "merchant_id": None,
                    "terminal_id": to_text(row["terminal_id"]),
                    "card_last4": to_text(row["card_last4"]),
                    "card_type": to_text(row["card_type"]),
                    "payment_method": to_text(row["transaction_type"]),
                    "authorization_code": None,
                    "response_code": to_text(row["response_code"]),
                }
            except ValidationError as exc:
                raise NormalizationError(f"Row {index} could not be normalized: {exc}", source=self.name) from exc
            records.append(self.build_record(record, raw_row=row))

        return records

    def get_required_columns(self) -> list[str]:
        """Return the required source column names."""
        return list(self._required_columns)