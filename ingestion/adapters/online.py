"""Online Banking source adapter."""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..exceptions import NormalizationError, ValidationError
from ..validation import to_number, to_text
from .base import BaseSourceAdapter


class OnlineBankingAdapter(BaseSourceAdapter):
    """
    Adapter for online / mobile banking transaction data.

    Expected source schema (CSV columns):
        transaction_id, customer_id, amount, currency, timestamp, merchant_id,
        card_last4, card_type, merchant_category, channel, transaction_status
    """

    _source_name = "online"
    _required_columns = [
        "transaction_id", "customer_id", "amount", "currency", "timestamp",
        "merchant_id", "card_last4", "card_type", "merchant_category", "channel",
        "transaction_status",
    ]

    def normalize(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Normalize online banking rows into canonical records.

        The canonical channel is ``ONLINE_BANKING``; the source ``channel`` column
        (e.g. WEB, MOBILE_APP) maps to ``payment_method`` and
        ``transaction_status`` maps to ``response_code``. Online traffic has no
        terminal or physical location, so those fields stay ``None``.

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
                    "channel": "ONLINE_BANKING",
                    "amount": to_number(row["amount"], field_name="amount"),
                    "currency": to_text(row["currency"]),
                    "timestamp": to_text(row["timestamp"]),
                    "location": None,
                    "merchant_id": to_text(row["merchant_id"]),
                    "terminal_id": None,
                    "card_last4": to_text(row["card_last4"]),
                    "card_type": to_text(row["card_type"]),
                    "payment_method": to_text(row["channel"]),
                    "authorization_code": None,
                    "response_code": to_text(row["transaction_status"]),
                }
            except ValidationError as exc:
                raise NormalizationError(f"Row {index} could not be normalized: {exc}", source=self.name) from exc
            records.append(self.build_record(record, raw_row=row))

        return records

    def get_required_columns(self) -> list[str]:
        """Return the required source column names."""
        return list(self._required_columns)