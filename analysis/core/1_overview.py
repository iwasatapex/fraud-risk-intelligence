"""Dataset Overview - cheap structural summary without loading the full file."""

from __future__ import annotations

from pathlib import Path

import utils


def run(csv_path: str) -> str:
    path = Path(csv_path)
    columns = utils.get_columns(path)
    row_count = utils.count_rows_fast(path)
    sample = utils.read_sample(path, n=5000)

    lines = [utils.section("Dataset Overview")]
    lines.append(f"File: {path.name}")
    lines.append(f"Rows: {row_count:,}")
    lines.append(f"Columns: {len(columns)}")

    lines.append("\nColumn names:")
    for col in columns:
        lines.append(f"  - {col}")

    lines.append("\nInferred data types (from a 5,000-row sample):")
    for col in columns:
        dtype = sample[col].dtype if col in sample.columns else "unknown"
        lines.append(f"  - {col}: {dtype}")

    sample_kb = sample.memory_usage(deep=True).sum() / 1024
    lines.append(f"\nSample memory footprint ({len(sample):,} rows): {sample_kb:.1f} KB")
    lines.append(
        "Note: row/column counts and column names are exact; data types are "
        "inferred from a sample to avoid loading the full file."
    )

    return "\n".join(lines)
