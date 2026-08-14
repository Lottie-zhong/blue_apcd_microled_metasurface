from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = "H1E1_A_small_N_GLOBAL_015_x"
POL = "x"
REPORT = ROOT / "reports/stage_h1e1_j1_anisotropy"
MANIFEST = json.loads((REPORT / "h1e1_candidate_manifest.json").read_text(encoding="utf-8"))
CHILD = next(x for x in MANIFEST["candidates"] if x["geometry_uid"] == CASE.rsplit("_x", 1)[0])
RUN_FSP = ROOT / "outputs/lp_extended_j1_h1e1/runtime/cases" / CASE / f"{CASE}_attempt_003_run.fsp"
CASE_DIR = RUN_FSP.parent


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod); return mod


def main():
    base = load(ROOT / "scripts/lp_global_h_h1c1a_broadband_v1.py", "h1e1_postfsp_base")
    base.ROOT = ROOT; base.REPORT = REPORT; base.RUNTIME = ROOT / "outputs/lp_extended_j1_h1e1/runtime"; base.ACCOUNTING_PATH = REPORT / "h1e1_solver_accounting.json"; base.MANIFEST_PATH = REPORT / "h1e1_candidate_manifest.json"; base.GRID = [450.0 + .5*i for i in range(9)]; base.H_GLOBAL_NM = 550.0; base.PERIOD_NM = 432.0; base.MATERIAL = "APCD_TIO2_NATIVE_M1"; base.PROJECTOR_ERROR_MAX = .1864961370084426
    if not RUN_FSP.exists(): raise RuntimeError("POSTFSP_RUN_FSP_MISSING")
    runtime = base.load_runtime(); f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
    try:
        f.load(str(RUN_FSP))
        rows, grid = base.extract_broadband(f)
        identity = base.case_identity(CHILD, POL, MANIFEST)
        checkpoint = {"schema": "H1E1_POSTFSP_RECOVERED_CHECKPOINT_V1", "status": "ACCEPTED", "case_id": CASE, "attempt_id": f"{CASE}_attempt_003", "geometry_uid": CHILD["geometry_uid"], "exact_hash": CHILD["exact_hash"], "case_identity": identity, "case_identity_sha256": base.sha256_obj(identity), "geometry": CHILD, "polarization": POL, "physical_contract": MANIFEST["contract"], "physical_contract_sha256": MANIFEST["contract_sha256"], "rows": rows, "grid_audit": grid, "solver_entered": True, "solver_replay": False, "recovery_method": "load_saved_run_fsp_and_extract_only", "run_fsp_path": str(RUN_FSP), "run_fsp_sha256": base.sha256_file(RUN_FSP)}
        tmp = CASE_DIR / "checkpoint.json.tmp"; tmp.write_text(json.dumps(checkpoint, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8"); os.replace(tmp, CASE_DIR / "checkpoint.json")
        print(json.dumps({"status": "ACCEPTED", "case_id": CASE, "solver_replay": False, "rows": len(rows)}, indent=2))
    finally:
        try: f.close()
        except Exception: pass


if __name__ == "__main__": main()
