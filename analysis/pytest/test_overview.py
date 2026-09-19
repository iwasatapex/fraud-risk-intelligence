import importlib
overview=importlib.import_module("1_overview")

def test_run_reports_exact_structure(tmp_path,write_csv):
    p=write_csv(tmp_path/"data.csv",["age,city","20,Delhi","30,Mumbai","40,Delhi"])
    r=overview.run(str(p))
    assert "Dataset Overview" in r
    assert "Rows: 3" in r and "Columns: 2" in r
    assert "age" in r and "city" in r
    assert "int64" in r or "int" in r
    assert "Sample memory footprint (3 rows)" in r

