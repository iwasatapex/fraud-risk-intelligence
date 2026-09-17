import importlib
feature_profile=importlib.import_module("3_feature_profile")

def test_numeric_and_categorical_profiles(tmp_path,write_csv):
    p=write_csv(tmp_path/"data.csv",["age,city","10,Delhi","20,Delhi","30,Mumbai"])
    r=feature_profile.run(str(p))
    assert "age" in r and "mean=20.0000" in r and "min=10.0000" in r and "max=30.0000" in r
    assert "city" in r and "categorical cardinality: 2 categories" in r
    assert "most common value: 'Delhi' (2 rows)" in r

def test_empty_numeric_and_boolean_profile(tmp_path):
    p=tmp_path/"data.csv"
    p.write_text("num,bool\n,True\n,False\n")
    r=feature_profile.run(str(p))
    assert "numeric stats: no non-missing values" in r
    assert "bool" in r and "categorical cardinality: 2 categories" in r
