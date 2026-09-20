"""Canonical transaction model for normalized transaction data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields as dataclass_fields
from datetime import datetime
from typing import Any, Optional


@dataclass
class CanonicalTransaction:
    """
    Canonical representation of a single transaction.
    
    This model defines the contract for transaction data after ingestion and
    normalization. Downstream ML/analysis layers operate on CanonicalTransaction
    instances without knowledge of the source format.
    
    Attributes:
        transaction_id: Unique identifier for the transaction.
        customer_id: Identifier for the customer who initiated the transaction.
        channel: Transaction channel (e.g., 'POS', 'ATM', 'ONLINE_BANKING').
        amount: Transaction amount in currency units.
        currency: Currency code (e.g., 'USD', 'EUR').
        timestamp: ISO 8601 formatted timestamp of the transaction.
        location: Geographic location identifier (e.g., store ID, terminal ID).
        merchant_id: Identifier for the merchant (POS-only field).
        terminal_id: Identifier for the terminal (ATM/POS-only field).
        card_last4: Last 4 digits of the payment card (optional).
        card_type: Payment card type (e.g., 'VISA', 'MASTERCARD').
        payment_method: Payment method type (e.g., 'CHIP', 'SWIPE', 'CONTACTLESS').
        authorization_code: Authorization code from the payment processor.
        response_code: Transaction response code from the payment processor.
        response_time_seconds: Time to authorization in seconds.
        is_fraud: Ground truth fraud label (None until validated).
        raw_source_data: Original raw data from source (optional, for debugging).
    """
    
    transaction_id: str
    customer_id: str
    channel: str
    amount: float
    currency: str
    timestamp: str
    location: Optional[str] = None
    merchant_id: Optional[str] = None
    terminal_id: Optional[str] = None
    card_last4: Optional[str] = None
    card_type: Optional[str] = None
    payment_method: Optional[str] = None
    authorization_code: Optional[str] = None
    response_code: Optional[str] = None
    response_time_seconds: Optional[float] = None
    is_fraud: Optional[bool] = None
    raw_source_data: Optional[dict] = field(default=None, repr=False)

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        """Canonical field names in declaration order (the Phase 1 contract)."""
        return tuple(f.name for f in dataclass_fields(cls))

    @classmethod
    def from_dict(cls, record: Mapping[str, Any]) -> "CanonicalTransaction":
        """
        Build a transaction from a mapping, ignoring unknown keys.

        Adapters hand over plain dicts; anything outside the canonical contract
        (extra source columns, helper keys) is dropped here instead of leaking
        into the normalized layer.
        """
        known = set(cls.field_names())
        return cls(**{key: value for key, value in record.items() if key in known})

    def to_dict(self) -> dict[str, Any]:
        """Return the transaction as a plain dict in canonical field order."""
        return {name: getattr(self, name) for name in self.field_names()}