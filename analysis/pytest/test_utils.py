from pathlib import Path
import pandas as pd
import pytest
import utils

def test_discover_csv_files_sorted_and_only_files(tmp_path):
    (tmp_path / "b.csv").write_text("a\n1\n")
    (tmp_path / "a.csv").write_text("a\n1\n")
    (tmp_path / "dir.csv").mkdir()
    assert [p.name for p in utils.discover_csv_files(tmp_path)] == ["a.csv", "b.csv"]

def test_discover_csv_files_errors(tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset directory not found"):
        utils.discover_csv_files(tmp_path / "missing")
    f=tmp_path/"file"; f.write_text("x")
    with pytest.raises(NotADirectoryError): utils.discover_csv_files(f)
    with pytest.raises(FileNotFoundError, match="No CSV files"):
        utils.discover_csv_files(tmp_path)

def test_get_columns_and_invalid(tmp_path):
    p=tmp_path/"x.csv"; p.write_text("a,b\n1,2\n")
    assert utils.get_columns(p)==["a","b"]
    bad=tmp_path/"bad.csv"; bad.write_text("\n\n")
    with pytest.raises(ValueError, match="Could not read header"):
        utils.get_columns(bad)

def test_count_rows_fast(tmp_path):
    p=tmp_path/"x.csv"; p.write_text("a\n1\n2\n")
    assert utils.count_rows_fast(p)==2
    empty=tmp_path/"empty.csv"; empty.write_text("")
    assert utils.count_rows_fast(empty)==0

def test_read_sample_and_invalid(tmp_path):
    p=tmp_path/"x.csv"; p.write_text("a,b\n1,x\n2,y\n3,z\n")
    assert len(utils.read_sample(p,2))==2
    bad=tmp_path/"bad.csv"; bad.write_text("\n")
    with pytest.raises(ValueError, match="Could not read a sample"):
        utils.read_sample(bad)

def test_optimize_dtypes_all_relevant_branches():
    df=pd.DataFrame({"i":list(range(100)),"f":[float(i) for i in range(100)],"s":["a","a"] + ["b"] * 98,"u":[f"item{i}" for i in range(100)],"b":[True,False] * 50})
    out=utils.optimize_dtypes(df)
    assert pd.api.types.is_integer_dtype(out.i)
    assert pd.api.types.is_float_dtype(out.f)
    assert out.s.dtype.name=="category"
    assert out.u.dtype.name!="category"
    assert pd.api.types.is_bool_dtype(out.b)

def test_read_full_uses_columns_and_wraps_errors(tmp_path):
    p=tmp_path/"x.csv"; p.write_text("a,b\n1,2\n")
    out=utils.read_full(p, usecols=["a"])
    assert list(out.columns)==["a"]
    with pytest.raises(ValueError, match="Could not read requested columns"):
        utils.read_full(p, usecols=["missing"])

def test_has_target_and_missing_message():
    assert utils.has_target(["fraud_bool"])
    assert not utils.has_target(["x"])
    msg=utils.missing_target_message("X")
    assert "X" in msg and "fraud_bool" in msg and "Skipping" in msg

def test_identify_categorical_numeric_and_exclude():
    df=pd.DataFrame({"bool":[True,False] * 15,"cat":["a","b"] * 15,"low":[1,1] * 15,"num":list(range(30)),"fraud_bool":[0,1] * 15})
    cat,num=utils.identify_categorical_numeric(df,exclude=["fraud_bool"])
    assert cat==["bool","cat","low"]
    assert num==["num"]

def test_detect_temporal_columns_tokens_and_cardinality():
    cols=["month","event_date","report_time","year","prev_address_months_count","amount"]
    assert utils.detect_temporal_columns(cols)==["month","event_date","report_time","year"]
    sample=pd.DataFrame({"month":list(range(1,13))+[1]*88,"event_date":list(range(100)),"report_time":[0,1]*50,"year":[2020,2021]*50})
    assert utils.detect_temporal_columns(cols,sample=sample)==["month","report_time","year"]
    assert utils.detect_temporal_columns(["unknown_time"], sample=pd.DataFrame())==["unknown_time"]

def test_pct_divider_section():
    assert utils.pct(1,0)=="0.00%"
    assert utils.pct(1,4)=="25.00%"
    assert utils.divider()=="-"*60
    assert utils.divider("+",3)=="+++"
    assert utils.section("ABC")=="\nABC\n==="
