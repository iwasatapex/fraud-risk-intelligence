"""Base adapter class and shared helpers for source data ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import pandas as pd

from ..exceptions import AdapterError, SchemaError
from ..validation import to_text


@runtime_checkable
class SourceAdapter(Protocol):
    """Structural type that every source adapter satisfies."""

    @property
    def name(self) -> str:
        """Short uppercase adapter label, e.g. "POS" or "ONLINE_BANKING"."""
        ...

    @property
    def required_columns(self) -> list[str]:
        """Columns that must exist in the source data."""
        ...

    def read(self, source_path: str | Path) -> pd.DataFrame:
        """Read raw source data into a DataFrame."""
        ...

    def normalize(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Convert raw rows into canonical transaction dicts."""
        ...


class BaseSourceAdapter(ABC):
    """
    Abstract base class for source data adapters.

    An adapter owns exactly one source format: it reads the raw file and maps it
    onto the Phase 1 canonical contract (``ingestion.models.CanonicalTransaction``).
    Subclasses declare ``_source_name``/``_required_columns`` and implement
    ``normalize``.
    """

    #: Short lowercase identifier used to register the adapter (e.g. "pos").
    _source_name: str = ""
    #: Columns that must be present in the source data.
    _required_columns: list[str] = []

    def __init__(self, *, include_raw: bool = False) -> None:
        #: When True every record carries its original source row in
        #: ``CanonicalTransaction.raw_source_data``. Off by default so large
        #: ingestions stay memory friendly.
        self.include_raw = include_raw

    @property
    def name(self) -> str:
        """Short uppercase adapter label, e.g. "POS" or "ONLINE_BANKING"."""
        if not self._source_name:
            raise AdapterError("Adapter does not define a source name.", adapter_name=type(self).__name__)
        return self._source_name.upper()

    @property
    def required_columns(self) -> list[str]:
        """Copy of the source columns this adapter depends on."""
        return list(self.get_required_columns())

    def read(self, source_path: str | Path) -> pd.DataFrame:
        """
        Read a CSV source file into a DataFrame.

        This is the default (CSV) implementation; subclasses override it for other
        source formats.

        Raises:
            FileNotFoundError: If the path does not exist.
            AdapterError: If the path is a directory or the file cannot be parsed.
        """
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        if not path.is_file():
            raise AdapterError(f"Expected a file but got a directory: {path}", adapter_name=self.name)
        try:
            # Read everything as text: identifiers such as card_last4/response_code
            # must keep leading zeros, and adapters coerce scalars themselves.
            return pd.read_csv(path, dtype=str)
        except Exception as exc:  # noqa: BLE001 - re-raised with adapter context
            raise AdapterError(f"Could not read CSV file '{path.name}': {exc}", adapter_name=self.name) from exc

    def check_required_columns(self, df: pd.DataFrame) -> None:
        """Raise SchemaError when the source frame is missing required columns."""
        missing = [column for column in self.required_columns if column not in df.columns]
        if missing:
            raise SchemaError(
                f"Source data is missing required column(s): {', '.join(missing)}",
                expected_fields=self.required_columns,
                missing_fields=missing,
                source=self.name,
            )

    def build_record(self, record: dict[str, Any], raw_row: pd.Series | None = None) -> dict[str, Any]:
        """Return the canonical record, optionally attaching the raw source row."""
        if self.include_raw and raw_row is not None:
            return {**record, "raw_source_data": {str(key): to_text(value) for key, value in raw_row.items()}}
        return record

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """
        Convert a raw source frame into canonical transaction dicts.

        Raises:
            SchemaError: If required columns are missing.
            NormalizationError: If a row cannot be converted.
        """
        raise NotImplementedError

    @abstractmethod
    def get_required_columns(self) -> list[str]:
        """Return the required source column names for this adapter."""
        raise NotImplementedError