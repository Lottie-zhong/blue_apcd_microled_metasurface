from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np

UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_csv(path, rows):
    if not rows:
        raise RuntimeError("EMPTY_FINAL_COMPARISON")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def val(d, *keys, default=None):
    for key in keys:
        if not isinstance(d, dict) or key not in d:
            return default
        d = d[key]
    return d


def delta(value, baseline):
    return None if value is None or baseline is None else float(value) - float(baseline)


def finite_summary(values):
    arr = np.asarray([x for x in values if x is not None], dtype=float)
    if not len(arr):
        return {"mean": None, "worst": None, "max": None, "max_min_ripple": None, "coefficient_of_variation": None}
    mean = float(np.mean(arr)); return {"mean": mean, "worst": float(np.min(arr)), "max": float(np.max(arr)), "max_min_ripple": float(np.max(arr) - np.min(arr)), "coefficient_of_variation": float(np.std(arr) / abs(mean)) if mean else None}


def run(args):
    out = args.output_dir; out.mkdir(parents=True, exist_ok=True)
    pair_dirs = {candidate: out / "pairs" / candidate for candidate in ("IAR3", "IAR4")}
    summaries = {candidate: json.loads((path / "pair_summary.json").read_text(encoding="utf-8")) for candidate, path in pair_dirs.items()}
    baseline = json.loads(args.baseline_anchor.read_text(encoding="utf-8"))
    base_dolp = val(baseline, "pair_DoLP")
    base_csource = val(baseline, "C_linear")
    base_cangular = val(baseline, "angular", "angular_cancellation", "C_angular")
    base_cones = {str(angle): val(baseline, "angular", f"normal_{angle}_deg", "DoLP") for angle in (5, 10, 20)}
    rows = []
    for candidate, summary in summaries.items():
        anchor = summary["anchor_450nm"]; pair450 = anchor["pair"]; angular = anchor["angular"]
        broad = summary["broadband"]
        csrc = anchor["C_source"]; cang = angular["C_angular"]
        if csrc < 0.5 and cang < 0.5: mechanism = "BOTH_SOURCE_AND_ANGULAR_CANCELLATION"
        elif csrc < 0.5: mechanism = "SOURCE_STOKES_CANCELLATION_DOMINANT"
        elif cang < 0.5: mechanism = "ANGULAR_STOKES_CANCELLATION_DOMINANT"
        elif broad["pair_DoLP"]["mean"] < 0.5: mechanism = "NO_MEANINGFUL_INTEGRATED_RESPONSE"
        else: mechanism = "DESCRIPTIVE_REINFORCEMENT_ONLY"
        rows.append({
            "candidate_id": candidate, "status": summary["status"], "mechanism_class_descriptive": mechanism,
            "pair_DoLP_450": pair450["DoLP"], "pair_DoLP_mean": broad["pair_DoLP"]["mean"], "pair_DoLP_worst": broad["pair_DoLP"]["worst"], "pair_DoLP_ripple": broad["pair_DoLP"]["max_min_ripple"],
            "useful_LP_axisfree_450": pair450["useful_LP_axisfree"], "useful_LP_axisfree_mean": broad["pair_useful_LP_axisfree"]["mean"], "useful_LP_axisfree_worst": broad["pair_useful_LP_axisfree"]["worst"], "useful_LP_over_S0_mean": broad["pair_useful_LP_over_S0"]["mean"],
            "upward_source_normalized_power_450": anchor["upward_source_normalized_power_pair"], "upward_source_normalized_power_mean": broad["upward_source_normalized_power"]["mean"], "upward_source_normalized_power_worst": broad["upward_source_normalized_power"]["worst"],
            "C_source_450": csrc, "C_source_mean": broad["C_source"]["mean"], "C_source_worst": broad["C_source"]["worst"], "C_angular_450": cang, "C_angular_mean": broad["C_angular"]["mean"], "C_angular_worst": broad["C_angular"]["worst"],
            "full_angle_DoLP_450": angular["full_angle_pair_DoLP"], "normal_5deg_DoLP_450": angular["normal_5deg_DoLP"], "normal_10deg_DoLP_450": angular["normal_10deg_DoLP"], "normal_20deg_DoLP_450": angular["normal_20deg_DoLP"], "x_y_S0_ratio_450": anchor["x_y_S0_ratio"], "Poincare_separation_450_deg": anchor["Poincare_separation_deg"],
        })
    write_csv(out / "candidate_comparison.csv", rows)
    baseline_rows = []
    for row in rows:
        baseline_rows.append({"candidate_id": row["candidate_id"], "pair_DoLP_450": row["pair_DoLP_450"], "baseline_pair_DoLP_450": base_dolp, "delta_pair_DoLP_450": delta(row["pair_DoLP_450"], base_dolp), "C_source_450": row["C_source_450"], "baseline_C_source_450": base_csource, "delta_C_source_450": delta(row["C_source_450"], base_csource), "C_angular_450": row["C_angular_450"], "baseline_C_angular_450": base_cangular, "delta_C_angular_450": delta(row["C_angular_450"], base_cangular), "full_angle_DoLP_450": row["full_angle_DoLP_450"], "baseline_full_angle_DoLP_450": val(baseline, "angular", "full_available_upper", "DoLP"), "normal_5deg_DoLP_450": row["normal_5deg_DoLP_450"], "baseline_normal_5deg_DoLP_450": base_cones["5"], "normal_10deg_DoLP_450": row["normal_10deg_DoLP_450"], "baseline_normal_10deg_DoLP_450": base_cones["10"], "normal_20deg_DoLP_450": row["normal_20deg_DoLP_450"], "baseline_normal_20deg_DoLP_450": base_cones["20"]})
    write_csv(out / "baseline_delta_comparison.csv", baseline_rows)
    controller = json.loads(args.controller_state.read_text(encoding="utf-8")) if args.controller_state.exists() else {}
    provenances = []
    for case in ("IAR3_x", "IAR3_y", "IAR4_x", "IAR4_y"):
        path = args.runtime_dir / "cases" / case / f"{case}_attempt_001_provenance.json"
        if not path.exists():
            raise RuntimeError(f"PROVENANCE_MISSING:{case}")
        provenances.append(json.loads(path.read_text(encoding="utf-8")))
    all_returned = all(item.get("status") == "RETURNED" and item.get("solver_entered") is True and item.get("solver_run_called") is True for item in provenances)
    all_pair_pass = all(s["status"] == "PASS" for s in summaries.values())
    status = "PASS" if all_returned and all_pair_pass else "HARD_GATE"
    final = {
        "schema": "PAPER_A_INTEGRATED_AWARE_LP_INITIAL_TRUTH_FINAL_V1", "status": status,
        "scientific_judgment": "Descriptive integrated-aware LP truth only; no composite score and no automatic champion. Final scientific promotion remains a Chart decision.",
        "IAR3_PAIR": summaries["IAR3"], "IAR4_PAIR": summaries["IAR4"],
        "baseline_comparison": {"authority": str(args.baseline_anchor), "authority_sha256": sha256(args.baseline_anchor), "baseline_450": {"pair_DoLP": base_dolp, "C_source": base_csource, "C_angular": base_cangular, "normal_cone_DoLP": base_cones}, "comparison_csv": str(out / "baseline_delta_comparison.csv")},
        "source_cancellation": {candidate: {"C_source_450": row["C_source_450"], "C_source_mean": row["C_source_mean"], "C_source_worst": row["C_source_worst"]} for candidate, row in ((r["candidate_id"], r) for r in rows)},
        "angular_cancellation": {candidate: {"C_angular_450": row["C_angular_450"], "C_angular_mean": row["C_angular_mean"], "C_angular_worst": row["C_angular_worst"], "full_angle_DoLP_450": row["full_angle_DoLP_450"]} for candidate, row in ((r["candidate_id"], r) for r in rows)},
        "power_tradeoff": {candidate: {"useful_LP_mean": row["useful_LP_axisfree_mean"], "useful_LP_worst": row["useful_LP_axisfree_worst"], "upward_source_normalized_power_mean": row["upward_source_normalized_power_mean"], "upward_source_normalized_power_worst": row["upward_source_normalized_power_worst"]} for candidate, row in ((r["candidate_id"], r) for r in rows)},
        "validity": {item["case_id"]: {"status": item.get("status"), "solver_entered": item.get("solver_entered"), "solver_run_called": item.get("solver_run_called")} for item in provenances},
        "solver_accounting": {"authorized_new_fdtd_entries": 4, "entered": sum(bool(item.get("solver_entered")) for item in provenances), "returned": sum(item.get("status") == "RETURNED" for item in provenances), "accepted_pair_count": sum(s["status"] == "PASS" for s in summaries.values()), "RCWA": 0, "ML": 0, "replay": 0, "new_cases_started": [item["case_id"] for item in provenances]},
        "controller_state": controller, "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE", "no_emitter_weighted_claim": True, "timestamp_utc": now(),
    }
    write_json(out / "final_closeout.json", final)
    report = ["# Integrated-aware LP initial truth", "", f"Status: **{status}**", "", "This is an integrated-aware LP truth acquisition for IAR3 and IAR4. It does not select a champion or use a composite score.", "", "## IAR3 pair", f"- 450 nm pair DoLP: `{rows[0]['pair_DoLP_450']:.8f}`; broadband mean/worst: `{rows[0]['pair_DoLP_mean']:.8f}` / `{rows[0]['pair_DoLP_worst']:.8f}`.", f"- 450 nm useful axis-free LP: `{rows[0]['useful_LP_axisfree_450']:.8e}`; upward source-normalized power: `{rows[0]['upward_source_normalized_power_450']:.8e}`.", f"- Source C / angular C: `{rows[0]['C_source_450']:.8f}` / `{rows[0]['C_angular_450']:.8f}`; mechanism: `{rows[0]['mechanism_class_descriptive']}`.", "", "## IAR4 pair", f"- 450 nm pair DoLP: `{rows[1]['pair_DoLP_450']:.8f}`; broadband mean/worst: `{rows[1]['pair_DoLP_mean']:.8f}` / `{rows[1]['pair_DoLP_worst']:.8f}`.", f"- 450 nm useful axis-free LP: `{rows[1]['useful_LP_axisfree_450']:.8e}`; upward source-normalized power: `{rows[1]['upward_source_normalized_power_450']:.8e}`.", f"- Source C / angular C: `{rows[1]['C_source_450']:.8f}` / `{rows[1]['C_angular_450']:.8f}`; mechanism: `{rows[1]['mechanism_class_descriptive']}`.", "", "## Baseline comparison", "The fixed IC1+IC2 I03 baseline is used only for delta comparison; no baseline solver was rerun.", f"- Baseline 450 nm pair DoLP / C_source / C_angular: `{base_dolp}` / `{base_csource}` / `{base_cangular}`.", "", "## Interpretation", "- x/y sources were combined incoherently at Stokes/coherency level; electric fields were not added and DoLP/psi were not averaged.", "- Angular metrics are wavelength-resolved over the full 400–500 nm descriptive grid; raw psi remains diagnostic and is ill-conditioned at low DoLP.", "- `W_emit` remains unresolved; no emitter-weighted or absolute LEE claim is made.", "- Mechanism classes are descriptive only. Final promotion remains a Chart scientific decision.", "", "## Validity and accounting", "- Same finite 3 um mesa, 5x5 array, MDC, source z, z datum, PML/domain/monitor and Native-M1 contract were used.", "- 4 new FDTD entries: IAR3_x, IAR3_y, IAR4_x, IAR4_y; 12 MPI x 1 thread/job; no replay; RCWA=0; ML=0.", ""]
    (out / "final_report.md").write_text("\n".join(report), encoding="utf-8")
    audit = {"schema": "PAPER_A_INTEGRATED_AWARE_LP_INITIAL_TRUTH_FINAL_AUDIT_V1", "status": status, "inputs": {str(args.baseline_anchor): sha256(args.baseline_anchor), "controller_state": sha256(args.controller_state) if args.controller_state.exists() else None}, "tests": {"all_four_returned": all_returned, "both_pairs_pass": all_pair_pass, "no_composite_score": True, "no_new_solver_in_postprocess": True}, "outputs": {path.name: {"sha256": sha256(path), "bytes": path.stat().st_size} for path in out.iterdir() if path.is_file() and path.name != "audit.json"}, "solver_accounting": final["solver_accounting"], "timestamp_utc": now()}
    write_json(out / "audit.json", audit)
    terminal = out / ("terminal_success.json" if status == "PASS" else "terminal_failure.json")
    write_json(terminal, {"schema": "PAPER_A_INTEGRATED_AWARE_LP_INITIAL_TRUTH_TERMINAL_V1", "status": status, "final_closeout": str(out / "final_closeout.json"), "solver_accounting": final["solver_accounting"], "timestamp_utc": now()})
    return final


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--runtime-dir", type=Path, required=True); parser.add_argument("--controller-state", type=Path, required=True); parser.add_argument("--baseline-anchor", type=Path, required=True)
    args = parser.parse_args(); print(json.dumps(run(args), ensure_ascii=False, indent=2, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
