from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "lp_ml0_existing_data_audit"
REPORT = ROOT / "reports" / "lp_ml0_existing_data_audit.md"
SCHEMA = ROOT / "reports" / "lp_ml0_schema_draft.yaml"

REQUIRED_COLUMNS = [
    "candidate_id", "H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg",
    "gap_or_dx_nm", "target_bin_deg", "nearest_bin_deg", "selected_phase_deg", "phase_error_deg",
    "Tx", "leakage", "conversion_to_leakage_ratio", "matrix_error", "strict_or_loose_or_fail",
    "source_stage", "source_file", "result_csv",
]
SPECTRAL_COLUMNS = [
    "phase_error_min_450_454", "phase_error_max_450_454", "phase_error_mean_450_454",
    "min_Tx_450_454", "max_leakage_450_454", "min_ratio_450_454", "bin_consistency_450_454",
]
EXTRA_COLUMNS = ["library_role", "robust_451_453_ready", "direct_k6_ready"]
ALL_COLUMNS = REQUIRED_COLUMNS + SPECTRAL_COLUMNS + EXTRA_COLUMNS

H500_SEEDS = [
    (0, "H500DIMER2C_029", "strict", 812.0, 1.016, 3.24, ""),
    (60, "H500DIMER2B_006", "strict", 258.74, 0.930, 6.01, ""),
    (120, "H500DIMER2C_004", "loose", 4.50, 0.506, "", 0.471),
    (180, "H500DIMER2C_026", "strict", 16.27, 0.934, "", ""),
    (240, "H500DIMER2D_018", "loose_near_miss", 6.33, 0.784, 15.788, ""),
    (300, "H500DIMER2D_006", "strict", 13.46, 0.987, "", ""),
]

ALIASES = {
    "candidate_id": ["candidate_id", "case_id", "dimer_case_id", "source_pair_id", "pair_id"],
    "H_nm": ["H_nm", "height_nm"],
    "target_bin_deg": ["target_bin_deg", "phase_bin_deg", "bin_deg", "original_target_bin_deg"],
    "nearest_bin_deg": ["nearest_bin_deg", "nearest_actual_bin_deg", "actual_nearest_bin_deg"],
    "selected_phase_deg": ["selected_phase_deg", "actual_common_phase_deg", "dimer_output_phase_deg", "output_phase_deg"],
    "phase_error_deg": ["phase_error_deg", "actual_common_phase_error_deg", "phase_err", "max_phase_error_deg"],
    "Tx": ["Tx", "target_Tx", "selected_power", "target_x_power", "worst_Tx"],
    "leakage": ["leakage", "y_leakage", "blocked_y_leakage", "blocked_input_total_power", "leak_y_power"],
    "conversion_to_leakage_ratio": ["conversion_to_leakage_ratio", "projection_selectivity_ratio", "predicted_ratio", "worst_ratio", "ratio"],
    "matrix_error": ["matrix_error", "matrix_projection_error_norm", "worst_matrix_error"],
    "strict_or_loose_or_fail": ["strict_or_loose_or_fail", "pass_level", "pass_level_as_reassigned", "best_pass_level", "status"],
    "result_csv": ["result_csv", "source_file"],
}


def first(row: dict, names: list[str]) -> str:
    for name in names:
        value = row.get(name, "")
        if str(value).strip() not in {"", "nan", "None"}:
            return str(value).strip()
    return ""


def number(value: str) -> float | None:
    try:
        out = float(value)
        return None if math.isnan(out) else out
    except (TypeError, ValueError):
        return None


def infer_stage(path: Path) -> str:
    text = str(path).replace("\\", "/")
    m = re.search(r"stage11[_-]?(\d+[a-z]?|4a\d+|3b\d+)", text, re.I)
    return "stage11_" + m.group(1).lower() if m else "manual_or_report"


def infer_height(candidate_id: str, row: dict) -> str:
    direct = first(row, ALIASES["H_nm"])
    if direct:
        return direct
    m = re.search(r"H(\d{3})", candidate_id)
    return m.group(1) if m else ""


def read_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            return []
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list) and any(isinstance(x, dict) for x in value):
                    return [x for x in value if isinstance(x, dict)]
            return [data]
    return []


def iter_sources() -> list[Path]:
    bad = (".fsp", ".ldf", ".log", "monitor", "farfield", "far_field", "fielddump", "dump")
    out: list[Path] = []
    for root in [ROOT / "outputs", ROOT / "reports", ROOT / "scripts"]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            low = str(path).lower()
            if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md"} and OUT_DIR not in path.parents and not any(x in low for x in bad):
                out.append(path)
    return out


def candidate_from_row(row: dict, source: Path) -> dict | None:
    cid = first(row, ALIASES["candidate_id"])
    if not cid or "DIMER" not in cid.upper():
        return None
    out = {col: "" for col in ALL_COLUMNS}
    out["candidate_id"] = cid
    out["H_nm"] = infer_height(cid, row)
    for col in ["target_bin_deg", "nearest_bin_deg", "selected_phase_deg", "phase_error_deg", "Tx", "leakage", "conversion_to_leakage_ratio", "matrix_error", "strict_or_loose_or_fail", "result_csv"]:
        out[col] = first(row, ALIASES[col])
    gap = re.search(r"G(-?\d+)", cid)
    out["gap_or_dx_nm"] = gap.group(1) if gap else ""
    out["source_stage"] = infer_stage(source)
    out["source_file"] = str(source.relative_to(ROOT)).replace("\\", "/")
    out["result_csv"] = out["result_csv"] or out["source_file"]
    if not any(out[k] for k in ["target_bin_deg", "nearest_bin_deg", "phase_error_deg", "Tx", "conversion_to_leakage_ratio"]):
        return None
    return out


def seed_rows() -> list[dict]:
    rows = []
    for bin_deg, cid, level, ratio, tx, phase_err, matrix in H500_SEEDS:
        row = {col: "" for col in ALL_COLUMNS}
        row.update({
            "candidate_id": cid, "H_nm": "500", "target_bin_deg": str(bin_deg), "nearest_bin_deg": str(bin_deg),
            "phase_error_deg": str(phase_err), "Tx": str(tx), "conversion_to_leakage_ratio": str(ratio),
            "matrix_error": str(matrix), "strict_or_loose_or_fail": level, "source_stage": "lp_ml0_seed",
            "source_file": "manual_seed_from_user_context", "result_csv": "manual_seed_from_user_context",
            "library_role": "450nm_single_point_seed_only", "robust_451_453_ready": "false", "direct_k6_ready": "false",
        })
        rows.append(row)
    return rows


def collect_candidates() -> list[dict]:
    rows, seen = [], set()
    for source in iter_sources():
        for raw in read_rows(source):
            cand = candidate_from_row(raw, source)
            if not cand:
                continue
            key = (cand["candidate_id"], cand["source_file"], cand["target_bin_deg"], cand["selected_phase_deg"])
            if key not in seen:
                seen.add(key)
                rows.append(cand)
    return rows + seed_rows()


def bucket(row: dict) -> str:
    target = int(number(row.get("target_bin_deg", "")) or number(row.get("nearest_bin_deg", "")) or -1)
    if target not in {240, 300}:
        return ""
    phase = number(row.get("phase_error_deg", ""))
    tx = number(row.get("Tx", ""))
    ratio = number(row.get("conversion_to_leakage_ratio", ""))
    matrix = number(row.get("matrix_error", ""))
    phase_near = phase is not None and phase <= 20
    projector_good = tx is not None and ratio is not None and matrix is not None and tx >= 0.45 and ratio >= 8 and matrix <= 0.45
    if phase_near and projector_good:
        detail = "strong_candidate" if phase is not None and phase <= 15 else "possible_overlap_near_miss"
    elif phase_near:
        detail = "phase_near_projector_bad"
    elif projector_good:
        detail = "projector_good_phase_wrong"
    else:
        detail = "no_overlap_evidence"
    return f"b{target}_candidates:{detail}"


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def table(rows: list[dict], fields: list[str], limit: int = 20) -> str:
    if not rows:
        return "No rows."
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(str(row.get(f, "")) for f in fields) + " |")
    return "\n".join(lines)


def write_schema() -> None:
    SCHEMA.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA.write_text("""# LP-ML0 schema draft. Audit only; no training is defined here.
feature_columns:
  geometry: [H_nm, L1_nm, W1_nm, theta1_deg, L2_nm, W2_nm, theta2_deg, gap_or_dx_nm]
  context: [wavelength_nm, target_bin_deg, source_stage]
target_columns:
  projection_metrics: [Tx, leakage, conversion_to_leakage_ratio, matrix_error]
  phase_metrics: [selected_phase_deg, nearest_bin_deg, phase_error_deg]
spectral_encoding:
  wavelength_nm: scalar input for future spectral Jones prediction
  window_features: [min_Tx_450_454, max_leakage_450_454, min_ratio_450_454, bin_consistency_450_454]
jones_encoding:
  note: Re/Im Jones encoding is required for future ML targets.
  fields: [Re_txx, Im_txx, Re_txy, Im_txy, Re_tyx, Im_tyx, Re_tyy, Im_tyy]
loss_notes:
  circular_phase_loss: Use sin/cos or wrapped angular distance; do not use naive phase MSE across 0/360.
rules:
  no_inverse_net_first: true
  no_k6_before_sixbin_robust_library: true
  no_intensity_only_farfield_phase_extraction: true
  complex_fields_required: true
  normal_incidence_periodic_setup_ok: true
  angled_plane_wave_requires_bloch_or_bfast: true
  prefer_lumapi_eval_batching: true
""", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = collect_candidates()
    seeds = seed_rows()
    diag = []
    for row in rows:
        b = bucket(row)
        if b:
            item = dict(row)
            item["diagnosis_bucket"] = b
            diag.append(item)
    write_csv(OUT_DIR / "lp_hnew_all_candidates_unified.csv", rows, ALL_COLUMNS)
    write_csv(OUT_DIR / "lp_h500_450nm_single_point_seed_library.csv", seeds, ALL_COLUMNS)
    write_csv(OUT_DIR / "lp_hnew_b240_b300_diagnosis.csv", diag, ALL_COLUMNS + ["diagnosis_bucket"])
    summary = {
        "total_candidate_count": len(rows),
        "h500_seed_rows": len(seeds),
        "counts_by_H_nm": dict(sorted(Counter(r.get("H_nm") or "unknown" for r in rows).items())),
        "counts_by_target_bin_deg": dict(sorted(Counter(r.get("target_bin_deg") or r.get("nearest_bin_deg") or "unknown" for r in rows).items())),
        "counts_by_pass_level": dict(sorted(Counter(r.get("strict_or_loose_or_fail") or "unknown" for r in rows).items())),
        "diagnosis_counts": dict(sorted(Counter(r["diagnosis_bucket"] for r in diag).items())),
        "no_fdtd_run": True,
    }
    (OUT_DIR / "lp_ml0_audit_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_schema()
    b240 = [r for r in diag if r["diagnosis_bucket"].startswith("b240")]
    b300 = [r for r in diag if r["diagnosis_bucket"].startswith("b300")]
    b300_decoupled = any("projector_good_phase_wrong" in r["diagnosis_bucket"] for r in b300)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join([
        "# LP-ML0 Existing Data Audit", "",
        "No FDTD was run. No Lumerical GUI was opened. This is a CSV/JSON/MD audit and schema freeze only.", "",
        f"Total unified candidate rows: {len(rows)}", "",
        "## Counts by H_nm", "```json\n" + json.dumps(summary["counts_by_H_nm"], indent=2, sort_keys=True) + "\n```",
        "## Counts by target_bin_deg", "```json\n" + json.dumps(summary["counts_by_target_bin_deg"], indent=2, sort_keys=True) + "\n```",
        "## Counts by pass level", "```json\n" + json.dumps(summary["counts_by_pass_level"], indent=2, sort_keys=True) + "\n```",
        "## H500 450 nm Single-Point Seed Library", table(seeds, ["target_bin_deg", "candidate_id", "strict_or_loose_or_fail", "conversion_to_leakage_ratio", "Tx", "phase_error_deg", "matrix_error", "library_role", "robust_451_453_ready", "direct_k6_ready"]),
        "## B240 Diagnosis", table(b240, ["candidate_id", "target_bin_deg", "phase_error_deg", "Tx", "conversion_to_leakage_ratio", "matrix_error", "diagnosis_bucket"], 30),
        "## B300 Diagnosis", table(b300, ["candidate_id", "target_bin_deg", "phase_error_deg", "Tx", "conversion_to_leakage_ratio", "matrix_error", "diagnosis_bucket"], 30),
        "## B300 Failure Interpretation", "B300 shows phase/projector decoupling evidence when high-selectivity rows are far from the B300 phase target." if b300_decoupled else "B300 decoupling evidence is not conclusive from the lightweight audit alone.",
        "## Recommended LP-ML1 Sampling Focus", "Start with a small supervised data schema around projector-good/phase-wrong and phase-near/projector-bad B240/B300 examples. Learn geometry to complex Jones matrix over wavelength before any inverse geometry network.", "",
        "Boundary: the H500 seed library is 450 nm single-point only, not robust over 451-453 nm and not direct K=6 ready.",
    ]) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
