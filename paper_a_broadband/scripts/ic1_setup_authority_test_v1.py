from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "authority"


def load(name: str) -> dict:
    return json.loads((AUTH / name).read_text(encoding="utf-8"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    main_a = load("paper_a_ic1_finite_integrated_canary_model_authority_v1.json")
    mesa = load("ic1_finite_mesa_authority.json")
    i03 = load("ic1_i03_5x5_replication_authority.json")
    z = load("ic1_absolute_z_layout.json")
    dom = load("ic1_domain_pml_authority.json")
    mon = load("ic1_monitor_contract.json")
    adapter = load("ic1_integrated_validity_adapter.json")
    readback = load("ic1_setup_readback.json")
    ready = load("ic1_canary_readiness.json")

    check(main_a["task_id"] == "PAPER_A_IC1_FINITE_INTEGRATED_CANARY_MODEL_AUTHORITY_V1", "main schema/task mismatch")
    for name, entry in main_a["source_provenance"].items():
        source_path = ROOT.parent / entry["path"]
        check(source_path.exists(), f"missing provenance source: {name}")
        check(sha256(source_path) == entry["sha256"].upper(), f"provenance SHA mismatch: {name}")
    solver = main_a["solver_accounting"]
    check(solver == {"NEW_FDTD_BUDGET": 0, "solver_run_called": False, "solver_entered": 0, "FDTD": 0, "RCWA": 0, "ML": 0, "hidden_auto_admission": False}, "solver accounting is not zero")
    check(mesa["mesa"]["x_nm"] == 3000.0 and mesa["mesa"]["y_nm"] == 3000.0, "mesa mismatch")
    check(i03["replication"]["Nx"] == 5 and i03["replication"]["Ny"] == 5, "replication mismatch")
    check(len(i03["cells"]) == 25, "not 25 full cells")
    check(all(c["i"] in [-2, -1, 0, 1, 2] and c["j"] in [-2, -1, 0, 1, 2] for c in i03["cells"]), "indices not -2..+2")
    for cell in i03["cells"]:
        i, j = cell["i"], cell["j"]
        check(cell["cell_center_nm"] == [432.0 * i, 432.0 * j], f"cell center mismatch: {i},{j}")
        check(cell["pillar_1"]["center_nm"] == [432.0 * i, 432.0 * j + 110.0], f"pillar 1 mismatch: {i},{j}")
        check(cell["pillar_2"]["center_nm"] == [432.0 * i, 432.0 * j - 110.0], f"pillar 2 mismatch: {i},{j}")
    check(i03["source_geometry_hash_sha256"] == "b818fd28e0535053a21940f40a9b45cfb0b9252aba9e0158be2496fba87eea06", "I03 hash mismatch")
    check(z["i03"]["bottom_z_nm"] == z["mdc"]["top_z_nm"] == 975.0 and z["i03"]["contact_gap_nm"] == 0.0, "direct contact mismatch")
    check(z["i03"]["spacer_237nm_used"] is False, "237 nm spacer imported")
    check(z["ic1_source"]["position_nm"] == [0.0, 0.0, -171.5], "IC1 source mismatch")
    check(z["ic1_source"]["well_id"] == "primary_well_01", "top-well source mismatch")
    check(len(z["mqw"]["regions"]) == 12 and abs(sum(r["ensemble_weight"] for r in z["mqw"]["regions"]) - 1.0) < 1e-12, "MQW registration mismatch")
    check(z["mqw"]["centers_nm"] == [-171.5, -190.5, -209.5, -228.5, -247.5, -266.5, -285.5, -304.5, -323.5, -342.5, -361.5, -380.5], "MQW centers mismatch")
    check(z["mdc"]["interfaces_z_nm"] == [0.0, 44.0, 123.0, 167.0, 246.0, 290.0, 606.0, 650.0, 729.0, 773.0, 852.0, 896.0, 975.0], "MDC interfaces mismatch")
    check(dom["boundary_condition"]["periodic_xy"] is False, "periodic xy present")
    check(dom["domain_nm"] == {"x_span": 6000.0, "y_span": 6000.0, "z_span": 4200.0, "x_bounds": [-3000.0, 3000.0], "y_bounds": [-3000.0, 3000.0], "z_bounds": [-1600.0, 2600.0]}, "domain mismatch")
    check(dom["pml"]["layers"] == 12, "PML layer authority missing")
    check(dom["physical_collision_checks"] == {"pml_intersects_physical_geometry": False, "source_in_pml": False, "monitors_in_pml": False}, "PML collision QA failed")
    check(len(mon["closed_flux_box"]["faces"]) == 6, "closed flux box is not six-face")
    check(mon["near_to_far"]["record_complex_components"] == ["Ex", "Ey"], "far-field components missing")
    check(mon["source_grid"] == {"start_nm": 400.0, "stop_nm": 500.0, "points": 101, "source_type": "broadband_electric_dipole", "emitter_weighting_applied": False}, "source grid mismatch")
    check(adapter["parent_authority"]["divergence_gate_unchanged"] is True and adapter["no_threshold_invention"] is True, "V2 adapter weakens parent")
    check(readback["solver_enterable_fsp_created"] is False and all(readback["qa"].values()), "geometry-only readback failed")
    check(ready["status"] == "PAPER_A_IC1_INTEGRATED_CANARY_READY", "readiness not ready")
    check("EMITTER_SPECTRUM_UNRESOLVED" in ready["production_hard_gates_retained"], "production emitter gate missing")
    check(main_a["production_boundary"]["W_emit_status"] == "EMITTER_SPECTRUM_UNRESOLVED", "W_emit was incorrectly resolved")
    check(main_a["solver_accounting"]["hidden_auto_admission"] is False, "hidden admission enabled")

    tracked = subprocess.run(["git", "ls-files", "*.fsp"], cwd=ROOT.parent, capture_output=True, text=True, check=True)
    check(not tracked.stdout.strip(), "tracked FSP detected")
    # Independent deterministic clearance replay for the canonical I03 rectangles.
    l1, w1, t1 = 264.0, 87.0, 0.0
    l2, w2, t2 = 194.0, 80.0, math.radians(85.819861293)
    p2_bbox_y = abs(l2 * math.sin(t2)) / 2.0 + abs(w2 * math.cos(t2)) / 2.0
    intra = 220.0 - w1 / 2.0 - p2_bbox_y
    periodic = 212.0 - w1 / 2.0 - p2_bbox_y
    check(abs(intra - 76.84233977127985) < 1e-9, "I03 intra-cell clearance replay mismatch")
    check(abs(periodic - 68.84233977127985) < 1e-9, "I03 adjacent-cell clearance replay mismatch")
    print("PASS: IC1 finite integrated canary zero-solver authority tests")
    print("mesa_nm=3000x3000 i03=5x5 direct_contact_z_nm=975..1500")
    print("domain_nm=6000x6000x4200 periodic_xy=False")
    print("solver_run_called=false solver_entered=0 readiness=PAPER_A_IC1_INTEGRATED_CANARY_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
