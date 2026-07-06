import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_4a20_legacy_fsp_object_inventory.py"
OUT = ROOT / "outputs" / "stage11_4a20_legacy_fsp_object_inventory"


def run_index_only():
    subprocess.run([sys.executable, str(SCRIPT), "--index-only"], cwd=ROOT, check=True)


def test_script_runs_index_only_and_outputs_exist():
    run_index_only()
    assert (OUT / "stage11_4a20_fsp_file_index.csv").exists()
    assert (OUT / "stage11_4a20_object_inventory.csv").exists()
    assert (OUT / "stage11_4a20_candidate_geometry_attempt.csv").exists()
    assert (OUT / "stage11_4a20_summary.json").exists()


def test_report_contains_required_boundaries():
    run_index_only()
    report = (ROOT / "reports" / "stage11_4a20_legacy_fsp_object_inventory.md").read_text(encoding="utf-8")
    for phrase in ["No FDTD simulation was run", "No FSP was saved or modified", "No K=6 was attempted", "No model was trained"]:
        assert phrase in report


def test_no_heavy_outputs_or_runtime_touch():
    run_index_only()
    heavy = {".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy"}
    assert not any(p.suffix.lower() in heavy for p in OUT.rglob("*"))
    summary = json.loads((OUT / "stage11_4a20_summary.json").read_text(encoding="utf-8"))
    assert summary["no_heavy_created_in_outputs"] is True
    runtime = ROOT / "configs" / "runtime.yaml"
    if runtime.exists():
        # Test only asserts the script did not create a runtime copy in outputs.
        assert not (OUT / "runtime.yaml").exists()
