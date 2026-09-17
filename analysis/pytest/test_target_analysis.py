import importlib
target_analysis=importlib.import_module("4_target_analysis")

def test_missing_target(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["amount","10","20"])
    assert "Target column 'fraud_bool' was not found" in target_analysis.run(str(p))

def test_balanced_target(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["fraud_bool","1","1","0","0"])
    r=target_analysis.run(str(p))
    assert "- 0: 2 (50.00%)" in r and "- 1: 2 (50.00%)" in r
    assert "Fraud rate: 50.00%" in r and "Legitimate rate: 50.00%" in r
    assert "1.0 : 1" in r

def test_no_fraud_ratio_undefined(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["fraud_bool","0","0","0"])
    r=target_analysis.run(str(p))
    assert "100.00%" in r
    assert "undefined" in r

def test_missing_target_value_is_counted(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["fraud_bool","0","NaN","1"])
    r=target_analysis.run(str(p))
    assert "Fraud rate: 33.33%" in r
    assert "Legitimate rate: 66.67%" in r
