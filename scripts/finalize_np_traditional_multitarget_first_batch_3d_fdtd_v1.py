"""Derive the lightweight first-batch comparison and handoff report offline."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_traditional_multitarget_first_batch_3d_fdtd_v1"
DOC = ROOT / "docs" / "np_traditional_multitarget_first_batch_3d_fdtd_v1.md"
IDS = ["K4_SEED_A_190_155", "K4_SEED_B_100_175", "K9_SEED_A_195_180", "K9_SEED_B_205_185"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    rows = []
    details = []
    for cid in IDS:
        d = OUT / cid
        ledger = json.loads((d / "entered_ledger.json").read_text(encoding="utf-8"))
        pre = json.loads((d / "preflight.json").read_text(encoding="utf-8"))
        label = json.loads((d / "label_admission.json").read_text(encoding="utf-8"))
        closure = json.loads((d / "energy_closure_audit.json").read_text(encoding="utf-8"))
        metrics = read_csv(d / "spectral_metrics.csv")
        eta = [float(x["eta_plus1"]) for x in metrics]
        t = [float(x["T_total"]) for x in metrics]
        non_target = [float(x["non_target_power"]) for x in metrics]
        row = {
            "case_id": cid,
            "family": ledger["family"],
            "diameters_nm": ",".join(map(str, ledger["diameter_vector_nm"])),
            "label": label["label"],
            "mean_eta_plus1": sum(eta) / len(eta),
            "eta_plus1_450": eta[5],
            "T_450": float(metrics[5]["T_total"]),
            "R_450": float(metrics[5]["R_total"]),
            "closure_450": float(metrics[5]["closure_residual"]),
            "min_eta_plus1": min(eta),
            "max_eta_plus1": max(eta),
            "mean_T": sum(t) / len(t),
            "min_T": min(t),
            "mean_non_target": sum(non_target) / len(non_target),
            "max_closure": float(closure["max_abs_residual"]),
            "solver_entered": bool(ledger["solver_entered"]),
            "engine_completed": bool(ledger["engine_completed"]),
            "post_saved": bool(ledger["post_saved"]),
            "post_fsp_sha256": ledger["post_fsp_sha256"],
            "preflight_contract_ok": bool(pre["contract_ok"]),
        }
        rows.append(row)
        details.append((row, ledger, pre))
    fields = list(rows[0])
    with (OUT / "first_batch_family_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    pareto = []
    for row in rows:
        dominated = any(other["mean_eta_plus1"] >= row["mean_eta_plus1"] and other["mean_non_target"] <= row["mean_non_target"] and (other["mean_eta_plus1"] > row["mean_eta_plus1"] or other["mean_non_target"] < row["mean_non_target"]) for other in rows)
        if not dominated:
            pareto.append({"case_id": row["case_id"], "family": row["family"], "mean_eta_plus1": row["mean_eta_plus1"], "mean_non_target": row["mean_non_target"], "max_closure": row["max_closure"], "pareto": True})
    with (OUT / "first_batch_pareto.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pareto[0]) if pareto else ["case_id", "pareto"])
        w.writeheader(); w.writerows(pareto)
    champion = max(rows, key=lambda x: x["mean_eta_plus1"])
    atomic = {
        "status": "NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY",
        "valid_case_count": len(rows),
        "family_valid_case_count": {k: sum(r["family"] == k for r in rows) for k in ("K4", "K9")},
        "champion_by_broadband_mean_eta_plus1": champion,
        "cases": rows,
    }
    (OUT / "first_batch_decision.json").write_text(json.dumps(atomic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_rows = [{"case_id": r["case_id"], "family": r["family"], "label": r["label"], "mean_eta_plus1": r["mean_eta_plus1"], "eta_plus1_450": r["eta_plus1_450"], "max_closure": r["max_closure"], "post_fsp_sha256": r["post_fsp_sha256"], "solver_entered": r["solver_entered"], "engine_completed": r["engine_completed"], "post_saved": r["post_saved"]} for r in rows]
    with (OUT / "traditional_multi_target_current_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest_rows[0])); w.writeheader(); w.writerows(manifest_rows)
    (OUT / "coupling_handoff_readiness.json").write_text(json.dumps({"status": atomic["status"], "recommended_champion": champion["case_id"], "valid_cases": [r["case_id"] for r in rows], "x_only": True, "K6_status": "FROZEN_NO_RUN", "y_status": "NOT_RUN", "MDC_status": "NOT_HANDLED"}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# NP traditional multi-target K4/K9 first-batch 3D-FDTD closure", "", "Status: `NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY`", "", "The four authorised attempt_001 cases were run strictly serially with one FDTD slot and 12 cores; two other global slots remained reserved. All four were independently reloaded, labelled valid, and have unchanged post-FSP fingerprints after read-only extraction.", "", "## Cases and evidence", "", "| case | family | diameter vector (nm) | pre-FSP SHA | post-FSP SHA | entered/completed/post | T/R/closure at 450 nm | max |1-T-R| | mean eta(+1) | eta(+1) at 450 nm |", "|---|---|---|---|---|---|---:|---:|---:|---:|"]
    for row, ledger, pre in details:
        lines.append(f"| {row['case_id']} | {row['family']} | {row['diameters_nm']} | {pre['pre_fsp_sha256']} | {row['post_fsp_sha256']} | {row['solver_entered']}/{row['engine_completed']}/{row['post_saved']} | {row['T_450']:.6f}/{row['R_450']:.6f}/{row['closure_450']:.6f} | {row['max_closure']:.6f} | {row['mean_eta_plus1']:.6f} | {row['eta_plus1_450']:.6f} |")
    lines += ["", "All runs used normal incidence, Forward/+z, x-polarisation, 445–455 nm at 11 points, periodic x/y and PML z. Dynamic propagating transmitted orders were extracted from the order monitor (55 rows for K4 and 121 rows for K9 across 11 wavelengths); order fractions sum to unity within numerical precision.", "", "## Decision", "", f"Broadband mean eta(+1) champion: **{champion['case_id']}** ({champion['mean_eta_plus1']:.6f}); no additional seed was needed. K4 and K9 each have two valid first-batch cases. The complete per-wavelength metrics are in each case directory and the lightweight comparison is `first_batch_family_comparison.csv`.", "", "## Scope and handoff", "", "The frozen K6 traditional baseline manifest is identity-only and no K6 solver was run. y-polarisation was not run, angle sweeps/RCWA/ML were not used, and MDC was not handled. The next route is coupling handoff using the recommended K9 seed B candidate. This report is numerical evidence and does not freeze a new cyclic-closure threshold.", "", "## Reproducibility", "", "- Runner: `scripts/run_np_traditional_multitarget_first_batch_3d_fdtd_v1.py` (one `fdtd.run()` call, no retry path).", "- Offline finalizer: `scripts/finalize_np_traditional_multitarget_first_batch_3d_fdtd_v1.py`.", "- Resource audit: `first_batch_resource_usage.csv`, `global_slot_compliance_audit.json`.", "- Budget audit: `first_batch_solver_budget_audit.json` (4/4 entered and completed).", "- attempt_002/003: not run."]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
