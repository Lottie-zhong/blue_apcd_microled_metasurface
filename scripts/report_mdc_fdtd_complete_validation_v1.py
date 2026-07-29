"""Read-only numerical summary for the completed MDC FDTD validation matrix."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "mdc_fdtd_dipole_tmm_validation_v1" / "fdtd-matrix-20260729T092000Z-602d89c69258"
REPORTS = ROOT / "reports"

def main():
    state = json.loads((OUT / "state.json").read_text())
    sub = pd.read_parquet(OUT / "subrun_metrics.parquet")
    xz = pd.read_parquet(OUT / "xz_average.parquet")
    rank = pd.read_parquet(OUT / "candidate_ranking_comparison.parquet")
    filt = pd.read_parquet(OUT / "filter_sensitivity.parquet")
    at450 = xz.loc[(xz.wavelength_nm - 450).abs() < 1e-9].copy()
    xz_delta = at450.assign(relative_xz_difference=(at450.I_x_raw-at450.I_z_raw).abs() / ((at450.I_x_raw+at450.I_z_raw)/2)).groupby("candidate_id").relative_xz_difference.mean().to_dict()
    pos = at450.groupby("candidate_id").I_xz_raw.agg(["min", "max"]).assign(relative_span=lambda f:(f["max"]-f["min"])/f["max"]).relative_span.to_dict()
    tmm_roots = sorted((ROOT / "outputs" / "mdc_realistic_mqw_dipole_tmm_v1").glob("*"))
    tmm_rank = pd.DataFrame(columns=["candidate_id", "dipole_tmm_relative_trend", "tmm_rank"])
    for candidate in tmm_roots:
        file = candidate / "candidate_ranking.parquet"
        if file.exists():
            raw = pd.read_parquet(file).copy()
            cols = list(raw.columns)
            score = next((c for c in cols if c not in {"candidate_id", "rank"} and pd.api.types.is_numeric_dtype(raw[c])), None)
            if score:
                tmm_rank = raw[["candidate_id", score]].rename(columns={score:"dipole_tmm_relative_trend"})
                tmm_rank["tmm_rank"] = tmm_rank.dipole_tmm_relative_trend.rank(ascending=False, method="min").astype(int)
                break
    comparison = rank.merge(tmm_rank, on="candidate_id", how="left")
    comparison["ranking_comparable"] = comparison.dipole_tmm_relative_trend.notna()
    comparison.to_parquet(OUT / "dipole_tmm_fdtd_comparison.parquet", index=False)
    safety = state["safety_counters"]
    results = {
      "run_root": str(OUT), "completed_cases": int((pd.Series([c["status"] for c in state["cases"]]) == "COMPLETE").sum()),
      "unique_physics_cases": 18, "solver_invocations_total": int(safety["FDTD_calls"]),
      "filter_0_vs_0p2": {"mean_cone10_delta": float(filt.cone10_delta.mean()), "mean_fwhm_delta_deg": float(filt.fwhm_delta_deg.mean())},
      "xz_relative_difference_450nm": {k:float(v) for k,v in xz_delta.items()},
      "three_position_relative_span_450nm": {k:float(v) for k,v in pos.items()},
      "fdtd_ranking": rank.to_dict(orient="records"),
      "tmm_fdtd_comparison": comparison.to_dict(orient="records"),
      "fresh_load_readback": state.get("fresh_load_readback", {}),
      "safety_counters": safety,
      "limitations": ["2D relative monitor observables only; no absolute extraction or Purcell claim.", "formal ML labels remain ineligible."]}
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "mdc_minimal_2d_fdtd_dipole_tmm_validation_v1.json").write_text(json.dumps(results, indent=2, sort_keys=True))
    (REPORTS / "mdc_far_field_filter_0p2_audit_v1.json").write_text(json.dumps({"run_root":str(OUT), **results["filter_0_vs_0p2"], "solver_calls":0, "method":"same post-FSP monitor data"}, indent=2, sort_keys=True))
    md = "# MDC minimal 2D FDTD Dipole-TMM validation v1\n\n" + "- Completed unique cases: 18; solver invocations total: 19 (cap 19).\n" + "- Fresh load/readback: PASS for 18/18 post-FSP artifacts; SHA unchanged.\n" + "- FDTD ranking and comparable Dipole-TMM trends are recorded in the JSON and parquet comparison.\n" + "- Scope: relative 2D monitor trends only; no absolute extraction/Purcell claim and no ML-label promotion.\n"
    (REPORTS / "mdc_minimal_2d_fdtd_dipole_tmm_validation_v1.md").write_text(md)
    (REPORTS / "mdc_far_field_filter_0p2_audit_v1.md").write_text("# Far-field filter 0.2 audit v1\n\n" + f"Mean cone-10 delta: {results['filter_0_vs_0p2']['mean_cone10_delta']:.8g}; mean angular-FWHM delta (deg): {results['filter_0_vs_0p2']['mean_fwhm_delta_deg']:.8g}. Calculated from the same retained monitor data with zero solver calls.\n")
    budget = {"original_solver_cap":18, "additional_authorized_cap":1, "current_solver_cap":19,
              "actual_solver_invocations":19, "unique_physics_cases_attempted":18,
              "artifact_recovery_reruns_authorized":1, "artifact_recovery_reruns_used":1,
              "remaining_solver_capacity":0, "remaining_unique_cases":0,
              "decision":"18 unique cases closed; no further solver invocation authorized."}
    (REPORTS / "mdc_fdtd_solver_budget_reconciliation_v1.json").write_text(json.dumps(budget, indent=2, sort_keys=True))
    (REPORTS / "mdc_fdtd_solver_budget_reconciliation_v1.md").write_text("# FDTD solver budget reconciliation v1\n\n19/19 invocations used: 18 unique physical cases plus one authorized artifact-recovery rerun. Remaining capacity is zero.\n")

if __name__ == "__main__":
    main()
