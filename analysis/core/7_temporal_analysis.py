"""Temporal Analysis - period-level counts and fraud rates over time.

Temporal columns are detected by name (month, date, day, year, period,
time) - this makes no modeling decisions, it only summarizes what's there.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import utils


def run(csv_path: str) -> str:
    path = Path(csv_path)
    columns = utils.get_columns(path)
    sample = utils.read_sample(path)
    temporal_cols = utils.detect_temporal_columns(columns, sample=sample)

    if not temporal_cols:
        return f"{utils.section('Temporal Analysis')}\nNo likely temporal columns were detected by name."

    has_target = utils.has_target(columns)
    usecols = temporal_cols + ([utils.TARGET_COLUMN] if has_target else [])
    df = utils.read_full(path, usecols=usecols)
    total = len(df)

    lines = [utils.section("Temporal Analysis")]
    lines.append(f"Detected temporal column(s): {', '.join(temporal_cols)}\n")

    for col in temporal_cols:
        periods = df[col].value_counts(dropna=False).sort_index()
        lines.append(f"{col} ({periods.shape[0]:,} unique periods)")

        for period, count in periods.items():
            row = f"  - {period}: {count:,} rows ({utils.pct(count, total)})"
            if has_target:
                mask = df[col].isna() if pd.isna(period) else df[col] == period
                fraud_count = int((df.loc[mask, utils.TARGET_COLUMN] == 1).sum())
                row += f" | fraud rate: {utils.pct(fraud_count, count)}"
            lines.append(row)

        try:
            is_increasing = df[col].is_monotonic_increasing
            is_decreasing = df[col].is_monotonic_decreasing
        except TypeError:
            is_increasing = is_decreasing = False

        if is_increasing or is_decreasing:
            direction = "increasing" if is_increasing else "decreasing"
            lines.append(f"  Row order appears sorted by {col} ({direction}).")
        else:
            lines.append(f"  Row order does not appear sorted by {col}.")
        lines.append("")

    return "\n".join(lines)
