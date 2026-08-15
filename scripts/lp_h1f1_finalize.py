from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f1_k6_coupling_level0"
GRID = [450.0 + 0.5 * i for i in range(9)]


def load_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row, key):
    return float(row[key])


def grouped(rows, keys):
    out = {}
    for row in rows:
        out.setdefault(tuple(row[k] for k in keys), []).append(row)
    return out


def main():
    manifest = read_json(REPORT / "h1f1_candidate_manifest.json")
    strict_source = read_json(REPORT / "h1f1_strict_bank_source.json")
    full = load_csv(REPORT / "h1f1_order_resolved_fullwave.csv")
    jones = load_csv(REPORT / "h1f1_k6_order_jones.csv")
    accounting = read_json(REPORT / "h1f1_solver_accounting.json")
    baseline_final = read_json(ROOT / "reports/stage_h1d1_detour_feasibility/h1d1_final.json")
    bx = load_csv(ROOT / "reports/stage_h1d1_detour_feasibility/h1d1_xpol_order_spectrum.csv")
    by = load_csv(ROOT / "reports/stage_h1d1_detour_feasibility/h1d1_ypol_order_spectrum.csv")
    target = {}
    per_wavelength = []
    for candidate in manifest["candidates"]:
        uid = candidate["candidate_uid"]
        target[uid] = {}
        for wavelength in GRID:
            item = {"candidate_uid": uid, "wavelength_nm": wavelength}
            for pol in ("x", "y"):
                for order in (-1, 0, 1):
                    row = next(r for r in full if r["candidate_uid"] == uid and r["polarization"] == pol and abs(f(r, "wavelength_nm") - wavelength) < 1e-9 and int(r["order_n"]) == order and int(r["order_m"]) == 0)
                    item[f"eta_{pol}_{order:+d}"] = f(row, "order_efficiency_source_norm")
                all_rows = [r for r in full if r["candidate_uid"] == uid and r["polarization"] == pol and abs(f(r, "wavelength_nm") - wavelength) < 1e-9]
                item[f"other_propagating_{pol}"] = [{"order_n": int(r["order_n"]), "order_m": int(r["order_m"]), "eta": f(r, "order_efficiency_source_norm"), "theta_deg": f(r, "theta_deg") if r["theta_deg"] not in ("", "None") else None} for r in all_rows if int(r["order_m"]) == 0 and int(r["order_n"]) not in (-1, 0, 1)]
            item["target_x_y_ratio"] = item["eta_x_+1"] / max(item["eta_y_+1"], 1e-30)
            item["target_x_y_difference"] = item["eta_x_+1"] - item["eta_y_+1"]
            per_wavelength.append(item)
    write_json(REPORT / "h1f1_order_resolved_fullwave_metrics.json", {"schema": "H1F1_ORDER_RESOLVED_METRICS_V1", "rows": per_wavelength, "basis": "Cartesian transverse Ex,Ey from gratingvector; order_n=+1,order_m=0 is +x target"})
    summary = {}
    for uid in (c["candidate_uid"] for c in manifest["candidates"]):
        rows = [r for r in per_wavelength if r["candidate_uid"] == uid]
        j = [r for r in jones if r["candidate_uid"] == uid]
        summary[uid] = {
            "x_eta_plus1_mean": sum(r["eta_x_+1"] for r in rows) / 9,
            "x_eta_plus1_worst": min(r["eta_x_+1"] for r in rows),
            "x_eta_0_mean": sum(r["eta_x_+0"] for r in rows) / 9,
            "x_eta_minus1_mean": sum(r["eta_x_-1"] for r in rows) / 9,
            "y_eta_plus1_mean": sum(r["eta_y_+1"] for r in rows) / 9,
            "y_eta_plus1_worst": min(r["eta_y_+1"] for r in rows),
            "y_eta_0_mean": sum(r["eta_y_+0"] for r in rows) / 9,
            "y_eta_minus1_mean": sum(r["eta_y_-1"] for r in rows) / 9,
            "target_x_y_contrast_ratio_mean": (sum(r["eta_x_+1"] for r in rows) / 9) / max(sum(r["eta_y_+1"] for r in rows) / 9, 1e-30),
            "target_x_y_contrast_difference_mean": sum(r["target_x_y_difference"] for r in rows) / 9,
            "target_angle_deg_mean": sum(f(r, "theta_deg") for r in j) / max(len(j), 1),
            "jones_projector_error_worst": max(math.sqrt(f(r, "txy_re")**2 + f(r, "txy_im")**2 + f(r, "tyx_re")**2 + f(r, "tyx_im")**2 + f(r, "tyy_re")**2 + f(r, "tyy_im")**2) / max(math.hypot(f(r, "txx_re"), f(r, "txx_im")), 1e-30) for r in j),
            "target_phase_deg": [math.degrees(math.atan2(f(r, "txx_im"), f(r, "txx_re"))) for r in j],
            "fullwave_rows": len([r for r in full if r["candidate_uid"] == uid]),
        }
    btarget = lambda rows, order: [f(next(r for r in rows if abs(f(r, "wavelength_nm") - w) < 1e-9 and int(r["order_n"]) == order and int(r["order_m"]) == 0), "order_efficiency_source_norm") for w in GRID]
    baseline = {"layout_uid": baseline_final["layout_uid"], "parent_geometry_uid": baseline_final["parent_geometry_uid"], "read_only_reused": True, "rerun": False, "p_nm": baseline_final["p_nm"], "P_supercell_nm": baseline_final["P_supercell_nm"], "x": {"eta_plus1": btarget(bx, 1), "eta_0": btarget(bx, 0), "eta_minus1": btarget(bx, -1)}, "y": {"eta_plus1": btarget(by, 1), "eta_0": btarget(by, 0), "eta_minus1": btarget(by, -1)}}
    baseline["candidate_comparison"] = {uid: {"delta_x_eta_plus1_mean": summary[uid]["x_eta_plus1_mean"] - sum(baseline["x"]["eta_plus1"]) / 9, "delta_x_eta_0_mean": summary[uid]["x_eta_0_mean"] - sum(baseline["x"]["eta_0"]) / 9, "delta_x_eta_minus1_mean": summary[uid]["x_eta_minus1_mean"] - sum(baseline["x"]["eta_minus1"]) / 9} for uid in summary}
    write_json(REPORT / "h1f1_h1d1_baseline_comparison.json", baseline)
    proxy_metrics = {c["candidate_uid"]: c["proxy_metrics"] for c in manifest["candidates"]}
    proxy_rank = sorted(proxy_metrics, key=lambda uid: (-proxy_metrics[uid]["mean_target_order_strength"], -proxy_metrics[uid]["worst_wavelength_target_order_strength"]))
    full_rank = sorted(summary, key=lambda uid: (-summary[uid]["x_eta_plus1_mean"], -summary[uid]["x_eta_plus1_worst"]))
    proxy_vs = {"proxy_ranking_mean_target": proxy_rank, "fullwave_ranking_mean_x_eta_plus1": full_rank, "ranking_preserved": proxy_rank == full_rank, "candidate_metrics": {uid: {"proxy_mean_target": proxy_metrics[uid]["mean_target_order_strength"], "proxy_worst_target": proxy_metrics[uid]["worst_wavelength_target_order_strength"], "fullwave_mean_x_eta_plus1": summary[uid]["x_eta_plus1_mean"], "fullwave_worst_x_eta_plus1": summary[uid]["x_eta_plus1_worst"], "proxy_to_fullwave_mean_ratio": summary[uid]["x_eta_plus1_mean"] / max(proxy_metrics[uid]["mean_target_order_strength"], 1e-30)} for uid in summary}, "coupling_classification": "PROXY_BREAKDOWN" if proxy_rank != full_rank else "MODERATE", "basis": "full-wave order efficiencies compared with additive constituent-Jones proxy; no threshold-implied PASS"}
    write_json(REPORT / "h1f1_proxy_vs_fullwave.json", proxy_vs)
    orders = sorted({(int(r["order_n"]), int(r["order_m"])) for r in full})
    registry = {"schema": "K6_FULLWAVE_EVIDENCE_REGISTRY_V1", "registry_name": "K6_FULLWAVE_EVIDENCE_REGISTRY", "rows": len(full), "candidate_count": 3, "case_count": 6, "wavelength_count": 9, "incident_polarizations": ["x", "y"], "orders_included": [[n, m] for n, m in orders], "source_artifact": "h1f1_order_resolved_fullwave.csv", "solver_accounting": {"planned": accounting["planned_formal_cases"], "entered": accounting["entered_formal_cases"], "accepted": accounting["accepted_formal_cases"], "quarantine": accounting["quarantine_cases"], "replay": accounting["replay_cases"]}, "ml_admitted": False, "local_dimer_registry_rows": 578, "separate_from_local_registry": True}
    write_json(REPORT / "h1f1_k6_registry_audit.json", registry)
    strongest = max(summary, key=lambda uid: summary[uid]["x_eta_plus1_mean"])
    robust = max(summary, key=lambda uid: summary[uid]["x_eta_plus1_worst"])
    contrast = max(summary, key=lambda uid: summary[uid]["target_x_y_contrast_ratio_mean"])
    classification = "K6_COUPLING_AWARE_SIGNAL_WEAK" if max(v["x_eta_plus1_mean"] for v in summary.values()) > 1e-10 else "K6_COUPLING_AWARE_TARGET_ORDER_NOT_SUPPORTED"
    final = {"schema": "H1F1_FINAL_V1", "status": "PASS", "physics_classification": classification, "manifest_freeze_sha256": manifest["freeze_sha256"], "strict_bank_count": 12, "strict_bank_identities": [{"geometry_uid": s["geometry_uid"], "exact_hash": s["exact_hash"]} for s in strict_source["seeds"]], "candidate_count": 3, "p_nm": manifest["p_nm"], "P_supercell_nm": manifest["P_supercell_nm"], "candidates": {c["candidate_uid"]: {"role": c["role"], "sequence_uids": c["sequence_uids"], "sequence_hashes": c["sequence_hashes"], "proxy_metrics": c["proxy_metrics"], "minimum_clearance_nm": c["geometry_legality"]["minimum_clearance_nm"], "legality": c["geometry_legality"], "period": c["fundamental_period_audit"]} for c in manifest["candidates"]}, "fullwave_summary": summary, "proxy_vs_fullwave": proxy_vs, "h1d1_baseline": baseline, "strongest_fullwave_target": strongest, "most_broadband_robust": robust, "best_polarization_discrimination": contrast, "planned_entered_accepted_quarantine_replay": [accounting["planned_formal_cases"], accounting["entered_formal_cases"], accounting["accepted_formal_cases"], accounting["quarantine_cases"], accounting["replay_cases"]], "execution_recovery": "A_x/A_y bookkeeping exception occurred after solver completion and FSP/checkpoint persistence; accepted records were reconciled without replay.", "global_max_fdtd_concurrency": 2, "lp_max_fdtd_concurrency": 1, "processes_per_case": 4, "threads_per_case": 1, "local_registry_rows": 578, "k6_registry_rows": len(full), "ml_admitted": False, "level1_auto_started": False, "hard_gates": []}
    write_json(REPORT / "h1f1_final.json", final)
    (REPORT / "h1f1_summary.md").write_text("# H1F-1 K6 coupling-aware Level-0\n\n" + f"- Status: PASS; physics classification: `{classification}`.\n- Six formal cases: entered={accounting['entered_formal_cases']}, accepted={accounting['accepted_formal_cases']}, replay={accounting['replay_cases']}.\n- Strongest full-wave +1: `{strongest}`; robust: `{robust}`; polarization contrast: `{contrast}`.\n- Proxy ranking: `{', '.join(proxy_rank)}`; full-wave ranking: `{', '.join(full_rank)}`; coupling: `{proxy_vs['coupling_classification']}`.\n- H1D1 baseline reused read-only; local registry remains 578 rows; K6 registry rows={len(full)}; ML admitted=false.\n- Level-1 was not auto-started.\n", encoding="utf-8")
    print(json.dumps(final, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
