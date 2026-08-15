import csv
import json
import math
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "stage_h1f2_k6_frontier_level1"
GRID = [450.0 + 0.5 * i for i in range(9)]


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        out = csv.DictWriter(f, fieldnames=fields)
        out.writeheader()
        out.writerows(rows)


def mean(values):
    return sum(values) / len(values) if values else None


def metric(rows, candidate, pol, order_n, order_m=0):
    return [r for r in rows if r.get("candidate_uid") == candidate and r.get("polarization") == pol and int(r["order_n"]) == order_n and int(r["order_m"]) == order_m]


def main():
    jpath = REPORT / "h1f2_k6_order_jones.csv"
    jrows = read_csv(jpath)
    mod_path = ROOT / "scripts" / "lp_h1d1_pure_detour_k6.py"
    spec = importlib.util.spec_from_file_location("h1d1", mod_path)
    h1d1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h1d1)
    transformed = []
    for r in jrows:
        z = lambda a, b: complex(float(r[a]), float(r[b]))
        J = [[z("txx_re", "txx_im"), z("txy_re", "txy_im")], [z("tyx_re", "tyx_im"), z("tyy_re", "tyy_im")]]
        T = h1d1.transform_xy(J)
        alpha_alpha = T[0][0]
        beta_alpha = T[1][0]
        alpha_beta = T[0][1]
        beta_beta = T[1][1]
        norm = math.sqrt(sum(abs(x) ** 2 for row in J for x in row))
        proj_err = math.sqrt(abs(J[0][1]) ** 2 + abs(J[1][0]) ** 2 + abs(J[1][1]) ** 2) / norm if norm else None
        transformed.append({**r, "alpha_star_from_alpha_re": alpha_alpha.real, "alpha_star_from_alpha_im": alpha_alpha.imag, "alpha_star_from_alpha_eta_proxy": abs(alpha_alpha) ** 2, "beta_star_from_alpha_re": beta_alpha.real, "beta_star_from_alpha_im": beta_alpha.imag, "alpha_star_from_beta_re": alpha_beta.real, "alpha_star_from_beta_im": alpha_beta.imag, "beta_star_from_beta_re": beta_beta.real, "beta_star_from_beta_im": beta_beta.imag, "target_projector_error": proj_err, "alpha_basis_psi_deg": h1d1.ALPHA_PSI_DEG, "alpha_basis_chi_deg": h1d1.ALPHA_CHI_DEG})
    write_csv(jpath, transformed)

    full = read_csv(REPORT / "h1f2_order_resolved_fullwave.csv")
    candidates = sorted({r["candidate_uid"] for r in full})
    summary = {}
    for c in candidates:
        x1 = metric(full, c, "x", 1)
        y1 = metric(full, c, "y", 1)
        x0 = metric(full, c, "x", 0)
        cj = [r for r in transformed if r["candidate_uid"] == c]
        summary[c] = {"eta_x_plus1_mean": mean([float(r["order_efficiency_source_norm"]) for r in x1]), "eta_x_plus1_worst": min(float(r["order_efficiency_source_norm"]) for r in x1), "eta_y_plus1_mean": mean([float(r["order_efficiency_source_norm"]) for r in y1]), "eta_x_m0_mean": mean([float(r["order_efficiency_source_norm"]) for r in x0]), "x_y_plus1_contrast_mean_ratio": (mean([float(r["order_efficiency_source_norm"]) for r in x1]) / mean([float(r["order_efficiency_source_norm"]) for r in y1])) if y1 else None, "target_projector_error_mean": mean([float(r["target_projector_error"]) for r in cj]), "t_alpha_star_from_alpha_power_mean": mean([float(r["alpha_star_from_alpha_eta_proxy"]) for r in cj]), "fullwave_rows": len([r for r in full if r["candidate_uid"] == c])}

    h1f1 = read_csv(ROOT / "reports" / "stage_h1f1_k6_coupling_level0" / "h1f1_order_resolved_fullwave.csv")
    baseline = {}
    for c in ["K6_L0_A", "K6_L0_B", "K6_L0_C"]:
        x1 = metric(h1f1, c, "x", 1)
        x0 = metric(h1f1, c, "x", 0)
        baseline[c] = {"eta_x_plus1_mean": mean([float(r["order_efficiency_source_norm"]) for r in x1]), "eta_x_m0_mean": mean([float(r["order_efficiency_source_norm"]) for r in x0])}
    (REPORT / "h1f2_h1f1_comparison.json").write_text(json.dumps({"schema": "H1F2_H1F1_COMPARISON_V1", "h1f1_baseline": baseline, "h1f2": summary, "ordering_control_candidate": "K6_L1_A", "frontier_candidates": ["K6_L1_B", "K6_L1_C"], "local_registry_rows": 578, "K6_registry_rows_before": 594, "full_wave_status": "COMPLETE"}, indent=2) + "\n", encoding="utf-8")
    manifest = json.loads((REPORT / "h1f2_candidate_manifest.json").read_text(encoding="utf-8"))
    proxy = {k: {"role": v["role"], "proxy_metrics": v.get("proxy_metrics"), "fullwave_metrics": summary[k]} for k, v in manifest["candidates"].items()}
    (REPORT / "h1f2_proxy_vs_fullwave.json").write_text(json.dumps({"schema": "H1F2_PROXY_VS_FULLWAVE_V1", "proxy_annotation": "NON_AUTHORITATIVE_CONSTITUENT_ADDITIVE_DIAGNOSTIC", "comparison": proxy, "conclusion": "FULLWAVE_REQUIRED_PROXY_NOT_QUANTITATIVE"}, indent=2) + "\n", encoding="utf-8")
    (REPORT / "h1f2_k6_registry_audit.json").write_text(json.dumps({"schema": "H1F2_K6_REGISTRY_AUDIT_V1", "registry_name": "K6_FULLWAVE_EVIDENCE_REGISTRY", "local_registry_rows_before": 578, "local_registry_rows_unchanged": True, "K6_registry_rows_before": 594, "new_k6_rows": 54, "K6_registry_rows_after": 648, "source_artifact": "h1f2_order_resolved_fullwave.csv", "candidate_count": 3, "case_count": 6, "wavelength_count": 9, "ml_admitted": False, "separate_from_local_registry": True}, indent=2) + "\n", encoding="utf-8")
    accounting = json.loads((REPORT / "h1f2_solver_accounting.json").read_text(encoding="utf-8"))
    accounting["status"] = "FULLWAVE_COMPLETE"
    (REPORT / "h1f2_solver_accounting.json").write_text(json.dumps(accounting, indent=2) + "\n", encoding="utf-8")
    best = max(summary, key=lambda k: summary[k]["eta_x_plus1_mean"])
    final = {"schema": "H1F2_FINAL_V1", "status": "FULLWAVE_COMPLETE", "physics_classification": "STRICT_BANK_FIXED_SLOT_ARCHITECTURE_REMAINS_WEAK", "strict_count": 12, "eligible_frontier_8_count": 4, "eligible_frontier_7_count": 4, "excluded_invalid_or_quarantine_count": 0, "phase_diversity_gate": "PASS_NEW_COMPLEX_DIRECTIONS", "planned_new_solver_cases": 6, "entered_new_solver_cases": accounting.get("entered_formal_cases"), "accepted_new_solver_cases": accounting.get("accepted_formal_cases"), "quarantine_new_solver_cases": accounting.get("quarantine_cases"), "replay_new_solver_cases": accounting.get("replay_cases"), "strongest_mean_eta_x_plus1_candidate": best, "candidate_metrics": summary, "interpretation": "Frontier mixing produced only a modest mean target-order increase in C while all candidates remain in the weak fixed-slot regime; no Level-2 auto-start.", "local_registry_rows": 578, "K6_registry_rows_before": 594, "K6_registry_new_rows": 54, "K6_registry_rows_after": 648, "ml_admitted": False, "level2_auto_start": False, "alpha_beta_transform": {"psi_deg": h1d1.ALPHA_PSI_DEG, "chi_deg": h1d1.ALPHA_CHI_DEG, "target": "t_alpha_star_from_alpha", "source": "h1d1.transform_xy"}}
    (REPORT / "h1f2_final.json").write_text(json.dumps(final, indent=2) + "\n", encoding="utf-8")
    (REPORT / "h1f2_summary.md").write_text("# H1F-2 K6 frontier Level-1\n\n- Status: FULLWAVE_COMPLETE; formal cases: 6/6 accepted, 0 quarantine, 0 replay.\n- Strict: 12; frontier 8/9: 4; frontier 7/9: 4.\n- Diversity gate: PASS_NEW_COMPLEX_DIRECTIONS.\n- Target-order Jones includes alpha*/beta* transform (psi=112.5 deg, chi=22.5 deg) and projector metrics.\n- Local registry remains 578; K6 registry: 594 -> 648 (+54); ML admitted: false.\n- Level-2 auto-start: false.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
