from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_np_k6_m5a_forward_diagnostic_v1 import validate


def test_m5a_zero_solver_validator():
    result = validate(ROOT)
    assert result["status"] == "PASS"
    assert result["solver_zero"] is True
    assert result["rows"] == 286
    assert result["geometry_count"] == 13
    assert result["paired_case_count"] == 26
    assert result["wavelength_count"] == 11


def test_m5a_formulation_audits_are_explicit():
    out = ROOT / "outputs" / "np_k6_m5a_forward_development_promotion_diagnostic_v1"
    residual = json.loads((out / "m5_residual_reconstruction_audit.json").read_text())
    ranking = json.loads((out / "m5_ranking_contract_audit.json").read_text())
    assert residual["classification"] == "IMPLEMENTATION_RECONSTRUCTION_BUG_CONFIRMED"
    assert residual["correct_formula"] == "eta_hat=LF_eta+delta_hat"
    assert ranking["canonical_eta_plus1_index_in_full_vector"] == 5
    assert ranking["m5_frozen_evidence_modified"] is False


def test_m5a_supplement_complete_zero_solver():
    result = validate(ROOT)
    assert result["supplement_exists"] is True
    assert result["supplement_fit_after_prereg"] is True
    assert result["supplement_solver_zero"] is True
    assert result["ranking_rows"] == 7
    assert result["bootstrap_rows"] == 6
    assert result["physics_rows"] == 12
    assert result["disagreement_rows"] == 9
