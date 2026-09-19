"""Fraud Relationships - how features differ between fraud and legitimate rows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import utils

MAX_CATEGORIES_SHOWN = 8


def run(csv_path: str) -> str:
    path = Path(csv_path)
    columns = utils.get_columns(path)

    if not utils.has_target(columns):
        return utils.missing_target_message("Fraud Relationships")

    sample = utils.read_sample(path)
    cat_cols, num_cols = utils.identify_categorical_numeric(sample, exclude=[utils.TARGET_COLUMN])
    usecols = cat_cols + num_cols + [utils.TARGET_COLUMN]
    df = utils.read_full(path, usecols=usecols)
    fraud_mask = df[utils.TARGET_COLUMN] == 1

    lines = [utils.section("Fraud Relationships")]

    lines.append("Categorical features - fraud rate by top categories:")
    if not cat_cols:
        lines.append("  No categorical/discrete columns were detected.")
    for col in cat_cols:
        counts = df[col].value_counts(dropna=False).head(MAX_CATEGORIES_SHOWN)
        lines.append(f"\n  {col}:")
        for value, count in counts.items():
            mask = df[col].isna() if pd.isna(value) else df[col] == value
            fraud_count = int((mask & fraud_mask).sum())
            lines.append(f"    - {value}: fraud rate {utils.pct(fraud_count, count)} (n={count:,})")

    lines.append("\nNumeric features - fraud vs legitimate comparison:")
    if not num_cols:
        lines.append("  No continuous numeric columns were detected.")
    for col in num_cols:
        fraud_vals = df.loc[fraud_mask, col].dropna()
        legit_vals = df.loc[~fraud_mask, col].dropna()
        if fraud_vals.empty or legit_vals.empty:
            lines.append(f"  {col}: not enough data in one of the two groups to compare.")
            continue
        lines.append(
            f"  {col}: fraud mean={fraud_vals.mean():.4f} / median={fraud_vals.median():.4f}"
            f"  |  legit mean={legit_vals.mean():.4f} / median={legit_vals.median():.4f}"
        )

    return "\n".join(lines)
