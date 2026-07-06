from __future__ import annotations

import csv
import importlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "lp_fmm0a_backend_and_schema_audit"
REPORTS = ROOT / "reports"
INPUT_DIR = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator"
PILOT = INPUT_DIR / "lp_ml1a4_pilot_recommendation.csv"
MANIFEST = INPUT_DIR / "lp_ml1a4_explicit_seed_manifest.csv"
SUMMARY = INPUT_DIR / "lp_ml1a4_explicit_seed_summary.json"
BACKENDS = ["grcwa", "rcwa", "s4", "S4", "meent", "reticolo"]
SEARCH_TERMS = ["FMM", "RCWA", "Fourier", "modal", "S4", "grcwa", "reticolo", "meent"]
FOURIER_ORDERS = [(7, 7), (11, 11), (15, 15), (21, 21)]
HEAVY_MARKERS = (".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy", "monitor", "farfield", "far_field", "raw")


def ensure_inputs() -> None:
    if PILOT.exists() and MANIFEST.exists() and SUMMARY.exists():
        return
    generator = ROOT / "scripts" / "lp_ml1" / "lp_ml1a4_explicit_geometry_seed_generator.py"
    if not generator.exists():
        raise FileNotFoundError(f"Missing LP-ML1A4 inputs and generator: {generator}")
    subprocess.run([os.environ.get("PYTHON", "python"), str(generator)], cwd=ROOT, check=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def backend_inventory() -> dict:
    packages = []
    for name in BACKENDS:
        try:
            mod = importlib.import_module(name)
            packages.append({"backend_name": name, "available": True, "error": "", "module_file": str(getattr(mod, "__file__", ""))})
        except Exception as exc:
            packages.append({"backend_name": name, "available": False, "error": str(exc), "module_file": ""})
    hits = []
    for dirpath, _, filenames in os.walk(ROOT / "scripts"):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = Path(dirpath) / filename
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            matched = [term for term in SEARCH_TERMS if term.lower() in text.lower()]
            if matched:
                hits.append({"source_file": str(path), "matched_terms": ";".join(sorted(set(matched)))})
    return {"package_imports": packages, "project_local_hits": hits, "no_solver_executed": True}


def make_queue(pilots: list[dict[str, str]], backend_status: str) -> list[dict[str, str]]:
    rows = []
    for i, p in enumerate(pilots, 1):
        rows.append({
            "queue_id": f"LPFMM0A_{i:03d}",
            "candidate_id": p.get("candidate_id", ""),
            "target_bin_deg": p.get("target_bin_deg", ""),
            "sampling_group": p.get("sampling_group", ""),
            "sampling_family": p.get("sampling_family", ""),
            "H_nm": p.get("H_nm", ""),
            "period_x_nm": p.get("period_x_nm", ""),
            "period_y_nm": p.get("period_y_nm", ""),
            "L1_nm": p.get("L1_nm", ""),
            "W1_nm": p.get("W1_nm", ""),
            "theta1_deg": p.get("theta1_deg", ""),
            "L2_nm": p.get("L2_nm", ""),
            "W2_nm": p.get("W2_nm", ""),
            "theta2_deg": p.get("theta2_deg", ""),
            "center_dx_nm": p.get("center_dx_nm", ""),
            "center_dy_nm": p.get("center_dy_nm", ""),
            "gap_or_dx_nm": p.get("gap_or_dx_nm", ""),
            "intended_wavelengths_nm": p.get("intended_wavelengths_nm", "450,450.5,451,451.5,452,452.5,453,453.5,454"),
            "num_wavelengths": "9",
            "input_polarizations": "x,y",
            "fmm_backend_status": backend_status,
            "fmm_run_status": "planned_not_run",
            "fdtd_anchor_status": "not_selected_yet",
            "notes": "FMM/RCWA audit queue only; no solver executed.",
        })
    return rows


def pick_subset(queue: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    used = set()

    def add_first(predicate) -> None:
        for row in queue:
            if row["candidate_id"] not in used and predicate(row):
                selected.append(row)
                used.add(row["candidate_id"])
                return

    for bin_deg in ["0", "60", "120", "180", "240", "300"]:
        add_first(lambda r, b=bin_deg: r["target_bin_deg"] == b)
    for _ in range(4 - sum(1 for r in selected if r["target_bin_deg"] == "300")):
        add_first(lambda r: r["target_bin_deg"] == "300")
    for _ in range(3 - sum(1 for r in selected if r["target_bin_deg"] == "240")):
        add_first(lambda r: r["target_bin_deg"] == "240")
    for h in ["500", "600", "650", "700"]:
        if any(r["H_nm"] == h for r in selected):
            continue
        add_first(lambda r, hh=h: r["H_nm"] == hh)
    for row in queue:
        if len(selected) >= 12:
            break
        if row["candidate_id"] not in used:
            selected.append(row)
            used.add(row["candidate_id"])
    return selected[:12]


def convergence_plan(subset: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in subset:
        for ox, oy in FOURIER_ORDERS:
            rows.append({
                "candidate_id": row["candidate_id"],
                "target_bin_deg": row["target_bin_deg"],
                "H_nm": row["H_nm"],
                "fourier_order_x": str(ox),
                "fourier_order_y": str(oy),
                "wavelengths_nm": row["intended_wavelengths_nm"],
                "input_polarizations": "x,y",
                "run_status": "planned_not_run",
                "purpose": "Fourier-order convergence check before trusting FMM screening.",
            })
    return rows


def expected_schema() -> list[dict[str, str]]:
    cols = ["candidate_id", "backend_name", "fourier_order_x", "fourier_order_y", "lambda_nm", "polarization_in", "txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im", "Tx", "leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "nearest_bin_deg", "phase_error_deg", "matrix_error", "energy_balance_error", "result_status", "error_message", "runtime_seconds"]
    return [{"column": c, "description": "planned FMM Jones result field"} for c in cols]


def write_reports(inv: dict, queue: list[dict[str, str]], subset: list[dict[str, str]], schema_rows: list[dict[str, str]]) -> None:
    available = [p for p in inv["package_imports"] if p["available"]]
    backend_lines = [f"- {p['backend_name']}: {'available' if p['available'] else 'missing'} {p['error']}".rstrip() for p in inv["package_imports"]]
    subset_lines = [f"- {r['candidate_id']}: B{r['target_bin_deg']}, H{r['H_nm']}, {r['sampling_group']}" for r in subset]
    report = [
        "# LP-FMM0A backend and schema audit",
        "",
        "Purpose: plan FMM/RCWA screening for periodic LP dimer Jones matrices before any solver run.",
        "",
        "## Inputs used",
        f"- {PILOT}", f"- {MANIFEST}", f"- {SUMMARY}",
        "",
        "## Backend import audit",
        *backend_lines,
        "",
        f"36 pilot queue count: {len(queue)}",
        f"12-candidate convergence subset count: {len(subset)}",
        "",
        "## Convergence subset",
        *subset_lines,
        "",
        "## Expected result schema",
        ", ".join(r["column"] for r in schema_rows),
        "",
        "No FMM solver was executed.",
        "No FDTD was run.",
        "No Lumerical GUI was opened.",
        "No model was trained.",
        "No K=6 was attempted.",
    ]
    (REPORTS / "lp_fmm0a_backend_and_schema_audit.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    audit_plan = [
        "# LP-FMM0A FMM-vs-FDTD audit plan",
        "",
        "FMM/RCWA is suitable for early periodic normal-incidence dimer screening because the geometry is periodic and the target output is a Jones transmission matrix.",
        "It cannot replace finite patch, dipole, Micro-LED, DBR/RCLED, or final validation because those require source, boundary, finite-size, and stack physics outside this periodic plane-wave screen.",
        "",
        "## Required convergence check",
        "Run planned Fourier orders 7x7, 11x11, 15x15, and 21x21 before trusting ranking.",
        "",
        "## FMM-vs-FDTD comparison metrics",
        "phase_error_deg difference; Tx difference; leakage difference; ratio difference; matrix_error difference; nearest-bin consistency; candidate ranking consistency; top-candidate overlap; runtime speedup.",
        "",
        "## Go criteria",
        "phase difference <= 5-10 deg; Tx difference <= 0.03-0.05; leakage difference <= 0.03-0.05; nearest-bin consistency >= 85%; B240/B300 ranking better than random; FMM top list overlaps with FDTD top list.",
        "",
        "## No-Go criteria",
        "unstable Fourier-order convergence; incorrect nearest-bin ranking; B240/B300 false positives dominate; strong disagreement with FDTD anchors.",
    ]
    (REPORTS / "lp_fmm0a_fmm_vs_fdtd_audit_plan.md").write_text("\n".join(audit_plan) + "\n", encoding="utf-8")
    yaml = """geometry_inputs:\n  - H_nm\n  - period_x_nm\n  - period_y_nm\n  - L1_nm\n  - W1_nm\n  - theta1_deg\n  - L2_nm\n  - W2_nm\n  - theta2_deg\n  - center_dx_nm\n  - center_dy_nm\nwavelength_grid: [450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454]\npolarization_convention: inputs x,y; outputs x,y\njones_matrix_ordering: [[txx, txy], [tyx, tyy]]\ntransmission_normalization_convention: normalize transmitted complex amplitudes to incident plane-wave amplitude; compare energy balance separately\nphase_wrapping_convention: selected_phase_deg wrapped to [-180, 180); bin error uses circular angular distance\nlp_metrics:\n  - Tx\n  - leakage\n  - conversion_to_leakage_ratio\n  - selected_phase_deg\n  - nearest_bin_deg\n  - phase_error_deg\n  - matrix_error\nfourier_order_convergence_fields:\n  - fourier_order_x\n  - fourier_order_y\n  - convergence_delta_phase_deg\n  - convergence_delta_Tx\n  - convergence_delta_leakage\nfdtd_anchor_comparison_fields:\n  - fdtd_candidate_id\n  - fmm_minus_fdtd_phase_deg\n  - fmm_minus_fdtd_Tx\n  - fmm_minus_fdtd_leakage\n  - nearest_bin_consistent\nheavy_file_avoidance_policy: do not create or commit .fsp, .ldf, .h5, .mat, .npz, .npy, monitor, farfield, or raw outputs in LP-FMM0A\n"""
    (REPORTS / "lp_fmm0a_fmm_jones_schema.yaml").write_text(yaml, encoding="utf-8")


def no_heavy_outputs() -> bool:
    if not OUT.exists():
        return True
    return not any(any(marker in p.name.lower() for marker in HEAVY_MARKERS) for p in OUT.rglob("*"))


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    pilots = read_csv(PILOT)
    if len(pilots) != 36:
        raise ValueError(f"Expected 36 pilot rows, got {len(pilots)}")
    inv = backend_inventory()
    backend_status = "available:" + ";".join(p["backend_name"] for p in inv["package_imports"] if p["available"]) if any(p["available"] for p in inv["package_imports"]) else "no_backend_available_import_only"
    queue = make_queue(pilots, backend_status)
    subset = pick_subset(queue)
    conv = convergence_plan(subset)
    schema_rows = expected_schema()
    write_csv(OUT / "lp_fmm0a_candidate_queue.csv", queue, ["queue_id", "candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "intended_wavelengths_nm", "num_wavelengths", "input_polarizations", "fmm_backend_status", "fmm_run_status", "fdtd_anchor_status", "notes"])
    write_csv(OUT / "lp_fmm0a_convergence_plan.csv", conv, ["candidate_id", "target_bin_deg", "H_nm", "fourier_order_x", "fourier_order_y", "wavelengths_nm", "input_polarizations", "run_status", "purpose"])
    write_csv(OUT / "lp_fmm0a_expected_result_schema.csv", schema_rows, ["column", "description"])
    (OUT / "lp_fmm0a_backend_inventory.json").write_text(json.dumps(inv, indent=2), encoding="utf-8")
    summary = {
        "candidate_queue_count": len(queue),
        "convergence_subset_count": len(subset),
        "convergence_subset_candidates": [r["candidate_id"] for r in subset],
        "backend_available": [p["backend_name"] for p in inv["package_imports"] if p["available"]],
        "backend_missing": [p["backend_name"] for p in inv["package_imports"] if not p["available"]],
        "project_local_hit_count": len(inv["project_local_hits"]),
        "no_fmm_solver_executed": True,
        "no_fdtd_run": True,
        "no_gui_opened": True,
        "no_model_trained": True,
        "no_k6_attempted": True,
        "no_heavy_outputs_created": no_heavy_outputs(),
    }
    (OUT / "lp_fmm0a_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_reports(inv, queue, subset, schema_rows)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
