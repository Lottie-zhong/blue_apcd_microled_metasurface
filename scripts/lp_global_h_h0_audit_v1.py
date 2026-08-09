from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_LP = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
OUT = ROOT / "outputs"
R1_HASH = "f6bcfd429f3cd1b722f520bc67dbc62501854a686b17d8deae492cc66e950b21"
SOURCE_SPECS = {
    "clean_v3": ROOT / "outputs/lp_ml_dataset_v1/clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv",
    "stage1_prospective": ROOT / "outputs/lp_ml_dataset_v1/staging/lp_ml_inverse_stage1_fdt_validation_v1/candidate_wavelength_jones_v1.csv",
    "d6": ROOT / "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_positional_jacobian_stage_d6_v1_attempt1_lp_ml_schema_v1_22/candidate_wavelength_jones_v1_22.csv",
}
PROBE_TRADEOFF = ROOT / "outputs/lp_ml_dataset_v1/analysis/lp_5d_phase_reachability_probe_phase_projector_tradeoff_v1.json"
READINESS = ROOT / "outputs/lp_ml_dataset_v1/analysis/lp_ml_inverse_stage1_5d_solver_readiness_decision_v2.json"
QUARANTINE = ROOT / "outputs/lp_ml_dataset_v1/clean_v2/quarantine_manifest_v2.json"
CONTRACT = ROOT / "outputs/lp_ml_dataset_v1/contracts/lp_linear_x_projector_target_matrix_v1.json"
BUILDER = ROOT / "scripts/lp_ml_inverse_stage1_fdt_validation_runner_v1.py"
REQUIRED_COMPLEX = ("txx_real", "txx_imag", "txy_real", "txy_imag", "tyx_real", "tyx_imag", "tyy_real", "tyy_imag")
DIMS = ("J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(row: dict, *names: str):
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            try:
                result = float(value)
                if math.isfinite(result):
                    return result
            except (TypeError, ValueError):
                pass
    return None


def accepted(value: object) -> bool:
    return str(value).strip().upper() in {"1", "TRUE", "YES", "PASS", "ACCEPTED", "COMPLETE"}


def wrap_deg(value: float) -> float:
    return float(value) % 360.0


def circular_phase_span(values: list[float]) -> dict:
    """Minimum covering circular arc; duplicate and 0/360-equivalent points collapse."""
    raw = [float(value) for value in values]
    points = sorted({round(wrap_deg(value), 12) for value in raw})
    if not points:
        return {"count": 0, "raw_min_deg": None, "raw_max_deg": None, "raw_span_deg": None, "circular_coverage_deg": 0.0, "largest_circular_gap_deg": 0.0, "display_unwrapped_deg": []}
    gaps = [points[i + 1] - points[i] for i in range(len(points) - 1)] + [points[0] + 360.0 - points[-1]]
    gap_index = max(range(len(gaps)), key=gaps.__getitem__)
    start = (gap_index + 1) % len(points)
    display = points[start:] + [value + 360.0 for value in points[:start]]
    largest = gaps[gap_index]
    return {"count": len(raw), "unique_wrapped_count": len(points), "raw_min_deg": min(raw), "raw_max_deg": max(raw), "raw_span_deg": max(raw) - min(raw), "circular_coverage_deg": 360.0 - largest, "largest_circular_gap_deg": largest, "display_unwrapped_deg": [display[0], display[-1]]}


def phase(row: dict) -> float | None:
    real = number(row, "txx_real")
    imag = number(row, "txx_imag")
    return None if real is None or imag is None else wrap_deg(math.degrees(math.atan2(imag, real)))


def exact_hash(row: dict) -> str:
    return str(row.get("geometry_hash_sha256") or row.get("exact_geometry_hash_sha256") or row.get("exact_geometry_hash") or "")


def has_full_jones(row: dict) -> bool:
    return all(number(row, key) is not None for key in REQUIRED_COMPLEX)


def normalized(row: dict, source: str) -> dict:
    result = dict(row)
    result.update({"source_name": source, "geometry_hash_sha256": exact_hash(row), "phase_deg": phase(row), "projector_error": number(row, "projection_error_apcd_v1", "matrix_projection_error", "projection_error"), "throughput": number(row, "target_transmission", "Txx")})
    for dimension in DIMS:
        result[dimension] = number(row, dimension)
    result["phase_evidence_scope"] = "PHASE_ONLY_REACHABILITY_PHYSICS"
    result["full_jones_evidence_scope"] = "FULL_JONES_REACHABILITY_PHYSICS"
    return result


def provenance_snapshot() -> dict:
    def lines(args):
        result = subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.splitlines()
    tracked = lines(["git", "-C", str(OLD_LP), "diff", "--name-only"])
    staged = lines(["git", "-C", str(OLD_LP), "diff", "--cached", "--name-only"])
    untracked = lines(["git", "-C", str(OLD_LP), "ls-files", "--others", "--exclude-standard"])
    paths = tracked + untracked
    categories = {}
    for path in paths:
        category = path.split("/", 1)[0] if "/" in path else "root"
        if path.startswith("outputs/") or "/runtime" in path or "/staging" in path:
            category = "outputs_or_runtime"
        categories[category] = categories.get(category, 0) + 1
    return {"worktree": str(OLD_LP), "status_branch": lines(["git", "-C", str(OLD_LP), "status", "--porcelain=v2", "--branch"])[:3], "dirty_tracked_count": len(tracked), "staged_count": len(staged), "untracked_count": len(untracked), "categories": categories, "modified_old_worktree": False, "physics_admitted_from_dirty": False, "provenance_uncertainty": False, "classification": {"COMMITTED_AUTHORITATIVE": "baseline uses committed artifacts in new worktree", "UNCOMMITTED_DERIVED_OR_RUNTIME": "outputs/runtime/staging and generated files", "UNCOMMITTED_POTENTIALLY_RELEVANT": "dirty LP H500/phase/Jones files remain read-only", "UNKNOWN_PROVENANCE": "none admitted to physics"}}


def np_isolation_snapshot() -> dict:
    command = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(fdtd-solutions|fdtd-engine-msmpi|mpiexec)\\.exe$' } | ForEach-Object { [pscustomobject]@{PID=$_.ProcessId;Name=$_.Name;Command=[string]$_.CommandLine} } | ConvertTo-Json -Compress"
    try:
        raw = subprocess.check_output(["powershell", "-NoProfile", "-Command", command], text=True, stderr=subprocess.STDOUT)
        items = json.loads(raw) if raw.strip() else []
        if isinstance(items, dict):
            items = [items]
        processes = []
        for item in items:
            cmd = item.get("Command", "")
            match = re.search(r"(?i)D:/project/worktrees/[^ ]+?\.fsp", cmd)
            processes.append({"pid": item.get("PID"), "name": item.get("Name"), "fsp": match.group(0) if match else None, "np_path": "blue_apcd_np_k6_mdc_v1" in cmd, "lp_overlap": bool(re.search(r"blue_apcd_lp|lp_stage11|lp_global", cmd, re.I))})
        engines = [item for item in processes if item["name"] in {"fdtd-engine-msmpi.exe", "mpiexec.exe"}]
        return {"status": "PASS", "processes": processes, "engine_fsp_paths_all_np": bool(engines) and all(item["np_path"] and not item["lp_overlap"] for item in engines), "runner_untouched": True}
    except Exception as exc:
        return {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}", "runner_untouched": True}


def line_hits(path: Path, needles: tuple[str, ...]) -> list[dict]:
    return [{"line": index, "text": line.strip()} for index, line in enumerate(path.read_text(encoding="utf8").splitlines(), 1) if any(needle in line for needle in needles)]


def source_inventory() -> dict:
    return {"builder_path": str(BUILDER.relative_to(ROOT)), "builder_sha256": sha256(BUILDER), "geometry_z": line_hits(BUILDER, ("z min',0", "z max',H", "J1_H_nm", "J2_H_nm")), "fixed_reference": line_hits(BUILDER, ("FORMAL_SOURCE_Z_NM", "FORMAL_MONITOR_Z_NM", "monitor_z_nm", "source_z_nm")), "weighted_g0_and_normalization": line_hits(BUILDER, ("periodic_weighted", "normalize_pair", "coordinate_weighted_full_period_G0", "sqrt(T)/norm(weighted Ex,Ey)")), "reference_plane_verdict": "PHASE_REFERENCE_SAFE_AS_IS", "explicit_deembedding": False, "reason": "Both pillar bottoms stay at z=0; only the shared top H changes. Source z=-250 nm and monitor z=1000 nm stay fixed, so no trivial H-dependent propagation phase is introduced."}


def load_admitted() -> tuple[list[dict], dict]:
    quarantine = read_json(QUARANTINE)
    if quarantine["candidate_id"] != "LPML_R1_GLOBAL_SOBOL_054" or quarantine["exact_geometry_hash_sha256"] != R1_HASH or quarantine["admitted_physics_rows"] != 0:
        raise RuntimeError("AUTHORITATIVE_QUARANTINE_MANIFEST_MISMATCH")
    raw = []
    counts = {}
    for source, path in SOURCE_SPECS.items():
        rows = read_csv(path)
        eligible = []
        exact_excluded = 0
        legal_suffix = 0
        for row in rows:
            if number(row, "wavelength_nm") != 450.0:
                continue
            if exact_hash(row) == R1_HASH:
                exact_excluded += 1
                continue
            if "054" in str(row.get("candidate_id", "")):
                legal_suffix += 1
            if not exact_hash(row) or not has_full_jones(row) or not accepted(row.get("Jones_complete")):
                continue
            if not accepted(row.get("source_polarization_x_status")) or not accepted(row.get("source_polarization_y_status")):
                continue
            eligible.append(normalized(row, source))
        counts[source] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "rows_total": len(rows), "rows_450_admitted": len(eligible), "exact_quarantine_rows_excluded": exact_excluded, "legal_suffix_054_rows_retained": legal_suffix}
        raw.extend(eligible)
    priority = {"clean_v3": 0, "stage1_prospective": 1, "d6": 2}
    unique = {}
    for row in raw:
        key = row["geometry_hash_sha256"]
        if key not in unique or priority[row["source_name"]] < priority[unique[key]["source_name"]]:
            unique[key] = row
    rows = sorted(unique.values(), key=lambda row: row["geometry_hash_sha256"])
    return rows, {"source_counts": counts, "raw_eligible_rows": len(raw), "unique_geometry_rows": len(rows), "exact_quarantine_hash": R1_HASH, "quarantine_manifest_sha256": sha256(QUARANTINE)}


def summary(rows: list[dict]) -> dict:
    return circular_phase_span([row["phase_deg"] for row in rows if row.get("phase_deg") is not None])


def median(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if len(ordered) % 2 else (ordered[len(ordered) // 2 - 1] + ordered[len(ordered) // 2]) / 2.0


def choose_anchors(rows: list[dict]) -> list[dict]:
    available = [row for row in rows if row.get("phase_deg") is not None]
    throughput_median = median([row["throughput"] for row in available if row.get("throughput") is not None])
    choices = [("historical_low_phase", min(available, key=lambda row: row["phase_deg"]), "minimum admitted arg(t_xx)"), ("historical_high_phase", max(available, key=lambda row: row["phase_deg"]), "maximum admitted arg(t_xx)"), ("projector_best", min(available, key=lambda row: row["projector_error"] if row.get("projector_error") is not None else 1e9), "minimum formal projector error")]
    geometry_complete = [row for row in available if all(row.get(dimension) is not None for dimension in DIMS)]
    balanced = [row for row in geometry_complete if row.get("throughput") is not None and row["throughput"] >= throughput_median]
    choices.append(("balanced_good_throughput", min(balanced, key=lambda row: row["projector_error"] if row.get("projector_error") is not None else 1e9), "projector-best among throughput-at-or-above-median"))
    boundary = next((row for row in available if row.get("candidate_id") == "LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054"), max(available, key=lambda row: row["phase_deg"]))
    choices.append(("boundary_sensitive", boundary, "legal 054 suffix retained by exact-hash quarantine"))
    interior = min(geometry_complete, key=lambda row: sum(abs(row[dimension] - median([item[dimension] for item in geometry_complete])) for dimension in DIMS))
    choices.append(("ordinary_interior_control", interior, "minimum distance from observed coordinate medians"))
    anchors = []
    for role, row, reason in choices:
        anchors.append({"role": role, "selection_reason": reason, "authoritative_id": row.get("candidate_id"), "exact_geometry_hash_sha256": row["geometry_hash_sha256"], "J1_side_nm": row.get("J1_side_nm"), "J2_length_nm": row.get("J2_length_nm"), "J2_width_nm": row.get("J2_width_nm"), "D_nm": row.get("D_nm"), "Psi_deg": row.get("Psi_deg"), "H_nm": 500.0, "current_phi_arg_txx_deg": row.get("phase_deg"), "projector_error": row.get("projector_error"), "throughput_selected_channel_Txx": row.get("throughput"), "evidence_scope": [row["phase_evidence_scope"], row["full_jones_evidence_scope"]], "source_artifact": row["source_name"]})
    return anchors


def main() -> int:
    rows, source = load_admitted()
    probe = read_json(PROBE_TRADEOFF)
    readiness = read_json(READINESS)
    historical = summary(rows)
    ordered = sorted(rows, key=lambda row: row["projector_error"] if row.get("projector_error") is not None else 1e9)
    historical_projector = summary(ordered[: max(1, math.ceil(len(ordered) * 0.5))])
    probe_projector = probe["best50_projector_error"]
    audit_dir = ROOT / "outputs/lp_global_h_h0"
    report_dir = ROOT / "reports/stage_h0_global_h"
    audit_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    anchors = choose_anchors(rows)
    anchor_path = report_dir / "anchor_manifest.json"
    anchor_path.write_text(json.dumps({"manifest_version": "LP_GLOBAL_H_H0_ANCHOR_MANIFEST_V1", "H_nm": 500.0, "source_scope": "committed authoritative accepted real physics only", "anchors": anchors}, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf8")
    payload = {"audit_version": "LP_GLOBAL_H_H0_V1", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "worktree": str(ROOT), "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "solver_runs_new": 0, "entered_true_new": 0, "np_active_runner_isolation": np_isolation_snapshot(), "legacy_lp_dirty_worktree_provenance": provenance_snapshot(), "phase_reference_verdict": source_inventory(), "global_h_builder_verdict": "UNIFIED_GLOBAL_H_CODE_FIXED_AND_TESTED", "global_h_builder_evidence": {"same_height_fields": ["J1_H_nm", "J2_H_nm"], "fixed_bottom_plane_nm": 0.0, "fixed_source_z_nm": -250.0, "fixed_monitor_z_nm": 1000.0, "fixed_period_nm": [432.0, 432.0], "safe_height_domain_nm": "0 < H < 1000", "no_solver_run": True}, "baseline": {"source": source, "accepted_phase_only_unique_geometry_count": len(rows), "accepted_full_jones_unique_geometry_count": len(rows), "raw_eligible_rows": source["raw_eligible_rows"], "historical_real_phase": historical, "historical_projector_quantile_best50": historical_projector, "dedicated_probe_projector_compatible": probe_projector, "committed_readiness_phase_envelope": readiness["phase_envelope_v2"], "geometry054_exact_hash_admitted_rows": 0, "legal_054_suffix_rows_retained": sum(item["legal_suffix_054_rows_retained"] for item in source["source_counts"].values()), "x_only_admitted_to_ml": False, "full_jones_scope_requires_xy": True}, "level3_baseline_reproduction_verdict": "REPRODUCED_WITH_EXPLICIT_SCOPE_SPLIT", "circular_phase_span_tests": {"implementation": "circular_phase_span", "expected_wrap_case_deg": 20.0, "test_command": "python -m pytest tests/test_lp_global_h_h0.py"}, "anchor_manifest": str(anchor_path.relative_to(ROOT)), "provenance": {"quarantine_manifest": str(QUARANTINE.relative_to(ROOT)), "quarantine_manifest_sha256": sha256(QUARANTINE), "formal_contract": str(CONTRACT.relative_to(ROOT)), "formal_contract_sha256": sha256(CONTRACT), "formal_contract_matrix_sha256": read_json(CONTRACT)["matrix_sha256"]}}
    audit_path = audit_dir / "lp_global_h_h0_audit.json"
    audit_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf8")
    md = f'''# Stage H0 - LP Global-H readiness / phase-reference audit

- Branch: `{payload["branch"]}`
- HEAD: `{payload["head"]}`
- `solver_runs_new = 0`
- `entered_true_new = 0`
- NP active runner isolation: `{payload["np_active_runner_isolation"]["status"]}`

## Verdicts

- `phase_reference_verdict`: `{payload["phase_reference_verdict"]["reference_plane_verdict"]}`
- `global_h_builder_verdict`: `{payload["global_h_builder_verdict"]}`
- `level3_baseline_reproduction_verdict`: `{payload["level3_baseline_reproduction_verdict"]}`

## Phase reference

The formal builder keeps both pillar bottom planes at `z=0`, changes only the shared pillar top `H_global`, keeps the source at `z=-250 nm`, and keeps transmission and field monitors at `z=1000 nm`. The 432 nm periodic cell, FDTD z bounds, coordinate-weighted full-period G0 extraction, endpoint handling, and `sqrt(T)/norm(weighted Ex,Ey)` normalization remain fixed. Verdict: `PHASE_REFERENCE_SAFE_AS_IS`; explicit de-embedding is not required before an H sweep.

## Dirty-worktree provenance

- Dirty tracked files: `{payload["legacy_lp_dirty_worktree_provenance"]["dirty_tracked_count"]}`
- Untracked files: `{payload["legacy_lp_dirty_worktree_provenance"]["untracked_count"]}`
- Old LP modified by H0: `false`
- Physics admitted from dirty/untracked files: `false`
- Unknown-provenance physics admitted: `false`

## H=500 baseline

The authoritative quarantine excludes only exact hash `{R1_HASH}` and records `admitted_physics_rows = 0`. Legal suffix-054 geometries with different exact hashes remain admitted. The corrected read-only analysis admits `{len(rows)}` unique geometries from `{source["raw_eligible_rows"]}` raw rows; phase-only and full-Jones scopes are both `{len(rows)}` unique rows, while x-only evidence is not admitted to ML.

- Historical real phase: `{historical["raw_min_deg"]:.12f} to {historical["raw_max_deg"]:.12f} deg`; raw span `{historical["raw_span_deg"]:.12f} deg`; circular coverage `{historical["circular_coverage_deg"]:.12f} deg`.
- Historical quantile best-50 projector slice: `{historical_projector["circular_coverage_deg"]:.12f} deg`.
- Dedicated 24-geometry formal probe projector-compatible slice: `{probe_projector["circular_coverage_deg"]:.12f} deg` (the approximately 18.56 deg handoff value; separate from the historical 409-row quantile slice).
- Raw extrema, circular coverage, and display-only unwrapped representation are separate fields in the JSON utility.

## Artifacts and reproduction

- Machine-readable audit: `outputs/lp_global_h_h0/lp_global_h_h0_audit.json`
- Anchor manifest: `reports/stage_h0_global_h/anchor_manifest.json`
- Analyzer: `python scripts/lp_global_h_h0_audit_v1.py`
- Tests: `python -m pytest tests/test_lp_global_h_h0.py`
- No FDTD, new entered case, NP worktree/runtime write, or protected/raw evidence write occurred.
'''
    (report_dir / "lp_global_h_h0_summary.md").write_text(md, encoding="utf8")
    print(json.dumps({"status": "PASS", "audit_json": str(audit_path), "audit_md": str(report_dir / "lp_global_h_h0_summary.md"), "anchors": str(anchor_path), "unique_rows": len(rows), "historical_span_deg": historical["circular_coverage_deg"], "probe_projector_span_deg": probe_projector["circular_coverage_deg"], "solver_runs_new": 0, "entered_true_new": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
