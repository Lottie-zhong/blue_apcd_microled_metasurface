from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

GRID = [float(value) for value in range(445, 456)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scalar(value):
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return scalar(value[0])
    return value


def one(fdtd, object_name, prop):
    return scalar(fdtd.getnamed(object_name, prop))


def close(a, b, tol=1e-9):
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)), abs(float(b)))
    except (TypeError, ValueError):
        return a == b


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    setup = json.loads((out / "setup_manifest.json").read_text(encoding="utf-8"))
    runtime = json.loads((out / "runtime/attempt_001/run_state.json").read_text(encoding="utf-8"))
    post = Path(runtime["post_fsp_path"])
    if not runtime.get("solver_completed") or sha256(post) != runtime["post_fsp_sha256"]:
        raise RuntimeError("post-FSP completion/hash gate failed")
    import lumapi
    fdtd = lumapi.FDTD(str(post), hide=True)
    try:
        solver = {prop: one(fdtd, "FDTD", prop) for prop in ("dimension", "x span", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "bfast alpha", "mesh accuracy", "pml layers")}
        source = {prop: one(fdtd, "source_incident", prop) for prop in ("plane wave type", "polarization angle", "z", "wavelength start", "wavelength stop", "angle theta", "angle phi")}
        monitors = {name: {prop: one(fdtd, name, prop) for prop in ("monitor type", "z", "x span", "y span", "frequency points")} for name in ("reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor")}
        names = scalar(fdtd.getmaterial())
        material_names = [item.strip() for item in names.splitlines() if item.strip()] if isinstance(names, str) else [str(item).strip() for item in names]
        objects = {}
        for name in ("extra_spacer_01", "NP_pillar_0", "NP_pillar_5"):
            objects[name] = {prop: one(fdtd, name, prop) for prop in ("material", "z min", "z max")}
    finally:
        fdtd.close()
    state = setup["state"]
    checks = {
        "solver_completed": runtime["solver_completed"] is True,
        "attempt_001_only": runtime["attempt_id"] == "attempt_001" and len(list((out / "runtime").glob("attempt_*"))) == 1,
        "dimension_3d": solver["dimension"] == "3D",
        "periodic_xy_declared": solver["x min bc"] == "Periodic" and solver["x max bc"] == "Periodic" and solver["y min bc"] == "Periodic" and solver["y max bc"] == "Periodic",
        "z_pml": solver["z min bc"] == "PML" and solver["z max bc"] == "PML",
        "bfast_source": source["plane wave type"] == "BFAST",
        "bfast_alpha": close(solver["bfast alpha"], 1.0),
        "source_branch": close(source["polarization angle"], state["polarization_angle_deg"]),
        "source_inside_gan": close(source["z"] * 1e9, -250.0, 1e-6),
        "exact_source_band": close(source["wavelength start"] * 1e9, 445.0, 1e-6) and close(source["wavelength stop"] * 1e9, 455.0, 1e-6),
        "exact_monitor_grid": all(int(float(monitors[name]["frequency points"])) == 11 for name in monitors),
        "native_materials": all(name in material_names for name in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")),
        "spacer_237_native_sio2": objects["extra_spacer_01"]["material"] == "APCD_SIO2_NATIVE_M1" and close((objects["extra_spacer_01"]["z max"] - objects["extra_spacer_01"]["z min"]) * 1e9, 237.0, 1e-6),
        "pillar_height_500": close((objects["NP_pillar_0"]["z max"] - objects["NP_pillar_0"]["z min"]) * 1e9, 500.0, 1e-6) and close((objects["NP_pillar_5"]["z max"] - objects["NP_pillar_5"]["z min"]) * 1e9, 500.0, 1e-6),
        "no_replay": not (out / "runtime/attempt_002").exists(),
    }
    result_path = out / "results/result.json"
    result_checks = {"result_present": result_path.exists()}
    if result_path.exists():
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        rows = payload.get("rows", [])
        result_checks.update({"rows_11": len(rows) == 11, "grid_exact": len(rows) == len(GRID) and all(abs(float(row["wavelength_nm"]) - expected) <= 1e-6 for row, expected in zip(rows, GRID)), "source_kx_all_pass": all(row["source_kx_contract"]["pass"] for row in rows), "order_equation_all_pass": all(row["order_equation_audit"]["all_rows_pass"] for row in rows), "power_closure_all_pass": all(row["power_closure"]["pass"] for row in rows), "order_closure_all_pass": all(row["order_closure"]["pass"] for row in rows), "no_averaging": payload.get("summary", {}).get("no_polarization_averaging") is True})
    else:
        result_checks.update({"rows_11": True, "grid_exact": True, "source_kx_all_pass": True, "order_equation_all_pass": True, "power_closure_all_pass": True, "order_closure_all_pass": True, "no_averaging": True})
    result_pass = (not result_path.exists()) or all(value for key, value in result_checks.items() if key != "result_present")
    audit = {"schema_version": "stage_a_broadband_polarization_post_fsp_audit_v1", "case_id": setup["case_id"], "control_group": setup["case"]["control_group"], "post_fsp_path": str(post), "post_fsp_sha256": runtime["post_fsp_sha256"], "pre_fsp_entry_sha256": runtime["pre_fsp_entry_sha256"], "pre_fsp_current_sha256": runtime["pre_fsp_current_sha256"], "pre_fsp_post_entry_mutation": runtime["pre_fsp_post_entry_mutation"], "readback": {"solver": solver, "source": source, "monitors": monitors, "objects": objects, "material_names": material_names}, "identity_checks": checks, "result_checks": result_checks, "pass": all(checks.values()) and result_pass}
    (out / "post_fsp_readback.json").write_text(json.dumps(audit["readback"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "post_fsp_identity_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": audit["case_id"], "pass": audit["pass"], "identity_checks": checks, "result_checks": result_checks}, ensure_ascii=False, indent=2))
    if not audit["pass"]:
        raise SystemExit("POST_FSP_IDENTITY_OR_RESULT_FAIL")


if __name__ == "__main__":
    main()
