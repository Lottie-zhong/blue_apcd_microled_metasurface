from __future__ import annotations

import csv
import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/stage11_2h_h500_120_y_pair_micro_rescue"
RECOMMENDATIONS = REPO_ROOT / "outputs/stage11_2g_h500_120_selectivity_readonly/recommended_next_120_micro_rescue_candidates.csv"
PLAN_SOURCES = [
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_alt_patch_plan_stage11_2c.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2d_h500_dimer_final_gap/h500_dimer_final_gap_patch_plan_stage11_2d.csv",
    REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine/h500_dimer_120_240_refine_patch_plan_stage11_2f.csv",
]

PLAN_CSV = OUT_DIR / "h500_120_y_pair_micro_rescue_plan_stage11_2h.csv"
PLAN_MD = OUT_DIR / "h500_120_y_pair_micro_rescue_plan_summary_stage11_2h.md"

PX = 431.907786
PY = 432.0
H = 500.0
LAM = 450.0

FIELDS = [
    "dimer_case_id",
    "base_donor_case_id",
    "target_actual_bin_deg",
    "source_pair_id",
    "static_original_bin_deg",
    "j1_candidate_id",
    "j2_candidate_id",
    "height_nm",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "j1_shape_family",
    "j1_geometry_params",
    "j2_length_nm",
    "j2_width_nm",
    "j2_rotation_deg",
    "placement_type",
    "swap_order",
    "gap_nm",
    "local_offset_nm",
    "j1_center_x_nm",
    "j1_center_y_nm",
    "j2_center_x_nm",
    "j2_center_y_nm",
    "dimer_gap_nm",
    "edge_margin_nm",
    "geometry_legal",
    "expected_failure_mode_to_fix",
    "expected_effect",
    "priority",
    "notes",
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


def sizes(row: dict[str, str]) -> tuple[float, float, float, float]:
    geom = json.loads(row["j1_geometry_params"])
    fam = row["j1_shape_family"]
    if fam == "circle":
        j1x = j1y = flt(geom.get("diameter_nm"))
    elif fam == "square":
        j1x = j1y = flt(geom.get("side_nm"))
    else:
        j1x = flt(geom.get("length_nm"))
        j1y = flt(geom.get("width_nm"))
    return j1x, j1y, flt(row["j2_length_nm"]), flt(row["j2_width_nm"])


def place_y_pair(row: dict[str, str], gap: float, offset: float, swap: bool) -> tuple[float, float, float, float, float, float, bool]:
    j1x, j1y, j2x, j2y = sizes(row)
    sep = (j1y + j2y) / 2 + gap
    x1, y1, x2, y2 = 0.0, -sep / 2 + offset / 2, 0.0, sep / 2 + offset / 2
    if swap:
        x1, y1, x2, y2 = x2, y2, x1, y1
    dx = abs(x2 - x1) - (j1x + j2x) / 2
    dy = abs(y2 - y1) - (j1y + j2y) / 2
    dgap = math.hypot(dx, dy) if dx >= 0 and dy >= 0 else (dx if dx >= 0 else (dy if dy >= 0 else -min(-dx, -dy)))
    edge = min(
        PX / 2 - max(abs(x1) + j1x / 2, abs(x2) + j2x / 2),
        PY / 2 - max(abs(y1) + j1y / 2, abs(y2) + j2y / 2),
    )
    return x1, y1, x2, y2, dgap, edge, dgap >= 16 and edge >= 10


def load_plan_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for path in PLAN_SOURCES:
        for row in read_csv(path):
            cid = row.get("dimer_case_id", "")
            if cid and cid not in lookup:
                lookup[cid] = row
    return lookup


def donor_rows() -> list[dict[str, str]]:
    lookup = load_plan_lookup()
    out: list[dict[str, str]] = []
    for rec in read_csv(RECOMMENDATIONS):
        cid = rec.get("candidate_id", "")
        row = lookup.get(cid)
        if not row:
            continue
        family = rec.get("geometry_family", "")
        if family.startswith("y_pair_noswap") or family.startswith("y_pair_swap"):
            out.append({**row, "_donor_case_id": cid, "_donor_family": family})
        if len(out) >= 6:
            break
    return out


def generate_candidates(max_cases: int = 12) -> list[dict[str, str]]:
    donors = donor_rows()
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, float, float, bool]] = set()
    primary_specs = [(20, -30), (18, -30), (22, -30), (20, -25), (20, -35), (16, -30), (24, -30), (20, -20), (20, -40)]
    control_specs = [(20, -30), (20, -40)]
    for donor in donors:
        is_swap_donor = donor.get("_donor_family", "").startswith("y_pair_swap")
        specs = control_specs if is_swap_donor else primary_specs
        swap_options = [True] if is_swap_donor else [False]
        cap_for_donor = 1 if is_swap_donor else 3
        count = 0
        for gap, offset in specs:
            for swap in swap_options:
                if len(rows) >= max_cases or count >= cap_for_donor:
                    break
                key = (donor.get("source_pair_id", donor.get("source_pair_id", "")), donor.get("_donor_family", ""), float(gap), float(offset), swap)
                if key in seen:
                    continue
                x1, y1, x2, y2, dgap, edge, legal = place_y_pair(donor, float(gap), float(offset), swap)
                if not legal:
                    continue
                seen.add(key)
                count += 1
                rows.append({
                    "dimer_case_id": f"H500DIMER2H_{len(rows)+1:03d}_B120_y_pair_{'swap' if swap else 'noswap'}_G{gap}_O{offset}",
                    "base_donor_case_id": donor["_donor_case_id"],
                    "target_actual_bin_deg": "120",
                    "source_pair_id": donor.get("source_pair_id", ""),
                    "static_original_bin_deg": donor.get("static_original_bin_deg", donor.get("target_actual_bin_deg", "")),
                    "j1_candidate_id": donor.get("j1_candidate_id", ""),
                    "j2_candidate_id": donor.get("j2_candidate_id", ""),
                    "height_nm": fmt(H),
                    "lambda_nm": fmt(LAM),
                    "p_x_nm": fmt(PX),
                    "p_y_nm": fmt(PY),
                    "j1_shape_family": donor.get("j1_shape_family", ""),
                    "j1_geometry_params": donor.get("j1_geometry_params", ""),
                    "j2_length_nm": donor.get("j2_length_nm", ""),
                    "j2_width_nm": donor.get("j2_width_nm", ""),
                    "j2_rotation_deg": donor.get("j2_rotation_deg", "0.000000"),
                    "placement_type": "y_pair",
                    "swap_order": "J2-J1" if swap else "J1-J2",
                    "gap_nm": fmt(float(gap)),
                    "local_offset_nm": fmt(float(offset)),
                    "j1_center_x_nm": fmt(x1),
                    "j1_center_y_nm": fmt(y1),
                    "j2_center_x_nm": fmt(x2),
                    "j2_center_y_nm": fmt(y2),
                    "dimer_gap_nm": fmt(dgap),
                    "edge_margin_nm": fmt(edge),
                    "geometry_legal": "true",
                    "expected_failure_mode_to_fix": "blocked_y_leakage_for_120",
                    "expected_effect": "reduce blocked y-input leakage while keeping selected-channel common phase near 120 deg",
                    "priority": "120_y_pair_micro_rescue",
                    "notes": "Stage11-2H H500-only 120-only y-pair micro-rescue. No K=6, no H600/H700.",
                })
        if len(rows) >= max_cases:
            break
    return rows[:max_cases]


def main() -> None:
    if not RECOMMENDATIONS.exists():
        raise SystemExit(f"missing required input: {RECOMMENDATIONS}")
    rows = generate_candidates(12)
    if not rows:
        raise SystemExit("no legal Stage11-2H candidates generated")
    write_csv(PLAN_CSV, rows, FIELDS)
    y_noswap = sum(row["swap_order"] == "J1-J2" for row in rows)
    y_swap = sum(row["swap_order"] == "J2-J1" for row in rows)
    gaps = [flt(row["gap_nm"]) for row in rows]
    offsets = [flt(row["local_offset_nm"]) for row in rows]
    lines = [
        "# Stage11-2H H500 120 y-pair micro-rescue plan",
        "",
        f"planned_case_count = {len(rows)}",
        f"legal_case_count = {len(rows)}",
        f"y_pair_noswap_count = {y_noswap}",
        f"y_pair_swap_control_count = {y_swap}",
        f"gap_range_nm = {min(gaps):.0f} to {max(gaps):.0f}",
        f"offset_range_nm = {min(offsets):.0f} to {max(offsets):.0f}",
        "",
        "Only H500, only actual common phase 120 deg rescue. No K=6, no metagrating, no H600/H700.",
    ]
    PLAN_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"planned_case_count={len(rows)}")
    print(f"legal_case_count={len(rows)}")
    print(f"y_pair_noswap_count={y_noswap}")
    print(f"y_pair_swap_control_count={y_swap}")
    print(f"out_plan={PLAN_CSV}")


if __name__ == "__main__":
    main()
