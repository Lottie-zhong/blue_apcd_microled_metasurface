import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def test_h500_d110_readonly_recovery_closure():
    output = ROOT / "outputs/np_k6_p1d1a0_h500_d110_v1"
    result = json.loads((output / "results.json").read_text())
    assert result["candidate_id"] == "NP_P1D_H500_D110"
    assert result["execution_mode"] == "readonly_recovery_after_existing_postrun_v1"
    assert result["new_solver_runs_started_this_thread"] == 0
    assert result["source_post_fsp"] == result["post_fsp_readonly_after"]
    assert result["R_total"] == -result["R_raw"]
    assert result["p1d1a_h500_line_complete"] is False
    assert result["reference_blank_recovery_status"] == "trusted_recovered_postrun"
    assert len((output / "results.csv").read_text().strip().splitlines()) == 2
    summary = json.loads((output / "verification_summary.json").read_text())
    assert summary["P1D1A0_FORMAL_STATUS"] == "pass"
    assert summary["solver_run_count_this_thread"] == 0
