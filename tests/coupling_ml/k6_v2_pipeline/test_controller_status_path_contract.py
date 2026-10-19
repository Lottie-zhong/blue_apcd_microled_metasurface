from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _ROOT / "scripts/coupling_ml/k6_v2_pipeline/serial_queue.py"
_SPEC = importlib.util.spec_from_file_location("k6_v2_status_path_contract_test_module", _SCRIPT)
sq = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sq)

RUN_ID_A = "K6V2SERIAL20261009T090000Z_12345678"
RUN_ID_B = "K6V2SERIAL20261009T090001Z_87654321"


def _queue(report_root: Path) -> Path:
    report_root.mkdir(parents=True, exist_ok=True)
    path = report_root / "BATCH_QUEUE_MANIFEST_V1.json"
    path.write_text(json.dumps({"schema": "fixture"}), encoding="utf-8")
    return path


def test_successor_path_comes_from_bound_queue_report_and_is_request_scoped(tmp_path):
    report = tmp_path / "reports" / "current_queue"
    qman = _queue(report)
    stale_report = tmp_path / "reports" / "old_g026_task"
    stale_report.mkdir(parents=True)
    predecessor = {"controller_run_id": "OLD_RUN", "status_path": str(stale_report / "CONTROLLER_STATUS_OLD_RUN.json"),
        "case_ids": ["K6GDP2_DEV_G027", "K6GDP2_DEV_G028"], "max_cases": 2,
        "queue_manifest_path": str(qman), "queue_manifest_sha256": "1" * 64}

    successor = sq.successor_controller_manifest_body(predecessor, RUN_ID_A, "a" * 64, qman, report)

    assert Path(successor["status_path"]) == report / ("CONTROLLER_STATUS_" + RUN_ID_A + ".json")
    assert Path(successor["status_path"]).parent != stale_report
    assert {key for key in set(predecessor) | set(successor)
            if predecessor.get(key) != successor.get(key)} == {
        "controller_run_id", "status_path", "controller_script_sha256"}
    assert successor["case_ids"] == predecessor["case_ids"]
    assert successor["queue_manifest_path"] == predecessor["queue_manifest_path"]


def test_status_path_outside_current_report_fails_closed(tmp_path):
    report = tmp_path / "reports" / "production"
    qman = _queue(report)
    wrong = tmp_path / "reports" / "g026" / ("CONTROLLER_STATUS_" + RUN_ID_A + ".json")
    with pytest.raises(sq.StopQueue, match="CONTROLLER_STATUS_PATH_OUTSIDE_REPORT_ROOT"):
        sq.verify_controller_status_path(wrong, RUN_ID_A, qman, report)


def test_wrong_filename_and_existing_status_are_rejected(tmp_path):
    report = tmp_path / "reports" / "production"
    qman = _queue(report)
    wrong_name = report / "CONTROLLER_STATUS_reused.json"
    with pytest.raises(sq.StopQueue, match="CONTROLLER_STATUS_PATH_NOT_REQUEST_SCOPED"):
        sq.verify_controller_status_path(wrong_name, RUN_ID_A, qman, report)

    expected = sq.controller_status_path(RUN_ID_A, qman, report)
    expected.write_text("{}", encoding="utf-8")
    with pytest.raises(sq.StopQueue, match="CONTROLLER_STATUS_PATH_ALREADY_EXISTS"):
        sq.controller_status_path(RUN_ID_A, qman, report, require_absent=True)


def test_each_successor_has_independent_status_and_future_report_root_is_derived(tmp_path):
    report_a = tmp_path / "reports" / "queue_a"
    qman_a = _queue(report_a)
    report_b = tmp_path / "reports" / "queue_b"
    qman_b = _queue(report_b)
    predecessor = {"controller_run_id": "OLD", "status_path": str(report_a / "CONTROLLER_STATUS_OLD.json")}

    first = sq.successor_controller_manifest_body(predecessor, RUN_ID_A, "a" * 64, qman_a, report_a)
    second = sq.successor_controller_manifest_body(predecessor, RUN_ID_B, "b" * 64, qman_b, report_b)

    assert Path(first["status_path"]).parent == report_a
    assert Path(second["status_path"]).parent == report_b
    assert first["status_path"] != second["status_path"]
    assert Path(second["status_path"]).parent != Path(predecessor["status_path"]).parent


def test_queue_manifest_and_declared_report_root_must_match(tmp_path):
    actual = tmp_path / "reports" / "actual"
    qman = _queue(actual)
    wrong = tmp_path / "reports" / "wrong"
    wrong.mkdir(parents=True)
    with pytest.raises(sq.StopQueue, match="CONTROLLER_STATUS_ROOT_QUEUE_REPORT_MISMATCH"):
        sq.controller_status_path(RUN_ID_A, qman, wrong)


def test_legacy_status_is_confined_to_bound_source_manifest_directory(tmp_path, monkeypatch):
    coupling = tmp_path / "coupling"
    legacy = coupling / "reports" / "g026_task"
    legacy.mkdir(parents=True)
    source = legacy / "SUCCESSOR_CONTROLLER_MANIFEST_V1.json"
    source.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sq, "ROOT", coupling)
    expected = legacy / ("CONTROLLER_STATUS_" + RUN_ID_A + ".json")

    assert sq.validate_legacy_controller_status_path(expected, RUN_ID_A, source, coupling) == expected
    with pytest.raises(sq.StopQueue, match="CONTROLLER_LEGACY_STATUS_NOT_BOUND_TO_SOURCE_MANIFEST"):
        sq.validate_legacy_controller_status_path(
            coupling / "reports" / ("CONTROLLER_STATUS_" + RUN_ID_A + ".json"),
            RUN_ID_A, source, coupling)


def test_manifest_request_sha_mismatch_is_rejected_before_loading_contract(tmp_path):
    manifest = tmp_path / "controller_manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(sq.StopQueue, match="CONTROLLER_MANIFEST_REQUEST_BINDING_INVALID"):
        sq.verify_controller_manifest(manifest, "0" * 64, "1" * 32)
