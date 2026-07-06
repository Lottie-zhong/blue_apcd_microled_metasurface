import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_ml1" / "lp_ml1b0_runner_planning.py"
OUT = ROOT / "outputs" / "lp_ml1b0_runner_planning"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_queue_and_smoke_outputs():
    run_script()
    with (OUT / "lp_ml1b0_pilot_queue.csv").open(newline="", encoding="utf-8") as f:
        queue = list(csv.DictReader(f))
    assert len(queue) == 36
    required = {"queue_id", "candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "intended_wavelengths_nm", "num_wavelengths", "source_manifest", "run_status", "prepared_not_run", "priority_score", "pilot_rank", "estimated_runtime_class", "smoke_test_candidate", "notes"}
    assert required.issubset(queue[0])
    assert all(r["run_status"] == "queued_not_run" for r in queue)
    assert all(r["prepared_not_run"] == "true" for r in queue)
    with (OUT / "lp_ml1b0_smoke_test_recommendation.csv").open(newline="", encoding="utf-8") as f:
        smoke = list(csv.DictReader(f))
    assert len(smoke) == 2


def test_result_schema_and_complex_spec():
    run_script()
    with (OUT / "lp_ml1b0_expected_result_schema.csv").open(newline="", encoding="utf-8") as f:
        cols = {r["column"] for r in csv.DictReader(f)}
    assert {"txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im"}.issubset(cols)
    spec = (ROOT / "reports" / "lp_ml1b0_complex_jones_extraction_spec.md").read_text(encoding="utf-8")
    assert "farfield3d is forbidden" in spec
    assert "farfieldvector3d" in spec and "farfieldpolar3d" in spec


def test_reports_boundaries_and_no_heavy_outputs():
    run_script()
    report = (ROOT / "reports" / "lp_ml1b0_runner_planning.md").read_text(encoding="utf-8")
    for phrase in ["No FDTD was run", "No FMM solver was executed", "No Lumerical GUI was opened", "No model was trained", "No K=6 was attempted"]:
        assert phrase in report
    heavy = (".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy", "monitor", "farfield", "raw")
    assert not any(any(marker in p.name.lower() for marker in heavy) for p in OUT.rglob("*"))
    summary = json.loads((OUT / "lp_ml1b0_summary.json").read_text(encoding="utf-8"))
    assert summary["no_fdtd_run"] is True
