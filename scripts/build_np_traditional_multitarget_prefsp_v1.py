"""Create and independently reload K4/K9 pre-FSPs without a solver run."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "outputs/np_traditional_multitarget_baseline_extension_v1"
RUNTIME = ROOT / "runtime_fsp/np_traditional_multitarget_baseline_extension_v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_family(k: int, cases: list[dict]) -> None:
    path = OUT / f"k{k}_fullsupercell_setup_manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value.update({"status": "SETUP_ONLY_SAVED_RELOADED", "solver_entered": 0, "cases": cases})
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checks = {"status": "PASS", "solver_entered": 0, "cases": {c["case_id"]: {"path": c["prefsp_path"], "sha256": c["sha256"], "reload_pass": c["reload_pass"], "semantic_diff": c["semantic_diff"]} for c in cases}}
    (OUT / f"k{k}_setup_checksums.json").write_text(json.dumps(checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_case(fdtd, k: int, case: dict, material_names: dict[str, str], path: Path) -> None:
    period_x = k * 290.0
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", period_x * 1e-9)
    fdtd.set("y span", 290e-9)
    fdtd.set("z min", -600e-9)
    fdtd.set("z max", 1200e-9)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.addrect()
    fdtd.set("name", "SiO2 substrate")
    fdtd.set("x span", period_x * 1e-9)
    fdtd.set("y span", 290e-9)
    fdtd.set("z min", -600e-9)
    fdtd.set("z max", 0)
    fdtd.set("material", material_names["APCD_SIO2_NATIVE_M1"])
    for j, (diameter, x) in enumerate(zip(case["diameters_nm"], case["x_positions_nm"])):
        fdtd.addcircle()
        fdtd.set("name", f"TiO2_pillar_{j}")
        fdtd.set("x", x * 1e-9)
        fdtd.set("y", 0)
        fdtd.set("radius", diameter * 0.5e-9)
        fdtd.set("z min", 0)
        fdtd.set("z max", 500e-9)
        fdtd.set("material", material_names["APCD_TIO2_NATIVE_M1"])
    fdtd.addplane()
    fdtd.set("name", "source_x_forward")
    fdtd.set("injection axis", "z-axis")
    fdtd.set("direction", "Forward")
    fdtd.set("polarization angle", 0)
    fdtd.set("x span", period_x * 1e-9)
    fdtd.set("y span", 290e-9)
    fdtd.set("z", -250e-9)
    fdtd.set("wavelength start", 445e-9)
    fdtd.set("wavelength stop", 455e-9)
    for name, z in (("reflection_monitor", -300e-9), ("transmission_monitor", 900e-9), ("order_monitor", 900e-9)):
        fdtd.addpower()
        fdtd.set("name", name)
        fdtd.set("monitor type", "2D Z-normal")
        fdtd.set("x span", period_x * 1e-9)
        fdtd.set("y span", 290e-9)
        fdtd.set("z", z)
    fdtd.setglobalmonitor("use source limits", 1)
    fdtd.setglobalmonitor("use wavelength spacing", 1)
    fdtd.setglobalmonitor("frequency points", 11)
    fdtd.save(str(path))


def main() -> None:
    import lumapi
    from metasurface.lumerical_native_materials import ensure_apcd_native_materials

    RUNTIME.mkdir(parents=True, exist_ok=True)
    for k in (4, 9):
        spec = json.loads((OUT / f"k{k}_fullsupercell_setup_manifest.json").read_text(encoding="utf-8"))
        results = []
        for case in spec["cases"]:
            path = RUNTIME / f"{k}_{case['case_id']}.fsp"
            fdtd = lumapi.FDTD(hide=True)
            try:
                names = ensure_apcd_native_materials(fdtd)
                build_case(fdtd, k, case, names, path)
            finally:
                fdtd.close()
            fdtd = lumapi.FDTD(str(path), hide=True)
            try:
                got = []
                for j in range(k):
                    obj = f"TiO2_pillar_{j}"
                    got.append({"x_nm": round(float(fdtd.getnamed(obj, "x")) * 1e9, 6), "diameter_nm": round(float(2 * fdtd.getnamed(obj, "radius")) * 1e9, 6), "height_nm": round(float(fdtd.getnamed(obj, "z max") - fdtd.getnamed(obj, "z min")) * 1e9, 6), "material": str(fdtd.getnamed(obj, "material"))})
                readback = {"pillars": got, "source": {"direction": str(fdtd.getnamed("source_x_forward", "direction")), "injection_axis": str(fdtd.getnamed("source_x_forward", "injection axis")), "polarization_angle": float(fdtd.getnamed("source_x_forward", "polarization angle")), "z_nm": float(fdtd.getnamed("source_x_forward", "z")) * 1e9}, "boundaries": {x: str(fdtd.getnamed("FDTD", x)) for x in ("x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc")}, "materials": sorted({p["material"] for p in got}), "monitor_z_nm": float(fdtd.getnamed("order_monitor", "z")) * 1e9, "wavelength_points": int(fdtd.getglobalmonitor("frequency points"))}
            finally:
                fdtd.close()
            expected = [{"x_nm": float(x), "diameter_nm": float(d), "height_nm": 500.0} for x, d in zip(case["x_positions_nm"], case["diameters_nm"])]
            results.append({"case_id": case["case_id"], "K": k, "diameters_nm": case["diameters_nm"], "x_positions_nm": case["x_positions_nm"], "prefsp_path": str(path), "sha256": sha(path), "reload_pass": all(abs(a["x_nm"] - b["x_nm"]) < 1e-3 and abs(a["diameter_nm"] - b["diameter_nm"]) < 1e-3 and abs(a["height_nm"] - b["height_nm"]) < 1e-3 for a, b in zip(readback["pillars"], expected)), "semantic_diff": {"geometry": readback["pillars"], "source_material_boundary_monitor": readback}})
        update_family(k, results)
    audit = json.loads((OUT / "solver_zero_audit.json").read_text(encoding="utf-8"))
    audit.update({"setup_only_fsp_saved": 6, "setup_only_reload_pass": True, "solver_entered": 0, "fdtd_run_called": False})
    (OUT / "solver_zero_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
