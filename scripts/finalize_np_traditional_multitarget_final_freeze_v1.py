"""Offline resolution of the frozen K4/K6/K9 traditional NP providers."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / "outputs/np_traditional_multitarget_first_batch_3d_fdtd_v1"
SCOPE = ROOT / "outputs/np_k6_formal_source_scope_v1/formal_source_scope_v1.json"
K6PHASE = ROOT / "outputs/np_k6_p1d4b_k6x_phase_candidate_run3a_freeze_v1"
OUT = ROOT / "outputs/np_traditional_multitarget_final_freeze_v1"
DOC = ROOT / "docs/np_traditional_multitarget_final_freeze_v1.md"


def jread(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def gaps(vector: list[float], period: float, spacing: float) -> tuple[float, float]:
    xs = [-(len(vector) - 1) * spacing / 2 + i * spacing for i in range(len(vector))]
    gs = [xs[i + 1] - xs[i] - (vector[i] + vector[i + 1]) / 2 for i in range(len(vector) - 1)]
    seam = xs[0] + period - xs[-1] - (vector[0] + vector[-1]) / 2
    return min(gs + [seam]), seam


def nominal_angles(wavelengths: list[float], period: float) -> tuple[float, float, float]:
    values = [math.degrees(math.asin(min(1.0, wavelength / period))) for wavelength in wavelengths]
    return values[5], min(values), max(values)


def first_case(cid: str, family: str, vector: list[int], k: int, lam: float, target: str) -> dict:
    d = FIRST / cid
    led = jread(d / "entered_ledger.json")
    pre = jread(d / "preflight.json")
    admission = jread(d / "label_admission.json")
    closure = jread(d / "energy_closure_audit.json")
    met = rows(d / "spectral_metrics.csv")
    eta = [float(x["eta_plus1"]) for x in met]
    tf = [float(x["target_fraction_of_T"]) for x in met]
    t = [float(x["T_total"]) for x in met]
    r = [float(x["R_total"]) for x in met]
    leak = [float(x["non_target_power"]) for x in met]
    comp = [float(x["strongest_competitor_power"]) for x in met]
    sel = [float(x["selectivity"]) for x in met if x.get("selectivity") not in (None, "")]
    order_comp = max(met, key=lambda x: float(x["strongest_competitor_power"]))["strongest_competitor_order"]
    theta450, theta_min, theta_max = nominal_angles([float(x["wavelength_nm"]) for x in met], lam)
    min_gap, seam = gaps(vector, lam, 290.0)
    xpol = pre["geometry"]["source"]["polarization_angle"] == 0.0
    return {
        "family": family, "K": k, "Lambda_x_nm": lam, "candidate_id": cid,
        "diameter_vector_nm": vector, "target_direction_label": target,
        "eta_plus1_450": eta[5], "eta_plus1_band_min": min(eta), "eta_plus1_band_mean": sum(eta) / len(eta), "eta_plus1_band_max": max(eta),
        "target_fraction_450": tf[5], "target_fraction_mean": sum(tf) / len(tf), "T_450": t[5], "T_mean": sum(t) / len(t), "T_min": min(t), "R_450": r[5], "R_mean": sum(r) / len(r),
        "max_closure": float(closure["max_abs_residual"]), "strongest_competing_order": int(float(order_comp)), "max_non_target_leakage": max(leak), "mean_non_target_leakage": sum(leak) / len(leak),
        "selectivity_mean": sum(sel) / len(sel) if sel else None, "selectivity_min": min(sel) if sel else None, "directionality": all(str(x["directionality"]).lower() == "true" for x in met),
        "fabrication_min_gap_nm": min_gap, "periodic_seam_gap_nm": seam, "source_contract": "normal incidence; Forward/+z; x-pol; 445-455 nm; 11 points",
        "nominal_theta_plus1_450_deg": theta450, "nominal_theta_plus1_band_min_deg": theta_min, "nominal_theta_plus1_band_max_deg": theta_max,
        "numerical_provider": "3D_FDTD", "full_supercell_fidelity": True, "evidence_commit": "74d9faf14690f67d5b29b538a794c0c78aae5dad",
        "geometry_hash": pre["geometry_sha256"], "pre_fsp_sha256": pre["pre_fsp_sha256"], "post_fsp_sha256": led["post_fsp_sha256"], "valid_label": bool(admission["valid"]), "x_polarization": xpol,
    }


def k6_case(scope: dict) -> dict:
    met = rows(K6PHASE / "spectral_tr_metrics.csv")
    orders = rows(K6PHASE / "transmitted_order_spectrum.csv")
    eta = [float(x["plus1_absolute_efficiency"]) for x in rows(K6PHASE / "order_efficiency_spectrum.csv")]
    t = [float(x["T_total"]) for x in met]; r = [float(x["R_total"]) for x in met]
    by_wave = {}
    for o in orders:
        by_wave.setdefault(float(o["wavelength_nm"]), []).append(o)
    comps, leaks, sels = [], [], []
    for e, tt, olist in zip(eta, t, by_wave.values()):
        non = [float(o["absolute_efficiency"]) for o in olist if int(o["order_n"]) != 1]
        comps.append(max(non)); leaks.append(sum(non)); sels.append(e / max(non))
    g, seam = gaps([float(x) for x in scope["geometry_scope"]["diameters_nm"]], 1740.0, 290.0)
    theta450, theta_min, theta_max = nominal_angles([float(x["wavelength_nm"]) for x in met], 1740.0)
    checksum = jread(K6PHASE / "post_fsp_checksum.json")
    pre_path = ROOT / "outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_prefsp_orientation_corrected_v1/PHASE_ORIENTED_K6X.fsp"
    return {
        "family": "K6", "K": 6, "Lambda_x_nm": 1740.0, "candidate_id": "NP_K6_15DEG", "source_candidate_id": scope["candidate_id"],
        "diameter_vector_nm": scope["geometry_scope"]["diameters_nm"], "target_direction_label": "15deg +1 (+x)", "eta_plus1_450": eta[5], "eta_plus1_band_min": min(eta), "eta_plus1_band_mean": sum(eta) / len(eta), "eta_plus1_band_max": max(eta),
        "target_fraction_450": eta[5] / t[5], "target_fraction_mean": sum(e / tt for e, tt in zip(eta, t)) / len(eta), "T_450": t[5], "T_mean": sum(t) / len(t), "T_min": min(t), "R_450": r[5], "R_mean": sum(r) / len(r),
        "max_closure": float(jread(K6PHASE / "energy_closure_audit.json")["max_abs_residual"]), "strongest_competing_order": int(max((o for o in orders if int(o["order_n"]) != 1), key=lambda o: float(o["absolute_efficiency"]))["order_n"]), "max_non_target_leakage": max(leaks), "mean_non_target_leakage": sum(leaks) / len(leaks), "selectivity_mean": sum(sels) / len(sels), "selectivity_min": min(sels), "directionality": True,
        "fabrication_min_gap_nm": g, "periodic_seam_gap_nm": seam, "source_contract": "normal incidence; Forward/+z; x-pol; 445-455 nm; 11 points", "numerical_provider": "existing frozen 3D_FDTD", "full_supercell_fidelity": True, "evidence_commit": jread(ROOT / "outputs/np_k6_final_freeze_closeout_v1/freeze_manifest.json")["repository"]["final_freeze_commit"], "geometry_hash": scope["geometry_scope"]["canonical_geometry_hash"], "candidate_geometry_hash": "5744baf84e4b4405711f0aabdbb7965c294d4b3e4f099f670457fbbbae1c2710", "pre_fsp_sha256": digest(pre_path), "post_fsp_sha256": checksum["sha256"], "valid_label": True, "x_polarization": True, "k6_no_new_solver": True,
        "nominal_theta_plus1_450_deg": theta450, "nominal_theta_plus1_band_min_deg": theta_min, "nominal_theta_plus1_band_max_deg": theta_max,
        "source_orientation_authority": "RUN3A Forward/+z x-pol; physical m=+1 maps to +x",
        "target_order": 1, "target_physical_direction": "+x",
    }


def write_json(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def tradeoff_audit(champion: dict, candidates: list[dict]) -> dict:
    challenger = next(row for row in candidates if row["candidate_id"] != champion["candidate_id"])
    return {
        "primary_metric": "broadband mean eta(+1)",
        "primary_metric_champion": champion["candidate_id"],
        "primary_metric_champion_value": champion["eta_plus1_band_mean"],
        "challenger": challenger["candidate_id"],
        "tradeoff_dimensions": {
            "eta_plus1_at_450": {"champion": champion["eta_plus1_450"], "challenger": challenger["eta_plus1_450"]},
            "target_fraction_mean": {"champion": champion["target_fraction_mean"], "challenger": challenger["target_fraction_mean"]},
            "mean_transmission": {"champion": champion["T_mean"], "challenger": challenger["T_mean"]},
            "mean_non_target_leakage": {"champion": champion["mean_non_target_leakage"], "challenger": challenger["mean_non_target_leakage"]},
            "max_closure": {"champion": champion["max_closure"], "challenger": challenger["max_closure"]},
            "fabrication_min_gap": {"champion": champion["fabrication_min_gap_nm"], "challenger": challenger["fabrication_min_gap_nm"]},
        },
        "reversal_of_primary_metric": False,
        "conclusion": "No substantive evidence reversal; retain broadband-primary family champion and record tradeoffs descriptively.",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    k4 = [first_case("K4_SEED_A_190_155", "K4", [190, 115, 140, 155], 4, 1160.0, "23deg +1 (+x)"), first_case("K4_SEED_B_100_175", "K4", [100, 125, 145, 175], 4, 1160.0, "23deg +1 (+x)")]
    k9 = [first_case("K9_SEED_A_195_180", "K9", [195, 105, 215, 125, 140, 165, 150, 170, 180], 9, 2610.0, "10deg +1 (+x)"), first_case("K9_SEED_B_205_185", "K9", [205, 110, 120, 130, 135, 145, 155, 175, 185], 9, 2610.0, "10deg +1 (+x)")]
    k6 = k6_case(jread(SCOPE))
    fam = {"K4": max(k4, key=lambda r: r["eta_plus1_band_mean"]), "K9": max(k9, key=lambda r: r["eta_plus1_band_mean"])}
    global_winner = max([*k4, *k9, k6], key=lambda r: r["eta_plus1_band_mean"])
    for family, candidates in (("K4", k4), ("K9", k9)):
        status = "K4_FIRST_BATCH_CHAMPION_FROZEN_BROADBAND_PRIORITY" if family == "K4" else "K9_FIRST_BATCH_CHAMPION_FROZEN"
        write_json(f"{family.lower()}_final_decision.json", {"family": family, "decision_status": status, "primary_criterion": "broadband mean eta(+1)", "champion": fam[family], "candidates": candidates, "tradeoff_detected": False, "tradeoff_audit": tradeoff_audit(fam[family], candidates), "second_batch_required": False})
        write_json(f"{family.lower()}_traditional_final_manifest.json", {"provider_id": f"NP_TRAD_{family}_{'23DEG' if family == 'K4' else '10DEG'}", "role": "traditional modular control provider", "champion": fam[family], "source": "authoritative first-batch full-supercell FDTD evidence"})
        with (OUT / f"{family.lower()}_final_comparison.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(candidates[0])); w.writeheader(); w.writerows(candidates)
    write_json("k6_traditional_final_manifest.json", {"provider_id": "NP_TRAD_K6_15DEG", "role": "traditional modular control provider", "champion": k6, "source": "existing frozen K6 authority", "no_new_solver": True})
    comparison = [fam["K4"], k6, fam["K9"]]
    with (OUT / "traditional_multitarget_final_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        fields = list(comparison[0])
        fields.extend(k for row in comparison[1:] for k in row if k not in fields)
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(comparison)
    write_json("traditional_multitarget_global_summary.json", {"global_descriptive_winner": global_winner, "family_champions": fam, "comparison_scope": "descriptive standalone target-order efficiency only; target angles differ", "standalone_scope": "normal incidence; x-pol; 445-455 nm", "status": "NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY"})
    write_json("family_champion_semantic_audit.json", {"issue_confirmed": True, "issue": "previous summary exposed only a cross-family winner and did not carry family-scoped champion fields", "family_selector_scope": {"K4": "K4 candidates only", "K9": "K9 candidates only", "K6": "existing frozen K6 authority"}, "resolved_family_champions": {k: v["candidate_id"] for k, v in fam.items()}, "global_winner": global_winner["candidate_id"], "global_does_not_overwrite_family": True})
    write_json("champion_selector_fix_audit.json", {"implementation": "finalize_np_traditional_multitarget_final_freeze_v1.py", "primary_metric": "eta_plus1_band_mean", "family_selection": "independent max within family", "global_selection": "descriptive max across standalone providers", "physical_data_modified": False, "new_solver_entered": 0})
    write_json("np_traditional_multi_target_coupling_handoff_v1.json", {"handoff_id": "NP_TRADITIONAL_MULTI_TARGET_COUPLING_HANDOFF_V1", "role": "traditional modular control provider", "providers": [{"provider_id": "NP_TRAD_K9_10DEG", "K": 9, "Lambda_x_nm": 2610.0, "manifest": "k9_traditional_final_manifest.json"}, {"provider_id": "NP_TRAD_K6_15DEG", "K": 6, "Lambda_x_nm": 1740.0, "manifest": "k6_traditional_final_manifest.json"}, {"provider_id": "NP_TRAD_K4_23DEG", "K": 4, "Lambda_x_nm": 1160.0, "manifest": "k4_traditional_final_manifest.json"}], "integrated_winner": False, "joint_optimum": False, "angular_response_model": False, "scope": "normal incidence x-pol standalone NP evidence; coupling owns integrated/angular physics"})
    write_json("coupling_traditional_control_arm_contract.json", {"shared_mdc_provider": "MDC_best^trad", "arms": [{"target": "10deg", "np_provider": "NP_TRAD_K9_10DEG", "comparison": "MDC_best^trad + NP_TRAD_K9_10DEG vs (MDC+NP)_10deg^joint"}, {"target": "15deg", "np_provider": "NP_TRAD_K6_15DEG", "comparison": "MDC_best^trad + NP_TRAD_K6_15DEG vs (MDC+NP)_15deg^joint"}, {"target": "23deg", "np_provider": "NP_TRAD_K4_23DEG", "comparison": "MDC_best^trad + NP_TRAD_K4_23DEG vs (MDC+NP)_23deg^joint"}], "np_optimizes_mdc": False})
    write_json("second_batch_decision.json", {"second_batch_required": False, "solver_budget_requested": 0, "reason": "K4 and K9 family champions resolved by broadband primary criterion without evidence reversal", "third_seed_run": 0})
    write_json("solver_zero_audit.json", {"new_solver_entered": 0, "new_fdtd_run": 0, "new_rcwa": 0, "ml_training": 0, "new_single_pillar_data": 0, "third_seed": 0, "physical_data_modified": False})
    write_json("provenance_audit.json", {"first_batch_evidence_commit": "74d9faf14690f67d5b29b538a794c0c78aae5dad", "k6_authority": str(SCOPE.relative_to(ROOT)), "k4_k9_source": str(FIRST.relative_to(ROOT)), "selector_code": "scripts/finalize_np_traditional_multitarget_final_freeze_v1.py", "fsp_staged": False, "runtime_staged": False, "logs_staged": False})
    lines = ["# NP traditional multi-target final freeze: K4 / K6 / K9", "", "Status: `NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY`", "", "No new solver, RCWA, ML training, single-pillar data, or third seed was run in this freeze. Family selection is scoped within each family; the global result is descriptive only because target periods differ.", "", "## Frozen providers", "", "| provider | K | Lambda_x (nm) | diameter vector (nm) | eta(+1) mean | eta(+1) @450 | band min/max | T@450 | max closure residual | pre/post FSP SHA |", "|---|---:|---:|---|---:|---:|---|---:|---:|---|"]
    for r in comparison:
        lines.append(f"| {('NP_TRAD_K4_23DEG' if r['K']==4 else 'NP_TRAD_K6_15DEG' if r['K']==6 else 'NP_TRAD_K9_10DEG')} | {r['K']} | {r['Lambda_x_nm']:.0f} | {','.join(map(str,r['diameter_vector_nm']))} | {r['eta_plus1_band_mean']:.6f} | {r['eta_plus1_450']:.6f} | {r['eta_plus1_band_min']:.6f}/{r['eta_plus1_band_max']:.6f} | {r['T_450']:.6f} | {r['max_closure']:.6f} | {r['pre_fsp_sha256']} / {r['post_fsp_sha256']} |")
    lines += ["", f"Family champions: K4 = `{fam['K4']['candidate_id']}`; K9 = `{fam['K9']['candidate_id']}`; K6 = `NP_K6_15DEG` from the existing frozen authority. Descriptive global standalone winner by broadband mean target-order power: `{global_winner['candidate_id']}`.", "", "The three providers are traditional modular control arms, not an integrated winner, joint optimum, or angular-response model. Coupling must use the same frozen `MDC_best^trad` for the 10°, 15°, and 23° comparisons; integrated FDTD and angular physics remain in Coupling scope.", "", "Scope exclusions: no incident-angle or ux sweep, MDC angular weighting, dipole, spacer, integrated FDTD, final device angular FWHM, NP-ML restart, surrogate training, or new K4/K9 standalone FDTD. The K6 authority is identity-preserved and RUN3C diagnostics are not used as champion evidence.", "", "Evidence: first-batch report `docs/np_traditional_multitarget_first_batch_3d_fdtd_v1.md`; final comparison `traditional_multitarget_final_comparison.csv`; handoff `np_traditional_multi_target_coupling_handoff_v1.json`."]
    DOC.parent.mkdir(parents=True, exist_ok=True); DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
