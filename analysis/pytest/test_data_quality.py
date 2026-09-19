import importlib
data_quality=importlib.import_module("2_data_quality")
def test_run_reports_missing_duplicates_constants_and_negatives(tmp_path,write_csv):
    p=write_csv(tmp_path/"data.csv",["a,b,c","1,,5","1,,5","-2,x,5","3,y,5"])
    r=data_quality.run(str(p))
    assert "Missing values (NaN):" in r and "b: 2 (50.00%)" in r
    assert "Duplicate rows: 1 (25.00%)" in r
    assert "Constant columns" in r and "c" in r
    assert "- a: 1 (25.00%)" in r
    assert "Other negative values" in r and "a: 1 (25.00%)" in r
    assert "Warnings:" in r

def test_run_reports_clean_dataset(tmp_path,write_csv):
    p=write_csv(tmp_path/"clean.csv",["a,b","1,x","2,y","3,z"])
    r=data_quality.run(str(p))
    assert "None found." in r
    assert "None." in r
