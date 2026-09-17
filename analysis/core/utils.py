"""
Shared helpers for the fraud-risk-intelligence dataset analysis CLI.

Kept deliberately small and dependency-free (pandas + stdlib only). Every
analysis module imports this file for dataset discovery, memory-friendly
reading, and simple text formatting.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

TARGET_COLUMN = "fraud_bool"

# Whole-word tokens (split on non-alphanumerics) that suggest a temporal
#/period column. Matched as whole tokens, not substrings, so "month"
# doesn't also match inside "prev_address_months_count".
_TEMPORAL_TOKENS = {
    "month", "months", "date", "dates", "day", "days",
    "year", "years", "period", "periods", "time", "times", "timestamp",
}
# Tokens that strongly suggest a duration/count field rather than a period
# label, even if a temporal word also appears (e.g. "address_months_count").
_TEMPORAL_DENYLIST_TOKENS = {"count", "counts", "amount", "amounts"}

# A genuine calendar-style period column rarely has more than this many
# distinct values in a single dataset - used to reject count-like columns
# that slip past the token check.
TEMPORAL_MAX_CARDINALITY = 60

# A numeric column with this many or fewer unique values is treated as
# categorical/discrete rather than continuous (flags, coded types, etc).
CATEGORICAL_UNIQUE_THRESHOLD = 20


def discover_csv_files(dataset_dir: Path) -> list[Path]:
    """Return all .csv files directly inside dataset_dir, sorted by name."""
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
    if not dataset_dir.is_dir():
        raise NotADirectoryError(f"Expected a directory, got a file: {dataset_dir}")

    files = sorted(p for p in dataset_dir.glob("*.csv") if p.is_file())
    if not files:
        raise FileNotFoundError(f"No CSV files found in {dataset_dir}")
    return files


def get_columns(csv_path: Path) -> list[str]:
    """Read only the header row - cheap even for a huge file."""
    try:
        header = pd.read_csv(csv_path, nrows=0)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as-is
        raise ValueError(f"Could not read header of {csv_path.name}: {exc}") from exc
    return list(header.columns)


def count_rows_fast(csv_path: Path) -> int:
    """
    Count data rows without ever loading the file into pandas.

    A plain line count keeps a 1M-row CSV from being parsed twice just to
    report its size.
    """
    with open(csv_path, "r", encoding="utf-8", errors="replace") as fh:
        total_lines = sum(1 for _ in fh)
    return max(total_lines - 1, 0)  # minus header row


def read_sample(csv_path: Path, n: int = 5000) -> pd.DataFrame:
    """Small sample used for dtype inference / column typing - never the full file."""
    try:
        return pd.read_csv(csv_path, nrows=n)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not read a sample of {csv_path.name}: {exc}") from exc


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Downcast numeric columns and convert low-cardinality object columns to
    'category' in place, to keep memory reasonable on wide/tall CSVs.
    """
    for col in df.columns:
        col_dtype = df[col].dtype
        if pd.api.types.is_bool_dtype(col_dtype):
            continue
        if pd.api.types.is_integer_dtype(col_dtype):
            df[col] = pd.to_numeric(df[col], downcast="integer")
        elif pd.api.types.is_float_dtype(col_dtype):
            df[col] = pd.to_numeric(df[col], downcast="float")
        elif col_dtype == object:
            nunique = df[col].nunique(dropna=True)
            if nunique and len(df) and nunique / len(df) < 0.5:
                df[col] = df[col].astype("category")
    return df


def read_full(csv_path: Path, usecols: Iterable[str] | None = None) -> pd.DataFrame:
    """
    Read a CSV with an optional column subset, then apply memory-friendly
    dtypes. Every module passes usecols whenever it does not need every
    column - this both reduces memory and speeds up parsing on a 1M-row file.
    """
    try:
        df = pd.read_csv(csv_path, usecols=list(usecols) if usecols else None)
    except ValueError as exc:
        raise ValueError(f"Could not read requested columns from {csv_path.name}: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not read {csv_path.name}: {exc}") from exc
    return optimize_dtypes(df)


def has_target(columns: Iterable[str]) -> bool:
    return TARGET_COLUMN in set(columns)


def missing_target_message(section_title: str) -> str:
    return (
        f"{section(section_title)}\n"
        f"Target column '{TARGET_COLUMN}' was not found in this dataset. "
        "Skipping this analysis."
    )


def identify_categorical_numeric(
    df: pd.DataFrame,
    exclude: Iterable[str] = (),
) -> tuple[list[str], list[str]]:
    """
    Heuristically split feature columns into categorical/discrete vs numeric.

    A column is treated as categorical if it is text/boolean, or if it is
    numeric but has few enough unique values to behave like a category
    (flags, coded types, etc). Everything else numeric is continuous.
    """
    exclude = set(exclude)
    categorical: list[str] = []
    numeric: list[str] = []

    for col in df.columns:
        if col in exclude:
            continue
        series = df[col]
        if (
            pd.api.types.is_bool_dtype(series)
            or series.dtype.name == "category"
            or series.dtype == object
        ):
            categorical.append(col)
        elif pd.api.types.is_numeric_dtype(series):
            nunique = series.nunique(dropna=True)
            if nunique <= CATEGORICAL_UNIQUE_THRESHOLD:
                categorical.append(col)
            else:
                numeric.append(col)
        # anything else (e.g. parsed datetime) is deliberately left out of both

    return categorical, numeric


def detect_temporal_columns(
    columns: Iterable[str],
    sample: pd.DataFrame | None = None,
) -> list[str]:
    """
    Return column names that plausibly hold time/period information.

    Matches whole-word tokens (so "months" doesn't also match inside
    "prev_address_months_count") and skips anything that also looks like a
    duration/count field. If a sample is given, columns with more unique
    values than a real calendar period would have are dropped too - this
    catches count-style fields that pass the naming check regardless.
    """
    candidates = []
    for col in columns:
        tokens = set(re.split(r"[^a-z0-9]+", col.lower()))
        if tokens & _TEMPORAL_DENYLIST_TOKENS:
            continue
        if tokens & _TEMPORAL_TOKENS:
            candidates.append(col)

    if sample is None:
        return candidates

    filtered = []
    for col in candidates:
        if col not in sample.columns:
            filtered.append(col)  # can't verify against the sample - keep it
            continue
        if sample[col].nunique(dropna=True) <= TEMPORAL_MAX_CARDINALITY:
            filtered.append(col)
    return filtered


def pct(part: float, whole: float) -> str:
    if not whole:
        return "0.00%"
    return f"{(part / whole) * 100:.2f}%"


def divider(char: str = "-", width: int = 60) -> str:
    return char * width


def section(title: str) -> str:
    return f"\n{title}\n{divider('=', len(title))}"
