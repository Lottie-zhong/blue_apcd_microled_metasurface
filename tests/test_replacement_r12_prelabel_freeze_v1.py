from pathlib import Path
import json
import pandas as pd

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1")
OUT = ROOT / "outputs/mdc_replacement_hf_external_r12_cleanroom_geometry_prelabel_freeze_v1/20260802T131000Z_R12_PRELABEL"


def read(name):
    return json.loads((OUT / name).read_text())


def test_nested_candidates_and_cases():
    manifest = read("completion_manifest.json")
    assert manifest["candidate_count"] == 12
    assert manifest["cases"] == {"R4": 24, "R8": 48, "R12": 72}
    assert read("candidates/replacement_nested_tiers.json")["R4"] == [0, 1, 2, 3]
    assert len(pd.read_csv(OUT / "solver/replacement_r12_solver_case_matrix.csv")) == 72


def test_prelabel_and_replay():
    lock = read("prelabel/replacement_prelabel_lock.json")
    pred = read("prelabel/replacement_prediction_sha.json")
    route = read("prelabel/replacement_routing_sha.json")
    assert lock["status"] == "FROZEN_PRELABEL_AWAITING_SOLVER_AUTHORIZATION"
    assert pred["identical"] is True
    assert route["identical"] is True
    assert read("registry/replacement_dataset_registry.json")["solver_authorized"] is False


def test_no_solver_and_hf15_reads():
    m = read("completion_manifest.json")
    assert m["HF15_reads"] == 0
    assert m["fits"] == 0
    assert m["solver_calls"] == 0
