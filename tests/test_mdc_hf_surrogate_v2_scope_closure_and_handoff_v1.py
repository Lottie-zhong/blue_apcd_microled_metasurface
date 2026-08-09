import json
from pathlib import Path

PKG = Path(__file__).parents[1] / "contracts" / "mdc_hf_surrogate_v2_coupling_handoff_v1"

def load(name):
    return json.loads((PKG / name).read_text(encoding="utf-8"))

def test_scope_and_model_lock():
    s = load("mdc_test40_scope_lock.json")
    assert s["scope_enum"] == "RANKING_SCREENING_ONLY"
    assert s["model_id"] == "MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1"
    assert s["selection"]["selection_timing"] == "POST_MODEL_LOCK_PRE_LABEL_PRE_PREDICTION"
    assert s["selection"]["raw_geometry_master_count"] == 8675

def test_output_restrictions():
    m = load("mdc_output_scope_matrix.json")
    assert m["power_scope"] == "NOT_QUANTITATIVELY_USABLE"
    assert "POWER_RANKING_WEAK_NOT_RECOMMENDED_FOR_PRIMARY_SELECTION" in m["power_warning"]
    assert "FDTD_REPLACEMENT" in m["forbidden_labels"]

def test_interface_is_reference_only():
    i = load("mdc_coupling_screening_interface_v1.json")
    assert i["row_count"] == 40
    assert i["contains_predicted_numeric_arrays"] is False
    assert i["contains_validated_relative_power"] is False
    assert all(r["profile_scope"] == "RANKING_SCREENING_ONLY" for r in i["rows"])
    assert all(r["power_scope"] == "NOT_QUANTITATIVELY_USABLE" for r in i["rows"])
    assert all("validated_relative_power" not in r for r in i["rows"])

def test_direct_fdtd_gate_and_level_route():
    d = load("mdc_direct_fdtd_confirmation_contract.json")
    assert d["contract_id"] == "APCD_MDC_DIRECT_FDTD_CONFIRMATION_FOR_COUPLING_V1"
    assert d["quality_gate"]["only_pass_enters_formal_level1_ranking"] is True
    n = load("mdc_np_interface_scope.json")
    assert n["stage_a"]["predicted_power_used"] is False
    assert n["stage_b"]["level"] == "LEVEL1_ONE_WAY_INCOHERENT_POWER"
    assert n["final_claim"]["level"] == "LEVEL2_INTEGRATED_FULL_WAVE"

def test_source_asset_registry_and_safety():
    src = load("mdc_source_lock.json")
    assert src["source_commit"] == "382a73f4e561da8bb7fe36eabccbc1be587f4095"
    assert len(src["frozen_assets"]["checkpoint_sha256"]) == 5
    assert src["coupling_worktree_read_only_observation"]["modified_by_this_task"] is False
    man = load("mdc_coupling_handoff_manifest.json")
    assert man["new_surrogate_development"] == "STOPPED"
    assert man["hf15_reevaluation"] == "NOT_REQUIRED"
