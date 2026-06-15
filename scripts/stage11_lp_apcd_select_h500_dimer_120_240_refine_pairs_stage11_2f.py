from __future__ import annotations

import csv
import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAIR_CSV = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/lp_pair_candidates_h500_stage11_1e_merged_reranked.csv"
BEST_2E = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/h500_dimer_best_actual_6bin_library_stage11_2e.csv"
SUMMARY_2E = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/h500_dimer_actual_6bin_summary_stage11_2e.md"
RESULT_2E = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/h500_dimer_240_fine_pull_fdtd_results_stage11_2e.csv"
OUT_DIR = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine"
OUT_CSV = OUT_DIR / "h500_dimer_120_240_refine_source_pairs_stage11_2f.csv"
OUT_MD = OUT_DIR / "h500_dimer_120_240_refine_pair_selection_summary_stage11_2f.md"

J1_LOOKUPS = [
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j1_gap_closure_plan_stage11_1e.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j1_identity_patch_plan_stage11_1d.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_plan.csv",
]
J2_LOOKUPS = [
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j2_gap_closure_plan_stage11_1e.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_1d_targeted_patch/j2_hwp_patch_plan_stage11_1d.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_j2_hwp_scan/j2_hwp_plan.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_1e_h500_gap_closure/h500_j2_gap_closure_fdtd_results_stage11_1e.csv",
]

FIELDS = [
    "refine_pair_id",
    "target_actual_bin_deg",
    "source_pair_id",
    "static_original_bin_deg",
    "j1_candidate_id",
    "j2_candidate_id",
    "height_nm",
    "j1_shape_family",
    "j1_geometry_params",
    "j2_length_nm",
    "j2_width_nm",
    "static_predicted_ratio",
    "static_target_x_power",
    "static_leak_y_power",
    "static_output_phase_deg",
    "static_s1_amp",
    "static_s2_amp",
    "static_s1_s2_amp_ratio",
    "static_s1_s2_phase_mismatch_deg",
    "selection_reason",
    "expected_failure_mode_to_fix",
    "priority",
    "中文说明",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def load_lookup(paths: list[Path]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for path in paths:
        for row in read_csv(path):
            cid = row.get("candidate_id") or row.get("j1_candidate_id") or row.get("j2_candidate_id")
            if cid and cid not in out:
                out[cid] = row
    return out


def j1_geometry(row: dict[str, str]) -> tuple[str, str, float, float]:
    fam = row.get("shape_family", "")
    if fam == "circle":
        d = flt(row.get("diameter_nm"))
        return fam, json.dumps({"diameter_nm": d}), d, d
    if fam == "square":
        s = flt(row.get("side_nm"))
        return fam, json.dumps({"side_nm": s}), s, s
    length = flt(row.get("length_nm"))
    width = flt(row.get("width_nm"))
    return fam, json.dumps({"length_nm": length, "width_nm": width}), length, width


def geometry_ok(pair: dict[str, str], j1: dict[str, dict[str, str]], j2: dict[str, dict[str, str]]) -> bool:
    j1row = j1.get(pair.get("j1_candidate_id", ""))
    j2row = j2.get(pair.get("j2_candidate_id", ""))
    if not j1row or not j2row:
        return False
    _, _, j1x, j1y = j1_geometry(j1row)
    j2x = flt(j2row.get("length_nm"))
    j2y = flt(j2row.get("width_nm"))
    return all(not math.isnan(v) for v in [j1x, j1y, j2x, j2y]) and (j1x + j2x + 60 <= 411.907786) and max(j1y, j2y) <= 412


def make_row(idx: int, target: int, pair: dict[str, str], j1row: dict[str, str], j2row: dict[str, str], reason: str, failure: str, priority: str, zh: str) -> dict[str, str]:
    fam, geom, _, _ = j1_geometry(j1row)
    return {
        "refine_pair_id": f"REF2F_B{target}_{idx:02d}",
        "target_actual_bin_deg": str(target),
        "source_pair_id": pair.get("pair_id", ""),
        "static_original_bin_deg": pair.get("target_phase_bin_deg", ""),
        "j1_candidate_id": pair.get("j1_candidate_id", ""),
        "j2_candidate_id": pair.get("j2_candidate_id", ""),
        "height_nm": "500.000000",
        "j1_shape_family": fam,
        "j1_geometry_params": geom,
        "j2_length_nm": fmt(flt(j2row.get("length_nm"))),
        "j2_width_nm": fmt(flt(j2row.get("width_nm"))),
        "static_predicted_ratio": pair.get("predicted_ratio", ""),
        "static_target_x_power": pair.get("target_x_power", ""),
        "static_leak_y_power": pair.get("leak_y_power", ""),
        "static_output_phase_deg": pair.get("output_phase_deg", ""),
        "static_s1_amp": pair.get("s1_amp", ""),
        "static_s2_amp": pair.get("s2_amp", ""),
        "static_s1_s2_amp_ratio": pair.get("s1_s2_amp_ratio", ""),
        "static_s1_s2_phase_mismatch_deg": pair.get("s1_s2_phase_mismatch_deg", ""),
        "selection_reason": reason,
        "expected_failure_mode_to_fix": failure,
        "priority": priority,
        "中文说明": zh,
    }


def main() -> None:
    for path in [PAIR_CSV, BEST_2E, SUMMARY_2E, RESULT_2E]:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    j1 = load_lookup(J1_LOOKUPS)
    j2 = load_lookup(J2_LOOKUPS)
    pairs = [
        row for row in read_csv(PAIR_CSV)
        if flt(row.get("j1_height_nm")) == 500
        and flt(row.get("j2_height_nm")) == 500
        and row.get("same_height_pair") == "true"
        and flt(row.get("predicted_ratio")) >= 8
        and flt(row.get("target_x_power")) >= 0.20
        and geometry_ok(row, j1, j2)
    ]

    rows: list[dict[str, str]] = []
    used: set[str] = set()

    def add(target: int, candidates: list[dict[str, str]], limit: int, reason: str, failure: str, priority: str, zh: str) -> None:
        count = 0
        for pair in candidates:
            if count >= limit:
                break
            pid = pair.get("pair_id", "")
            if pid in used:
                continue
            j1row = j1.get(pair.get("j1_candidate_id", ""))
            j2row = j2.get(pair.get("j2_candidate_id", ""))
            if not j1row or not j2row:
                continue
            count += 1
            used.add(pid)
            rows.append(make_row(count, target, pair, j1row, j2row, reason, failure, priority, zh))

    def phase_err(pair: dict[str, str], target: int) -> float:
        return abs(wrap180(flt(pair.get("output_phase_deg")) - target))

    projection_120 = sorted(
        [p for p in pairs if phase_err(p, 120) <= 35],
        key=lambda p: (
            flt(p.get("leak_y_power"), 999),
            flt(p.get("s1_s2_phase_mismatch_deg"), 999),
            abs(1 - flt(p.get("s1_s2_amp_ratio"), 0)),
            phase_err(p, 120),
            -flt(p.get("predicted_ratio"), 0),
        ),
    )
    cross_120 = sorted(
        [p for p in pairs if p not in projection_120],
        key=lambda p: (
            flt(p.get("leak_y_power"), 999),
            flt(p.get("s1_s2_phase_mismatch_deg"), 999),
            abs(1 - flt(p.get("s1_s2_amp_ratio"), 0)),
            -flt(p.get("predicted_ratio"), 0),
        ),
    )
    add(
        120,
        projection_120,
        8,
        "120 projection-selectivity rescue: static phase near 120 with low predicted blocked y-input leakage",
        "projection_selectivity_ratio_low",
        "projection_repair_primary",
        "120°：优先降低 blocked y-input leakage，提高 APCD 投影选择性；phase 已经较好，不能只追 phase hit。",
    )
    add(
        120,
        cross_120,
        4,
        "120 cross-bin high-projection static pair: accept coupling/rebin if projection matrix improves",
        "projection_selectivity_ratio_low",
        "projection_repair_cross_bin",
        "120°：从高投影质量 cross-bin pair 中寻找真实 dimer rebin 机会，重点仍是降低 y-input 泄漏。",
    )

    best_240_source = ""
    best_240_source_pair = ""
    for row in read_csv(BEST_2E):
        if row.get("bin_deg") == "240":
            best_case = row.get("best_case_id", "")
            best_240_source = best_case
            for result_row in read_csv(RESULT_2E):
                if result_row.get("dimer_case_id") == best_case:
                    best_240_source_pair = result_row.get("source_pair_id", "")
                    break
            break
    if best_240_source_pair:
        base_candidates = [p for p in pairs if p.get("pair_id") == best_240_source_pair]
        add(
            240,
            base_candidates,
            1,
            f"240 current real-dimer best source pair from {best_240_source}",
            "common_phase_strict_threshold",
            "common_phase_fine_pull_base",
            "240°：以当前 2E 最佳 loose dimer 的 source pair 为 base，优先把 phase_err 从 8.016489° 拉到 <=8°。",
        )
    near_240 = sorted(
        [p for p in pairs if phase_err(p, 240) <= 40],
        key=lambda p: (
            phase_err(p, 240),
            flt(p.get("s1_s2_phase_mismatch_deg"), 999),
            abs(1 - flt(p.get("s1_s2_amp_ratio"), 0)),
            -flt(p.get("predicted_ratio"), 0),
        ),
    )
    high_240 = sorted(
        [p for p in pairs if p not in near_240],
        key=lambda p: (
            flt(p.get("leak_y_power"), 999),
            phase_err(p, 240),
            -flt(p.get("predicted_ratio"), 0),
        ),
    )
    add(
        240,
        near_240,
        6,
        f"240 strict fine pull: static phase near 240 plus current real best {best_240_source}",
        "common_phase_strict_threshold",
        "common_phase_fine_pull_near",
        "240°：优先微调 selected-channel common phase，使其进入 strict phase threshold，同时保持 projection matrix 不坏。",
    )
    add(
        240,
        high_240,
        6,
        "240 high-projection backup: keep projection usable while seeking actual common-phase strict hit",
        "common_phase_strict_threshold",
        "common_phase_fine_pull_backup",
        "240°：使用高投影质量备选 pair，目标是 phase_err <= 8° 且 ratio、Tx、matrix_error 继续合格。",
    )

    write_csv(OUT_CSV, rows[:24], FIELDS)
    lines = [
        "# Stage11-2F H500 120/240 Refine Source Pair Selection",
        "",
        f"source_pair_count = {len(rows[:24])}",
        f"target_120_count = {sum(r['target_actual_bin_deg'] == '120' for r in rows[:24])}",
        f"target_240_count = {sum(r['target_actual_bin_deg'] == '240' for r in rows[:24])}",
        "",
        "120 deg focuses on APCD projection selectivity: reduce blocked y-input leakage and improve projection_selectivity_ratio.",
        "240 deg focuses on strict selected-channel common-phase fine pull while preserving projection matrix quality.",
        "",
        "No K=6, no phase-gradient supercell, no H600/H700.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"source_pair_count={len(rows[:24])}")
    print(f"target_120_count={sum(r['target_actual_bin_deg'] == '120' for r in rows[:24])}")
    print(f"target_240_count={sum(r['target_actual_bin_deg'] == '240' for r in rows[:24])}")


if __name__ == "__main__":
    main()
