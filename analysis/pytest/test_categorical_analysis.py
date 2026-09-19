import importlib
categorical_analysis=importlib.import_module("5_categorical_analysis")

def test_no_categorical_columns(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["a,b"] + [f"{i},{i+100}" for i in range(30)])
    r=categorical_analysis.run(str(p))
    assert "No categorical/discrete columns were detected." in r

def test_categories_with_target_and_missing(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["city,fraud_bool","Delhi,0","Delhi,1","Mumbai,0","Other,1"])
    r=categorical_analysis.run(str(p))
    assert "Detected categorical columns: city" in r
    assert "Delhi" in r and "fraud rate: 50.00%" in r
    assert "Other" in r and "fraud rate: 100.00%" in r

def test_categories_without_target(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["city","Delhi","Mumbai","Delhi"])
    r=categorical_analysis.run(str(p))
    assert "fraud rate" not in r
    assert "Delhi" in r

def test_output_caps_categories(tmp_path):
    p=tmp_path/"x.csv"
    p.write_text("category\n"+"\n".join(f"c{i}" for i in range(20))+"\n")
    r=categorical_analysis.run(str(p))
    assert "category (20 categories)" in r
    assert "... 5 more categories not shown" in r
    assert "c19" not in r
