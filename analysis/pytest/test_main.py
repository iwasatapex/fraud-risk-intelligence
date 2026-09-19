from pathlib import Path
import importlib
import main

def test_analysis_registry_has_all_ten_entries():
    assert len(main.analysis)==10
    assert [label for label,_ in main.analysis] == [
        "Dataset Overview","Data Quality","Feature Profile","Target / Fraud analysis",
        "Categorical analysis","Numeric analysis","Temporal analysis","Fraud Relationships",
        "Outlier analysis","Leakage Checks"]

def test_select_dataset_exit_and_selection(monkeypatch,tmp_path):
    dataset=tmp_path/"dataset"; dataset.mkdir()
    csv=dataset/"b.csv"; csv.write_text("x\n1\n")
    monkeypatch.setattr(main,"DATASET_DIR",dataset)
    monkeypatch.setattr("builtins.input",lambda _:"1")
    assert main.select_dataset()==csv
    monkeypatch.setattr("builtins.input",lambda _:"0")
    assert main.select_dataset() is None

def test_select_dataset_handles_missing_dir(tmp_path,capsys,monkeypatch):
    monkeypatch.setattr(main,"DATASET_DIR",tmp_path/"missing")
    assert main.select_dataset() is None
    assert "Dataset directory not found" in capsys.readouterr().out

def test_select_dataset_invalid_then_valid(monkeypatch,tmp_path):
    d=tmp_path/"dataset"; d.mkdir(); csv=d/"x.csv"; csv.write_text("x\n1\n")
    answers=iter(["bad","9","1"]); monkeypatch.setattr(main,"DATASET_DIR",d); monkeypatch.setattr("builtins.input",lambda _:next(answers))
    assert main.select_dataset()==csv

def test_select_analysis(monkeypatch):
    answers=iter(["bad","99","1"]); monkeypatch.setattr("builtins.input",lambda _:next(answers))
    label,func=main.select_analysis(); assert label=="Dataset Overview" and callable(func)
    monkeypatch.setattr("builtins.input",lambda _:"0")
    label,func=main.select_analysis()
    assert label==main.COMBINED_analysis_LABEL
    assert callable(func)

def test_run_analysis_success_and_missing(capsys,tmp_path):
    p=tmp_path/"x.csv"; p.write_text("x\n1\n")
    assert main.run_analysis("Test",lambda _:"ok",p)=="ok"
    missing=tmp_path/"missing.csv"
    assert main.run_analysis("Test",lambda _:"ok",missing) is None
    assert "Dataset file missing" in capsys.readouterr().out

def test_run_analysis_error_handlers(capsys,tmp_path):
    p=tmp_path/"x.csv"; p.write_text("x\n1\n")
    for exc,msg in [(ValueError("bad"),"Could not read this CSV"),(KeyError("x"),"'x'"),(RuntimeError("boom"),"analysis failed unexpectedly")]:
        assert main.run_analysis("Test",lambda _:(_ for _ in ()).throw(exc),p) is None
        assert msg in capsys.readouterr().out

def test_ensure_results_file(tmp_path,monkeypatch):
    monkeypatch.setattr(main,"RESULTS_DIR",tmp_path/"nested")
    main.ensure_results_file(); assert (tmp_path/"nested").exists()
    main.ensure_results_file(); assert (tmp_path/"nested").exists()

def test_save_result_appends_to_analysis_file(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(main,"RESULTS_DIR",tmp_path)
    f=tmp_path/"analysis_2026-01-01_12-00-00.txt"
    main.save_result("RESULT","Base.csv","Dataset Overview","2026-01-01_12-00-00")
    main.save_result("RESULT2","Base.csv","Data Quality","2026-01-01_12-00-00")
    text=f.read_text()
    assert text.count("#"*70)==4
    assert "dataset=Base.csv | analysis=Dataset Overview" in text
    assert "RESULT2" in text
    assert "Appended to" in capsys.readouterr().out

def test_prompt_yes_no(monkeypatch,capsys):
    answers=iter(["maybe","YES"]); monkeypatch.setattr("builtins.input",lambda _:next(answers))
    assert main.prompt_yes_no("Continue?") is True
    assert "Please answer y or n." in capsys.readouterr().out
    monkeypatch.setattr("builtins.input",lambda _:"no")
    assert main.prompt_yes_no("Continue?") is False
