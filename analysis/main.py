#!/usr/bin/env python3
"""
Interactive CLI for exploratory fraud-dataset analysis.

Run with:
    /home/kshitij/anaconda3/envs/projects/bin/python analysis/main.py

This tool only reads CSVs and writes plain-text summaries to
analysis-results/analysis.txt. It never modifies the source dataset, trains a
model, engineers features, or makes any modeling decisions.
"""

from __future__ import annotations

import importlib
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CORE_DIR = BASE_DIR / "core"
DATASET_DIR = BASE_DIR / "dataset"
RESULTS_DIR = BASE_DIR / "analysis_results"

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

analysis = [
    ("Dataset Overview", overview.run),
    ("Data Quality", data_quality.run),
    ("Feature Profile", feature_profile.run),
    ("Target / Fraud analysis", target_analysis.run),
    ("Categorical analysis", categorical_analysis.run),
    ("Numeric analysis", numeric_analysis.run),
    ("Temporal analysis", temporal_analysis.run),
    ("Fraud Relationships", fraud_relationships.run),
    ("Outlier analysis", outlier_analysis.run),
    ("Leakage Checks", leakage_checks.run),
]

COMBINED_analysis_LABEL = "Run All analysis (1-10) and Save Combined Output"


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
        print()
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


def select_analysis() -> tuple[str, callable] | None:
    """Show the analysis menu. Returns (label, func) or None to go back.

    Option 0 runs all analysis (1-10) and saves combined output.
    """
    while True:
        print("\nAvailable analysis:")
        print()
        print(f"  0. {COMBINED_analysis_LABEL}")
        for i, (label, _) in enumerate(analysis, start=1):
            print(f"  {i}. {label}")

        choice = input("\nSelect an analysis: ").strip()
        if choice == "0":
            return (COMBINED_analysis_LABEL, _run_all_analysis)
        if not choice.isdigit() or not (1 <= int(choice) <= len(analysis)):
            print("Invalid choice - enter a number from the list.")
            continue
        return analysis[int(choice) - 1]


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
        print(f"[Error] analysis failed unexpectedly: {exc}")
    return None


def ensure_results_file() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_result(text: str, dataset_name: str, analysis_label: str, session_timestamp: str) -> None:
    entry = (
        f"\n{'#' * 70}\n"
        f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | dataset={dataset_name} | analysis={analysis_label}\n"
        f"{'#' * 70}\n"
        f"{text}\n"
    )
    analysis_file = RESULTS_DIR / f"analysis_{session_timestamp}.txt"
    with open(analysis_file, "a", encoding="utf-8") as fh:
        fh.write(entry)
    print(f"\nAppended to {analysis_file}")


def prompt_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def _run_all_analysis(csv_path_str: str) -> str | None:
    """Run all 10 analysis in sequence and return combined output."""
    csv_path = Path(csv_path_str)
    combined_parts: list[str] = []
    for label, func in analysis:
        print(f"\n{'=' * 60}")
        print(f"Running: {label} on {csv_path.name} ...")
        print(f"{'=' * 60}")
        result = run_analysis(label, func, csv_path)
        if result is not None:
            combined_parts.append(f"\n{'#' * 70}\n# {label}\n{'#' * 70}\n{result}")
        else:
            combined_parts.append(f"\n{'#' * 70}\n# {label}\n{'#' * 70}\n[analysis failed or returned no output]")
    return "\n".join(combined_parts)


def main() -> None:
    print("Fraud & Risk Intelligence - Dataset analysis CLI")
    print(f"Dataset directory: {DATASET_DIR}")
    ensure_results_file()

    session_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

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

            if label == COMBINED_analysis_LABEL:
                # Save combined output to a timestamped txt file
                combined_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                combined_file = RESULTS_DIR / f"analysis_{combined_timestamp}.txt"
                with open(combined_file, "w", encoding="utf-8") as fh:
                    fh.write(f"analysis Report\n")
                    fh.write(f"Dataset: {dataset_path.name}\n")
                    fh.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    fh.write(f"{'#' * 70}\n\n")
                    fh.write(result)
                print(f"\nCombined output saved to: {combined_file}")
            else:
                print(f"\n{result}\n")
                if prompt_yes_no("Save this analysis to a file?"):
                    save_result(result, dataset_path.name, label, session_timestamp)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye.")
        sys.exit(0)
