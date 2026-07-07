from __future__ import annotations

import ast
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "lp_ml1b2b_36case_pilot"
BATCH = OUT / "batch_01"
REPORT = ROOT / "reports" / "lp_ml1b_seed_objective_audit_selectivity_first.md"
SUMMARY = OUT / "lp_ml1b_seed_objective_audit_summary.json"
RECLASS = BATCH / "lp_ml1b_batch01_selectivity_first_reclass.csv"

A4 = ROOT / "scripts" / "lp_ml1" / "lp_ml1a4_explicit_geometry_seed_generator.py"
B0 = ROOT / "scripts" / "lp_ml1" / "lp_ml1b0_runner_planning.py"
B2B = ROOT / "scripts" / "lp_ml1" / "lp_ml1b2b_batch01_fdtd.py"
RANKING = BATCH / "lp_ml1b2b_batch01_candidate_ranking.csv"
RESULTS = BATCH / "lp_ml1b2b_batch01_results.csv"
NEXT_REC = OUT / "lp_ml1b2b_next_batch_recommendation.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def f(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def fmt(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    if not math.isfinite(float(value)):
        return ""
    return f"{float(value):.6f}"


def median(values: list[float]) -> float:
    vals = sorted(values)
    if not vals:
        return 0.0
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def extract_group_targets() -> dict[str, int]:
    text = A4.read_text(encoding="utf-8")
    m = re.search(r"GROUP_TARGETS\s*=\s*(\{[^\n]+\})", text)
    return ast.literal_eval(m.group(1)) if m else {}


def source_evidence() -> dict[str, object]:
    a4 = A4.read_text(encoding="utf-8")
    b0 = B0.read_text(encoding="utf-8")
    b2b = B2B.read_text(encoding="utf-8")
    return {
        "a4_group_targets": extract_group_targets(),
        "a4_label_source": "geometric_intent_sampling_group",
        "a4_uses_simulated_jones_phase_for_labels": False,
        "a4_uses_previous_proxy_static_phasor": False,
        "a4_has_selectivity_gate": any(s in a4 for s in ["conversion_to_leakage_ratio", "matrix_error", "selected_Tx", "leakage_xin_to_yout"]),
        "b0_mentions_projection_schema": "selected_Tx = |txx|^2" in b0 and "matrix_error" in b0,
        "b0_selection_basis": "sampling_balance_and_priority_score",
        "b2b_strong_gate": "tx >= 0.45 and ratio >= 6 and phase <= 15 and matrix <= 0.60" in b2b,
        "b2b_usable_gate": "tx >= 0.10 and ratio >= 3 and phase <= 25 and matrix <= 1.00" in b2b,
        "b2b_sort_basis": "status_then_ratio_then_phase" if "return (rank, -f(r.get(\"ratio_median\")), f(r.get(\"phase_err_at_452nm\")))" in b2b else "unknown",
    }


def classify_candidate(r: dict[str, str], grouped: dict[str, list[dict[str, str]]]) -> dict[str, object]:
    cid = r["candidate_id"]
    rows = grouped[cid]
    tx = f(r.get("Tx_mean"))
    ratio = f(r.get("ratio_median"))
    phase = f(r.get("phase_err_at_452nm"))
    target = int(f(r.get("target_bin")))
    nearest = int(f(r.get("nearest_bin_mode")))
    matrix_vals = [f(x.get("matrix_error")) for x in rows if x.get("result_status") == "ok"]
    y_leak_vals = [f(x.get("y_direct_leakage")) for x in rows if x.get("result_status") == "ok"]
    yin_x_vals = [f(x.get("leakage_yin_to_xout")) for x in rows if x.get("result_status") == "ok"]
    xin_y_vals = [f(x.get("leakage_xin_to_yout")) for x in rows if x.get("result_status") == "ok"]
    bins = [str(int(f(x.get("nearest_bin_deg")))) for x in rows if x.get("result_status") == "ok"]
    unique_bins = sorted(set(bins), key=lambda x: int(x))
    matrix_med = median(matrix_vals)
    projector_pass = tx >= 0.45 and ratio >= 6 and matrix_med <= 0.60
    projector_near = tx >= 0.45 and ratio >= 3 and matrix_med <= 1.00
    phase_pass = nearest == target and phase <= 15
    phase_near = nearest == target and phase <= 30
    if not rows:
        cls = "failed_invalid"
    elif projector_pass and phase_pass:
        cls = "projector_and_phase_pass"
    elif phase_near and not projector_near:
        cls = "phase_near_but_nonselective"
    elif tx >= 0.45 and ratio < 3:
        cls = "high_Tx_but_nonselective"
    elif nearest != target and not projector_near:
        cls = "phase_drifted_and_nonselective"
    elif nearest != target and projector_near:
        cls = "projector_possible_but_wrong_bin"
    else:
        cls = "potentially_useful_negative_sample"
    return {
        "candidate_id": cid,
        "target_bin": target,
        "nearest_bin_mode": nearest,
        "unique_nearest_bins": ";".join(unique_bins),
        "Tx_mean": fmt(tx),
        "ratio_median": fmt(ratio),
        "matrix_error_median": fmt(matrix_med),
        "phase_err_at_452nm": fmt(phase),
        "y_direct_leakage_median": fmt(median(y_leak_vals)),
        "leakage_yin_to_xout_median": fmt(median(yin_x_vals)),
        "leakage_xin_to_yout_median": fmt(median(xin_y_vals)),
        "old_preliminary_status": r.get("preliminary_status", ""),
        "projector_gate": "pass" if projector_pass else ("near" if projector_near else "fail"),
        "phase_gate": "pass" if phase_pass else ("near" if phase_near else "fail"),
        "selectivity_first_class": cls,
        "use_as_next_seed": "maybe_reassign_not_target" if cls == "projector_possible_but_wrong_bin" else "no",
    }


def md_table(rows: list[dict[str, object]], cols: list[str]) -> list[str]:
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    return out


def main() -> None:
    ranking = read_csv(RANKING)
    results = read_csv(RESULTS)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in results:
        grouped[row["candidate_id"]].append(row)

    evidence = source_evidence()
    reclass = [classify_candidate(row, grouped) for row in ranking]
    fields = [
        "candidate_id", "target_bin", "nearest_bin_mode", "unique_nearest_bins", "Tx_mean", "ratio_median", "matrix_error_median",
        "phase_err_at_452nm", "y_direct_leakage_median", "leakage_yin_to_xout_median", "leakage_xin_to_yout_median",
        "old_preliminary_status", "projector_gate", "phase_gate", "selectivity_first_class", "use_as_next_seed",
    ]
    write_csv(RECLASS, reclass, fields)

    next_rec = json.loads(NEXT_REC.read_text(encoding="utf-8")) if NEXT_REC.exists() else {}
    class_counts = Counter(r["selectivity_first_class"] for r in reclass)
    nearest_counts = Counter(str(r["nearest_bin_mode"]) for r in reclass)
    old_counts = Counter(r["old_preliminary_status"] for r in reclass)
    high_tx_nonselective = [r for r in reclass if r["selectivity_first_class"] == "high_Tx_but_nonselective"]
    phase_near_nonselective = [r for r in reclass if r["selectivity_first_class"] == "phase_near_but_nonselective"]
    drift_nonselective = [r for r in reclass if r["selectivity_first_class"] == "phase_drifted_and_nonselective"]

    thresholds = {
        "minimum_selected_Tx": 0.45,
        "minimum_ratio_median": 6.0,
        "maximum_y_direct_leakage_relative_to_selected_Tx": "Tx/6 provisional budget",
        "maximum_phase_err_at_452nm_deg": 15.0,
        "maximum_bin_instability_unique_bins": 1,
        "matrix_error_warning_threshold": 0.60,
    }
    summary = {
        "audit_scope": "LP-ML1B seed objective audit; no FDTD run",
        "a4_target_bin_source": evidence["a4_label_source"],
        "a4_uses_simulated_jones_phase_for_labels": evidence["a4_uses_simulated_jones_phase_for_labels"],
        "a4_uses_previous_proxy_static_phasor": evidence["a4_uses_previous_proxy_static_phasor"],
        "a4_uses_selectivity_first_gate": bool(evidence["a4_has_selectivity_gate"]),
        "b0_selection_basis": evidence["b0_selection_basis"],
        "b2b_ranking_status_gate": "mixed Tx/ratio/phase/matrix thresholds; status then ratio then phase sort",
        "conclusion": "not_selectivity_first_seed_generation",
        "recommendation": "adjust_ranking_and_seed_logic_before_batch_02",
        "batch04_remains_recommended_if_next_fdtd_is_authorized": next_rec.get("recommended_next_batch_id") == "LPML1B2A_BATCH_04",
        "recommended_next_batch_id": next_rec.get("recommended_next_batch_id", ""),
        "provisional_thresholds": thresholds,
        "nearest_bin_counts": dict(nearest_counts),
        "old_status_counts": dict(old_counts),
        "selectivity_first_class_counts": dict(class_counts),
        "no_fdtd_run": True,
        "no_gui": True,
        "no_fmm": True,
        "no_training": True,
        "no_k6": True,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# LP-ML1B seed-objective audit: selectivity first",
        "",
        "## Direct answer",
        "Current LP-ML1A4 / LP-ML1B candidates are mainly target-bin geometry exploration seeds, not a true selectivity-first LP-APCD seed set.",
        "The code computes and preserves the correct Jones/projection metrics later, but the A4 seed labels are assigned from geometry-intent sampling groups rather than simulated Jones phase or a projector/selectivity gate.",
        "",
        "## What A4 target_bin means",
        f"A4 defines GROUP_TARGETS as `{evidence['a4_group_targets']}` and generates target_bin_deg from sampling groups such as B300_exploration, B240_exploration, global_escape_lhs, and sixbin_balance.",
        "This means target_bin is an intended exploration label. It is not proof that the selected channel phase landed in that bin, and it is not proof that the candidate behaves like `t exp(i phi)|x><x|`.",
        "",
        "## Selectivity-first gates found",
        f"- A4 selectivity-first gate before inclusion: `{evidence['a4_has_selectivity_gate']}`.",
        "- B0 queue planning documents the desired LP Jones schema, but queue selection is mainly sampling balance / priority-score exploration, not measured selectivity-first selection.",
        "- B2B strong/usable labels use Tx, ratio, phase, and matrix_error thresholds, then ranking sorts by status, ratio, and phase. This is a mixed gate, not a clean hierarchy of projector first then phase.",
        "",
        "## Batch-01 selectivity-first reclassification",
    ]
    lines += md_table(reclass, ["candidate_id", "target_bin", "nearest_bin_mode", "Tx_mean", "ratio_median", "matrix_error_median", "phase_err_at_452nm", "projector_gate", "phase_gate", "selectivity_first_class"])
    lines += [
        "",
        "## Batch-01 failure in selectivity-first language",
        f"- nearest_bin_mode counts: `{dict(nearest_counts)}`.",
        f"- old preliminary_status counts: `{dict(old_counts)}`.",
        f"- selectivity-first class counts: `{dict(class_counts)}`.",
        f"- high-Tx but nonselective candidates: `{[r['candidate_id'] for r in high_tx_nonselective]}`.",
        f"- phase-near but nonselective candidates: `{[r['candidate_id'] for r in phase_near_nonselective]}`.",
        f"- phase-drifted and nonselective candidates: `{[r['candidate_id'] for r in drift_nonselective]}`.",
        "Batch-01 is technically healthy as a data extraction run, but physically weak for LP APCD because projector/selectivity behavior is not established before phase targeting.",
        "",
        "## Corrected LP-ML1B2C ranking hierarchy",
        "1. Hard gate 1: extraction/schema pass, finite complex Jones values, correct wavelength/polarization coverage, no anomaly flags.",
        "2. Hard gate 2: projector/selectivity pass: selected_Tx floor, leakage ceilings, selected-to-leakage ratio, and matrix_error against `t exp(i phi)|x><x|`.",
        "3. Hard gate 3: phase-bin pass: nearest_bin_mode equals target and phase_err_at_452nm or spectral max phase error meets threshold.",
        "4. Hard gate 4: wavelength stability pass: nearest bin is stable and phase/ratio remain acceptable across the sampled wavelengths.",
        "5. Soft ranking: higher Tx, better ratio, lower matrix_error, bandwidth stability, then geometry/fabrication margin.",
        "",
        "## Provisional pilot-stage thresholds",
        "- minimum selected_Tx: 0.45",
        "- minimum ratio_median: 6.0",
        "- maximum y_direct_leakage relative to selected_Tx: y_direct_leakage <= selected_Tx / 6 as a first budget",
        "- maximum phase_err_at_452nm: 15 deg for pass, 30 deg for near-miss diagnostics",
        "- maximum bin instability: one nearest-bin mode across wavelengths for a pass",
        "- matrix_error warning threshold: 0.60",
        "",
        "## Next batch recommendation",
        "LPML1B2A_BATCH_04 remains the best next FDTD batch if another batch is authorized because it adds B240 plus global/sixbin diversity.",
        "However, this audit recommends adjusting LP-ML1B2C ranking/seed logic before continuing to batch-02. Batch-02 is mostly B300 continuation and should be treated as statistical failure mapping, not the default next physical rescue batch.",
        "",
        "No FDTD was run. No GUI, FMM, model training, K=6, coverage, or heavy output generation was performed.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
