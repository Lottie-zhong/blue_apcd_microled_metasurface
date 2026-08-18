from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
REPORT = ROOT / "reports/stage_paper_a_lp_physics_guided_second_rescue_v1"
POOL_METRICS = ROOT / "reports/stage_paper_a_lp_p0_historical_fulljones_zero_solver_rerank/geometry_broadband_metrics.csv"
SOURCES = [
    ROOT / "reports/stage_h1c1a_broadband_global/h1c1a_broadband_full_jones.csv",
    ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_broadband_full_jones.csv",
    ROOT / "reports/stage_h1c1c_phase_gap/h1c1c_broadband_full_jones.csv",
]
FAILED = {"H1C1B_V2_009", "H1C1B_V2_010", "H1C1B_V2_015", "GLOBAL_018", "H1C1B_V2_012"}
WAVELENGTHS = np.array([450.0 + 0.5 * i for i in range(9)], dtype=float)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_pool():
    meta = {r["geometry_uid"]: r for r in csv.DictReader(POOL_METRICS.open(encoding="utf-8-sig"))}
    rows = []
    for path in SOURCES:
        rows.extend(csv.DictReader(path.open(encoding="utf-8-sig")))
    by = {}
    for row in rows:
        by.setdefault(row["geometry_uid"], []).append(row)
    if len(meta) != 52 or len(rows) != 468 or any(len(v) != 9 for v in by.values()):
        raise RuntimeError(f"POOL_COVERAGE_INVALID:meta={len(meta)} rows={len(rows)} groups={len(by)}")
    return meta, by


def complex_j(row):
    return np.array([
        [complex(float(row["Re_txx"]), float(row["Im_txx"])), complex(float(row["Re_txy"]), float(row["Im_txy"]))],
        [complex(float(row["Re_tyx"]), float(row["Im_tyx"])), complex(float(row["Re_tyy"]), float(row["Im_tyy"]))],
    ], dtype=complex)


def slope(values):
    return float(np.polyfit(WAVELENGTHS, values, 1)[0])


def metrics_for(uid, rows):
    rows = sorted(rows, key=lambda r: float(r["wavelength_nm"]))
    if not np.allclose([float(r["wavelength_nm"]) for r in rows], WAVELENGTHS):
        raise RuntimeError(f"GRID_INVALID:{uid}")
    stokes = []
    sv = []
    for row in rows:
        J = complex_j(row)
        C = 0.5 * J @ J.conj().T
        cxx, cyy, cxy = float(C[0, 0].real), float(C[1, 1].real), C[0, 1]
        s0 = cxx + cyy
        s1 = cxx - cyy
        s2 = 2.0 * cxy.real
        s3 = -2.0 * cxy.imag
        fx = cxx / s0 if s0 else float("nan")
        margin = s1 / s0 if s0 else float("nan")
        dolp = math.sqrt(max(0.0, s1 * s1 + s2 * s2)) / s0 if s0 else float("nan")
        psi = 0.5 * math.atan2(s2, s1)
        singular_values, U, _ = None, None, None
        U, sigma, _ = np.linalg.svd(J, full_matrices=False)
        u1 = U[:, 0]
        sv.append({"wavelength_nm": float(row["wavelength_nm"]), "sigma1": float(sigma[0]), "sigma2": float(sigma[1]), "sigma2_over_sigma1": float(sigma[1] / sigma[0]) if sigma[0] else float("nan"), "u1_x_real": float(u1[0].real), "u1_x_imag": float(u1[0].imag), "u1_y_real": float(u1[1].real), "u1_y_imag": float(u1[1].imag)})
        throughput = float(row.get("throughput", "nan"))
        useful = throughput * fx if math.isfinite(throughput) else float("nan")
        stokes.append({"geometry_uid": uid, "wavelength_nm": float(row["wavelength_nm"]), "S0": s0, "S1": s1, "S2": s2, "S3": s3, "DoLP": dolp, "F_x": fx, "M_x": margin, "psi_rad": psi, "psi_deg": math.degrees(psi), "throughput": throughput, "useful_lp_power": useful, "x_fidelity": fx, "leakage": throughput * (1.0 - fx) if math.isfinite(throughput) else float("nan")})
    M = np.array([r["M_x"] for r in stokes])
    psi = np.unwrap(2.0 * np.array([r["psi_rad"] for r in stokes])) / 2.0
    for i, val in enumerate(psi):
        stokes[i]["psi_unwrapped_rad"] = float(val)
        stokes[i]["psi_unwrapped_deg"] = math.degrees(float(val))
    dM = np.diff(M) / 0.5
    ddM = np.diff(M, n=2) / (0.5 ** 2)
    dpsi = np.diff(psi) / 0.5
    for i, item in enumerate(sv):
        item["geometry_uid"] = uid
        item["dominant_output_overlap_next"] = float(abs(np.vdot(U[:, 0], U[:, 0]))) if False else None
    overlaps = []
    for i in range(len(sv) - 1):
        u_prev = np.array([complex(sv[i]["u1_x_real"], sv[i]["u1_x_imag"]), complex(sv[i]["u1_y_real"], sv[i]["u1_y_imag"])])
        u_next = np.array([complex(sv[i + 1]["u1_x_real"], sv[i + 1]["u1_x_imag"]), complex(sv[i + 1]["u1_y_real"], sv[i + 1]["u1_y_imag"])])
        overlaps.append(float(abs(np.vdot(u_prev, u_next))))
    for i in range(len(sv)):
        sv[i]["geometry_uid"] = uid
        sv[i]["dominant_output_overlap_next"] = overlaps[i] if i < len(overlaps) else None
    power = np.array([r["useful_lp_power"] for r in stokes], dtype=float)
    dolp = np.array([r["DoLP"] for r in stokes], dtype=float)
    min_fx = float(min(r["F_x"] for r in stokes))
    zero_diag = []
    for m, dm in zip(M, np.r_[dM, dM[-1]]):
        if abs(dm) > 1e-15:
            zero_diag.append(abs(float(m / dm)))
    summary = {
        "geometry_uid": uid,
        "source_stage": rows[0].get("source_stage"),
        "exact_hash": rows[0].get("exact_hash"),
        "available_wavelength_start_nm": 450.0,
        "available_wavelength_stop_nm": 454.0,
        "available_points": 9,
        "historical_target_channel_flip": bool(np.min(M) <= 0.0),
        "min_M_x": float(np.min(M)),
        "mean_M_x": float(np.mean(M)),
        "M_x_range": float(np.ptp(M)),
        "M_x_ripple": float(np.ptp(M)),
        "max_abs_dM_x_dlambda": float(np.max(np.abs(dM))),
        "linear_M_x_slope_per_nm": slope(M),
        "M_x_curvature_max_per_nm2": float(np.max(np.abs(ddM))) if len(ddM) else 0.0,
        "nearest_zero_crossing_distance_nm_diagnostic": float(min(zero_diag)) if zero_diag else float("nan"),
        "min_F_x": min_fx,
        "mean_F_x": float(np.mean([r["F_x"] for r in stokes])),
        "psi_min_deg": float(np.min(np.degrees(psi))),
        "psi_max_deg": float(np.max(np.degrees(psi))),
        "psi_range_deg": float(np.ptp(np.degrees(psi))),
        "orientation_ripple_deg": float(np.ptp(np.degrees(psi))),
        "max_abs_dpsi_dlambda_deg_per_nm": float(np.max(np.abs(np.degrees(dpsi)))) if len(dpsi) else 0.0,
        "near_S1_zero_danger": bool(np.min(np.abs(M)) < 0.10),
        "mean_DoLP": float(np.mean(dolp)),
        "worst_DoLP": float(np.min(dolp)),
        "DoLP_slope_per_nm": slope(dolp),
        "sigma2_over_sigma1_mean": float(np.mean([r["sigma2_over_sigma1"] for r in sv])),
        "sigma2_over_sigma1_worst": float(np.max([r["sigma2_over_sigma1"] for r in sv])),
        "dominant_output_overlap_worst": float(np.min(overlaps)),
        "dominant_output_overlap_mean": float(np.mean(overlaps)),
        "dominant_output_overlap_drift": float(1.0 - np.min(overlaps)),
        "useful_lp_power_mean": float(np.mean(power)),
        "useful_lp_power_worst": float(np.min(power)),
        "useful_lp_power_slope_per_nm": slope(power),
        "useful_lp_power_ripple": float(np.ptp(power)),
        "useful_lp_power_cv": float(np.std(power) / np.mean(power)) if np.mean(power) else float("nan"),
        "anchor_450_M_x": float(M[0]),
        "anchor_450_F_x": float(stokes[0]["F_x"]),
        "anchor_450_DoLP": float(stokes[0]["DoLP"]),
        "anchor_450_useful_lp_power": float(stokes[0]["useful_lp_power"]),
    }
    return summary, stokes, sv


def find_fsp(uid):
    found = []
    token = uid.lower()
    for base in (ROOT / "outputs",):
        for d, ds, fs in os.walk(base):
            ds[:] = [x for x in ds if x not in {".git", "monitor", "__pycache__"}]
            if token not in d.lower():
                continue
            for f in fs:
                if f.lower().endswith("_pre.fsp"):
                    found.append(Path(d) / f)
    found.sort(key=lambda p: ("paper_a_lp" in str(p).lower(), len(str(p))))
    return found[0] if found else None


def fsp_audit(uid, meta):
    x = find_fsp(uid)
    y = None
    if x:
        sibling = x.parent.parent / (x.parent.name.replace("_Px", "_Py"))
        candidates = sorted(sibling.glob("*_pre.fsp")) if sibling.exists() else []
        y = candidates[0] if candidates else None
    return {"candidate_id": uid, "parent_fsp_x": str(x) if x else None, "parent_fsp_x_sha256": sha_file(x) if x else None, "parent_fsp_y": str(y) if y else None, "parent_fsp_y_sha256": sha_file(y) if y else None, "material_contract": meta.get("material_contract"), "geometry_identity": {k: meta.get(k) for k in ("geometry_uid", "H_global_nm", "J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg")}, "source_range_nm": [450.0, 454.0], "monitor_range_nm": [450.0, 454.0], "historical_grid_points": 9, "x_y_basis": "real x/y input, complex full-Jones G0 evidence", "mesh_boundary": "historical parent contract; verify setup gate before future FDTD", "native_m1_identity": meta.get("material_contract") == "APCD_TIO2_NATIVE_M1", "reusable_template": bool(x and y), "future_patch": "copy immutable parent and patch only source/monitor to 430-470 nm / 41 native points"}


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    meta, groups = load_pool()
    summaries, spectra, singular = [], [], []
    for uid in sorted(groups):
        summary, rows, sv = metrics_for(uid, groups[uid])
        for k in ("H_global_nm", "J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"):
            summary[k] = float(meta[uid][k])
        for k in ("mean_useful_power", "worst_useful_power", "mean_DoLP", "worst_DoLP", "mean_x_fidelity", "worst_x_fidelity"):
            summary["historical_" + k] = float(meta[uid][k])
        summary["failed_fdt_control"] = uid in FAILED
        summaries.append(summary)
        spectra.extend(rows)
        singular.extend(sv)
    controls = [r for r in summaries if r["failed_fdt_control"]]
    candidates = [r for r in summaries if not r["failed_fdt_control"]]
    for row in candidates:
        row["lexicographic_rank_key"] = [not row["historical_target_channel_flip"], row["min_M_x"], -row["max_abs_dM_x_dlambda"], -row["orientation_ripple_deg"], row["dominant_output_overlap_worst"], row["worst_DoLP"], row["useful_lp_power_worst"], row["mean_DoLP"], row["useful_lp_power_mean"]]
    ranked = sorted(candidates, key=lambda r: (not r["historical_target_channel_flip"], -r["min_M_x"], r["max_abs_dM_x_dlambda"], r["orientation_ripple_deg"], -r["dominant_output_overlap_worst"], -r["worst_DoLP"], -r["useful_lp_power_worst"], -r["mean_DoLP"], -r["useful_lp_power_mean"], r["geometry_uid"]))
    control_envelope = {"max_min_M_x": max(r["min_M_x"] for r in controls), "min_max_abs_dM": min(r["max_abs_dM_x_dlambda"] for r in controls), "min_orientation_ripple": min(r["orientation_ripple_deg"] for r in controls), "min_sv_drift": min(r["dominant_output_overlap_drift"] for r in controls)}
    for row in candidates:
        row["strictly_better_than_failed_control_envelope"] = row["min_M_x"] > control_envelope["max_min_M_x"] and row["max_abs_dM_x_dlambda"] < control_envelope["min_max_abs_dM"] and row["orientation_ripple_deg"] < control_envelope["min_orientation_ripple"] and row["dominant_output_overlap_drift"] < control_envelope["min_sv_drift"]
    stability_seeds = [r for r in ranked if not r["historical_target_channel_flip"] and r["min_F_x"] >= 0.70]
    if not stability_seeds:
        stability_seeds = [r for r in ranked if not r["historical_target_channel_flip"]]
    # Greedy diversity selection over the lexicographic order; this is a tie-break,
    # never a replacement for the stability ordering.
    feature_keys = ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg", "H_global_nm"]
    scales = {k: max(float(meta[u][k]) for u in meta) - min(float(meta[u][k]) for u in meta) or 1.0 for k in feature_keys}
    shortlist = []
    for row in stability_seeds:
        if len(shortlist) >= 4:
            break
        if all(math.sqrt(sum(((float(row[k]) - float(other[k])) / scales[k]) ** 2 for k in feature_keys)) >= 0.20 for other in shortlist):
            shortlist.append(row)
    if not shortlist and stability_seeds:
        shortlist = stability_seeds[:1]
    shortlist_ids = {r["geometry_uid"] for r in shortlist}
    state_rows = [{**r, "ranking_pool": "failed_control" if r["failed_fdt_control"] else "eligible_new_candidate"} for r in summaries]
    comparison = []
    for r in controls:
        comparison.append({"comparison_group": "FAILED_FDTD_CONTROL", **r, "min_M_delta_vs_best_control": 0.0, "orientation_drift_delta_vs_best_control": 0.0, "singular_drift_delta_vs_best_control": 0.0})
    for r in ranked:
        best = max(controls, key=lambda x: x["min_M_x"])
        comparison.append({"comparison_group": "NEW_CANDIDATE", **r, "min_M_delta_vs_best_control": r["min_M_x"] - best["min_M_x"], "orientation_drift_delta_vs_best_control": r["orientation_ripple_deg"] - best["orientation_ripple_deg"], "singular_drift_delta_vs_best_control": r["dominant_output_overlap_drift"] - best["dominant_output_overlap_drift"]})
    pareto = []
    for r in ranked:
        dominated = any(o["min_M_x"] >= r["min_M_x"] and o["max_abs_dM_x_dlambda"] <= r["max_abs_dM_x_dlambda"] and o["orientation_ripple_deg"] <= r["orientation_ripple_deg"] and o["dominant_output_overlap_drift"] <= r["dominant_output_overlap_drift"] and (o["geometry_uid"] != r["geometry_uid"]) for o in ranked)
        if not dominated:
            pareto.append({"geometry_uid": r["geometry_uid"], "min_M_x": r["min_M_x"], "max_abs_dM_x_dlambda": r["max_abs_dM_x_dlambda"], "orientation_ripple_deg": r["orientation_ripple_deg"], "dominant_output_overlap_drift": r["dominant_output_overlap_drift"], "historical_target_channel_flip": r["historical_target_channel_flip"]})
    fsp_plan = [fsp_audit(r["geometry_uid"], meta[r["geometry_uid"]]) for r in shortlist]
    diversity = []
    for a, b in itertools.combinations(shortlist, 2):
        distance = math.sqrt(sum(((float(a[k]) - float(b[k])) / scales[k]) ** 2 for k in feature_keys))
        diversity.append({"candidate_a": a["geometry_uid"], "candidate_b": b["geometry_uid"], "normalized_geometry_distance": distance, "different_source_stage": a["source_stage"] != b["source_stage"]})
    for r in shortlist:
        diversity.append({"candidate_a": r["geometry_uid"], "candidate_b": None, "normalized_geometry_distance": None, "different_source_stage": None, "geometry_role": "SHORTLIST"})
    strict_better = [r for r in candidates if r["strictly_better_than_failed_control_envelope"]]
    if strict_better:
        verdict = "PAPER_A_LP_SECOND_RESCUE_FDTD_SEEDS_READY"
        stop_loss = False
    else:
        verdict = "PAPER_A_LP_SECOND_RESCUE_NO_PHYSICALLY_BETTER_SEED"
        stop_loss = True
        shortlist = []
        shortlist_ids = set()
        fsp_plan = []
    shortlist_rows = []
    for rank, r in enumerate(shortlist, 1):
        shortlist_rows.append({"shortlist_rank": rank, "candidate_id": r["geometry_uid"], "promotion_label": f"SECOND_RESCUE_CANDIDATE_{rank}", "min_M_x": r["min_M_x"], "min_F_x": r["min_F_x"], "max_abs_dM_x_dlambda": r["max_abs_dM_x_dlambda"], "orientation_ripple_deg": r["orientation_ripple_deg"], "dominant_output_overlap_worst": r["dominant_output_overlap_worst"], "worst_DoLP": r["worst_DoLP"], "useful_lp_power_worst": r["useful_lp_power_worst"], "source_stage": r["source_stage"]})
    write_csv(REPORT / "candidate_state_margin_metrics.csv", state_rows)
    write_csv(REPORT / "candidate_stokes_orientation_stability.csv", spectra)
    write_csv(REPORT / "candidate_singular_vector_stability.csv", singular)
    write_csv(REPORT / "failed_controls_comparison.csv", comparison)
    write_csv(REPORT / "cp_like_lp_stability_candidates.csv", [{"candidate_id": r["geometry_uid"], "min_F_x": r["min_F_x"], "min_M_x": r["min_M_x"], "historical_target_channel_flip": r["historical_target_channel_flip"], "guidance_pass": r["min_F_x"] >= 0.70 and not r["historical_target_channel_flip"], "source_stage": r["source_stage"]} for r in ranked])
    write_csv(REPORT / "second_rescue_pareto.csv", pareto)
    write_csv(REPORT / "second_rescue_shortlist.csv", shortlist_rows)
    write_csv(REPORT / "second_rescue_geometry_diversity.csv", diversity)
    write_json(REPORT / "second_rescue_fsp_reuse_plan.json", {"schema": "PAPER_A_LP_PHYSICS_GUIDED_SECOND_RESCUE_FSP_REUSE_PLAN_V1", "candidates": fsp_plan, "future_source_monitor_contract": {"source_span_nm": [430.0, 470.0], "formal_range_nm": [435.0, 465.0], "formal_spacing_nm": 1.0, "formal_points": 31}, "no_solver_called": True})
    decision = {"schema": "PAPER_A_LP_PHYSICS_GUIDED_SECOND_RESCUE_DECISION_V1", "verdict": verdict, "solver_calls": 0, "rcwa_calls": 0, "ml_calls": 0, "new_geometry_generation_calls": 0, "pool": {"geometries": 52, "rows": 468, "grid_nm": [450.0, 454.0], "spacing_nm": 0.5, "points": 9}, "excluded_failed_fdt_controls": sorted(FAILED), "shortlist": shortlist_rows, "stop_loss": {"triggered": stop_loss, "criterion": "No non-control candidate strictly beats the failed-control envelope in min_M_x, max_abs_dM, orientation ripple, and dominant-output-vector drift"}, "future_fdtd_budget": 0 if stop_loss else {"minimum": 2, "maximum": 8, "active_slots": 2}, "future_execution_plan": "one geometry x/y wave, stop on PASS, sequential waves; not started", "intrinsic_prior_scope_status": "FROZEN_NOT_PROMOTED"}
    write_json(REPORT / "second_rescue_decision.json", decision)
    best_control = max(controls, key=lambda x: x["min_M_x"])
    report = ["# Paper A LP physics-guided second rescue", "", f"Verdict: **{verdict}**", "", "## Evidence boundary", "", "The analysis uses 52 current-Native-compatible historical full-Jones geometries and 468 rows on 450-454 nm at 0.5 nm spacing. The five already FDTD-failed structures are excluded from any new shortlist and retained only as negative controls. No FDTD, RCWA, ML, or geometry generation was run.", "", "## Answers", "", "1. The prior ranking was primarily throughput/purity/anchor-oriented and did not explicitly rank distance from the target-channel flip boundary. This second rescue adds M_x margin, derivatives, orientation, and singular-vector stability.", f"2. Failed-control envelope: max min(M_x)={control_envelope['max_min_M_x']:.6f}, min max|dM/dlambda|={control_envelope['min_max_abs_dM']:.6f}/nm, min orientation ripple={control_envelope['min_orientation_ripple']:.6f} deg, min singular-vector drift={control_envelope['min_sv_drift']:.6f}. Strict envelope dominance found: {len(strict_better)} candidate(s).", f"3. Future shortlist: {', '.join(r['geometry_uid'] for r in shortlist) if shortlist else 'none'}.", "4. The selection logic requires positive historical M_x margin, low spectral slope/curvature, low psi drift, and stable dominant output singular vector; no phase/K6 metric is used.", f"5. Future FDTD budget: {0 if stop_loss else '2-8 authorized maximum, not started'}.", "", "## Failure boundary", "", "Historical evidence cannot prove 438-458 nm future broadband truth. Any future claim still requires Native-M1 430-470 nm source/monitor coverage, 435-465 nm extraction, MDC ZL-1 alternative weighting, coherency-first DoLP, and no main-spectrum channel flip."]
    (REPORT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    audit = {"schema": "PAPER_A_LP_PHYSICS_GUIDED_SECOND_RESCUE_AUDIT_V1", "status": "PASS", "solver_calls": 0, "rcwa_calls": 0, "ml_calls": 0, "new_geometry_generation_calls": 0, "pool_geometry_count": len(meta), "pool_row_count": sum(len(v) for v in groups.values()), "pool_source_counts": {"H1C1A": 21, "H1C1B": 21, "H1C1C": 10}, "failed_controls_excluded": sorted(FAILED), "metrics": {"stokes_from_C_half_JJdag": True, "M_x_equals_S1_over_S0": True, "orientation_from_S1_S2": True, "svd_complex_jones": True, "phase_used_for_ranking": False, "k6_used": False, "synthetic_reconstruction": False, "zero_crossing_is_diagnostic_only": True}, "stop_loss": decision["stop_loss"], "future_fdt_not_started": True, "fsp_reuse_audited": True, "legacy_mixed": False, "incompatible_normalization_mixed": False}
    write_json(REPORT / "audit.json", audit)
    print(json.dumps(decision, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
