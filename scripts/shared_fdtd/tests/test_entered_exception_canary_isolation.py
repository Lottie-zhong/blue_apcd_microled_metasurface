import importlib.util
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_entered_exception_real_canary_v1.py"
sys.path.insert(0, str(ROOT.parent))
spec = importlib.util.spec_from_file_location("entered_exception_canary_under_test", SCRIPT)
canary = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = canary
spec.loader.exec_module(canary)


def test_parser_requires_db_path_and_isolated_assertion():
    with pytest.raises(SystemExit):
        canary.parse_args([])
    with pytest.raises(SystemExit):
        canary.parse_args(["--db-path", "D:/isolated/control.sqlite3"])


def test_production_db_and_children_are_rejected(tmp_path):
    output = tmp_path / "output"
    for candidate in (
        canary.PRODUCTION_DB_PATH,
        canary.PRODUCTION_DB_ROOT / "shadow.sqlite3",
    ):
        with pytest.raises(ValueError, match="production DB/root"):
            canary.validate_isolated_paths(candidate, output, True)


def test_symlink_db_or_output_is_rejected(tmp_path):
    target = tmp_path / "target.sqlite3"
    target.write_text("", encoding="utf-8")
    db_link = tmp_path / "db-link.sqlite3"
    output_target = tmp_path / "output-target"
    output_target.mkdir()
    output_link = tmp_path / "output-link"
    try:
        os.symlink(target, db_link)
        os.symlink(output_target, output_link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this host")
    with pytest.raises(ValueError, match="symlink"):
        canary.validate_isolated_paths(db_link, tmp_path / "out", True)
    with pytest.raises(ValueError, match="symlink"):
        canary.validate_isolated_paths(tmp_path / "isolated.sqlite3", output_link, True)


def test_isolated_paths_are_accepted(tmp_path):
    db_path, output_root = canary.validate_isolated_paths(
        tmp_path / "isolated.sqlite3", tmp_path / "output", True
    )
    assert db_path == (tmp_path / "isolated.sqlite3").resolve()
    assert output_root == (tmp_path / "output").resolve()


def test_negative_main_stops_before_reading_db(tmp_path, monkeypatch, capsys):
    def fail_if_opened(_db_path):
        raise AssertionError("negative isolation gate must not open any database")

    monkeypatch.setattr(canary, "read_db", fail_if_opened)
    rc = canary.main(
        [
            "--db-path",
            str(canary.PRODUCTION_DB_PATH),
            "--isolated-db",
            "--output-root",
            str(tmp_path / "output"),
        ]
    )
    assert rc == 2
    payload = capsys.readouterr().out
    assert "ISOLATION_GATE_FAILED" in payload
    assert "solver_runs" in payload
