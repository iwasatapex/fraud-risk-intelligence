from pathlib import Path
import sys

import pandas as pd
import pytest

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ANALYSIS_DIR))
sys.path.insert(0, str(ANALYSIS_DIR / "core"))


@pytest.fixture
def write_csv(tmp_path):
    def _write_csv(path, df):
        if isinstance(df, list):
            path.write_text("\n".join(df) + "\n")
        else:
            df.to_csv(path, index=False)
        return path

    return _write_csv