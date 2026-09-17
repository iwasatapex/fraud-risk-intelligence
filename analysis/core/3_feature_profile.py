"""Feature Profile - one summary per column: type, uniqueness, missingness, stats."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import utils


def run(csv_path: str) -> str:
    path = Path(csv_path)
    df = utils.read_full(path)
    n = len(df)

    lines = [utils.section("Feature Profile")]
    lines.append(f"File: {path.name} ({n:,} rows, {len(df.columns)} columns)\n")

    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())

        lines.append(f"{col}")
        lines.append(f"  dtype: {series.dtype}")
        lines.append(f"  unique values: {series.nunique(dropna=True):,}")
        lines.append(f"  missing: {missing:,} ({utils.pct(missing, n)})")

        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            non_null = series.dropna()
            if non_null.empty:
                lines.append("  numeric stats: no non-missing values")
            else:
                lines.append(
                    "  numeric stats: "
                    f"mean={non_null.mean():.4f}, std={non_null.std():.4f}, "
                    f"min={non_null.min():.4f}, max={non_null.max():.4f}"
                )
        else:
            cardinality = series.nunique(dropna=True)
            lines.append(f"  categorical cardinality: {cardinality:,} categories")
            top = series.value_counts(dropna=True).head(1)
            if not top.empty:
                lines.append(f"  most common value: {top.index[0]!r} ({top.iloc[0]:,} rows)")

        lines.append("")  # spacer between features

    return "\n".join(lines)
