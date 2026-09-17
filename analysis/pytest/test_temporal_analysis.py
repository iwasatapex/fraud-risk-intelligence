import importlib
temporal_analysis=importlib.import_module("7_temporal_analysis")

def test_no_temporal_column(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["amount,fraud_bool","1,0","2,1"])
    assert "No likely temporal columns were detected by name." in temporal_analysis.run(str(p))

def test_period_counts_rates_and_sorted_order(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["month,fraud_bool","1,0","1,0","2,1"])
    r=temporal_analysis.run(str(p))
    assert "month (2 unique periods)" in r
    assert "- 1: 2 rows (66.67%) | fraud rate: 0.00%" in r
    assert "- 2: 1 rows (33.33%) | fraud rate: 100.00%" in r
    assert "sorted by month (increasing)" in r

def test_decreasing_and_unsorted(tmp_path,write_csv):
    dec=write_csv(tmp_path/"dec.csv",["month","3","2","1"])
    shuf=write_csv(tmp_path/"shuf.csv",["month","2","1","3"])
    assert "decreasing" in temporal_analysis.run(str(dec))
    assert "does not appear sorted" in temporal_analysis.run(str(shuf))

def test_without_target_omits_fraud_rate(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["month,amount","1,10","2,20","3,30"])
    r=temporal_analysis.run(str(p))
    assert "fraud rate" not in r
    assert "1 rows" in r
