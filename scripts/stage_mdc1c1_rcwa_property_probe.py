from __future__ import annotations

import csv
import importlib.util
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_defect_450")
OUT = ROOT / "outputs" / "mdc1c1_rcwa_property_probe"
LUMAPI = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python\lumapi.py")
RCWA_OBJECT = "RCWA"

OUT.mkdir(parents=True, exist_ok=True)

def safe_str(v: Any, limit: int = 3000) -> str:
    try:
        if hasattr(v, "tolist"):
            v = v.tolist()
        text = json.dumps(v, default=str) if isinstance(v, (dict, list, tuple)) else str(v)
    except Exception:
        text = repr(v)
    return text[:limit]

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def load_lumapi():
    spec = importlib.util.spec_from_file_location("lumapi", str(LUMAPI))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load lumapi from {LUMAPI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lumapi"] = module
    spec.loader.exec_module(module)
    return module

def try_call(rows: list[dict[str, Any]], step: str, func) -> tuple[bool, Any]:
    try:
        result = func()
        rows.append({"step": step, "status": "ok", "detail": safe_str(result)})
        return True, result
    except Exception as exc:
        rows.append({"step": step, "status": "failed", "detail": f"{type(exc).__name__}: {exc}"})
        return False, None

def main() -> int:
    rows: list[dict[str, Any]] = []
    prop_rows: list[dict[str, Any]] = []
    fdtd = None

    summary = {
        "stage": "MDC1C1_rcwa_property_probe_no_run",
        "created": datetime.now().isoformat(timespec="seconds"),
        "worktree": str(ROOT),
        "fsp_opened": False,
        "simulation_run_performed": False,
        "save_performed": False,
        "rcwa_object_created": False,
        "can_set_gaN_air_media": False,
        "decision": "undetermined",
    }

    try:
        lumapi = load_lumapi()
        ok_session, fdtd = try_call(rows, "open blank Lumerical FDTD session", lambda: lumapi.FDTD(hide=False))
        if not ok_session:
            summary["decision"] = "failed_to_open_lumerical"
            return 1

        try_call(rows, "switchtolayout", lambda: fdtd.switchtolayout())

        ok_rcwa, _ = try_call(rows, "addrcwa", lambda: fdtd.addrcwa())
        summary["rcwa_object_created"] = bool(ok_rcwa)
        if not ok_rcwa:
            summary["decision"] = "addrcwa_failed"
            return 1

        # Try to obtain full property list if available.
        try_call(rows, "getnamed RCWA full", lambda: fdtd.getnamed(RCWA_OBJECT))
        try_call(rows, "getproperties RCWA", lambda: fdtd.getproperties(RCWA_OBJECT))

        # Candidate property names that might control superstrate/substrate/background media.
        test_props = [
            ("background material", "<Object defined dielectric>"),
            ("background index", 2.41),
            ("index", 2.41),
            ("material", "<Object defined dielectric>"),

            ("substrate material", "<Object defined dielectric>"),
            ("substrate index", 2.41),
            ("superstrate material", "<Object defined dielectric>"),
            ("superstrate index", 1.0),

            ("upper material", "<Object defined dielectric>"),
            ("upper index", 2.41),
            ("lower material", "<Object defined dielectric>"),
            ("lower index", 1.0),

            ("n upper", 2.41),
            ("n_upper", 2.41),
            ("n lower", 1.0),
            ("n_lower", 1.0),

            ("incident medium", "GaN"),
            ("transmission medium", "Air"),
            ("input medium", "GaN"),
            ("output medium", "Air"),

            ("injection axis", "z"),
            ("propagation axis", "z"),
            ("interface absolute positions", [[-1e-7, 1e-7]]),
        ]

        for prop, value in test_props:
            set_ok, _ = try_call(rows, f"set RCWA.{prop}", lambda p=prop, v=value: fdtd.setnamed(RCWA_OBJECT, p, v))
            get_ok, got = try_call(rows, f"get RCWA.{prop}", lambda p=prop: fdtd.getnamed(RCWA_OBJECT, p))
            prop_rows.append({
                "property": prop,
                "test_value": safe_str(value),
                "set_ok": set_ok,
                "get_ok": get_ok,
                "readback": safe_str(got),
            })

        # Conservative decision: require some explicit upper/lower or substrate/superstrate index control.
        ok_names = {r["property"] for r in prop_rows if r["set_ok"]}
        explicit_media_ok = any(p in ok_names for p in [
            "substrate index", "superstrate index",
            "upper index", "lower index",
            "n upper", "n_upper", "n lower", "n_lower",
        ])

        summary["set_ok_properties"] = sorted(ok_names)
        summary["can_set_gaN_air_media"] = bool(explicit_media_ok)
        summary["decision"] = "can_attempt_GaN_to_Air_RCWA_parity" if explicit_media_ok else "do_not_run_GaN_Air_RCWA_until_media_control_is_known"

    except Exception:
        summary["decision"] = "exception"
        summary["traceback"] = traceback.format_exc()
        return 1
    finally:
        if fdtd is not None:
            try_call(rows, "close Lumerical session", lambda: fdtd.close())

        write_csv(OUT / "mdc1c1_rcwa_property_probe_log.csv", rows)
        write_csv(OUT / "mdc1c1_rcwa_property_matrix.csv", prop_rows)
        (OUT / "mdc1c1_rcwa_property_probe_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        md = []
        md.append("# MDC1C1 RCWA property probe, no-run\n")
        md.append("## Scope\n")
        md.append("Blank-project RCWA property probe only. No FSP opened, no save, no run, no FDTD, no RCLED continuation.\n")
        md.append("## Summary\n")
        md.append(f"- decision = `{summary.get('decision')}`")
        md.append(f"- rcwa_object_created = `{summary.get('rcwa_object_created')}`")
        md.append(f"- can_set_gaN_air_media = `{summary.get('can_set_gaN_air_media')}`")
        md.append("## Properties with set_ok=True\n")
        for p in summary.get("set_ok_properties", []):
            md.append(f"- `{p}`")
        md.append("\n## Output files\n")
        md.append("- `outputs/mdc1c1_rcwa_property_probe/mdc1c1_rcwa_property_probe_log.csv`")
        md.append("- `outputs/mdc1c1_rcwa_property_probe/mdc1c1_rcwa_property_matrix.csv`")
        md.append("- `outputs/mdc1c1_rcwa_property_probe/mdc1c1_rcwa_property_probe_summary.json`")
        (OUT / "mdc1c1_rcwa_property_probe_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

        print("MDC1C1 RCWA property probe complete")
        print("decision=", summary.get("decision"))
        print("rcwa_object_created=", summary.get("rcwa_object_created"))
        print("can_set_gaN_air_media=", summary.get("can_set_gaN_air_media"))
        print("set_ok_properties=", summary.get("set_ok_properties"))
        print("summary=", OUT / "mdc1c1_rcwa_property_probe_summary.json")
        print("matrix=", OUT / "mdc1c1_rcwa_property_matrix.csv")
        print("report=", OUT / "mdc1c1_rcwa_property_probe_report.md")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
