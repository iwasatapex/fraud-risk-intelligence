"""Numeric Analysis - core descriptive statistics for continuous features."""

from __future__ import annotations

from pathlib import Path

import utils

QUANTILES = [0.05, 0.25, 0.75, 0.95]


def run(csv_path: str) -> str:
    path = Path(csv_path)
    sample = utils.read_sample(path)
    _, num_cols = utils.identify_categorical_numeric(sample, exclude=[utils.TARGET_COLUMN])

    if not num_cols:
        return f"{utils.section('Numeric Analysis')}\nNo continuous numeric columns were detected."

    df = utils.read_full(path, usecols=num_cols)

    lines = [utils.section("Numeric Analysis")]
    lines.append(f"Detected numeric columns: {', '.join(num_cols)}\n")

    for col in num_cols:
        series = df[col].dropna()
        n = len(series)
        lines.append(f"{col}")

        if n == 0:
            lines.append("  No non-missing values.")
            lines.append("")
            continue

        quantiles = series.quantile(QUANTILES)
        zero_count = int((series == 0).sum())
        neg_one_count = int((series == -1).sum())

        lines.append(f"  count: {n:,}")
        lines.append(f"  mean: {series.mean():.4f}")
        lines.append(f"  median: {series.median():.4f}")
        lines.append(f"  std: {series.std():.4f}")
        lines.append(f"  min: {series.min():.4f}")
        lines.append(f"  max: {series.max():.4f}")
        for q in QUANTILES:
            lines.append(f"  p{int(q * 100)}: {quantiles[q]:.4f}")
        lines.append(f"  zero count: {zero_count:,} ({utils.pct(zero_count, n)})")
        lines.append(f"  -1 count: {neg_one_count:,} ({utils.pct(neg_one_count, n)})")
        lines.append("")

    return "\n".join(lines)
