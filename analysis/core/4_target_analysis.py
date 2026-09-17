"""Target / Fraud Analysis - class balance for the fraud_bool label."""

from __future__ import annotations

from pathlib import Path

import utils


def run(csv_path: str) -> str:
    path = Path(csv_path)
    columns = utils.get_columns(path)

    if not utils.has_target(columns):
        return utils.missing_target_message("Target / Fraud Analysis")

    df = utils.read_full(path, usecols=[utils.TARGET_COLUMN])
    total = len(df)
    counts = df[utils.TARGET_COLUMN].value_counts(dropna=False).sort_index()

    lines = [utils.section("Target / Fraud Analysis")]
    lines.append(f"File: {path.name} ({total:,} rows)\n")

    lines.append("Class counts:")
    for value, count in counts.items():
        lines.append(f"  - {value}: {count:,} ({utils.pct(count, total)})")

    fraud_count = int((df[utils.TARGET_COLUMN] == 1).sum())
    legit_count = total - fraud_count

    lines.append(f"\nFraud rate: {utils.pct(fraud_count, total)}")
    lines.append(f"Legitimate rate: {utils.pct(legit_count, total)}")

    if fraud_count > 0:
        imbalance_ratio = legit_count / fraud_count
        lines.append(f"Class imbalance ratio (legitimate:fraud): {imbalance_ratio:.1f} : 1")
    else:
        lines.append("Class imbalance ratio: undefined (no positive/fraud cases found).")

    return "\n".join(lines)
