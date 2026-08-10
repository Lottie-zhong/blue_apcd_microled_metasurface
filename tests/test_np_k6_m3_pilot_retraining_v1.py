from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_k6_m3_pilot_retraining_v1"


def read_json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8-sig"))


def read_csv(name: str):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_training_view_contract_is_complete():
    rows = read_csv("development_hf_v2_training_view.csv")
    assert len(rows) == 198
    assert len({r["geometry_hash"] for r in rows}) == 9
    assert len({r["case_id"] for r in rows}) == 18
    assert {r["polarization"] for r in rows} == {"p", "s"}
    assert {int(r["wavelength_nm"]) for r in rows} == set(range(445, 456))
    assert all(r["training_label"].lower() == "true" for r in rows)
    assert all(r["quality_gate_pass"].lower() == "true" for r in rows)
    assert all(r["diagnostic_only"].lower() == "false" for r in rows)


def test_oof_is_geometry_grouped_and_complete():
    rows = read_csv("m3_oof_predictions_long.csv")
    assert len(rows) == 594
    assert all(r["held_out_geometry"] == r["geometry_id"] for r in rows)
    keys = [(r["model"], r["geometry_id"], r["case_id"], r["wavelength_nm"]) for r in rows]
    assert len(keys) == len(set(keys))
    assert all(math.isfinite(float(r["pred_eta_plus1"])) for r in rows)


def test_p_s_diagnostic_does_not_merge_training():
    summary = read_json("p_s_paired_diagnostic_summary.json")
    assert summary["p_s_not_merged_for_training"] is True
    assert summary["final_p_s_equivalence_claim"] is False
    assert summary["classification"] == "P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA"


def test_zero_solver_and_runtime_authority():
    zero = read_json("solver_zero_audit.json")
    assert zero["fdtd_run_invocations"] == 0
    assert zero["lumapi_run_invocations"] == 0
    assert zero["sealed_target_reads"] == 0
    assert zero["batch2_started"] is False
    runtime = read_json("batch1_runtime_cost_audit.json")
    assert runtime["physical_solver_invocation_count"] == 13
    assert runtime["accepted_execution_count"] == 12
    assert runtime["lost_infrastructure_execution_count"] == 1


def test_standalone_validator_report_passes():
    report = read_json("m3_standalone_validator_report.json")
    assert report["status"] == "PASS"
    assert report["errors"] == []
    assert report["solver_run_invocations"] == 0
    assert report["sealed_target_reads"] == 0
