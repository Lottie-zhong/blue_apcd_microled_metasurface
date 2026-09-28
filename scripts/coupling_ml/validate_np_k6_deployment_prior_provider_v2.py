from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT = ROOT / "outputs" / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2"
HF = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv")
OOF = OUT / "logo_oof_predictions.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    manifest = json.loads((OUT / "NP_K6_DEPLOYMENT_PRIOR_PROVIDER_V2_MANIFEST.json").read_text(encoding="utf-8"))
    gate = json.loads((OUT / "v2_acceptance_gate.json").read_text(encoding="utf-8"))
    assert manifest["source_authority"]["commit"] == "c8e6eb4"
    assert manifest["source_authority"]["hf22_sha256"].lower() == "5c5dca90928498c927663ad3eedbf502394a68c741feef836195573846ba1599"
    assert sha256(HF).lower() == manifest["source_authority"]["hf22_sha256"].lower()
    with OOF.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 484
    assert len({r["geometry_id"] for r in rows}) == 22
    assert len({(r["geometry_id"], r["polarization"]) for r in rows}) == 44
    assert len({int(r["wavelength_nm"]) for r in rows}) == 11
    assert manifest["solver_invocations"] == 0
    assert manifest["coupling_h1_errors_read"] is False
    assert gate["accepted"] is False
    assert gate["full_order_gate_pass"] is False
    assert not (OUT / "deployment_model.npz").exists()
    print(json.dumps({"validator": "PASS", "status": manifest["status"], "rows": len(rows), "solver_invocations": 0, "deployment_fit": "not_run_gate_failed"}, indent=2))


if __name__ == "__main__":
    main()
