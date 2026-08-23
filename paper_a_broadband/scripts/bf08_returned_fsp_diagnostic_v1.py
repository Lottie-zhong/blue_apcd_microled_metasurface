from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1")
RUNTIME = ROOT / "paper_a_broadband/runtime/search_anisotropy_balanced_truth_v1/cases"
OUT = ROOT / "paper_a_broadband/reports/lp_anisotropy_balanced_conditional_truth_v1/bf08_returned_fsp_diagnostic.json"
sys.path.insert(0, r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python")
import lumapi


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


records = []
for case_id in ("BF08_x", "BF08_y"):
    case_dir = RUNTIME / case_id
    run_fsp = case_dir / f"{case_id}_run.fsp"
    attempt = json.loads((case_dir / "attempt_provenance.json").read_text(encoding="utf-8"))
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(run_fsp))
        transmission = np.real(np.asarray(f.transmission("T")).reshape(-1))
        wavelength = np.linspace(430.0, 470.0, len(transmission))
        records.append(
            {
                "case_id": case_id,
                "run_fsp": str(run_fsp),
                "run_fsp_sha256": sha(run_fsp),
                "attempt_run_fsp_sha256": attempt.get("run_fsp_sha256"),
                "hash_match": sha(run_fsp) == attempt.get("run_fsp_sha256"),
                "count": len(transmission),
                "minimum": {"wavelength_nm": float(wavelength[int(np.argmin(transmission))]), "T": float(np.min(transmission))},
                "negative_points": [
                    {"wavelength_nm": float(wl), "T": float(value)}
                    for wl, value in zip(wavelength, transmission)
                    if value < 0
                ],
                "formal_435_465": [
                    {"wavelength_nm": float(wl), "T": float(value)}
                    for wl, value in zip(wavelength, transmission)
                    if 435.0 <= wl <= 465.0
                ],
            }
        )
    finally:
        f.close()

output = {
    "schema": "PAPER_A_LP_BF08_RETURNED_FSP_DIAGNOSTIC_V1",
    "solver_run_called": False,
    "solver_replay": False,
    "source": "immutable entered=true returned run-FSP",
    "cases": records,
}
OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
print(json.dumps(output, indent=2))
