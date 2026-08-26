from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
V2 = ROOT / "paper_a_broadband/scripts/fdtd_physics_validity_gate_v2_instrumented.py"
REPORT = ROOT / "paper_a_broadband/reports/fdtd_physics_validity_gate_v2_instrumented"
BF01 = ROOT / "paper_a_broadband/runtime/search_anisotropy_bf01_bf04_initial_truth_v1/cases/BF01_x"
def run(case, post, log, name):
    out = REPORT / name
    p = subprocess.run([sys.executable, str(V2), "--case-id", case, "--post-fsp", str(post), "--solver-log", str(log), "--output", str(out)], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-1000:])
    return json.loads(out.read_text(encoding="utf-8"))
def path_of(value):
    result = value["path"] if isinstance(value, dict) and "path" in value else value
    path = Path(result)
    return str(path if path.is_absolute() else ROOT / path)
def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    b8 = json.loads((ROOT / "paper_a_broadband/reports/fdtd_physics_validity_gate_v1/BF08_x_attempt_003.json").read_text())
    b7 = json.loads((ROOT / "paper_a_broadband/reports/fdtd_physics_validity_gate_v1/BF07_x_attempt_001_control.json").read_text())
    old = json.loads((BF01 / "physics_validity_gate.json").read_text())
    r8 = run("BF08_x", path_of(b8["post_fsp"]), path_of(b8["solver_log"]), "BF08_x_v2_regression.json")
    bf07_path = path_of(b7["post_fsp"])
    bf07_log = path_of(b7["solver_log"])
    r7 = run("BF07_x", bf07_path, bf07_log, "BF07_x_v2_regression.json")
    r1 = run("BF01_x", old["post_fsp"]["path"], BF01 / "controller.log", "BF01_x_attempt_001_v2_regression.json")
    assert r8["status"] == "INVALID_FOR_PHYSICS_TRUTH_NUMERICAL_DIVERGENCE"
    assert r7["status"] == "INSUFFICIENT_EVIDENCE_NOT_VALIDATED"
    assert r1["status"] == "INSUFFICIENT_EVIDENCE_NOT_VALIDATED"
    assert old["status"] == "INSUFFICIENT_EVIDENCE_NOT_VALIDATED"
    return {"status": "PASS", "solver_run_called": False, "solver_entered": 0, "BF08": r8["status"], "BF07": r7["status"], "BF01_x_attempt_001_v1_preserved": old["status"]}
if __name__ == "__main__": print(json.dumps(main(), indent=2))
