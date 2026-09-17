"""Data Quality - missingness, duplicates, constant columns, sentinel/odd values."""

from __future__ import annotations

from pathlib import Path

import utils


def run(csv_path: str) -> str:
    path = Path(csv_path)
    df = utils.read_full(path)
    n = len(df)

    lines = [utils.section("Data Quality")]
    lines.append(f"File: {path.name} ({n:,} rows, {len(df.columns)} columns)")

    # Missing values (NaN)
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    lines.append("\nMissing values (NaN):")
    if missing.empty:
        lines.append("  None found.")
    else:
        for col, count in missing.items():
            lines.append(f"  - {col}: {count:,} ({utils.pct(count, n)})")

    # Duplicate rows
    dup_count = int(df.duplicated().sum())
    lines.append(f"\nDuplicate rows: {dup_count:,} ({utils.pct(dup_count, n)})")

    # Constant columns
    constant_cols = [c for c in df.columns if df[c].nunique(dropna=False) <= 1]
    lines.append("\nConstant columns (single unique value):")
    if constant_cols:
        for c in constant_cols:
            lines.append(f"  - {c}")
    else:
        lines.append("  None found.")

    # -1 sentinel values (common "missing" marker in fraud datasets like this one)
    lines.append("\nColumns containing -1 values (common missing-value sentinel):")
    found_neg_one = False
    for col in df.select_dtypes(include="number").columns:
        neg_count = int((df[col] == -1).sum())
        if neg_count:
            found_neg_one = True
            lines.append(f"  - {col}: {neg_count:,} ({utils.pct(neg_count, n)})")
    if not found_neg_one:
        lines.append("  None found.")

    # Other negative values - a light heuristic for "unusual" values, since
    # what counts as invalid is domain-specific and -1 is already handled above.
    lines.append("\nOther negative values (excluding the -1 sentinel above):")
    found_other_negative = False
    for col in df.select_dtypes(include="number").columns:
        neg_mask = (df[col] < 0) & (df[col] != -1)
        neg_count = int(neg_mask.sum())
        if neg_count:
            found_other_negative = True
            lines.append(f"  - {col}: {neg_count:,} ({utils.pct(neg_count, n)})")
    if not found_other_negative:
        lines.append("  None found.")

    # Basic warnings
    warnings = []
    high_missing = missing[missing / n > 0.5] if n else missing
    if not high_missing.empty:
        warnings.append(f"{len(high_missing)} column(s) have over 50% missing values.")
    if constant_cols:
        warnings.append(f"{len(constant_cols)} column(s) are constant and add no information.")
    if dup_count:
        warnings.append(f"{dup_count:,} duplicate row(s) present.")

    lines.append("\nWarnings:")
    if warnings:
        for w in warnings:
            lines.append(f"  - {w}")
    else:
        lines.append("  None.")

    return "\n".join(lines)
