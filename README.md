# Fraud & Risk Intelligence - Dataset Analysis CLI

Interactive command-line tool for exploratory analysis of fraud datasets.

## Features

This tool reads CSV datasets and produces plain-text analysis reports. It **never** modifies the source data, trains models, or makes modeling decisions.

### Available Analyses (10 modules)

1. **Dataset Overview** - File info, row/column counts, column names and dtypes
2. **Data Quality** - Missing values, duplicates, unique value counts
3. **Feature Profile** - Statistical summaries for each column
4. **Target / Fraud Analysis** - Distribution of fraud_bool target variable
5. **Categorical Analysis** - Frequency tables for categorical features
6. **Numeric Analysis** - Descriptive statistics for numeric columns
7. **Temporal Analysis** - Detection and analysis of date/time columns
8. **Fraud Relationships** - Cross-tabulations between features and fraud_bool
9. **Outlier Analysis** - Identification of extreme values in numeric columns
10. **Leakage Checks** - Detection of potential data leakage features

### Option 0: Run All Analyses

Select option 0 to run all 10 analyses sequentially and save a combined report with timestamped filename.

## Requirements

- Python 3.8+
- pandas
- numpy

## Installation

```bash
# Create environment (if using conda)
conda create -n fraud-analysis python=3.12 pandas numpy pytest
conda activate fraud-analysis

# Or with pip
pip install pandas numpy pytest
```

## Usage

```bash
cd fraud-risk-intelligence
python analysis/main.py
```

### Menu Flow

1. Select a dataset from `analysis/dataset/` (CSV files)
2. Choose an analysis (1-10) or option 0 for all analyses
3. View results in terminal
4. Save to file when prompted

### Output Files

Analysis results are saved to `analysis/analysis_results/`:

- **Individual analyses** (options 1-10): Append to `analyses_YYYY-MM-DD_HH-MM-SS.txt`
- **Combined analysis** (option 0): Creates `analyses_YYYY-MM-DD_HH-MM-SS.txt`

## Dataset Requirements

Place CSV files in `analysis/dataset/`. The tool expects:

- A CSV file with a `fraud_bool` column (0/1 integer) for target analysis
- Standard tabular format with headers

### Example Dataset Structure

```csv
fraud_bool,income,name_email_similarity,prev_address_months_count,...
0,100000,0.85,12,...
1,50000,0.32,3,...
```

## Running Tests

```bash
cd fraud-risk-intelligence
pytest analysis/pytest/ -v
```

## Project Structure

```
fraud-risk-intelligence/
├── analysis/
│   ├── main.py              # CLI entry point
│   ├── core/
│   │   ├── utils.py         # Shared helpers
│   │   ├── 1_overview.py    # Dataset overview analysis
│   │   ├── 2_data_quality.py
│   │   ├── 3_feature_profile.py
│   │   ├── 4_target_analysis.py
│   │   ├── 5_categorical_analysis.py
│   │   ├── 6_numeric_analysis.py
│   │   ├── 7_temporal_analysis.py
│   │   ├── 8_fraud_relationships.py
│   │   ├── 9_outlier_analysis.py
│   │   └── 10_leakage_checks.py
│   ├── dataset/             # Place CSV files here
│   └── analysis_results/    # Output files (gitignored)
├── dataset/                 # Alternative dataset location (gitignored)
├── .gitignore
└── README.md
```

## License

MIT License
