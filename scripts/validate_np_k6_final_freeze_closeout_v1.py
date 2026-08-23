from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_final_freeze_closeout_v1"

def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))

def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True, stdout=subprocess.PIPE, check=True).stdout.strip()

freeze = load("freeze_manifest.json")
provider = load("provider_manifest.json")
figure = json.loads((ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_v1/figure_validator_report.json").read_text(encoding="utf-8"))
with (ROOT / "outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv").open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

errors = []
if freeze["status"] != "NP_K6_FROZEN_FORWARD_PROVIDER_COUPLING_HANDOFF_READY": errors.append("freeze status")
if git("branch", "--show-current") != "work/np-k6-mdc-v1": errors.append("branch")
if freeze["repository"].get("freeze_input_head") != "a87042a74060cf88a0de70ee2b5e346785015d3f": errors.append("freeze input HEAD")
stored_head = freeze["repository"].get("head")
ancestor = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", stored_head, "HEAD"], check=False)
if ancestor.returncode != 0: errors.append("final HEAD ancestry")
if git("rev-list", "--left-right", "--count", "HEAD...@{upstream}") not in {"0\t0", "0 0"}: errors.append("divergence")
if len(rows) != 484 or len({r["geometry_id"] for r in rows}) != 22 or len({(r["geometry_id"], r["polarization"]) for r in rows}) != 44: errors.append("HF authority counts")
if provider["scope"]["u_x"] != [0.0] or provider["scope"]["k_y"] != 0.0: errors.append("normal incidence")
if provider["components_are_distinct"] is not True: errors.append("provider distinction")
if figure.get("status") != "PASS" or figure.get("solver_calls") != 0 or figure.get("rcwa_calls") != 0 or figure.get("ml_training") != 0: errors.append("figure zero-compute evidence")
if any(value != 0 for key, value in freeze["zero_solver_audit"].items() if key != "basis"): errors.append("zero solver audit")
print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors, "solver_delta": freeze["zero_solver_audit"]}, indent=2))
raise SystemExit(0 if not errors else 1)
