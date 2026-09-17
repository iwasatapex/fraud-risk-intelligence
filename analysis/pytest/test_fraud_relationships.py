import importlib
fraud_relationships=importlib.import_module("8_fraud_relationships")

def test_missing_target(tmp_path,write_csv):
    p=write_csv(tmp_path/"x.csv",["city,age","Delhi,20","Mumbai,30"])
    assert "Target column 'fraud_bool' was not found" in fraud_relationships.run(str(p))

def test_categorical_and_numeric_relationships(tmp_path,write_csv):
    rows=["city,age,fraud_bool"] + [f"{"Delhi" if i % 2 == 0 else "Mumbai"},{i},{1 if i % 2 else 0}" for i in range(30)]
    p=write_csv(tmp_path/"x.csv",rows)
    r=fraud_relationships.run(str(p))
    assert "Categorical features" in r and "city" in r
    assert "fraud rate" in r
    assert "Numeric features" in r and "age" in r
    assert "fraud mean=15.0000" in r and "legit mean=14.0000" in r

def test_numeric_group_missing_branch(tmp_path,write_csv):
    rows=["age,fraud_bool"] + [f"{i},{0}" for i in range(30)]
    p=write_csv(tmp_path/"x.csv",rows)
    r=fraud_relationships.run(str(p))
    assert "age: not enough data in one of the two groups" in r
