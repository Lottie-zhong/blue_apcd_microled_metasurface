from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("PAPER_A_ROOT", r"D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1"))
BASE = ROOT / "paper_a_broadband"
REGISTRY = BASE / "reports/integrated_aware_lp_redesign_contract_v1/integrated_candidate_registry_initial.csv"
IC1_BUILDER = BASE / "scripts/ic1_solver_ready_prefsp_builder_v1.py"
API = r"N:/Program Files/ANSYS Inc/v251/Lumerical/api/python"
if API not in sys.path:
    sys.path.insert(0, API)


def load_base_builder():
    spec = importlib.util.spec_from_file_location("ic1_builder_for_iar", IC1_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("IC1_BUILDER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_row(candidate: str) -> dict[str, Any]:
    with REGISTRY.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    matches = [row for row in rows if row.get("geometry_id") == candidate]
    if len(matches) != 1:
        raise RuntimeError(f"CANDIDATE_REGISTRY_CARDINALITY:{candidate}:{len(matches)}")
    row = matches[0]
    numeric = {
        "L1_nm", "W1_nm", "L2_nm", "W2_nm", "A1", "A2", "A_mean", "Delta_A",
        "delta_theta_deg", "D_nm", "theta1_deg", "theta2_deg", "j1_center_x_nm",
        "j1_center_y_nm", "j2_center_x_nm", "j2_center_y_nm", "height_nm", "period_x_nm",
        "period_y_nm", "direct_clearance_nm", "periodic_image_clearance_nm",
        "global_minimum_clearance_nm", "minimum_lateral_feature_nm", "aspect_ratio_H_over_min_feature",
        "distance_from_i03_6d",
    }
    for key in numeric:
        row[key] = float(row[key])
    for key in ("L1_nm", "W1_nm", "L2_nm", "W2_nm", "D_nm", "height_nm", "period_x_nm", "period_y_nm"):
        row[key] = int(round(row[key]))
    return row


def candidate_authorities(module: Any, row: dict[str, Any]) -> dict[str, Any]:
    authorities = module.load_authorities()
    i03 = copy.deepcopy(authorities["i03"])
    candidate = row["geometry_id"]
    i03["source_geometry_id"] = candidate
    i03["source_geometry_hash_sha256"] = row["geometry_hash_sha256"]
    i03["period_nm"] = {"Px": float(row["period_x_nm"]), "Py": float(row["period_y_nm"])}
    i03["unit_cell"]["height_nm"] = float(row["height_nm"])
    i03["unit_cell"]["pillar_1"].update({
        "L_nm": float(row["L1_nm"]), "W_nm": float(row["W1_nm"]),
        "rotation_z_deg": float(row["theta1_deg"]),
        "center_offset_nm": [float(row["j1_center_x_nm"]), float(row["j1_center_y_nm"])],
    })
    i03["unit_cell"]["pillar_2"].update({
        "L_nm": float(row["L2_nm"]), "W_nm": float(row["W2_nm"]),
        "rotation_z_deg": float(row["theta2_deg"]),
        "center_offset_nm": [float(row["j2_center_x_nm"]), float(row["j2_center_y_nm"])],
    })
    i03["geometry_only_clearance"] = {
        "direct_clearance_nm": float(row["direct_clearance_nm"]),
        "periodic_image_clearance_nm": float(row["periodic_image_clearance_nm"]),
        "global_minimum_clearance_nm": float(row["global_minimum_clearance_nm"]),
        "overlap": False,
        "threshold_authority": "inherited IC1/I03 geometry authority; no new threshold",
    }
    for cell in i03["cells"]:
        cx, cy = map(float, cell["cell_center_nm"])
        for number, length, width, xoff, yoff, angle in (
            (1, row["L1_nm"], row["W1_nm"], row["j1_center_x_nm"], row["j1_center_y_nm"], row["theta1_deg"]),
            (2, row["L2_nm"], row["W2_nm"], row["j2_center_x_nm"], row["j2_center_y_nm"], row["theta2_deg"]),
        ):
            pillar = cell[f"pillar_{number}"]
            pillar.update({
                "center_nm": [cx + float(xoff), cy + float(yoff)],
                "length_nm": float(length), "width_nm": float(width),
                "rotation_z_deg": float(angle), "height_nm": float(row["height_nm"]),
                "bottom_z_nm": 975.0, "top_z_nm": 1500.0,
                "material": "APCD_TIO2_NATIVE_M1",
            })
    authorities["i03"] = i03
    return authorities


def source_adder(case_id: str, phi_deg: float):
    def add_source(fdtd: Any, authorities: dict[str, Any]) -> None:
        c, source = authorities["monitor"]["source_grid"], authorities["z"]["ic1_source"]
        fdtd.setglobalmonitor("frequency points", int(c["points"]))
        fdtd.setglobalmonitor("use wavelength spacing", True)
        fdtd.adddipole()
        fdtd.set("name", case_id)
        for key, value in (
            ("x", float(source["position_nm"][0]) * 1e-9),
            ("y", float(source["position_nm"][1]) * 1e-9),
            ("z", float(source["position_nm"][2]) * 1e-9),
            ("theta", 90.0), ("phi", phi_deg),
            ("wavelength start", float(c["start_nm"]) * 1e-9),
            ("wavelength stop", float(c["stop_nm"]) * 1e-9),
            ("amplitude", 1.0), ("phase", 0.0),
        ):
            fdtd.setnamed(case_id, key, value)
    return add_source


def expected_geometry(module: Any, row: dict[str, Any]) -> dict[str, dict[str, float]]:
    expected = {}
    for cell in module.load_authorities()["i03"]["cells"]:
        cx, cy = map(float, cell["cell_center_nm"])
        i, j = int(cell["i"]), int(cell["j"])
        for number, length, width, xoff, yoff, angle in (
            (1, row["L1_nm"], row["W1_nm"], row["j1_center_x_nm"], row["j1_center_y_nm"], row["theta1_deg"]),
            (2, row["L2_nm"], row["W2_nm"], row["j2_center_x_nm"], row["j2_center_y_nm"], row["theta2_deg"]),
        ):
            name = module.pillar_name(i, j, number)
            expected[name] = {"x": cx + float(xoff), "y": cy + float(yoff), "x span": float(length), "y span": float(width), "rotation 1": float(angle)}
    return expected


def validate_candidate(module: Any, readback: dict[str, Any], row: dict[str, Any], phi_deg: float) -> dict[str, Any]:
    inherited = module.validate_readback(readback)
    got = {item["name"]: item for item in readback["physics_semantic"]["i03"]}
    expected = expected_geometry(module, row)
    geometry_checks = {}
    for name, target in expected.items():
        actual = got.get(name, {})
        geometry_checks[name] = all(abs(float(actual.get(key, float("nan"))) - value) <= 1e-6 for key, value in target.items()) and actual.get("material") == "APCD_TIO2_NATIVE_M1"
    source = readback["physics_semantic"]["source"]
    source_check = abs(float(source["phi"]) - phi_deg) <= 1e-6 and abs(float(source["z"]) * 1e9 + 171.5) <= 1e-6
    # The inherited IC1 validator contains an intentional phi=0 x-source
    # assertion.  Keep every shared architecture check, but replace only that
    # orientation-specific assertion with the candidate's x/y source check.
    checks = {**{key: bool(value) for key, value in inherited.items() if key not in {"all", "source"}}, "candidate_geometry": all(geometry_checks.values()), "source_orientation": source_check}
    checks["all"] = all(checks.values())
    return {"checks": checks, "per_object_geometry": geometry_checks, "expected_record": row, "source_phi_deg": phi_deg}


def build(candidate: str, case_id: str, polarization: str, output: Path) -> dict[str, Any]:
    if output.exists():
        raise RuntimeError(f"REFUSE_OVERWRITE_PREFSP:{output}")
    row = read_row(candidate)
    if polarization not in {"x", "y"}:
        raise ValueError(polarization)
    module = load_base_builder()
    module.CASE_ID = case_id
    module.V2_TIME_PROBE = "ic1_v2_time_probe"
    module.pillar_name = lambda i, j, p: f"{candidate.lower()}_i{module.tag(i)}_j{module.tag(j)}_p{p}"
    authorities = candidate_authorities(module, row)
    module.load_authorities = lambda: authorities
    module.add_source = source_adder(case_id, 0.0 if polarization == "x" else 90.0)
    result = module.build_from_authority(output)
    readback = module.readback(output)
    validation = validate_candidate(module, readback, row, 0.0 if polarization == "x" else 90.0)
    if not validation["checks"]["all"]:
        raise RuntimeError(f"IAR_SETUP_VALIDATION_FAILED:{case_id}:{json.dumps(validation, sort_keys=True)}")
    return {
        "schema": "PAPER_A_INTEGRATED_AWARE_LP_SETUP_ONLY_V1",
        "status": "PASS_SOLVER_READY_PREFSP",
        "case_id": case_id, "candidate_id": candidate, "polarization": polarization,
        "pre_fsp": {"path": str(output), "sha256": module.sha_file(output), "size_bytes": output.stat().st_size},
        "candidate_registry": row,
        "candidate_geometry_hash_authority": row["geometry_hash_sha256"],
        "readback": readback,
        "validation": validation,
        "solver_counters": {"solver_run_called": False, "solver_entered": 0, "active_fdtd": 0, "rcwa": 0, "ml": 0, "hidden_auto_admission": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--polarization", choices=("x", "y"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.candidate, args.case_id, args.polarization, args.output), indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
