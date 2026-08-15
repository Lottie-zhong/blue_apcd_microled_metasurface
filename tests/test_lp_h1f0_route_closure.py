import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/stage_h1f0_lp_route_closure"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_scope():
    chain = read("h1f0_local_dimer_evidence_chain.json")
    assert chain["scope"] == "CURRENT_H550_LOCAL_DIMER_GRAMMAR_PHASE_LEVERAGE_INSUFFICIENT"
    assert [r["stage"] for r in chain["rows"]] == ["H1A", "H1B", "H1C", "H1D", "H1E1", "H1E3A", "H1E3B", "H1E3C"]
    assert chain["formal_compatibility"] == "9/9 projector-compatible broadband acceptance where labelled strict"
    assert read("h1f0_proposed_next_stage.json")["budget"]["solver_entered_now"] == 0
    source = (ROOT / "scripts/lp_h1f0_route_closure.py").read_text(encoding="utf-8")
    assert "lumapi" not in source.lower()
    assert "subprocess" not in source.lower()
    assert "fdtd-engine" not in source.lower()


def test_strict_bank_and_phase_cluster():
    bank = read("h1f0_strict_bank_summary.json")
    assert bank["old_strict_count"] == 7
    assert bank["new_strict_count"] == 5
    assert bank["strict_count"] == 12
    assert bank["selected_phase_coverage"]["coverage_deg"] == 32.207338325516275
    assert bank["geometry_space_diversity"]["label"] == "GEOMETRIC_DIVERSITY_WITH_OPTICAL_PHASE_CLUSTERING"


def test_local_strategy_not_final_objective():
    k6 = read("h1f0_full_k6_route_audit.json")
    assert k6["six_bin_local_phase_library"] == "strategy_or_initialization_not_Maxwell_requirement"
    assert k6["full_jones_requirement"].startswith("x and y source subruns are required")
    assert any("eta_x,+1(lambda)" in x for x in k6["primary_objectives"])
    assert "eta_x,0(lambda)" in k6["diagnostic_metrics"]


def test_deterministic_route_and_global_h_audit():
    decision = read("h1f0_route_decision.json")
    comparison = read("h1f0_route_comparison.json")
    gh = read("h1f0_global_h_revisit_audit.json")
    assert decision["recommendation"] == "COUPLING_AWARE_FULL_K6_FIRST"
    assert comparison["decision"] == decision["recommendation"]
    assert gh["GLOBAL_H_REVISIT_VALUE"] == "MEDIUM"
    assert gh["table"][3]["H_global_nm"] == 550
    assert decision["scheduler"]["active_fdtd_jobs"] < 2
    assert decision["scheduler"]["active_rcwa_jobs"] == 0
    assert decision["scheduler"]["unresolved_entered_cases"] == []
    assert decision["execution_guard"]["solver_entered_delta"] == 0
    assert sum(decision["execution_guard"][k] for k in ("new_fdtd_runs", "new_rcwa_runs", "new_ml_training_runs", "new_inverse_runs", "new_k6_full_wave_runs")) == 0


def test_registry_and_ml_governance():
    ml = read("h1f0_ml_role_audit.json")
    assert ml["versioned_local_dimer_rows"] == 578
    assert ml["canonical_registry_unchanged"] is True
    assert ml["ml_admitted"] is False
    assert ml["training_performed"] is False
    assert ml["ml_roles"]["coupled_K6_model"].startswith("not valid")
