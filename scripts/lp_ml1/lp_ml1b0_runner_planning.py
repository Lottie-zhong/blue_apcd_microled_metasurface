from __future__ import annotations

import csv
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "lp_ml1b0_runner_planning"
REPORTS = ROOT / "reports"
ML1A4_OUT = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator"
FMM0A_OUT = ROOT / "outputs" / "lp_fmm0a_backend_and_schema_audit"
PILOT = ML1A4_OUT / "lp_ml1a4_pilot_recommendation.csv"
MANIFEST = ML1A4_OUT / "lp_ml1a4_explicit_seed_manifest.csv"
SEED_SUMMARY = ML1A4_OUT / "lp_ml1a4_explicit_seed_summary.json"
FMM_QUEUE = FMM0A_OUT / "lp_fmm0a_candidate_queue.csv"
FMM_CONV = FMM0A_OUT / "lp_fmm0a_convergence_plan.csv"
WAVELENGTHS = [450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454]
QUEUE_COLUMNS = ["queue_id", "candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "intended_wavelengths_nm", "num_wavelengths", "source_manifest", "run_status", "prepared_not_run", "priority_score", "pilot_rank", "estimated_runtime_class", "smoke_test_candidate", "notes"]
SCHEMA_COLUMNS = ["candidate_id", "H_nm", "target_bin_deg", "lambda_nm", "polarization_in", "txx_re", "txx_im", "txy_re", "txy_im", "tyx_re", "tyx_im", "tyy_re", "tyy_im", "selected_Tx", "leakage_xin_to_yout", "leakage_yin_to_xout", "y_direct_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "nearest_bin_deg", "phase_error_deg", "matrix_error", "spectral_pass", "result_status", "error_message", "fsp_path_not_committed", "csv_path"]
HEAVY_MARKERS = (".fsp", ".ldf", ".h5", ".mat", ".npz", ".npy", "monitor", "farfield", "raw")


def ensure_inputs() -> None:
    if not PILOT.exists() or not MANIFEST.exists() or not SEED_SUMMARY.exists():
        gen = ROOT / "scripts" / "lp_ml1" / "lp_ml1a4_explicit_geometry_seed_generator.py"
        subprocess.run([os.environ.get("PYTHON", "python"), str(gen)], cwd=ROOT, check=True)
    if not FMM_QUEUE.exists() or not FMM_CONV.exists():
        gen = ROOT / "scripts" / "lp_fmm0" / "lp_fmm0a_backend_and_schema_audit.py"
        subprocess.run([os.environ.get("PYTHON", "python"), str(gen)], cwd=ROOT, check=True)


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


def verify_pilot(pilots: list[dict[str, str]]) -> None:
    if len(pilots) != 36:
        raise ValueError(f"Expected 36 LP-ML1A4 pilot rows, got {len(pilots)}")
    bins = {row.get("target_bin_deg", "") for row in pilots}
    heights = {row.get("H_nm", "") for row in pilots}
    if not {"0", "60", "120", "180", "240", "300"}.issubset(bins):
        raise ValueError(f"Missing bins in pilot: {bins}")
    if not {"500", "600", "650", "700"}.issubset(heights):
        raise ValueError(f"Missing heights in pilot: {heights}")
    numeric = ["H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm"]
    for row in pilots:
        if row.get("geometry_source") != "LP-ML1A4_explicit_generator":
            raise ValueError("Pilot contains non-LP-ML1A4 geometry source")
        if row.get("historical_geometry_recovered", "").lower() != "false":
            raise ValueError("Pilot contains recovered historical geometry")
        if row.get("prepared_not_run", "").lower() != "true":
            raise ValueError("Pilot row is not prepared_not_run")
        for key in numeric:
            float(row[key])


def make_queue(pilots: list[dict[str, str]]) -> list[dict[str, str]]:
    smoke_ids = {row["candidate_id"] for row in pick_smoke(pilots)}
    rows = []
    for i, row in enumerate(pilots, 1):
        rows.append({
            "queue_id": f"LPML1B0_{i:03d}",
            "candidate_id": row["candidate_id"],
            "target_bin_deg": row["target_bin_deg"],
            "sampling_group": row["sampling_group"],
            "sampling_family": row["sampling_family"],
            "H_nm": row["H_nm"],
            "period_x_nm": row["period_x_nm"],
            "period_y_nm": row["period_y_nm"],
            "L1_nm": row["L1_nm"],
            "W1_nm": row["W1_nm"],
            "theta1_deg": row["theta1_deg"],
            "L2_nm": row["L2_nm"],
            "W2_nm": row["W2_nm"],
            "theta2_deg": row["theta2_deg"],
            "center_dx_nm": row["center_dx_nm"],
            "center_dy_nm": row["center_dy_nm"],
            "gap_or_dx_nm": row["gap_or_dx_nm"],
            "intended_wavelengths_nm": row.get("intended_wavelengths_nm", ",".join(map(str, WAVELENGTHS))),
            "num_wavelengths": "9",
            "source_manifest": str(PILOT),
            "run_status": "queued_not_run",
            "prepared_not_run": "true",
            "priority_score": row.get("priority_score", ""),
            "pilot_rank": row.get("pilot_rank", ""),
            "estimated_runtime_class": "small_periodic_dimer_9wl_2pol",
            "smoke_test_candidate": str(row["candidate_id"] in smoke_ids).lower(),
            "notes": "planning only; no FDTD execution in LP-ML1B0",
        })
    return rows


def pick_smoke(pilots: list[dict[str, str]]) -> list[dict[str, str]]:
    sorted_rows = sorted(pilots, key=lambda r: float(r.get("priority_score") or 0), reverse=True)
    b300 = next(row for row in sorted_rows if row.get("target_bin_deg") == "300")
    fallback = next(row for row in sorted_rows if row.get("target_bin_deg") in {"240", "0", "60", "120", "180"} and row["candidate_id"] != b300["candidate_id"])
    return [b300, fallback]


def make_smoke_rows(pilots: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in pick_smoke(pilots):
        reason = "highest-priority B300 candidate" if row["target_bin_deg"] == "300" else "non-B300 anchor for template sanity check"
        out.append({
            "candidate_id": row["candidate_id"],
            "target_bin_deg": row["target_bin_deg"],
            "H_nm": row["H_nm"],
            "sampling_group": row["sampling_group"],
            "reason_selected": reason,
            "planned_polarizations": "x,y",
            "planned_wavelengths_nm": ",".join(map(str, WAVELENGTHS)),
            "run_status": "smoke_test_recommended_not_run",
        })
    return out


def runner_config() -> dict:
    return {
        "project_root": str(ROOT),
        "worktree_root": str(ROOT),
        "python_exe": r"N:\anaconda_envs\RCP_LCP\python.exe",
        "lumerical_mode": "fdtd",
        "simulation_type": "normal_incidence_periodic_plane_wave_dimer",
        "wavelengths_nm": WAVELENGTHS,
        "polarizations": ["x", "y"],
        "boundary_condition": "periodic_normal_incidence_only",
        "mesh_policy": "reuse_prior_periodic_dimer_template_or_create_explicit_template_in_LP-ML1B1",
        "farfield_policy": "complex_fields_only_no_farfield3d_phase",
        "planned_complex_field_commands": ["farfieldvector3d", "farfieldpolar3d"],
        "result_policy": "csv_json_lightweight_only",
        "heavy_file_policy": "do_not_commit_fsp_ldf_monitor_farfield_raw",
        "execution_policy": "planning_only_no_fdtd_in_LP-ML1B0",
        "fmm_policy": "backend_unavailable_from_LP-FMM0A_do_not_use_for_LP-ML1B0",
    }


def write_reports(queue: list[dict[str, str]], smoke: list[dict[str, str]]) -> None:
    bin_counts = Counter(row["target_bin_deg"] for row in queue)
    h_counts = Counter(row["H_nm"] for row in queue)
    group_counts = Counter(row["sampling_group"] for row in queue)
    bin_lines = [f"- {k}: {v}" for k, v in sorted(bin_counts.items(), key=lambda kv: int(kv[0]))]
    h_lines = [f"- H{k}: {v}" for k, v in sorted(h_counts.items(), key=lambda kv: int(kv[0]))]
    group_lines = [f"- {k}: {v}" for k, v in sorted(group_counts.items())]
    planning = [
        "# LP-ML1B0 runner planning",
        "",
        "Purpose: plan the normal-incidence periodic full-wave FDTD runner for the LP-ML1A4 explicit 36-case pilot queue.",
        "",
        "Legacy route No-Go: A2/A3/A3B/A19/A20 recovered no high-confidence run-ready legacy geometry; A20 indexed 2735 FSP files and attempted 20 candidate-matched FSP opens, all failed.",
        "FMM not used yet: LP-FMM0A found no importable FMM/RCWA backend among grcwa, rcwa, s4, S4, meent, reticolo.",
        "LP-ML1A4 pilot is used because it contains explicit numeric geometry and prepared_not_run rows.",
        "",
        "## Inputs used",
        f"- {PILOT}", f"- {MANIFEST}", f"- {SEED_SUMMARY}", f"- {FMM_QUEUE}", f"- {FMM_CONV}",
        "",
        f"Pilot queue count: {len(queue)}",
        "",
        "## Counts by target bin", *bin_lines,
        "", "## Counts by H_nm", *h_lines,
        "", "## Counts by sampling group", *group_lines,
        "",
        "Expected output schema: see outputs/lp_ml1b0_runner_planning/lp_ml1b0_expected_result_schema.csv.",
        "Runner boundaries: LP-ML1B0 is planning only; LP-ML1B1 should run a 2-candidate template smoke test before the full 36-case pilot.",
        "Next step: LP-ML1B1 template smoke test, not full 36-case execution.",
        "",
        "No FDTD was run.", "No FMM solver was executed.", "No Lumerical GUI was opened.", "No model was trained.", "No K=6 was attempted.",
    ]
    (REPORTS / "lp_ml1b0_runner_planning.md").write_text("\n".join(planning) + "\n", encoding="utf-8")
    spec = [
        "# LP-ML1B0 complex Jones extraction spec",
        "",
        "Intensity-only farfield3d is forbidden for phase because it returns intensity |E|^2 and loses complex phase.",
        "Use farfieldvector3d or farfieldpolar3d, or equivalent complex-field monitor data, for complex far-field/Jones extraction.",
        "LP-ML1B uses normal-incidence periodic plane-wave dimer simulations. Later angled validation must use Bloch/BFAST rather than plain periodic.",
        "Run x and y input polarizations across 450-454 nm.",
        "",
        "Jones convention: Jt = [[txx, txy], [tyx, tyy]], columns are input polarization, rows are output polarization.",
        "txx = x_out from x_in; tyx = y_out from x_in; txy = x_out from y_in; tyy = y_out from y_in.",
        "selected x-channel phase is angle(txx). Phase error uses wrapped/circular angular distance to nearest 60-degree bin.",
        "selected_Tx = |txx|^2; leakage_xin_to_yout = |tyx|^2; leakage_yin_to_xout = |txy|^2; y_direct_leakage = |tyy|^2; ratio and matrix_error follow the LP projection target Jt(lambda) ~= t(lambda) exp(i phi_bin) |x><x|.",
        "Spectral aggregation is over 450-454 nm using the 9-point wavelength grid.",
        "Batch Lumerical commands with lumapi.eval where appropriate.",
        "",
        "No FDTD was run.",
    ]
    (REPORTS / "lp_ml1b0_complex_jones_extraction_spec.md").write_text("\n".join(spec) + "\n", encoding="utf-8")
    review = ["# LP-ML1B0 pilot queue review", "", "## All 36 pilot rows", "", "| candidate_id | bin | H | group | family | score | smoke |", "|---|---:|---:|---|---|---:|---|"]
    for row in queue:
        review.append(f"| {row['candidate_id']} | {row['target_bin_deg']} | {row['H_nm']} | {row['sampling_group']} | {row['sampling_family']} | {row['priority_score']} | {row['smoke_test_candidate']} |")
    review += ["", "## Top B300 rows"]
    for row in [r for r in queue if r["target_bin_deg"] == "300"][:10]:
        review.append(f"- {row['candidate_id']} H{row['H_nm']} score={row['priority_score']}")
    review += ["", "## Top B240 rows"]
    for row in [r for r in queue if r["target_bin_deg"] == "240"][:10]:
        review.append(f"- {row['candidate_id']} H{row['H_nm']} score={row['priority_score']}")
    review += ["", "## Coverage checks", f"Six-bin coverage: {dict(sorted(bin_counts.items(), key=lambda kv: int(kv[0])))}", f"H coverage: {dict(sorted(h_counts.items(), key=lambda kv: int(kv[0])))}", "Geometry validity: all rows contain explicit numeric geometry from LP-ML1A4.", "", "## 2-candidate smoke-test recommendation"]
    for row in smoke:
        review.append(f"- {row['candidate_id']}: B{row['target_bin_deg']} H{row['H_nm']} ({row['reason_selected']})")
    review += ["", "Recommendation: proceed to LP-ML1B1 only after reviewing this runner plan."]
    (REPORTS / "lp_ml1b0_pilot_queue_review.md").write_text("\n".join(review) + "\n", encoding="utf-8")


def no_heavy_outputs() -> bool:
    if not OUT.exists():
        return True
    return not any(any(marker in p.name.lower() for marker in HEAVY_MARKERS) for p in OUT.rglob("*"))


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    pilots = read_csv(PILOT)
    verify_pilot(pilots)
    queue = make_queue(pilots)
    smoke = make_smoke_rows(pilots)
    schema_rows = [{"column": col, "description": "planned complex Jones FDTD result field"} for col in SCHEMA_COLUMNS]
    write_csv(OUT / "lp_ml1b0_pilot_queue.csv", queue, QUEUE_COLUMNS)
    write_csv(OUT / "lp_ml1b0_smoke_test_recommendation.csv", smoke, ["candidate_id", "target_bin_deg", "H_nm", "sampling_group", "reason_selected", "planned_polarizations", "planned_wavelengths_nm", "run_status"])
    write_csv(OUT / "lp_ml1b0_expected_result_schema.csv", schema_rows, ["column", "description"])
    (OUT / "lp_ml1b0_runner_config_draft.json").write_text(json.dumps(runner_config(), indent=2), encoding="utf-8")
    bin_counts = dict(Counter(row["target_bin_deg"] for row in queue))
    h_counts = dict(Counter(row["H_nm"] for row in queue))
    group_counts = dict(Counter(row["sampling_group"] for row in queue))
    summary = {"pilot_queue_count": len(queue), "count_by_target_bin": bin_counts, "count_by_H_nm": h_counts, "count_by_sampling_group": group_counts, "smoke_test_candidates": [r["candidate_id"] for r in smoke], "no_fdtd_run": True, "no_fmm_solve": True, "no_gui_opened": True, "no_model_trained": True, "no_k6_attempted": True, "no_heavy_outputs_created": no_heavy_outputs()}
    (OUT / "lp_ml1b0_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_reports(queue, smoke)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
