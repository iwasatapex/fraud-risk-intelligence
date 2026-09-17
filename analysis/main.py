#!/usr/bin/env python3
"""
Interactive CLI for exploratory fraud-dataset analysis.

Run with:
    /home/kshitij/anaconda3/envs/projects/bin/python analysis/main.py

This tool only reads CSVs and writes plain-text summaries to
analysis-results/results.txt. It never modifies the source dataset, trains a
model, engineers features, or makes any modeling decisions.
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / "core"
DATASET_DIR = BASE_DIR.parent / "dataset"
RESULTS_FILE = BASE_DIR.parent / "analysis-results" / "results.txt"

# Make the analysis modules in core/ importable regardless of the working
# directory the script is launched from.
sys.path.insert(0, str(CORE_DIR))

# The analysis modules are numbered for reading order, so their names start
# with a digit and cannot be named in an import statement - load them here.
categorical_analysis = importlib.import_module("5_categorical_analysis")
data_quality = importlib.import_module("2_data_quality")
feature_profile = importlib.import_module("3_feature_profile")
fraud_relationships = importlib.import_module("8_fraud_relationships")
leakage_checks = importlib.import_module("10_leakage_checks")
numeric_analysis = importlib.import_module("6_numeric_analysis")
outlier_analysis = importlib.import_module("9_outlier_analysis")
overview = importlib.import_module("1_overview")
target_analysis = importlib.import_module("4_target_analysis")
temporal_analysis = importlib.import_module("7_temporal_analysis")
import utils

ANALYSES = [
    ("Dataset Overview", overview.run),
    ("Data Quality", data_quality.run),
    ("Feature Profile", feature_profile.run),
    ("Target / Fraud Analysis", target_analysis.run),
    ("Categorical Analysis", categorical_analysis.run),
    ("Numeric Analysis", numeric_analysis.run),
    ("Temporal Analysis", temporal_analysis.run),
    ("Fraud Relationships", fraud_relationships.run),
    ("Outlier Analysis", outlier_analysis.run),
    ("Leakage Checks", leakage_checks.run),
]


def select_dataset() -> Path | None:
    """Show the CSV files under dataset/. Returns None if the user exits."""
    try:
        files = utils.discover_csv_files(DATASET_DIR)
    except FileNotFoundError as exc:
        print(f"\n[Error] {exc}")
        print(f"Create the directory and add a CSV file, e.g.: {DATASET_DIR}/Base.csv")
        return None
    except NotADirectoryError as exc:
        print(f"\n[Error] {exc}")
        return None

    while True:
        print("\nAvailable datasets:")
        for i, path in enumerate(files, start=1):
            print(f"  {i}. {path.name}")
        print("  0. Exit")

        choice = input("\nSelect a dataset: ").strip()
        if choice == "0":
            return None
        if not choice.isdigit() or not (1 <= int(choice) <= len(files)):
            print("Invalid choice - enter a number from the list.")
            continue
        return files[int(choice) - 1]


def select_analysis():
    """Show the analysis menu. Returns (label, func) or None to go back."""
    while True:
        print("\nAvailable analyses:")
        for i, (label, _) in enumerate(ANALYSES, start=1):
            print(f"  {i}. {label}")
        print("  0. Back to dataset selection")

        choice = input("\nSelect an analysis: ").strip()
        if choice == "0":
            return None
        if not choice.isdigit() or not (1 <= int(choice) <= len(ANALYSES)):
            print("Invalid choice - enter a number from the list.")
            continue
        return ANALYSES[int(choice) - 1]


def run_analysis(label: str, func, csv_path: Path) -> str | None:
    print(f"\nRunning: {label} on {csv_path.name} ...")
    try:
        if not csv_path.exists():
            raise FileNotFoundError(f"{csv_path} no longer exists")
        return func(str(csv_path))
    except FileNotFoundError as exc:
        print(f"[Error] Dataset file missing: {exc}")
    except ValueError as exc:
        print(f"[Error] Could not read this CSV: {exc}")
    except KeyError as exc:
        print(f"[Error] {exc}")
    except Exception as exc:  # noqa: BLE001 - keep the CLI alive on any analysis bug
        print(f"[Error] Analysis failed unexpectedly: {exc}")
    return None


def ensure_results_file() -> None:
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not RESULTS_FILE.exists():
        RESULTS_FILE.touch()


def save_result(text: str, dataset_name: str, analysis_label: str) -> None:
    ensure_results_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = (
        f"\n{'#' * 70}\n"
        f"# {timestamp} | dataset={dataset_name} | analysis={analysis_label}\n"
        f"{'#' * 70}\n"
        f"{text}\n"
    )
    with open(RESULTS_FILE, "a", encoding="utf-8") as fh:
        fh.write(entry)
    print(f"\nSaved to {RESULTS_FILE}")


def prompt_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def main() -> None:
    print("Fraud & Risk Intelligence - Dataset Analysis CLI")
    print(f"Dataset directory: {DATASET_DIR}")
    ensure_results_file()

    while True:
        dataset_path = select_dataset()
        if dataset_path is None:
            print("\nGoodbye.")
            return

        while True:
            selection = select_analysis()
            if selection is None:
                break  # back to dataset selection

            label, func = selection
            result = run_analysis(label, func, dataset_path)
            if result is None:
                continue  # error already printed - stay on the analysis menu

            print(f"\n{result}\n")

            if prompt_yes_no("Append this result to results.txt?"):
                save_result(result, dataset_path.name, label)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye.")
        sys.exit(0)
