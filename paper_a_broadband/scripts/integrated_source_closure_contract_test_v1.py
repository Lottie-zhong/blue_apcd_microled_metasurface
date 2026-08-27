from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "authority"


def load(name):
    with (AUTH / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    scope = load("paper_a_integrated_source_closure_contract_v1.json")
    inventory = load("source_asset_inventory.json")
    ensemble = load("source_ensemble_contract.json")
    ablation = load("integrated_ablation_matrix.json")
    validity = load("integrated_validity_contract.json")
    adapter = load("integrated_source_closure_adapter_v2.json")
    audit = load("integrated_source_closure_contract_audit.json")

    assert scope["status"] == "HARD_GATE_CONTRACT_LEVEL"
    assert scope["solver_accounting"] == {"fdtd": 0, "rcwa": 0, "ml": 0, "solver_run_called": False, "solver_entered": 0, "new_admission": False, "hidden_auto_admission": False}
    assert ensemble["primary_wells"]["count"] == 12
    assert len(ensemble["primary_wells"]["centers_nm_source_frame"]) == 12
    assert abs(sum(ensemble["primary_wells"]["weights"]) - 1.0) < 1e-12
    assert ensemble["polarization_cases"]["full_primary_target_cases"] == 24
    assert len(ablation["configs"]) == 4
    assert all(row["status"] == "NOT_RUN" for row in ablation["configs"])
    assert validity["status"] == "HARD_GATE_CONTRACT_LEVEL"
    assert adapter["status"] == "SPECIFICATION_ONLY_NOT_IMPLEMENTED_NOT_AUTHORIZED"
    assert audit["zero_solver_proof"]["fdtd"] == 0
    assert audit["zero_solver_proof"]["rcwa"] == 0
    assert audit["zero_solver_proof"]["ml"] == 0
    assert audit["zero_solver_proof"]["solver_run_called"] is False
    assert audit["zero_solver_proof"]["solver_entered"] == 0

    copied = 0
    for item in inventory["assets"]:
        destination = ROOT.parent / item["destination_path"]
        if item["copied_or_referenced"] == "copied":
            copied += 1
            assert destination.exists(), destination
            assert sha(destination) == item["source_sha256"] == item["destination_sha256"], item["asset_id"]
    assert copied >= 5

    tracked_fsp = subprocess.check_output(["git", "ls-files", "*.fsp"], cwd=ROOT.parent, text=True).splitlines()
    assert not tracked_fsp, "FSP files must remain untracked"
    print("PASS: integrated source closure contract zero-solver tests")
    print("copied_sha256_assets=" + str(copied))
    print("solver_run_called=false solver_entered=0")


if __name__ == "__main__":
    main()
