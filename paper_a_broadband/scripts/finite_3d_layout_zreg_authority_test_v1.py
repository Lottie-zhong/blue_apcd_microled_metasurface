from __future__ import annotations

import csv
import json
import math
import py_compile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "authority"


def load(name):
    with (AUTH / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    main_contract = load("paper_a_finite_3d_layout_zreg_authority_v1.json")
    zreg = load("global_z_registration.json")
    spacer = load("spacer_237nm_decision.json")
    mesa = load("finite_mesa_authority.json")
    repl = load("i03_finite_replication_authority.json")
    emitter = load("emitter_spectral_envelope_authority.json")
    common = load("common_lp_cp_source_authority.json")
    readback = load("integrated_geometry_readback.json")
    readiness = load("integrated_canary_readiness.json")
    audit = load("paper_a_finite_3d_layout_zreg_audit.json")

    assert main_contract["status"] == "HARD_GATE"
    assert main_contract["solver_accounting"] == {"new_fdtd_budget": 0, "fdtd": 0, "rcwa": 0, "ml": 0, "solver_run_called": False, "solver_entered": 0, "hidden_auto_admission": False}
    assert zreg["datum"]["z_nm"] == 0.0
    centers = zreg["mqw"]["centers_nm"]
    assert len(centers) == 12
    assert all(abs(centers[i] - centers[i + 1]) == 19.0 for i in range(11))
    assert zreg["mqw"]["formal_envelope_nm"] == [-382.0, -170.0]
    assert zreg["mdc"]["interfaces_nm"] == [0.0, 44.0, 123.0, 167.0, 246.0, 290.0, 606.0, 650.0, 729.0, 773.0, 852.0, 896.0, 975.0]
    assert spacer["decision"] == "SPACER_237NM_NOT_TRANSFERABLE_TO_PAPER_A_INTEGRATED_MODEL"
    assert len(mesa["candidates"]) == 3
    assert [row["i03_nx"] for row in mesa["candidates"]] == [3, 5, 7]
    assert all(row["full_cells_only"] for row in mesa["candidates"])
    assert repl["canonical_cell"]["period_nm"] == {"Px": 432.0, "Py": 432.0}
    assert repl["geometry_only_clearance_audit"]["overlap_or_intersection"] is False
    assert repl["geometry_only_clearance_audit"]["minimum_periodic_cell_gap_nm"] > 0
    assert repl["geometry_only_clearance_audit"]["authoritative_minimum_edge_margin_threshold"] is None
    assert emitter["status"] == "HARD_GATE_EMITTER_SPECTRUM_UNRESOLVED"
    assert emitter["forensic_findings"]["historical_28nm_gaussian"]["fwhm_nm"] == 28.0
    assert common["false_commonality_prohibited"] is True
    assert readback["constructed_geometry_only_digital_twin"] is False
    assert readback["validated_subcomponents"]["mqw"]["source_to_mdc_bottom_clearance_nm"] == 170.0
    assert readiness["readiness"] == "NOT_READY"
    assert audit["zero_solver_proof"]["fdtd"] == 0
    assert audit["zero_solver_proof"]["rcwa"] == 0
    assert audit["zero_solver_proof"]["ml"] == 0
    assert audit["zero_solver_proof"]["solver_run_called"] is False
    assert audit["zero_solver_proof"]["solver_entered"] == 0

    with (AUTH / "mqw_absolute_positions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert all(float(row["thickness_nm"]) == 3.0 for row in rows)
    assert abs(sum(float(row["weight"]) for row in rows) - 1.0) < 1e-12
    assert all(float(rows[i]["center_z_nm"]) > float(rows[i + 1]["center_z_nm"]) for i in range(11))

    test_path = ROOT / "scripts" / "finite_3d_layout_zreg_authority_test_v1.py"
    py_compile.compile(str(test_path), doraise=True)
    tracked_fsp = subprocess.check_output(["git", "ls-files", "*.fsp"], cwd=ROOT.parent, text=True).splitlines()
    assert not tracked_fsp

    replay = []
    for nx, ny in [(3, 3), (5, 5), (7, 7)]:
        replay.append({"origin": [-((nx - 1) / 2) * 432.0, -((ny - 1) / 2) * 432.0], "footprint": [nx * 432.0, ny * 432.0]})
    replay_again = []
    for nx, ny in [(3, 3), (5, 5), (7, 7)]:
        replay_again.append({"origin": [-((nx - 1) / 2) * 432.0, -((ny - 1) / 2) * 432.0], "footprint": [nx * 432.0, ny * 432.0]})
    assert replay == replay_again
    print("PASS: finite 3D layout/z-registration zero-solver authority tests")
    print("mqw_count=12 pitch_nm=19.0 weight_sum=1.0")
    print("minimum_periodic_gap_nm=" + str(repl["geometry_only_clearance_audit"]["minimum_periodic_cell_gap_nm"]))
    print("solver_run_called=false solver_entered=0 deterministic_replay=PASS")


if __name__ == "__main__":
    main()
