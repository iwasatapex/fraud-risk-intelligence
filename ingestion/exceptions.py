from __future__ import annotations

import typing
from typing import Any

class IngestionError(Exception):
    """
    Base exception for all ingestion-related errors.

    ``source`` optionally records where the failure came from (source label or
    file name) and is rendered as a prefix by ``str()``.
    """

    def __init__(self, message: str, *, source: str | None = None) -> None:
        super().__init__(message)
        self.source = source

    def __str__(self) -> str:
        message = super().__str__()
        return message if self.source is None else f"[{self.source}] {message}"


class ValidationError(IngestionError):
    """Raised when a single record or field value fails validation."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        value: Any | None = None,
        source: str | None = None,
    ) -> None:
        self.field = field
        self.value = value
        super().__init__(message if field is None else f"Field '{field}': {message}", source=source)


class AdapterError(IngestionError):
    """Raised when an adapter fails to read or normalize source data."""

    def __init__(
        self,
        message: str,
        *,
        adapter_name: str | None = None,
        source: str | None = None,
    ) -> None:
        self.adapter_name = adapter_name
        super().__init__(
            message if adapter_name is None else f"Adapter '{adapter_name}': {message}",
            source=source,
        )


class SchemaError(IngestionError):
    """Raised when source data does not match the expected schema."""

    def __init__(
        self,
        message: str,
        *,
        expected_fields: list[str] | None = None,
        missing_fields: list[str] | None = None,
        source: str | None = None,
    ) -> None:
        self.expected_fields = expected_fields
        self.missing_fields = missing_fields
        super().__init__(message, source=source)


class NormalizationError(IngestionError):
    """Raised when a raw source row cannot be converted to the canonical shape."""

    def __init__(
        self,
        message: str,
        *,
        column: str | None = None,
        source: str | None = None,
    ) -> None:
        self.column = column
        super().__init__(message if column is None else f"Column '{column}': {message}", source=source)