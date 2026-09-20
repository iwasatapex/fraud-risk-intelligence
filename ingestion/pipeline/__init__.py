"""
Ingestion pipeline orchestration.

This is the only place that knows the full Phase 1 flow::

    read source -> normalize -> validate -> deduplicate -> report

``IngestionPipeline`` wires the source adapters to the canonical contract
(``ingestion.validation``) and produces an ``IngestionReport`` that can be turned
into a canonical DataFrame/CSV for downstream feature engineering and modeling.

Example:
    from ingestion.pipeline import run_ingestion, write_canonical_csv

    report = run_ingestion({"pos": "data/pos_transactions.csv", "atm": "data/atm.csv"})
    frame = report.to_frame()
    write_canonical_csv(report.records, "data/canonical_transactions.csv")
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any

import pandas as pd

from ..adapters import ATMAdapter, BaseSourceAdapter, OnlineBankingAdapter, POSAdapter
from ..exceptions import AdapterError, IngestionError
from ..models.transaction import CanonicalTransaction
from ..validation import (
    InvalidRecord,
    ValidationResult,
    assert_required_columns,
    validate_records,
)

#: Adapters registered by default, keyed by the source name they handle.
DEFAULT_ADAPTERS: dict[str, type[BaseSourceAdapter]] = {
    "pos": POSAdapter,
    "atm": ATMAdapter,
    "online": OnlineBankingAdapter,
}


def detect_adapter(
    source_path: str | Path,
    adapters: Mapping[str, type[BaseSourceAdapter]] | None = None,
) -> str:
    """
    Guess which registered adapter handles a file, e.g. ``pos_2024-05.csv`` -> ``"pos"``.

    Raises:
        AdapterError: If no registered adapter name appears in the file name.
    """
    registry = DEFAULT_ADAPTERS if adapters is None else adapters
    haystack = Path(source_path).stem.lower()
    for key in registry:
        if key in haystack:
            return key
    raise AdapterError(
        f"Could not determine an adapter for '{Path(source_path).name}'. "
        f"Pass adapter=... explicitly (registered: {', '.join(sorted(registry))})."
    )


@dataclass(frozen=True)
class SourceSpec:
    """One source file to ingest."""

    path: Path
    name: str
    adapter: str | None = None

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        adapter: str | None = None,
        name: str | None = None,
    ) -> "SourceSpec":
        """Build a spec from a path, defaulting the reporting name to the file stem."""
        resolved = Path(path)
        return cls(path=resolved, name=name or resolved.stem, adapter=adapter)


@dataclass
class SourceResult:
    """Ingestion outcome for a single source file."""

    name: str
    path: Path
    adapter: str
    rows_read: int = 0
    result: ValidationResult = dc_field(default_factory=ValidationResult)
    duplicates_removed: int = 0
    error: IngestionError | None = None

    @property
    def ok(self) -> bool:
        """True when the source was read, normalized and validated without error."""
        return self.error is None

    @property
    def valid(self) -> list[CanonicalTransaction]:
        """Canonical transactions accepted from this source."""
        return self.result.valid

    @property
    def invalid(self) -> list[InvalidRecord]:
        """Records rejected from this source."""
        return self.result.invalid

    def summary(self) -> str:
        """One line summary suitable for logs and reports."""
        status = "ok" if self.ok else "FAILED"
        line = (
            f"{self.name} ({self.adapter}): {status}, {self.rows_read} row(s) read, "
            f"{len(self.valid)} valid, {len(self.invalid)} invalid"
        )
        if self.duplicates_removed:
            line += f", {self.duplicates_removed} duplicate(s) dropped"
        if self.error is not None:
            line += f" - {self.error}"
        return line


@dataclass
class IngestionReport:
    """Aggregated result of one pipeline run."""

    sources: list[SourceResult] = dc_field(default_factory=list)
    records: list[CanonicalTransaction] = dc_field(default_factory=list)
    duplicates_removed: int = 0

    @property
    def total_read(self) -> int:
        """Number of source rows read across every source."""
        return sum(source.rows_read for source in self.sources)

    @property
    def invalid(self) -> list[InvalidRecord]:
        """Every rejected record across all sources."""
        return [record for source in self.sources for record in source.invalid]

    @property
    def failed_sources(self) -> list[SourceResult]:
        """Sources that could not be read or normalized."""
        return [source for source in self.sources if not source.ok]

    @property
    def ok(self) -> bool:
        """True when no source failed and no record was rejected."""
        return not self.failed_sources and not self.invalid

    def to_frame(self) -> pd.DataFrame:
        """Canonical transaction DataFrame (columns in declaration order)."""
        return canonical_frame(self.records)

    def summary(self) -> str:
        """Multi-line summary with one line per source."""
        lines = [
            f"Ingestion report: {len(self.records)} canonical record(s) from "
            f"{len(self.sources)} source(s), {self.total_read} row(s) read"
        ]
        lines.extend(f"  - {source.summary()}" for source in self.sources)
        if self.duplicates_removed:
            lines.append(f"  duplicates removed: {self.duplicates_removed}")
        if self.invalid:
            lines.append(f"  invalid records: {len(self.invalid)}")
        if self.failed_sources:
            lines.append(f"  failed sources: {len(self.failed_sources)}")
        return "\n".join(lines)


class IngestionPipeline:
    """
    Orchestrates ingestion for one or more source files.

    Args:
        adapters: Registry mapping a source name to an adapter class; defaults to
            ``DEFAULT_ADAPTERS`` (pos/atm/online).
        dedupe: Drop records whose ``transaction_id`` was already seen in this run.
        strict: Reject canonical records that carry unknown fields.
        allow_negative_amount: Permit negative amounts (refunds).
        raise_on_error: Raise the first source/validation error instead of
            collecting it in the report.

    Example:
        pipeline = IngestionPipeline()
        report = pipeline.run({"pos": "data/pos.csv"})
        report.to_frame()
    """

    def __init__(
        self,
        adapters: Mapping[str, type[BaseSourceAdapter]] | None = None,
        *,
        dedupe: bool = True,
        strict: bool = False,
        allow_negative_amount: bool = False,
        raise_on_error: bool = False,
    ) -> None:
        self.adapters: dict[str, type[BaseSourceAdapter]] = dict(
            DEFAULT_ADAPTERS if adapters is None else adapters
        )
        self.dedupe = dedupe
        self.strict = strict
        self.allow_negative_amount = allow_negative_amount
        self.raise_on_error = raise_on_error

    def register(self, key: str, adapter: type[BaseSourceAdapter]) -> None:
        """Register (or replace) an adapter class under ``key``."""
        if not isinstance(adapter, type) or not issubclass(adapter, BaseSourceAdapter):
            raise AdapterError(f"{adapter!r} is not a BaseSourceAdapter subclass.", adapter_name=key)
        self.adapters[key.lower()] = adapter

    def adapter_for(self, spec: SourceSpec) -> tuple[str, BaseSourceAdapter]:
        """Return the registry key and a fresh adapter instance for ``spec``."""
        key = (spec.adapter or detect_adapter(spec.path, self.adapters)).lower()
        adapter_cls = self.adapters.get(key)
        if adapter_cls is None:
            raise AdapterError(
                f"Unknown adapter '{key}'. Registered adapters: {', '.join(sorted(self.adapters))}.",
                adapter_name=key,
            )
        return key, adapter_cls()

    def ingest(
        self,
        source: str | Path | SourceSpec,
        *,
        adapter: str | None = None,
        name: str | None = None,
    ) -> SourceResult:
        """
        Ingest a single source file.

        Failures are captured in ``SourceResult.error`` unless ``raise_on_error``
        is set, so one bad file never hides the good ones.

        Args:
            source: Path to the source file, or a pre-built ``SourceSpec``.
            adapter: Registry key forcing a specific adapter.
            name: Reporting name (defaults to the file stem).
        """
        spec = source if isinstance(source, SourceSpec) else SourceSpec.from_path(source, adapter=adapter, name=name)
        key, adapter_instance = self.adapter_for(spec)
        outcome = SourceResult(name=spec.name, path=spec.path, adapter=key)
        try:
            frame = adapter_instance.read(spec.path)
            outcome.rows_read = len(frame)
            assert_required_columns(frame.columns, adapter_instance.required_columns, source=adapter_instance.name)
            records = adapter_instance.normalize(frame)
            outcome.result = validate_records(
                records,
                source=adapter_instance.name,
                allow_negative_amount=self.allow_negative_amount,
                strict=self.strict,
                raise_on_error=self.raise_on_error,
            )
        except Exception as exc:  # noqa: BLE001 - collected into the report
            error = (
                exc
                if isinstance(exc, IngestionError)
                else AdapterError(f"{type(exc).__name__}: {exc}", adapter_name=key, source=str(spec.path))
            )
            outcome.error = error
            if self.raise_on_error:
                raise error
        return outcome

    def run(
        self,
        sources: Mapping[str, str | Path] | Iterable[str | Path | SourceSpec | tuple[str | Path, str]],
    ) -> IngestionReport:
        """
        Ingest every source and return the aggregated report.

        Args:
            sources: Mapping of reporting name -> path, or an iterable of paths,
                ``SourceSpec`` objects or ``(path, adapter_key)`` tuples.

        Returns:
            IngestionReport with deduplicated canonical records and per-source stats.
        """
        report = IngestionReport(sources=[self.ingest(spec) for spec in self._build_specs(sources)])

        seen: set[str] = set()
        for source_result in report.sources:
            for record in source_result.valid:
                if self.dedupe and record.transaction_id in seen:
                    source_result.duplicates_removed += 1
                    report.duplicates_removed += 1
                    continue
                seen.add(record.transaction_id)
                report.records.append(record)
        return report

    def _build_specs(self, sources: Any) -> list[SourceSpec]:
        """Normalize the accepted ``sources`` shapes into ``SourceSpec`` objects."""
        if isinstance(sources, Mapping):
            return [SourceSpec.from_path(path, name=str(name)) for name, path in sources.items()]

        specs: list[SourceSpec] = []
        for item in sources:
            if isinstance(item, SourceSpec):
                specs.append(item)
            elif isinstance(item, tuple) and len(item) == 2:
                specs.append(SourceSpec.from_path(item[0], adapter=item[1]))
            elif isinstance(item, (str, Path)):
                specs.append(SourceSpec.from_path(item))
            else:
                raise AdapterError(f"Unsupported source specification: {item!r}")
        return specs


def canonical_frame(records: Iterable[CanonicalTransaction]) -> pd.DataFrame:
    """Build a DataFrame whose columns are the canonical fields, in order."""
    return pd.DataFrame(
        [record.to_dict() for record in records],
        columns=list(CanonicalTransaction.field_names()),
    )


def write_canonical_csv(
    records: Iterable[CanonicalTransaction],
    output_path: str | Path,
    *,
    index: bool = False,
) -> Path:
    """Write canonical records to CSV, creating parent directories as needed."""
    path = Path(output_path)
    if str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)
    canonical_frame(records).to_csv(path, index=index)
    return path


def run_ingestion(sources: Any, **kwargs: Any) -> IngestionReport:
    """One-shot helper: build an ``IngestionPipeline`` with ``kwargs`` and run it."""
    return IngestionPipeline(**kwargs).run(sources)


__all__ = [
    "DEFAULT_ADAPTERS",
    "IngestionPipeline",
    "IngestionReport",
    "SourceResult",
    "SourceSpec",
    "canonical_frame",
    "detect_adapter",
    "run_ingestion",
    "write_canonical_csv",
]