from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from apcd_coupling.joint_stack_builder import build_joint_case
from apcd_coupling.joint_case_schema import canonical_hash

CASE_ID = "STAGE_A_450NM_X_UX0_TEXTRA0"
MDC_COMMIT = "489b54e43bbf2c08ce030a945b9d4b70ee7550f2"
NP_COMMIT = "7a8588f6b5a1c96d88813f60406d418b488135fd"
DEFAULT_HELPER_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def load_material_helper(helper_root: Path):
    sys.path.insert(0, str(helper_root / "scripts"))
    return importlib.import_module("apcd_native_materials")


def one(fdtd: Any, object_name: str, prop: str) -> Any:
    value = fdtd.getnamed(object_name, prop)
    if hasattr(value, "tolist"):
        value = value.tolist()
    return value


def material_names(fdtd: Any) -> list[str]:
    raw = fdtd.getmaterial()
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, str):
        return [x.strip() for x in raw.splitlines() if x.strip()]
    return [str(x).strip() for x in raw if str(x).strip()]


def build_fsp(case: dict[str, Any], prefsp: Path, helper_root: Path) -> None:
    import lumapi
    helper = load_material_helper(helper_root)
    fdtd = lumapi.FDTD(hide=True)
    try:
        for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"):
            helper.register_lumerical_sampled_material(fdtd, material_id)
        fdtd.addfdtd()
        fdtd.set("dimension", "3D")
        fdtd.set("x span", 1740e-9)
        fdtd.set("y span", 290e-9)
        fdtd.set("z min", -600e-9)
        fdtd.set("z max", 2175e-9)
        for prop, value in (("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML")):
            fdtd.set(prop, value)
        for prop, value in (("mesh accuracy", 2), ("pml layers", 8), ("simulation time", 1e-12), ("auto shutoff min", 1e-5), ("dt stability factor", 0.99)):
            fdtd.set(prop, value)

        substrate = next(x for x in case["objects"] if x["role"] == "gan_substrate")
        fdtd.addrect()
        fdtd.set("name", "GaN_substrate")
        fdtd.set("x span", 1740e-9)
        fdtd.set("y span", 290e-9)
        fdtd.set("z min", substrate["z_min_nm"] * 1e-9)
        fdtd.set("z max", substrate["z_max_nm"] * 1e-9)
        fdtd.set("material", substrate["material_id"])
        for obj in case["objects"]:
            if obj["role"] != "mdc_layer":
                continue
            fdtd.addrect()
            fdtd.set("name", f"MDC_layer_{int(obj['index']):02d}")
            fdtd.set("x span", 1740e-9)
            fdtd.set("y span", 290e-9)
            fdtd.set("z min", obj["z_min_nm"] * 1e-9)
            fdtd.set("z max", obj["z_max_nm"] * 1e-9)
            fdtd.set("material", obj["material_id"])
        for obj in case["objects"]:
            if obj["role"] != "np_pillar":
                continue
            fdtd.addcircle()
            fdtd.set("name", f"NP_pillar_{int(obj['index'])}")
            fdtd.set("x", obj["x_nm"] * 1e-9)
            fdtd.set("y", obj["y_nm"] * 1e-9)
            fdtd.set("radius", obj["diameter_nm"] * 0.5e-9)
            fdtd.set("z min", obj["z_min_nm"] * 1e-9)
            fdtd.set("z max", obj["z_max_nm"] * 1e-9)
            fdtd.set("material", obj["material_id"])

        fdtd.addplane()
        fdtd.set("name", "source_x_forward")
        fdtd.set("injection axis", "z-axis")
        fdtd.set("direction", "Forward")
        fdtd.set("polarization angle", 0)
        fdtd.set("x span", 1740e-9)
        fdtd.set("y span", 290e-9)
        fdtd.set("z", -250e-9)
        fdtd.set("wavelength start", 450e-9)
        fdtd.set("wavelength stop", 450e-9)
        for name, z in (("reflection_monitor", -300e-9), ("transmission_monitor", 1875e-9), ("order_monitor", 1875e-9), ("field_450_monitor", 1875e-9)):
            fdtd.addpower()
            fdtd.set("name", name)
            fdtd.set("monitor type", "2D Z-normal")
            fdtd.set("x span", 1740e-9)
            fdtd.set("y span", 290e-9)
            fdtd.set("z", z)
        fdtd.setglobalmonitor("use source limits", 1)
        fdtd.setglobalmonitor("use wavelength spacing", 1)
        fdtd.setglobalmonitor("frequency points", 1)
        fdtd.save(str(prefsp))
    finally:
        fdtd.close()


def readback(case: dict[str, Any], prefsp: Path, helper_root: Path) -> dict[str, Any]:
    import lumapi
    fdtd = lumapi.FDTD(str(prefsp), hide=True)
    try:
        solver_props = {prop: one(fdtd, "FDTD", prop) for prop in ("dimension", "x span", "y span", "z min", "z max", "x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "mesh accuracy", "pml layers", "simulation time", "auto shutoff min", "dt stability factor")}
        source = {prop: one(fdtd, "source_x_forward", prop) for prop in ("injection axis", "direction", "polarization angle", "x span", "y span", "z", "wavelength start", "wavelength stop", "angle theta", "angle phi")}
        monitors = {name: {prop: one(fdtd, name, prop) for prop in ("monitor type", "z", "x span", "y span", "frequency points", "use source limits", "use wavelength spacing")} for name in ("reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor")}
        layers = [{"name": f"MDC_layer_{i:02d}", "material": one(fdtd, f"MDC_layer_{i:02d}", "material"), "z_min_nm": one(fdtd, f"MDC_layer_{i:02d}", "z min") * 1e9, "z_max_nm": one(fdtd, f"MDC_layer_{i:02d}", "z max") * 1e9} for i in range(1, 13)]
        pillars = [{"name": f"NP_pillar_{i}", "material": one(fdtd, f"NP_pillar_{i}", "material"), "x_nm": one(fdtd, f"NP_pillar_{i}", "x") * 1e9, "diameter_nm": 2 * one(fdtd, f"NP_pillar_{i}", "radius") * 1e9, "z_min_nm": one(fdtd, f"NP_pillar_{i}", "z min") * 1e9, "z_max_nm": one(fdtd, f"NP_pillar_{i}", "z max") * 1e9} for i in range(6)]
        substrate = {"name": "GaN_substrate", "material": one(fdtd, "GaN_substrate", "material"), "z_min_nm": one(fdtd, "GaN_substrate", "z min") * 1e9, "z_max_nm": one(fdtd, "GaN_substrate", "z max") * 1e9}
        names = material_names(fdtd)
        material_identity = {material_id: {"present": material_id in names, "type": str(fdtd.getmaterial(material_id, "type")), "sample_count": int(len(fdtd.getmaterial(material_id, "sampled data")))} for material_id in ("APCD_GAN_NATIVE_M1", "APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")}
        return {"case_id": CASE_ID, "solver": solver_props, "source": source, "monitors": monitors, "substrate": substrate, "mdc_layers": layers, "np_pillars": pillars, "materials": material_identity, "material_names": names, "reference_medium": "Air", "reference_plane": "NP pillar bottom", "readback_session_readonly": True}
    finally:
        fdtd.close()


def validate_readback(case: dict[str, Any], rb: dict[str, Any]) -> dict[str, Any]:
    expected_layers = case["mdc_candidate"]["layers"]
    expected_pillars = case["np_candidate"]["pillars"]
    checks = {
        "dimension_3d": rb["solver"]["dimension"] == "3D",
        "periodic_xy": all(rb["solver"][key] == "Periodic" for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
        "pml_z": rb["solver"]["z min bc"] == "PML" and rb["solver"]["z max bc"] == "PML",
        "pml_layers": float(rb["solver"]["pml layers"]) == 8.0,
        "mesh_accuracy": float(rb["solver"]["mesh accuracy"]) == 2.0,
        "simulation_time": float(rb["solver"]["simulation time"]) == 1e-12,
        "autoshutoff": float(rb["solver"]["auto shutoff min"]) == 1e-5,
        "source_x_normal": rb["source"]["direction"] == "Forward" and float(rb["source"]["polarization angle"]) == 0.0 and float(rb["source"]["angle theta"]) == 0.0 and float(rb["source"]["angle phi"]) == 0.0,
        "source_wavelength": float(rb["source"]["wavelength start"]) == 450e-9 and float(rb["source"]["wavelength stop"]) == 450e-9,
        "layer_count": len(rb["mdc_layers"]) == 12,
        "layer_sequence": [round((x["z_max_nm"] - x["z_min_nm"]), 6) for x in rb["mdc_layers"]] == [x["thickness_nm"] for x in expected_layers],
        "mdc_total_975": abs(rb["mdc_layers"][-1]["z_max_nm"] - 975.0) < 1e-6,
        "final_sio2_79": rb["mdc_layers"][-1]["material"] == "APCD_SIO2_NATIVE_M1" and abs(rb["mdc_layers"][-1]["z_max_nm"] - rb["mdc_layers"][-1]["z_min_nm"] - 79.0) < 1e-6,
        "no_extra_spacer": rb["np_pillars"][0]["z_min_nm"] == rb["mdc_layers"][-1]["z_max_nm"],
        "pillar_count": len(rb["np_pillars"]) == 6,
        "pillar_order": [round(x["x_nm"], 6) for x in rb["np_pillars"]] == [x["x_nm"] for x in expected_pillars],
        "pillar_diameters": [round(x["diameter_nm"], 6) for x in rb["np_pillars"]] == [x["diameter_nm"] for x in expected_pillars],
        "pillar_height": all(abs(x["z_max_nm"] - x["z_min_nm"] - 500.0) < 1e-6 for x in rb["np_pillars"]),
        "pillar_material": all(x["material"] == "APCD_TIO2_NATIVE_M1" for x in rb["np_pillars"]),
        "native_materials": all(x["present"] and x["sample_count"] > 1 for x in rb["materials"].values()),
        "monitor_positions": rb["monitors"]["reflection_monitor"]["z"] == -300e-9 and rb["monitors"]["transmission_monitor"]["z"] == 1875e-9,
    }
    return {"pass": all(checks.values()), "checks": checks}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-registry", type=Path, default=ROOT / "configs/coupling/stage_a_golden_fixture_v1.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/coupling/stage_a_450nm_xpol_normal_textra0_golden_fixture_v1")
    parser.add_argument("--material-helper-root", type=Path, default=DEFAULT_HELPER_ROOT)
    args = parser.parse_args()
    fixture = json.loads(args.fixture_registry.read_text(encoding="utf-8"))
    case = build_joint_case(fixture["mdc_candidate"], fixture["np_candidate"], fixture["spacer_nm"], fixture["source"]["wavelength_nm"], fixture["source"]["polarization"], fixture["source"]["kx_over_k0"])
    if case["case_id"] != CASE_ID:
        raise ValueError("unexpected Stage-A case identity")
    setup_dir = args.output_dir / "setup"
    setup_dir.mkdir(parents=True, exist_ok=True)
    prefsp = setup_dir / f"{CASE_ID}_pre.fsp"
    build_fsp(case, prefsp, args.material_helper_root)
    pre_sha = sha256(prefsp)
    rb = readback(case, prefsp, args.material_helper_root)
    gate = validate_readback(case, rb)
    source_helper = args.material_helper_root / "scripts/apcd_native_materials.py"
    manifest = {
        "schema_version": "stage_a_joint_setup_manifest_v1",
        "case_id": CASE_ID,
        "fixture_registry": str(args.fixture_registry),
        "case": case,
        "readback": rb,
        "setup_gate": gate,
        "pre_fsp_path": str(prefsp),
        "pre_fsp_sha256": pre_sha,
        "solver_entered": False,
        "solver_completed": False,
        "source_commits": {"mdc": MDC_COMMIT, "np": NP_COMMIT},
        "coupling_commit": git_head(),
        "material_helper_path": str(source_helper),
        "material_helper_sha256": sha256(source_helper),
        "inherited_solver_settings": {"source": "RUN3A authoritative post-FSP readback", "mesh_accuracy": 2, "pml_layers": 8, "simulation_time_s": 1e-12, "auto_shutoff_min": 1e-5, "dt_stability_factor": 0.99},
        "overrides": {"wavelength": "450 nm exact single point instead of RUN3A 445-455 nm axis", "reason": "authorized single physical Stage-A case"},
    }
    json_write(args.output_dir / "joint_case.json", case)
    json_write(args.output_dir / "setup_manifest.json", manifest)
    json_write(args.output_dir / "setup_readback.json", rb)
    json_write(args.output_dir / "setup_gate.json", gate)
    (args.output_dir / "pre_fsp.sha256").write_text(pre_sha + "  " + str(prefsp) + "\n", encoding="utf-8")
    print(json.dumps({"case_id": CASE_ID, "pre_fsp_path": str(prefsp), "pre_fsp_sha256": pre_sha, "setup_gate": gate}, indent=2))
    if not gate["pass"]:
        raise SystemExit("SETUP_GATE_FAIL")

if __name__ == "__main__":
    main()
