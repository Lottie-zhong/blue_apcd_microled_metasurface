import csv
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O = ROOT / "outputs/lp_ml_dataset_v1"
C = O / "clean_v2"
A = O / "analysis"
QID = "LPML_R1_GLOBAL_SOBOL_054"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_clean_recompetition_data_contract():
    data = rows(C / "lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv")
    assert len(data) == 2871
    assert len({r["candidate_id"] for r in data}) == 319
    assert not any(r["candidate_id"] == QID for r in data)
    assert all(r["model_fill"] == "NONE" for r in data)
    assert len(data) == len({(r["candidate_id"], r["wavelength_nm"]) for r in data})


def test_recompetition_has_five_seeds_and_no_solver():
    training = json.loads((A / "lp_ml_round2_clean_recompetition_training_v2.json").read_text())
    assert training["solver_calls"] == 0
    assert training["seed_list"] == [11, 22, 33, 44, 55]
    assert {x["candidate"] for x in training["candidates"]} == {"C1", "C2", "C3", "C4"}
    for item in training["candidates"]:
        assert item["from_scratch"] is True
        assert item["warm_start"] is False
        assert len(item["seeds"]) == 5


def test_validation_selection_and_frozen_tests_are_ordered():
    selection = json.loads((A / "lp_ml_round2_clean_recompetition_validation_selection_v2.json").read_text())
    final = json.loads((A / "lp_ml_round2_clean_recompetition_final_tests_v2.json").read_text())
    promotion = json.loads((A / "lp_ml_round2_clean_recompetition_promotion_v2.json").read_text())
    assert selection["validation_only"] is True
    assert final["selection_frozen_before_tests"] is True
    assert promotion["test_evaluation_frozen_after_selection"] is True
    assert promotion["outcome"] in {
        "LP_ML_ROUND2_RECOMPETITION_PASS_INVERSE_PLANNING_READY",
        "LP_ML_ROUND2_RECOMPETITION_PARTIAL_CHAMPION_RETAINED",
        "LP_ML_ROUND2_RECOMPETITION_MODEL_FIX_REQUIRED",
    }


def test_clean_splits_exclude_quarantine():
    split = rows(C / "split_clean_v2.csv")
    assert len(split) == 319
    assert not any(r["candidate_id"] == QID for r in split)
    assert {r["split"] for r in split} == {"train", "validation", "test"}


def test_recompetition_checksum_manifest_and_scope():
    payload = json.loads((A / "lp_ml_round2_clean_recompetition_checksums_v2.json").read_text())
    assert payload["solver_calls"] == 0
    assert payload["model_filled_rows"] == 0
    assert payload["protected_reports_unchanged"] is True
    for rel, digest in payload["artifact_sha256"].items():
        p = ROOT / rel
        assert p.exists(), rel
        assert len(digest) == 64
