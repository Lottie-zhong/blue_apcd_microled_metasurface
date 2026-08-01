import json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); AN=ROOT/"outputs/lp_ml_dataset_v1/analysis"

def test_provenance_reaches_branch_and_upstream():
    p=json.loads((AN/"b120_j2lm06_post_d8_repository_worktree_provenance_audit_v1.json").read_text())
    assert p["head"]==p["upstream"]
    assert p["cb57069_reachable_from_branch"] is True
    assert p["ahead_behind"]=="0\t0"
    assert p["git_toplevel"].replace('\\','/').endswith('worktrees/blue_apcd_lp_stage11_4')

def test_txx_reproduction_is_original22_only():
    a=json.loads((AN/"b120_j2lm06_post_d8_frozen_txx_reproduction_audit_v1.json").read_text())
    assert a["status"]=="PASS" and a["training_rows"]==22 and a["bounded6_excluded"] is True
    assert a["real_max_abs_coefficient_difference"]<1e-12
    assert a["imag_max_abs_coefficient_difference"]<1e-12

def test_full_jones_spec_hard_gate_is_explicit():
    m=json.loads((AN/"b120_j2lm06_post_d8_frozen_full_jones_model_reconstruction_v1.json").read_text())
    t=json.loads((AN/"b120_j2lm06_post_d8_frozen_full_jones_training_manifest_v1.json").read_text())
    assert m["status"]=="HARD_GATE_FROZEN_MODEL_SPEC_INCOMPLETE"
    assert t["model_spec_complete"] is False
    assert set(t["missing_full_jones_outputs"])=={"Re(txy)","Im(txy)","Re(tyx)","Im(tyx)","Re(tyy)","Im(tyy)"}
    assert m["bounded6_fit_used"] is False

def test_no_bounded_replay_or_solver_import():
    s=(ROOT/"scripts/lp_b120_j2lm06_post_d8_frozen_full_jones_model_reconstruction_v1.py").read_text()
    assert "import lumapi" not in s and "FDTD(" not in s and "subprocess.run" not in s
    assert json.loads((AN/"b120_j2lm06_post_d8_frozen_full_jones_model_reconstruction_v1.json").read_text())["action"]=="STOP_BEFORE_BOUNDED6_REPLAY"
