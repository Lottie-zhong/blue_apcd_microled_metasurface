import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/stage_h1f3c_k6_complex_lever_audit"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_closure_scope():
    closure = load("h1f3c_h1f3b_closure.json")
    provenance = load("h1f3c_provenance_manifest.json")
    assert closure["position_mode_scoped_closure"] == "POSITION_MODE_RESPONSE_WEAK"
    assert closure["solver_entered_delta"] == 0
    assert provenance["solver_calls"] == 0
    assert provenance["ml_admitted"] is False


def test_first_harmonic_basis_and_covariance():
    basis = load("h1f3c_first_harmonic_basis.json")
    assert basis["zero_mean"] is True
    assert basis["orthogonal"] is True
    assert basis["translation_covariant_2d_subspace"] is True
    assert basis["six_independent_D_variables"] is False
    assert abs(basis["inner_products"]["c_c"] - 3.0) < 1e-12
    assert abs(basis["inner_products"]["s_s"] - 3.0) < 1e-12


def test_builder_semantics_freeze_site_centers_and_other_parameters():
    builder = load("h1f3c_d_builder_semantics.json")
    assert builder["dimer_center_invariant"] is True
    assert builder["site_center_invariant"] is True
    assert builder["cx_formula"] == "D*cos(Psi)/2"
    assert builder["cy_formula"] == "D*sin(Psi)/2"
    assert "H" in builder["frozen"] and "material" in builder["frozen"]


def test_local_jacobian_does_not_infer_unmatched_pairs():
    audit = load("h1f3c_local_d_jacobian_audit.json")
    assert audit["versioned_local_registry_rows"] == 578
    assert audit["matched_pair_source_rows"] == 488
    assert audit["matched_D_local_jacobian_available"] is False
    assert audit["pair_count"] == 0
    assert audit["no_unmatched_derivative_inference"] is True


def test_legality_envelope_and_probe_are_proposed_only():
    env = load("h1f3c_d_mode_legality_envelope.json")
    proposed = load("h1f3c_proposed_h1f4a.json")
    assert env["amplitude_is_phi_dependent"] is True
    assert all(x["conservative_radial_bound_nm"] > 4.0 for x in env["seeds"])
    assert proposed["A_D_probe_nm"] == 4.0
    assert proposed["solver_authorized"] is False
    assert proposed["maximum_future_solver_budget"] == 12


def test_canonical_registry_is_materialized_without_fake_rows():
    manifest = load("h1f3c_k6_registry_materialization.json")
    registry = OUT / "K6_FULLWAVE_EVIDENCE_REGISTRY.csv"
    with registry.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert manifest["row_count"] == 720
    assert manifest["exact_count_match"] is True
    assert len(rows) == 720
    assert manifest["fake_rows_added"] == 0
    assert all(row["geometry_hash_sha256"] for row in rows)
    assert all(row["source_artifact_sha256"] for row in rows)


def test_local_registry_separate_and_route_decision():
    manifest = load("h1f3c_k6_registry_materialization.json")
    decision = load("h1f3c_route_decision.json")
    assert manifest["local_registry_rows"] == 578
    assert manifest["matched_pair_source_rows"] == 488
    assert manifest["ml_admitted"] is False
    assert decision["formal_decision"] in {
        "GROUPED_D_FIRST_HARMONIC_READY",
        "GROUPED_D_LEVER_LOW_EXPECTED_VALUE",
        "GLOBAL_H_OPERATING_POINT_REVISIT_FIRST",
        "ESCALATE_GRAMMAR_WITHOUT_D_PROBE",
        "INSUFFICIENT_EVIDENCE",
    }
