import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def test_d140_readonly_recovery_and_pair_gate():
    out = ROOT / "outputs/np_k6_p1d1a1_h500_d140_v1"
    result = json.loads((out / "results.json").read_text())
    pair = json.loads((out / "pair_analysis.json").read_text())
    assert result["candidate_id"] == "NP_P1D_H500_D140"
    assert result["new_solver_runs_started_this_thread"] == 0
    assert result["source_post_fsp"] == result["post_fsp_readonly_after"]
    assert result["R_total"] == -result["R_raw"]
    assert result["p1d1a_h500_completed_candidates"] == ["NP_P1D_H500_D110", "NP_P1D_H500_D140"]
    assert pair["analysis_scope"] == "D110_D140_pair_only_not_phase_line"
    assert -180 < pair["minimal_wrapped_phase_difference_deg"] <= 180
    assert len((out / "results.csv").read_text().strip().splitlines()) == 2
