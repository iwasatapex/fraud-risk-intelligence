"""Leakage Checks - heuristic scan for possible target leakage.

Everything reported here is a POTENTIAL risk to investigate manually, not
confirmed leakage - these are simple statistical heuristics, not proof.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import utils

HIGH_CORRELATION_THRESHOLD = 0.9
MIN_CATEGORY_SIZE = 30  # ignore tiny categories - not statistically meaningful

# A category is flagged only if it is BOTH a majority-fraud group in
# absolute terms AND far above the dataset's own baseline fraud rate.
# Fraud is a rare-event problem (often 1-5% overall), so a fixed absolute
# cutoff like "fraud rate >= 95%" would flag almost every category once the
# baseline itself is low - comparing against the baseline avoids that.
MIN_ABSOLUTE_FRAUD_RATE = 0.3
MIN_LIFT_OVER_BASELINE = 5.0


def run(csv_path: str) -> str:
    path = Path(csv_path)
    columns = utils.get_columns(path)

    if not utils.has_target(columns):
        return utils.missing_target_message("Leakage Checks")

    sample = utils.read_sample(path)
    cat_cols, num_cols = utils.identify_categorical_numeric(sample, exclude=[utils.TARGET_COLUMN])
    usecols = cat_cols + num_cols + [utils.TARGET_COLUMN]
    df = utils.read_full(path, usecols=usecols)
    target = df[utils.TARGET_COLUMN].astype(float)

    findings: list[str] = []

    # Constant features carry no signal - also sometimes a sign of a broken
    # join or an over-filtered export, worth flagging during a leakage pass.
    constant_cols = [c for c in cat_cols + num_cols if df[c].nunique(dropna=False) <= 1]
    if constant_cols:
        findings.append(f"Constant feature(s), no predictive value: {', '.join(constant_cols)}")

    # Numeric features very strongly correlated with the target.
    if num_cols:
        correlations = df[num_cols].corrwith(target).abs().sort_values(ascending=False)
        for col, corr in correlations.items():
            if pd.notna(corr) and corr > HIGH_CORRELATION_THRESHOLD:
                findings.append(
                    f"'{col}' correlates with the target at |r|={corr:.3f} - unusually "
                    "strong for a feature that should be known before the fraud decision."
                )

    # Categorical features where one category is a majority-fraud group that
    # is also far above this dataset's own baseline fraud rate.
    overall_fraud_rate = float(target.mean())
    for col in cat_cols:
        counts = df[col].value_counts(dropna=False)
        for value, count in counts.items():
            if count < MIN_CATEGORY_SIZE:
                continue
            mask = df[col].isna() if pd.isna(value) else df[col] == value
            fraud_rate = float((df.loc[mask, utils.TARGET_COLUMN] == 1).mean())
            lift = (fraud_rate / overall_fraud_rate) if overall_fraud_rate > 0 else float("inf")
            if fraud_rate >= MIN_ABSOLUTE_FRAUD_RATE and lift >= MIN_LIFT_OVER_BASELINE:
                findings.append(
                    f"'{col}' = {value!r} (n={count:,}) has a fraud rate of {fraud_rate * 100:.2f}%"
                    f" - {lift:.1f}x this dataset's baseline of {overall_fraud_rate * 100:.2f}%. "
                    "Check whether this value could only be set after a fraud decision was made."
                )

    # Duplicate numeric columns - a cheap fingerprint on the first 200 rows,
    # flagged as "near-duplicate" since it's a practical check, not exhaustive.
    seen: dict[tuple, str] = {}
    for col in num_cols:
        key = tuple(df[col].fillna(-999999).head(200).tolist())
        if key in seen:
            findings.append(
                f"'{col}' looks identical to '{seen[key]}' across the first 200 rows - "
                "check whether it's a duplicate or derived copy of the same signal."
            )
        else:
            seen[key] = col

    # Suspicious temporal relationships - a large jump in fraud rate between
    # consecutive periods can indicate a labeling or data-collection artifact.
    temporal_cols = utils.detect_temporal_columns(columns, sample=sample)
    if temporal_cols:
        temporal_col = temporal_cols[0]
        df_t = utils.read_full(path, usecols=[temporal_col, utils.TARGET_COLUMN])
        period_rates = df_t.groupby(temporal_col, dropna=False)[utils.TARGET_COLUMN].mean().sort_index()
        if len(period_rates) > 1:
            jumps = period_rates.pct_change().abs()
            for period, jump in jumps.items():
                if pd.notna(jump) and jump > 4:  # rate more than 4x'd or dropped ~80%+
                    findings.append(
                        f"Fraud rate in '{temporal_col}' shifts sharply at period {period} "
                        f"({jump * 100:.0f}% relative change) - worth checking for a "
                        "labeling or data-collection artifact around that period."
                    )

    lines = [utils.section("Leakage Checks")]
    lines.append("These are potential risks worth investigating manually, not confirmed leakage.\n")

    if findings:
        for f in findings:
            lines.append(f"  - {f}")
    else:
        lines.append("  No obvious leakage signals found by these heuristics.")

    return "\n".join(lines)
