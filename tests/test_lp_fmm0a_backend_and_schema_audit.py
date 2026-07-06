import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_fmm0" / "lp_fmm0a_backend_and_schema_audit.py"
OUT = ROOT / "outputs" / "lp_fmm0a_backend_and_schema_audit"


def run_script():
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)


def test_script_runs_and_queue_has_36_rows():
    run_script()
    assert (OUT / "lp_fmm0a_backend_inventory.json").exists()
    with (OUT / "lp_fmm0a_candidate_queue.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 36
    assert all(r["fmm_run_status"] == "planned_not_run" for r in rows)


def test_convergence_plan_orders_and_schema():
    run_script()
    with (OUT / "lp_fmm0a_convergence_plan.csv").open(newline="", encoding="utf-8") as f:
        conv = list(csv.DictReader(f))
    orders = {(r["fourier_order_x"], r["fourier_order_y"]) for r in conv}
    assert {("7", "7"), ("11", "11"), ("15", "15"), ("21", "21")}.issubset(orders)
    with (OUT / "lp_fmm0a_expected_result_schema.csv").open(newline="", encoding="utf-8") as f:
        cols = {r["column"] for r in csv.DictReader(f)}
    assert {"txx_re", "txx_im", "tyy_re", "tyy_im"}.issubset(cols)


def test_reports_and_no_heavy_outputs():
    run_script()
    report = (ROOT / "reports" / "lp_fmm0a_backend_and_schema_audit.md").read_text(encoding="utf-8")
    for phrase in ["No FMM solver was executed", "No FDTD was run", "No Lumerical GUI was opened", "No model was trained", "No K=6 was attempted"]:
        assert phrase in report
    heavy = (".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy", "monitor", "farfield", "raw")
    assert not any(any(marker in p.name.lower() for marker in heavy) for p in OUT.rglob("*"))
    summary = json.loads((OUT / "lp_fmm0a_summary.json").read_text(encoding="utf-8"))
    assert summary["no_fmm_solver_executed"] is True
