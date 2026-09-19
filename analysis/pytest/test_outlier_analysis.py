import importlib
outlier_analysis=importlib.import_module("9_outlier_analysis")

def test_no_continuous_numeric(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["flag","0","1","0"])
    assert "No continuous numeric columns" in outlier_analysis.run(str(p))

def test_iqr_bounds_and_extremes(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["value"]+[str(x) for x in range(1,31)]+["100"])
    r=outlier_analysis.run(str(p))
    assert "IQR rule" in r
    assert "bounds:" in r
    assert "outliers: 1" in r
    assert "most extreme values: [100]" in r

def test_no_outliers_omits_extremes(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["value"]+[str(x) for x in range(1,31)])
    r=outlier_analysis.run(str(p))
    assert "outliers: 0" in r
    assert "most extreme values" not in r
