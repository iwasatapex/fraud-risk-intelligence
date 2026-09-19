import importlib
numeric_analysis=importlib.import_module("6_numeric_analysis")

def test_no_continuous_numeric(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["flag","0","1","0"])
    assert "No continuous numeric columns were detected." in numeric_analysis.run(str(p))

def test_numeric_statistics_zero_and_sentinel(tmp_path,write_csv):
    values=list(range(-1,30))
    p=tmp_path/"x.csv"
    p.write_text("value\n"+"\n".join(map(str,values))+"\n")
    r=numeric_analysis.run(str(p))
    assert "Detected numeric columns: value" in r
    assert "count: 31" in r
    assert "mean: 14.0000" in r
    assert "median: 14.0000" in r
    assert "min: -1.0000" in r and "max: 29.0000" in r
    assert "p5:" in r and "p25:" in r and "p75:" in r and "p95:" in r
    assert "zero count: 1 (3.23%)" in r
    assert "-1 count: 1 (3.23%)" in r

def test_numeric_all_missing_branch(tmp_path):
    p=tmp_path/"x.csv"; p.write_text("value\n\n\n")
    # With no observed numeric values pandas infers object, so the module intentionally finds no continuous column.
    assert "No continuous numeric columns" in numeric_analysis.run(str(p))
