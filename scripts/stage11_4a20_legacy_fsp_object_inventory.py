from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[0]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))
from lp_protected_artifact_guard_v1 import assert_not_protected_write_target, guarded_write_text

WORKTREE = Path(__file__).resolve().parents[1]
OUT = WORKTREE / "outputs" / "stage11_4a20_legacy_fsp_object_inventory"
REPORTS = OUT / "derived_reports"
SEARCH_ROOTS = [
    Path(r"D:\project\blue_apcd_microled_metasurface\outputs"),
    Path(r"D:\project\blue_apcd_microled_metasurface\scripts"),
    Path(r"D:\project\blue_apcd_microled_metasurface\reports"),
    Path(r"D:\project\blue_apcd_microled_metasurface_wt_stage11_4a0"),
]
TARGET_STEMS = [
    "H500DIMER2C_029", "H500DIMER2B_006", "H500DIMER2C_004", "H500DIMER2C_026",
    "H500DIMER2D_018", "H500DIMER2D_006", "H500DIMER12D_001", "H500DIMER12D_004",
    "DIMER2B", "DIMER2C", "DIMER2D", "DIMER12D", "B240", "B300", "Hnew", "stage11_4",
]
PREFERRED_TERMS = ["H500", "DIMER", "B240", "B300", "stage11", "stage11_4", "Hnew", "2B", "2C", "2D", "12D"]
HEAVY_EXTS = {".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy"}


def score_path(path: Path) -> tuple[int, list[str]]:
    text = str(path).lower()
    name = path.name.lower()
    matches = [s for s in TARGET_STEMS if s.lower() in text]
    filename_score = sum(3 for t in PREFERRED_TERMS if t.lower() in name)
    path_score = sum(1 for t in PREFERRED_TERMS if t.lower() in text)
    return filename_score + path_score + 5 * len(matches), matches


def index_fsp_files() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.lower().endswith(".fsp"):
                    continue
                path = Path(dirpath) / filename
                try:
                    st = path.stat()
                except OSError:
                    continue
                score, matches = score_path(path)
                rows.append({
                    "path": str(path),
                    "file_size_bytes": str(st.st_size),
                    "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                    "filename_score": str(score_path(Path(path.name))[0]),
                    "path_score": str(score),
                    "candidate_stem_matches": ";".join(matches),
                    "priority_rank": "",
                })
    rows.sort(key=lambda r: (int(r["path_score"]), int(r["file_size_bytes"]) * -1), reverse=True)
    for i, row in enumerate(rows, 1):
        row["priority_rank"] = str(i)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    assert_not_protected_write_target(path, "write", __file__)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def load_lumapi():
    api_path = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    if api_path.exists() and str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))
    try:
        import lumapi  # type: ignore
        return lumapi, "available"
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, f"unavailable: {exc}"


def inventory_fsp(path: Path, lumapi):
    objects: list[dict[str, str]] = []
    attempts: list[dict[str, str]] = []
    status = "fsp_open_failed"
    message = ""
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=True)
        fdtd.load(str(path))
        # Best-effort read-only object enumeration. Different Lumerical versions expose different scripting helpers.
        script = "names=getobjects; n=length(names);"
        fdtd.eval(script)
        try:
            names = list(fdtd.getv("names"))
        except Exception:
            names = []
        for raw in names:
            name = str(raw).strip()
            row = {"fsp_path": str(path), "object_name": name, "object_type": "", "parent_group": "", "x": "", "y": "", "z": "", "x_span": "", "y_span": "", "z_span": "", "rotation": "", "first_axis_rotation": "", "theta": "", "material": "", "status": "object_listed"}
            for prop, key in [("x", "x"), ("y", "y"), ("z", "z"), ("x span", "x_span"), ("y span", "y_span"), ("z span", "z_span"), ("rotation", "rotation"), ("first axis rotation", "first_axis_rotation"), ("material", "material")]:
                try:
                    row[key] = str(fdtd.getnamed(name, prop))
                except Exception:
                    pass
            objects.append(row)
        status = "fsp_no_candidate_objects" if not objects else "fsp_partial_only"
    except Exception as exc:
        message = str(exc).replace("\n", " ")[:500]
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    attempts.append({"fsp_path": str(path), "evidence_label": status, "message": message, "object_count": str(len(objects)), "run_ready_geometry": "false"})
    return objects, attempts


def no_heavy_created() -> bool:
    if not OUT.exists():
        return True
    return not any(p.suffix.lower() in HEAVY_EXTS for p in OUT.rglob("*"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-only", action="store_true")
    parser.add_argument("--max-open", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-output", default=str(REPORTS / "legacy_fsp_object_inventory.md"))
    parser.add_argument("--decision-output", default=str(REPORTS / "next_action_decision.md"))
    args = parser.parse_args(argv)
    report_path = Path(args.report_output)
    decision_path = Path(args.decision_output)
    assert_not_protected_write_target(report_path, "write", __file__)
    assert_not_protected_write_target(decision_path, "write", __file__)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "report_output": str(report_path), "decision_output": str(decision_path)}, sort_keys=True))
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    fsp_rows = index_fsp_files()
    selected = [r for r in fsp_rows if int(r["path_score"]) > 0][: max(0, min(args.max_open, 20))]

    lumapi, lumapi_status = (None, "skipped index-only") if args.index_only else load_lumapi()
    object_rows: list[dict[str, str]] = []
    attempt_rows: list[dict[str, str]] = []
    hidden_mode = bool(lumapi) and not args.index_only
    if lumapi and selected:
        for row in selected:
            objs, attempts = inventory_fsp(Path(row["path"]), lumapi)
            object_rows.extend(objs)
            attempt_rows.extend(attempts)
    elif selected:
        attempt_rows = [{"fsp_path": r["path"], "evidence_label": "fsp_open_failed", "message": lumapi_status, "object_count": "0", "run_ready_geometry": "false"} for r in selected]

    geometry_rows = [{"candidate_id": "", "fsp_path": r["fsp_path"], "evidence_label": r["evidence_label"], "run_ready_geometry": "false", "H_nm": "", "L1_nm": "", "W1_nm": "", "theta1_deg": "", "L2_nm": "", "W2_nm": "", "theta2_deg": "", "center_dx_nm": "", "gap_or_dx_nm": "", "period_x_nm": "", "period_y_nm": "", "notes": r["message"]} for r in attempt_rows]

    write_csv(OUT / "stage11_4a20_fsp_file_index.csv", fsp_rows, ["path", "file_size_bytes", "mtime", "filename_score", "path_score", "candidate_stem_matches", "priority_rank"])
    write_csv(OUT / "stage11_4a20_object_inventory.csv", object_rows, ["fsp_path", "object_name", "object_type", "parent_group", "x", "y", "z", "x_span", "y_span", "z_span", "rotation", "first_axis_rotation", "theta", "material", "status"])
    write_csv(OUT / "stage11_4a20_candidate_geometry_attempt.csv", geometry_rows, ["candidate_id", "fsp_path", "evidence_label", "run_ready_geometry", "H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "gap_or_dx_nm", "period_x_nm", "period_y_nm", "notes"])

    summary = {
        "fsp_files_indexed": len(fsp_rows),
        "fsp_files_opened": len(attempt_rows) if lumapi and not args.index_only else 0,
        "fsp_open_failures": sum(1 for r in attempt_rows if r["evidence_label"] == "fsp_open_failed"),
        "object_inventory_count": len(object_rows),
        "recovered_run_ready_geometry_count": 0,
        "partial_geometry_count": sum(1 for r in attempt_rows if r["evidence_label"] == "fsp_partial_only"),
        "top_candidate_matched_fsp_paths": [r["path"] for r in selected[:10]],
        "lumapi_status": lumapi_status,
        "hidden_mode_attempted": hidden_mode,
        "no_fdtd_simulation_run": True,
        "no_fsp_saved_or_modified": True,
        "no_k6_attempted": True,
        "no_model_trained": True,
        "no_heavy_created_in_outputs": no_heavy_created(),
        "legacy_geometry_route_go": False,
    }
    guarded_write_text(OUT / "stage11_4a20_summary.json", json.dumps(summary, indent=2), encoding="utf-8", caller=__file__)

    gui_line = "No Lumerical GUI was opened; hidden lumapi mode was attempted." if hidden_mode else f"No Lumerical GUI was opened; lumapi hidden mode was not used ({lumapi_status})."
    report = [
        "# Stage11-4A20 legacy FSP object inventory",
        "",
        "Purpose: final low-cost legacy geometry recovery attempt after A19 found only partial_base_only evidence.",
        "",
        f"FSP files indexed: {summary['fsp_files_indexed']}",
        f"FSP files opened: {summary['fsp_files_opened']}",
        f"FSP open failures: {summary['fsp_open_failures']}",
        f"Object inventory count: {summary['object_inventory_count']}",
        f"Recovered run-ready geometry count: {summary['recovered_run_ready_geometry_count']}",
        f"Partial geometry count: {summary['partial_geometry_count']}",
        "",
        "## Matched FSP examples",
    ]
    report += [f"- {p}" for p in summary["top_candidate_matched_fsp_paths"][:10]] or ["- none"]
    report += [
        "",
        "## Decision",
        "No-Go for the legacy geometry route unless manual review finds geometry in the indexed FSPs.",
        "If run_ready_count == 0, stop legacy recovery and proceed with LP-ML1A4 -> LP-ML1B0/1B1.",
        "",
        "No FDTD simulation was run.",
        "No FSP was saved or modified.",
        gui_line,
        "No K=6 was attempted.",
        "No model was trained.",
    ]
    guarded_write_text(report_path, "\n".join(report) + "\n", encoding="utf-8", caller=__file__)
    decision = [
        "# Stage11-4A20 next action decision",
        "",
        "Go/No-Go: No-Go for legacy geometry route based on automated read-only FSP inventory.",
        "Recommended next: proceed with LP-ML1A4 explicit geometry seeds, then LP-ML1B0/1B1. Manual inspect only if a human wants to open the matched FSPs interactively.",
        "",
        "No FDTD simulation was run. No FSP was saved or modified. No K=6 was attempted. No model was trained.",
    ]
    guarded_write_text(decision_path, "\n".join(decision) + "\n", encoding="utf-8", caller=__file__)
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
