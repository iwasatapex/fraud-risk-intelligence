"""Outlier Analysis - IQR-based outlier counts for numeric features.

Reporting only - nothing here removes or modifies any values.
"""

from __future__ import annotations

from pathlib import Path

import utils

MAX_EXTREMES_SHOWN = 5


def run(csv_path: str) -> str:
    path = Path(csv_path)
    sample = utils.read_sample(path)
    _, num_cols = utils.identify_categorical_numeric(sample, exclude=[utils.TARGET_COLUMN])

    if not num_cols:
        return f"{utils.section('Outlier Analysis')}\nNo continuous numeric columns were detected."

    df = utils.read_full(path, usecols=num_cols)

    lines = [utils.section("Outlier Analysis")]
    lines.append("Method: IQR rule - values beyond Q1 - 1.5*IQR or Q3 + 1.5*IQR are flagged.\n")

    for col in num_cols:
        series = df[col].dropna()
        lines.append(f"{col}")
        if series.empty:
            lines.append("  No non-missing values.")
            lines.append("")
            continue

        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = series[(series < lower) | (series > upper)]
        count = len(outliers)

        lines.append(f"  bounds: [{lower:.4f}, {upper:.4f}]")
        lines.append(f"  outliers: {count:,} ({utils.pct(count, len(series))})")

        if count:
            median = series.median()
            extremes = outliers.reindex(
                outliers.sub(median).abs().sort_values(ascending=False).index
            )
            top_extremes = extremes.head(MAX_EXTREMES_SHOWN).tolist()
            lines.append(f"  most extreme values: {top_extremes}")
        lines.append("")

    return "\n".join(lines)
