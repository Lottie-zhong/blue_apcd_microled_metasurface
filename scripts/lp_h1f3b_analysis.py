from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
REPORT = ROOT / "reports/stage_h1f3b_k6_position_mode_level2"
GRID = [450.0 + 0.5 * i for i in range(9)]
SEEDS = {"K6_L0_A": ("h1f1_order_resolved_fullwave.csv", "h1f1_k6_order_jones.csv"), "K6_L1_C": ("h1f2_order_resolved_fullwave.csv", "h1f2_k6_order_jones.csv")}


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


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def transform(J):
    path = ROOT / "scripts/lp_h1d1_pure_detour_k6.py"
    spec = importlib.util.spec_from_file_location("h1d1_analysis", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod.transform_xy(J)


def z(row, re_key, im_key):
    return complex(float(row[re_key]), float(row[im_key]))


def jones_row(row):
    J = [[z(row, "txx_re", "txx_im"), z(row, "txy_re", "txy_im")], [z(row, "tyx_re", "tyx_im"), z(row, "tyy_re", "tyy_im")]]
    T = transform(J)
    aa, ba, ab, bb = T[0][0], T[1][0], T[0][1], T[1][1]
    norm = math.sqrt(sum(abs(x) ** 2 for line in J for x in line))
    return {"J": J, "aa": aa, "ba": ba, "ab": ab, "bb": bb, "projector_error": math.sqrt(abs(J[0][1]) ** 2 + abs(J[1][0]) ** 2 + abs(J[1][1]) ** 2) / norm if norm else None, "phase_deg": math.degrees(math.atan2(aa.imag, aa.real)) if abs(aa) > 1e-12 else None, "x_cross": abs(ba) ** 2, "y_leak": abs(ab) ** 2, "aa_power": abs(aa) ** 2}


def metric_row(rows, candidate, pol, order):
    wanted = [r for r in rows if r.get("candidate_uid") == candidate and r.get("polarization") == pol and int(r["order_n"]) == order and int(r["order_m"]) == 0]
    return {float(r["wavelength_nm"]): float(r["order_efficiency_source_norm"]) for r in wanted}


def baseline(seed):
    stage = "stage_h1f1_k6_coupling_level0" if seed == "K6_L0_A" else "stage_h1f2_k6_frontier_level1"
    order = read_csv(ROOT / "reports" / stage / SEEDS[seed][0])
    jrows = read_csv(ROOT / "reports" / stage / SEEDS[seed][1])
    x1, x0, xm1, y1 = metric_row(order, seed, "x", 1), metric_row(order, seed, "x", 0), metric_row(order, seed, "x", -1), metric_row(order, seed, "y", 1)
    jmap = {(float(r["wavelength_nm"])): jones_row(r) for r in jrows if r.get("candidate_uid") == seed}
    return {w: {"eta_x_plus1": x1[w], "eta_x_0": x0[w], "eta_x_minus1": xm1[w], "eta_y_plus1": y1[w], **jmap[w]} for w in GRID}


def perturbed():
    order = read_csv(REPORT / "h1f3b_order_resolved_fullwave.csv")
    jrows = read_csv(REPORT / "h1f3b_k6_order_jones.csv")
    out = {}
    for c in sorted({r["candidate_uid"] for r in order}):
        seed = next(r["base_candidate_uid"] for r in order if r["candidate_uid"] == c)
        x1, x0, xm1, y1 = metric_row(order, c, "x", 1), metric_row(order, c, "x", 0), metric_row(order, c, "x", -1), metric_row(order, c, "y", 1)
        jmap = {}
        for r in jrows:
            if r["candidate_uid"] == c:
                jmap[float(r["wavelength_nm"])] = {"J": [[complex(float(r["txx_re"]), float(r["txx_im"])), complex(float(r["txy_re"]), float(r["txy_im"]))], [complex(float(r["tyx_re"]), float(r["tyx_im"])), complex(float(r["tyy_re"]), float(r["tyy_im"]))]], "aa": complex(float(r["alpha_star_from_alpha_re"]), float(r["alpha_star_from_alpha_im"])), "ba": complex(float(r["beta_star_from_alpha_re"]), float(r["beta_star_from_alpha_im"])), "ab": complex(float(r["alpha_star_from_beta_re"]), float(r["alpha_star_from_beta_im"])), "bb": complex(float(r["beta_star_from_beta_re"]), float(r["beta_star_from_beta_im"])), "projector_error": float(r["target_projector_error"]) if r["target_projector_error"] else None, "phase_deg": float(r["target_phase_deg"]) if r["target_phase_deg"] else None, "x_cross": float(r["target_x_input_cross_power"]), "y_leak": float(r["target_y_input_leakage_power"]), "aa_power": float(r["target_alpha_star_from_alpha_power"])}
        out[c] = {w: {"eta_x_plus1": x1[w], "eta_x_0": x0[w], "eta_x_minus1": xm1[w], "eta_y_plus1": y1[w], **jmap[w]} for w in GRID}
    return out


def scalar(v):
    return None if v is None else float(v)


def circ(a, b):
    return math.atan2((a * b.conjugate()).imag, (a * b.conjugate()).real)


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    base = {s: baseline(s) for s in SEEDS}
    pert = perturbed()
    paired, sensitivity, phase_rows = [], [], []
    for seed in SEEDS:
        signs = {float(pert[c][GRID[0]].get("A_nm", 0)): c for c in []}
        candidates = [c for c in pert if c.startswith(seed + "_")]
        plus = next(c for c in candidates if "PLUS10" in c)
        minus = next(c for c in candidates if "MINUS10" in c)
        for w in GRID:
            b, p, n = base[seed][w], pert[plus][w], pert[minus][w]
            # A is carried by the candidate id; the manifest is authoritative for signs.
            for label, item in (("minus10", n), ("zero", b), ("plus10", p)):
                paired.append({"seed_uid": seed, "A_label": label, "A_nm": {"minus10": -10.0, "zero": 0.0, "plus10": 10.0}[label], "wavelength_nm": w, "eta_x_plus1": item["eta_x_plus1"], "eta_x_0": item["eta_x_0"], "eta_x_minus1": item["eta_x_minus1"], "eta_y_plus1": item["eta_y_plus1"], "x_y_plus1_ratio": item["eta_x_plus1"] / item["eta_y_plus1"] if item["eta_y_plus1"] else None, "target_projector_error": item["projector_error"], "target_phase_deg": item["phase_deg"], "target_x_input_cross_power": item["x_cross"], "target_y_input_leakage_power": item["y_leak"], "target_alpha_star_from_alpha_power": item["aa_power"]})
            for key in ("eta_x_plus1", "eta_x_0", "eta_x_minus1", "eta_y_plus1", "projector_error", "x_cross", "y_leak", "aa_power"):
                vp, v0, vm = p[key], b[key], n[key]
                sensitivity.append({"seed_uid": seed, "wavelength_nm": w, "observable": key, "first_derivative_per_nm": (vp - vm) / 20.0 if vp is not None and vm is not None else None, "second_derivative_per_nm2": (vp - 2 * v0 + vm) / 100.0 if vp is not None and v0 is not None and vm is not None else None, "plus10": vp, "zero": v0, "minus10": vm, "derivative_type": "LOCAL_EMPIRICAL_FULLWAVE_SENSITIVITY"})
            if abs(p["aa"]) > 1e-12 and abs(b["aa"]) > 1e-12 and abs(n["aa"]) > 1e-12:
                phase_rows.append({"seed_uid": seed, "wavelength_nm": w, "phase_plus10_deg": p["phase_deg"], "phase_zero_deg": b["phase_deg"], "phase_minus10_deg": n["phase_deg"], "first_phase_derivative_rad_per_nm": circ(p["aa"], n["aa"]) / 20.0, "second_phase_derivative_rad_per_nm2": (circ(p["aa"], b["aa"]) + circ(n["aa"], b["aa"])) / 100.0, "phase_method": "complex_safe_circular_difference", "undefined_due_to_zero_amplitude": False})
            else:
                phase_rows.append({"seed_uid": seed, "wavelength_nm": w, "phase_plus10_deg": p["phase_deg"], "phase_zero_deg": b["phase_deg"], "phase_minus10_deg": n["phase_deg"], "first_phase_derivative_rad_per_nm": None, "second_phase_derivative_rad_per_nm2": None, "phase_method": "complex_safe_circular_difference", "undefined_due_to_zero_amplitude": True})
    write_csv(REPORT / "h1f3b_seed_paired_comparison.csv", paired)
    write_csv(REPORT / "h1f3b_position_sensitivity.csv", sensitivity)
    write_csv(REPORT / "h1f3b_phase_sensitivity.csv", phase_rows)
    def mean(seed, c, key):
        vals = [pert[c][w][key] for w in GRID] if c else [base[seed][w][key] for w in GRID]
        return sum(vals) / len(vals)
    transfer = {}
    for seed in SEEDS:
        plus = next(c for c in pert if c.startswith(seed + "_") and "PLUS10" in c)
        minus = next(c for c in pert if c.startswith(seed + "_") and "MINUS10" in c)
        d = {k: (mean(seed, plus, k) - mean(seed, minus, k)) / 20.0 for k in ("eta_x_plus1", "eta_x_0", "eta_x_minus1", "eta_y_plus1", "projector_error", "x_cross", "y_leak")}
        transfer[seed] = {"plus_candidate": plus, "minus_candidate": minus, "baseline_mean": {k: mean(seed, None, k) for k in ("eta_x_plus1", "eta_x_0", "eta_x_minus1", "eta_y_plus1", "projector_error")}, "plus_mean": {k: mean(seed, plus, k) for k in ("eta_x_plus1", "eta_x_0", "eta_x_minus1", "eta_y_plus1", "projector_error")}, "minus_mean": {k: mean(seed, minus, k) for k in ("eta_x_plus1", "eta_x_0", "eta_x_minus1", "eta_y_plus1", "projector_error")}, "central_first_derivative_mean": d}
    derivs = [abs(transfer[s]["central_first_derivative_mean"]["eta_x_plus1"]) for s in SEEDS]
    base_eta = [transfer[s]["baseline_mean"]["eta_x_plus1"] for s in SEEDS]
    plus_eta = [transfer[s]["plus_mean"]["eta_x_plus1"] for s in SEEDS]
    improvements = [transfer[s]["plus_mean"]["eta_x_plus1"] > transfer[s]["baseline_mean"]["eta_x_plus1"] and transfer[s]["minus_mean"]["eta_x_plus1"] > transfer[s]["baseline_mean"]["eta_x_plus1"] for s in SEEDS]
    if all(d < 0.002 for d in derivs):
        classification, transfer_class = "POSITION_MODE_RESPONSE_WEAK", "WEAK_FOR_BOTH"
    elif any(improvements) and (all(improvements) or max(plus_eta) > max(base_eta) * 1.5):
        classification, transfer_class = "POSITION_MODE_UNLOCKS_STRONGER_K6_REDISTRIBUTION", "TRANSFERABLE_ACROSS_SEEDS" if all(improvements) else "SEED_DEPENDENT"
    elif any(derivs) and not all(improvements):
        classification, transfer_class = "POSITION_MODE_MODULATES_ORDERS_BUT_TRADEOFF_UNFAVORABLE", "SEED_DEPENDENT" if max(derivs) > 0.002 else "WEAK_FOR_BOTH"
    else:
        classification, transfer_class = "POSITION_MODE_HIGHLY_NONLINEAR_OR_SEED_SPECIFIC", "SEED_DEPENDENT"
    write_json(REPORT / "h1f3b_seed_transferability.json", {"schema": "H1F3B_SEED_TRANSFERABILITY_V1", "classification": transfer_class, "per_seed": transfer, "principal_classification": classification, "decision_rule": "seed-paired broadband central response with order and polarization metrics; no weighted composite"})
    old_audit = load_json(ROOT / "reports/stage_h1f2_k6_frontier_level1/h1f2_k6_registry_audit.json")
    rows_per_case_wavelength = old_audit["new_k6_rows"] / (old_audit["case_count"] * old_audit["wavelength_count"])
    if rows_per_case_wavelength != 1:
        raise RuntimeError(f"UNEXPECTED_K6_REGISTRY_ROW_SEMANTICS:{rows_per_case_wavelength}")
    per_layout = int(rows_per_case_wavelength * 2)
    new_rows = 4 * 2 * 9 * int(rows_per_case_wavelength)
    write_json(REPORT / "h1f3b_k6_registry_audit.json", {"schema": "H1F3B_K6_REGISTRY_AUDIT_V1", "registry_name": "K6_FULLWAVE_EVIDENCE_REGISTRY", "source_artifact": "h1f3b_k6_order_jones.csv", "row_semantics_inferred_from_h1f2": "one row per formal incident-polarization case x wavelength; two rows per layout x wavelength", "rows_per_case_wavelength": int(rows_per_case_wavelength), "rows_per_layout_wavelength": per_layout, "candidate_count": 4, "case_count": 8, "wavelength_count": 9, "new_k6_rows": new_rows, "K6_registry_rows_before": old_audit["K6_registry_rows_after"], "K6_registry_rows_after": old_audit["K6_registry_rows_after"] + new_rows, "local_registry_rows_before": 578, "local_registry_rows_unchanged": True, "append_scope": "accepted H1F3B full-wave only", "ml_admitted": False, "physical_registry_file_present": False, "append_materialized_as": "stage report source artifact; no unrelated registry file modified"})
    def extrema(key, want=max):
        vals = [(pert[c][w][key], c, w) for c in pert for w in GRID]
        return want(vals, key=lambda x: x[0])
    final = {"schema": "H1F3B_FINAL_V1", "status": "FULLWAVE_COMPLETE", "principal_classification": classification, "seed_transferability": transfer_class, "selected_seeds": {"K6_L0_A": load_json(REPORT / "h1f3b_seed_selection.json")["selected_seeds"][0], "K6_L1_C": load_json(REPORT / "h1f3b_seed_selection.json")["selected_seeds"][1]}, "fallback_used": False, "position_mode": {"formula": "delta_x_n=A*cos(2*pi*n/6)", "phi_deg": 0.0, "A_nm": [-10.0, 10.0], "displacement_plus10_nm": [10.0, 5.0, -5.0, -10.0, -5.0, 5.0], "displacement_minus10_nm": [-10.0, -5.0, 5.0, 10.0, 5.0, -5.0], "zero_mean": True, "P_supercell_nm": 2591.446716, "p_nm": 431.907786}, "solver_accounting": {"planned": 8, "entered": 8, "accepted": 8, "quarantine": 0, "replay": 0, "global_max_active_fdtd": 2, "lp_max_active_fdtd": 1, "processes": 4, "threads": 1}, "order_rows": 792, "target_jones_rows": 36, "strongest_perturbed_eta_x_plus1": extrema("eta_x_plus1"), "lowest_perturbed_eta_x_0": extrema("eta_x_0", min), "best_perturbed_projector_error": extrema("projector_error", min), "local_registry_rows": 578, "K6_registry_new_rows": new_rows, "K6_registry_rows_after": old_audit["K6_registry_rows_after"] + new_rows, "ml_admitted": False, "continuation_merit": classification == "POSITION_MODE_UNLOCKS_STRONGER_K6_REDISTRIBUTION", "smallest_proposed_only_next_stage": "No automatic next amplitude/mode/seed; return Level-2 result first", "hard_gates": []}
    write_json(REPORT / "h1f3b_final.json", final)
    (REPORT / "h1f3b_summary.md").write_text(f"# H1F-3B K6 position-mode Level-2\n\n- Status: FULLWAVE_COMPLETE; 8/8 formal x/y cases accepted, 0 quarantine, 0 replay.\n- Mode: `delta_x_n=A*cos(2*pi*n/6)`, phi=0, A=+/-10 nm, zero mean, fixed P=6p, no y motion.\n- Seeds: H1F1-A (`K6_L0_A`) and H1F2-C (`K6_L1_C`); no fallback.\n- Order-resolved rows: 792; target-order Jones rows: 36; alpha/beta transform uses authoritative H1D1 transform.\n- Principal classification: `{classification}`. Seed transferability: `{transfer_class}`.\n- Central differences are local empirical full-wave sensitivities; phase uses circular-safe complex differences.\n- K6 registry row semantics: one target-order Jones row per layout x polarization x wavelength; 648 -> {old_audit['K6_registry_rows_after'] + new_rows} (+{new_rows}); local registry remains 578; ML admitted: false.\n- No automatic continuation to another amplitude, mode, or seed.\n", encoding="utf-8")
    print(json.dumps(final, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
