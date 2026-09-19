import importlib
leakage_checks=importlib.import_module("10_leakage_checks")

def test_missing_target(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["amount","1","2"])
    assert "Target column 'fraud_bool' was not found" in leakage_checks.run(str(p))

def test_constant_and_duplicate_numeric_findings(tmp_path):
    p=tmp_path/"x.csv"
    p.write_text("constant,feature,duplicate,fraud_bool\n"+"\n".join(f"1,{i},{i},{i%2}" for i in range(30))+"\n")
    r=leakage_checks.run(str(p))
    assert "Constant feature(s)" in r
    assert "'duplicate' looks identical to 'feature'" in r

def test_high_correlation_finding(tmp_path):
    p=tmp_path/"x.csv"
    rows=["feature,noise,fraud_bool"]
    for i in range(50):
        target=1 if i%2 else 0
        rows.append(f"{target},{i},{target}")
    p.write_text("\n".join(rows)+"\n")
    # feature has only two unique values and is therefore categorical; use a continuous
    # transform that remains highly correlated while having >20 unique values.
    rows=["feature,fraud_bool"]
    for i in range(100):
        target=1 if i>=50 else 0
        feature=i if target==0 else 1000+i
        rows.append(f"{feature},{target}")
    p.write_text("\n".join(rows)+"\n")
    r=leakage_checks.run(str(p))
    assert "correlates with the target" in r

def test_no_findings_clean_case(tmp_path,write_csv):
    rows=["value,fraud_bool"]+[f"{i},{i%2}" for i in range(40)]
    p=write_csv(tmp_path/"x.csv",rows)
    r=leakage_checks.run(str(p))
    assert "No obvious leakage signals found" in r

def test_temporal_sharp_shift_finding(tmp_path):
    rows=["month,fraud_bool"]
    # Month 1: 1 fraud out of 100. Month 2: 100 fraud out of 100 -> >4x relative jump.
    rows += [f"1,{1 if i==0 else 0}" for i in range(100)]
    rows += ["2,1" for _ in range(100)]
    p=tmp_path/"x.csv"; p.write_text("\n".join(rows)+"\n")
    r=leakage_checks.run(str(p))
    assert "shifts sharply at period 2" in r
