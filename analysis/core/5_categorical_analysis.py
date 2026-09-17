"""Categorical Analysis - distribution and fraud rate per category.

Output is capped per column so a high-cardinality field (e.g. an ID-like
column) never floods the terminal.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import utils

MAX_CATEGORIES_SHOWN = 15


def run(csv_path: str) -> str:
    path = Path(csv_path)
    columns = utils.get_columns(path)

    sample = utils.read_sample(path)
    cat_cols, _ = utils.identify_categorical_numeric(sample, exclude=[utils.TARGET_COLUMN])

    if not cat_cols:
        return f"{utils.section('Categorical Analysis')}\nNo categorical/discrete columns were detected."

    has_target = utils.has_target(columns)
    usecols = cat_cols + ([utils.TARGET_COLUMN] if has_target else [])
    df = utils.read_full(path, usecols=usecols)
    total = len(df)

    lines = [utils.section("Categorical Analysis")]
    lines.append(f"Detected categorical columns: {', '.join(cat_cols)}\n")

    for col in cat_cols:
        counts = df[col].value_counts(dropna=False)
        n_categories = len(counts)
        lines.append(f"{col} ({n_categories:,} categories)")

        shown = counts.head(MAX_CATEGORIES_SHOWN)
        for value, count in shown.items():
            if pd.isna(value):
                mask = df[col].isna()
                display_value = "<missing>"
            else:
                mask = df[col] == value
                display_value = value

            row = f"  - {display_value}: {count:,} ({utils.pct(count, total)})"
            if has_target:
                fraud_count = int((df.loc[mask, utils.TARGET_COLUMN] == 1).sum())
                row += f" | fraud rate: {utils.pct(fraud_count, count)}"
            lines.append(row)

        remaining = n_categories - len(shown)
        if remaining > 0:
            lines.append(f"  ... {remaining:,} more categories not shown")
        lines.append("")

    return "\n".join(lines)
