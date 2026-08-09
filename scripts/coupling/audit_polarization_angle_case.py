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
LUMAPI_ROOT = Path(r"N:\\Program Files\\ANSYS Inc\\v251\\Lumerical\\api\\python")
if str(LUMAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(LUMAPI_ROOT))


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


def close(a, b, tol=1e-12):
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
        solver = {prop: one(fdtd, "FDTD", prop) for prop in ("dimension", "x span", "y span", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "kx", "ky")}
        source = {prop: one(fdtd, "source_incident", prop) for prop in ("plane wave type", "injection axis", "direction", "polarization angle", "z", "wavelength start", "wavelength stop", "angle theta", "angle phi")}
        monitors = {name: {prop: one(fdtd, name, prop) for prop in ("monitor type", "z", "x span", "y span")} for name in ("reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor")}
        objects = {
            "mdc_layer_01": {"material": one(fdtd, "mdc_layer_01", "material"), "z min": one(fdtd, "mdc_layer_01", "z min"), "z max": one(fdtd, "mdc_layer_01", "z max")},
            "extra_spacer_01": {"material": one(fdtd, "extra_spacer_01", "material"), "z min": one(fdtd, "extra_spacer_01", "z min"), "z max": one(fdtd, "extra_spacer_01", "z max")},
            "NP_pillar_0": {"material": one(fdtd, "NP_pillar_0", "material"), "z min": one(fdtd, "NP_pillar_0", "z min"), "z max": one(fdtd, "NP_pillar_0", "z max")},
            "NP_pillar_5": {"material": one(fdtd, "NP_pillar_5", "material"), "z min": one(fdtd, "NP_pillar_5", "z min"), "z max": one(fdtd, "NP_pillar_5", "z max")},
        }
        materials = []
        names = fdtd.getmaterial()
        names = scalar(names)
        if isinstance(names, str):
            materials = [item.strip() for item in names.splitlines() if item.strip()]
        else:
            materials = [str(item).strip() for item in names if str(item).strip()]
    finally:
        fdtd.close()
    pre = setup["readback"]
    state = setup["state"]
    checks = {
        "solver_completed": runtime["solver_completed"] is True,
        "dimension_3d": solver["dimension"] == "3D",
        "boundary_x": solver["x min bc"] == ("Bloch" if abs(float(state["ux"])) > 0 else "Periodic") and solver["x max bc"] == ("Bloch" if abs(float(state["ux"])) > 0 else "Periodic"),
        "boundary_y": solver["y min bc"] == "Periodic" and solver["y max bc"] == "Periodic",
        "kx_readback": abs(float(solver["kx"]) - float(state["real_kx"])) <= max(abs(float(state["real_kx"])), 1.0) * 1e-9 if abs(float(state["ux"])) > 0 else True,
        "ky_readback": solver["ky"] is None or abs(float(solver["ky"])) <= 1e-12,
        "source_branch": close(source["polarization angle"], state["polarization_angle_deg"]),
        "source_theta_identity": close(source["angle theta"], pre["source"]["angle theta"], 1e-10),
        "source_phi_zero": close(source["angle phi"], 0.0),
        "source_wavelength": close(source["wavelength start"], 450e-9, 1e-9) and close(source["wavelength stop"], 450e-9, 1e-9),
        "native_materials": all(item in materials for item in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")),
        "extra_spacer_material": objects["extra_spacer_01"]["material"] == "APCD_SIO2_NATIVE_M1",
        "extra_spacer_237": close((objects["extra_spacer_01"]["z max"] - objects["extra_spacer_01"]["z min"]) * 1e9, 237.0, 1e-9),
        "pillar_height_500": close((objects["NP_pillar_0"]["z max"] - objects["NP_pillar_0"]["z min"]) * 1e9, 500.0, 1e-9) and close((objects["NP_pillar_5"]["z max"] - objects["NP_pillar_5"]["z min"]) * 1e9, 500.0, 1e-9),
        "monitor_identity": all(name in monitors for name in ("reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor")),
        "no_replay": runtime["attempt_id"] == "attempt_001" and len(list((out / "runtime").glob("attempt_*"))) == 1,
    }
    audit = {"schema_version": "stage_a_polarization_post_fsp_audit_v1", "case_id": setup["case_id"], "control_group": setup["case"]["control_group"], "post_fsp_path": str(post), "post_fsp_sha256": runtime["post_fsp_sha256"], "pre_fsp_entry_sha256": runtime["pre_fsp_entry_sha256"], "pre_fsp_current_sha256": runtime["pre_fsp_current_sha256"], "pre_fsp_post_entry_mutation": runtime["pre_fsp_post_entry_mutation"], "readback": {"solver": solver, "source": source, "monitors": monitors, "objects": objects, "material_names": materials}, "identity_checks": checks, "pass": all(checks.values())}
    (out / "post_fsp_readback.json").write_text(json.dumps(audit["readback"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "post_fsp_identity_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": audit["case_id"], "pass": audit["pass"], "identity_checks": checks}, ensure_ascii=False, indent=2))
    if not audit["pass"]:
        raise SystemExit("POST_FSP_IDENTITY_FAIL")


if __name__ == "__main__":
    main()
