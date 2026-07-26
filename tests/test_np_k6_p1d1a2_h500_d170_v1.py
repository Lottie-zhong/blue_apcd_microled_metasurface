import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def test_d170_readonly_recovery_and_three_point_scope():
    out = ROOT / "outputs/np_k6_p1d1a2_h500_d170_v1"
    result = json.loads((out / "results.json").read_text())
    analysis = json.loads((out / "partial_phase_analysis.json").read_text())
    assert result["candidate_id"] == "NP_P1D_H500_D170"
    assert result["new_solver_runs_started_this_thread"] == 0
    assert result["source_post_fsp"] == result["post_fsp_readonly_after"]
    assert result["R_total"] == -result["R_raw"]
    assert result["p1d1a_h500_completed_candidates"] == ["NP_P1D_H500_D110", "NP_P1D_H500_D140", "NP_P1D_H500_D170"]
    assert analysis["provisional_three_point_unwrap"] is True
    assert analysis["P1C_D160_included"] is False
    assert len(analysis["points"]) == 3
    assert len((out / "results.csv").read_text().strip().splitlines()) == 2
