import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "stage_h1f3a_k6_level2_grammar_audit"


def load(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_registry_invariants():
    final = load("h1f3a_final.json")
    closure = load("h1f3a_h1f1_h1f2_closure.json")
    readiness = load("h1f3a_k6_data_readiness.json")
    assert final["status"] == "PASS_ZERO_SOLVER_AUDIT"
    assert final["solver_entered_delta"] == 0
    assert closure["solver_entered_delta"] == 0
    assert final["local_registry_rows"] == 578
    assert final["K6_registry_rows"] == 648
    assert readiness["ml_admitted"] is False
    assert readiness["training_performed"] is False
    assert readiness["independent_K6_geometry_count"] == 6
    assert readiness["surrogate_readiness"] == "TOO_FEW_INDEPENDENT_K6_GEOMETRIES_FOR_FORMAL_SURROGATE"
    assert closure["seeds"]["K6_L0_A"]["sequence_uids"] == ["H1C1B_V2_005", "H1C1B_V2_005", "H1C1B_V2_015", "H1C1B_V2_015", "H1E3C_A_DECOUPLED_MINUS_H1C1B_V2_010", "H1E3C_A_TIED_PLUS_H1C1B_V2_010"]
    assert closure["seeds"]["K6_L0_B"]["candidate_hash"]
    assert closure["seeds"]["K6_L1_C"]["candidate_hash"]
    assert closure["fixed_slot_scope"]["P_supercell_nm"] == 2591.446716


def test_position_mode_is_zero_mean_one_dimensional_and_legal():
    audit = load("h1f3a_position_mode_audit.json")
    envelope = load("h1f3a_position_legality_envelope.json")
    proposed = load("h1f3a_proposed_next_stage.json")
    assert audit["phase_fixed"] is True
    assert audit["zero_mean"] is True
    assert audit["P_supercell_fixed"] is True
    assert audit["y_motion"] is False
    assert "not detour phase" in audit["interpretation"]
    assert envelope["exact_polygon_model"]
    assert proposed["candidate_count"] == 4
    assert proposed["formal_x_y_solver_budget"] == 8
    assert proposed["status"] == "PROPOSED_ONLY"
    assert proposed["level2_auto_start"] is False
    for seed, item in envelope["seeds"].items():
        assert item["A_legal_max_nm"] > 0
        assert item["base_minimum_clearance_nm"] > 0
        assert 0 < item["probe_scale_nm"] < item["A_legal_max_nm"]
    assert proposed["amplitudes_nm"]["K6_L0_A"] == 10.0
    assert proposed["amplitudes_nm"]["K6_L1_C"] == 10.0


def test_route_b_c_and_deterministic_decision():
    grouped = load("h1f3a_grouped_geometry_options.json")
    global_h = load("h1f3a_global_h_k6_audit.json")
    decision = load("h1f3a_route_decision.json")
    assert grouped["six_site_independent_variables"] is False
    assert grouped["no_isolated_dimer_search"] is True
    assert grouped["options"][0]["dimensionality"] == 1
    assert all(x["D_legal_max_nm"] > 0 for x in grouped["options"][0]["seed_audits"].values())
    assert global_h["one_shared_H_only"] is True
    assert global_h["per_site_H"] is False
    assert global_h["mixed_heights"] is False
    assert global_h["verdict"] == "GLOBAL_H_REVISIT_VALUE_MEDIUM"
    assert decision["formal_decision"] == "LOW_DIMENSIONAL_POSITION_MODE_FIRST"
    assert decision["evidence_complete"] is True
    assert decision["hard_gates"] == []
