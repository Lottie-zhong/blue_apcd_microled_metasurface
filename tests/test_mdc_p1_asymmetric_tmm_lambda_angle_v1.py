from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_mdc_p1_asymmetric_tmm_lambda_angle_v1 as runner

def test_candidate_selection_and_frozen_inputs():
    selected, metrics = runner.load_inputs()
    assert len(selected) == 9 and len(metrics) == 9
    assert sum(1 for _, _, c in runner.CASES if c == "EX_N3_L79_H45_C156") == 3
    assert sum(1 for _, _, c in runner.CASES if c == "ZL1_N3_M3_L78_H46") == 3
    assert sum(1 for _, _, c in runner.CASES if c == "ZL1_N3_M3_L79_H44_C316") == 3

def test_native_policy_and_solver_free_source():
    meta = {m: runner.material_metadata(m) for m in ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")}
    assert all(v["sample_count"] == 101 and v["extrapolation"] == "forbidden" for v in meta.values())
    source = (ROOT / "scripts" / "run_mdc_p1_asymmetric_tmm_lambda_angle_v1.py").read_text(encoding="utf-8").lower()
    assert "import lumapi" not in source and "fdtd.run" not in source and "rcwa" not in source and "fmmax" not in source
    assert "signed_grid" in source and "unpolarized" in source

def test_no_extreme_rows():
    assert all("G1_A5" not in sid and "G5_A1" not in sid for sid, _, _ in runner.CASES)
