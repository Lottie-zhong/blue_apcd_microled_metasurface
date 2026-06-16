from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

OUT_DIR = Path("outputs/blue_stage10_cp_zprop_validation")
RUN_SCRIPT = Path("scripts/blue_stage10_cp_zprop_validation/run_cp_zprop_center_xy_t100.py")
EXTRACT_SCRIPT = Path("scripts/blue_stage10_cp_zprop_validation/extract_cp_zprop_center_farfield.py")
DEBUG_JSON = OUT_DIR / "cp_zprop_sanity_convergence_debug.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static sanity audit for +z CP setup/extraction scripts.")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    return parser.parse_args()


def literal_constants(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    out: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            try:
                out[name] = ast.literal_eval(node.value)
            except Exception:
                pass
    return out


def text_has(path: Path, pattern: str) -> bool:
    return re.search(pattern, path.read_text(encoding="utf-8-sig"), re.MULTILINE) is not None


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_consts = literal_constants(RUN_SCRIPT)
    extract_text = EXTRACT_SCRIPT.read_text(encoding="utf-8-sig")
    run_text = RUN_SCRIPT.read_text(encoding="utf-8-sig")
    checks = {
        "metasurface_plane_is_xy": bool(run_consts.get("ARRAY_NX") == 7 and run_consts.get("ARRAY_NY") == 3 and "center_y_nm" in run_text and "PERIOD_Y_NM" in run_text),
        "pillar_height_is_z": bool('fdtd.set("z min", 0)' in run_text and 'fdtd.set("z max", float(pillar["height_nm"]) * NM)' in run_text),
        "pillar_rotation_axis_is_z": bool('fdtd.set("first axis", "z")' in run_text),
        "finite_patch_extends_x_y": bool("X_CENTERS_NM" in run_text and "Y_CENTERS_NM" in run_text and "dimer_iy" in run_text),
        "source_below_metasurface": bool(run_consts.get("SOURCE_Z_NM") == -200.0 and run_consts.get("GAN_TOP_Z_NM") == 0.0),
        "monitor_above_metasurface_plus_z": bool(run_consts.get("MONITOR_Z_NM") == 1000.0 and run_consts.get("FIELD_MONITOR") == "top_field_monitor_zprop"),
        "x_dipole_x_oriented": bool('"orientation": "x"' in run_text and '"theta_deg": 90.0, "phi_deg": 0.0' in run_text),
        "y_dipole_y_oriented": bool('"orientation": "y"' in run_text and '"theta_deg": 90.0, "phi_deg": 90.0' in run_text),
        "extract_uses_ex_ey_for_z_cp": bool("Ex-iEy" in extract_text and "Ex+iEy" in extract_text and "ex" in extract_text and "ey" in extract_text),
        "extract_uses_farfieldvector3d": bool("farfieldvector3d" in extract_text),
    }
    audit_ok = all(checks.values())
    report = {
        "audit_ok": audit_ok,
        "run_script": str(RUN_SCRIPT),
        "extract_script": str(EXTRACT_SCRIPT),
        "checks": checks,
        "constants": {k: run_consts.get(k) for k in ["PERIOD_X_NM", "PERIOD_Y_NM", "SOURCE_X_NM", "SOURCE_Y_NM", "SOURCE_Z_NM", "MONITOR_Z_NM", "FIELD_MONITOR", "POWER_MONITOR", "X_SOURCE", "Y_SOURCE"]},
        "handedness_note": "Negative DoCP_RminusL means L component is stronger under the current +z convention; final source-side handedness label still needs plane-wave control/reciprocity audit.",
    }
    existing: dict[str, Any] = {}
    if DEBUG_JSON.exists():
        try:
            existing = json.loads(DEBUG_JSON.read_text(encoding="utf-8-sig"))
        except Exception:
            existing = {}
    existing["static_audit"] = report
    DEBUG_JSON.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if audit_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

