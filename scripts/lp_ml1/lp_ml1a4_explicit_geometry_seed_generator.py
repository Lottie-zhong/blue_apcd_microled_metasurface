from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "lp_ml1a4_explicit_geometry_seed_generator"
REPORT = ROOT / "reports" / "lp_ml1a4_explicit_geometry_seed_plan.md"
RULES = ROOT / "reports" / "lp_ml1a4_explicit_geometry_rules.yaml"
SEED = 20260706
PERIOD = 431.907786
MARGIN = 10.0
WAVELENGTHS = "450,450.5,451,451.5,452,452.5,453,453.5,454"
RUN_POLICY = "LP-ML1B_periodic_plane_wave_fullwave_pilot_later"
GROUP_TARGETS = {"B300_exploration": 220, "B240_exploration": 160, "sixbin_balance": 120, "global_escape_lhs": 100}
HEIGHT_TARGETS = [500] * 240 + [600] * 210 + [650] * 120 + [700] * 30
BINS = [0, 60, 120, 180, 240, 300]
COLUMNS = [
    "candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "geometry_source",
    "historical_geometry_recovered", "source_candidate_id", "source_provenance", "H_nm", "period_x_nm",
    "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg",
    "center_dx_nm", "center_dy_nm", "gap_or_dx_nm", "theta1_sin2", "theta1_cos2", "theta2_sin2",
    "theta2_cos2", "intended_lambda_min_nm", "intended_lambda_max_nm", "intended_lambda_points",
    "intended_wavelengths_nm", "run_policy", "prepared_not_run", "geometry_valid", "geometry_reject_reason",
    "duplicate_group_id", "priority_score", "pilot_rank", "notes",
]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rect(cx: float, cy: float, length: float, width: float, theta: float) -> list[tuple[float, float]]:
    a = math.radians(theta % 180)
    ux, uy = math.cos(a), math.sin(a)
    vx, vy = -math.sin(a), math.cos(a)
    pts = []
    for sx, sy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]:
        pts.append((cx + sx * length * ux / 2 + sy * width * vx / 2, cy + sx * length * uy / 2 + sy * width * vy / 2))
    return pts


def project(poly: list[tuple[float, float]], axis: tuple[float, float]) -> tuple[float, float]:
    vals = [x * axis[0] + y * axis[1] for x, y in poly]
    return min(vals), max(vals)


def overlap(poly1: list[tuple[float, float]], poly2: list[tuple[float, float]]) -> bool:
    for poly in (poly1, poly2):
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            ax, ay = -(y2 - y1), x2 - x1
            norm = math.hypot(ax, ay)
            axis = (ax / norm, ay / norm)
            a1, a2 = project(poly1, axis)
            b1, b2 = project(poly2, axis)
            if a2 < b1 or b2 < a1:
                return False
    return True


def in_cell(poly: list[tuple[float, float]]) -> bool:
    half = PERIOD / 2 - MARGIN
    return all(-half <= x <= half and -half <= y <= half for x, y in poly)


def boundary_margin(poly: list[tuple[float, float]]) -> float:
    half = PERIOD / 2
    return min(half - abs(x) for x, _ in poly + []) if poly else 0.0


def bbox_clearance(p1: list[tuple[float, float]], p2: list[tuple[float, float]]) -> float:
    x1 = (min(x for x, _ in p1), max(x for x, _ in p1)); y1 = (min(y for _, y in p1), max(y for _, y in p1))
    x2 = (min(x for x, _ in p2), max(x for x, _ in p2)); y2 = (min(y for _, y in p2), max(y for _, y in p2))
    dx = max(x2[0] - x1[1], x1[0] - x2[1], 0)
    dy = max(y2[0] - y1[1], y1[0] - y2[1], 0)
    return math.hypot(dx, dy)


def valid(g: dict) -> tuple[bool, str]:
    vals = [g[k] for k in ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm"]]
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v == 0 for v in vals):
        return False, "nan_or_zero_numeric_field"
    if g["L1_nm"] < g["W1_nm"] + 20 or g["L2_nm"] < g["W2_nm"] + 20:
        return False, "length_not_at_least_width_plus_20"
    if min(g["W1_nm"], g["W2_nm"]) < 60:
        return False, "min_width_below_60"
    if max(g["L1_nm"], g["L2_nm"]) > 250:
        return False, "max_length_above_250"
    if g["H_nm"] / min(g["W1_nm"], g["W2_nm"]) > 10.5:
        return False, "height_to_width_ratio_above_10p5"
    p1 = rect(-g["center_dx_nm"] / 2, 0, g["L1_nm"], g["W1_nm"], g["theta1_deg"])
    p2 = rect(g["center_dx_nm"] / 2, 0, g["L2_nm"], g["W2_nm"], g["theta2_deg"])
    if not in_cell(p1) or not in_cell(p2):
        return False, "boundary_margin_below_10nm"
    if overlap(p1, p2):
        return False, "rotated_rectangles_overlap"
    if bbox_clearance(p1, p2) < 20:
        return False, "conservative_bbox_clearance_below_20nm"
    return True, ""


def angle_features(theta: float) -> tuple[float, float]:
    r = math.radians(2 * (theta % 180))
    return round(math.sin(r), 8), round(math.cos(r), 8)


def target_for(group: str, index: int) -> int:
    if group == "B300_exploration":
        return 300
    if group == "B240_exploration":
        return 240
    if group == "sixbin_balance":
        return BINS[index // 20]
    weighted = [0, 60, 120, 180] * 12 + [240, 300] * 26
    return weighted[index % len(weighted)]


def family_for(group: str, index: int) -> str:
    families = {
        "B300_exploration": ["B300_asymmetric_length", "B300_theta_contrast", "B300_dx_sweep", "B300_global_mixed"],
        "B240_exploration": ["B240_moderate_asymmetry", "B240_theta_sweep", "B240_dx_sweep", "B240_global_mixed"],
        "sixbin_balance": ["sixbin_moderate_mixed"],
        "global_escape_lhs": ["global_lhs_mixed"],
    }
    return families[group][index % len(families[group])]


def geom(rng: random.Random, group: str, family: str, i: int, height: int) -> dict:
    if group == "global_escape_lhs":
        # Deterministic LHS-style stratification without scipy.
        frac = ((i * 37) % 100 + 0.5) / 100
        l1 = 100 + round(frac * 15) * 10
        l2 = 100 + round((((i * 53) % 100 + 0.5) / 100) * 15) * 10
        w1 = 60 + round((((i * 29) % 100 + 0.5) / 100) * 9) * 10
        w2 = 60 + round((((i * 71) % 100 + 0.5) / 100) * 9) * 10
        t1 = ((i * 47) % 180)
        t2 = ((i * 83 + 30) % 180)
        dx = 120 + round((((i * 61) % 100 + 0.5) / 100) * 11) * 10
    else:
        lbase = rng.randrange(120, 241, 10)
        if "asymmetric" in family:
            l1, l2 = lbase, min(250, max(100, lbase + rng.choice([-50, -40, 40, 50])))
        elif "theta" in family:
            l1, l2 = lbase, rng.randrange(120, 241, 10)
        else:
            l1, l2 = rng.randrange(110, 251, 10), rng.randrange(110, 251, 10)
        w1 = rng.randrange(60, min(150, l1 - 20) + 1, 10)
        w2 = rng.randrange(60, min(150, l2 - 20) + 1, 10)
        if group == "B300_exploration":
            t1 = rng.choice([0, 15, 30, 45, 60, 75, 90, 120, 150])
            t2 = (t1 + rng.choice([45, 60, 75, 90, 105, 120, 135])) % 180
        elif group == "B240_exploration":
            t1 = rng.choice([0, 20, 40, 60, 80, 100, 120, 140, 160])
            t2 = (t1 + rng.choice([20, 40, 60, 80, 100])) % 180
        else:
            t1 = rng.randrange(0, 180, 10)
            t2 = rng.randrange(0, 180, 10)
        dx = rng.randrange(120, 231, 10)
    return {"H_nm": height, "period_x_nm": PERIOD, "period_y_nm": PERIOD, "L1_nm": float(l1), "W1_nm": float(w1), "theta1_deg": float(t1 % 180), "L2_nm": float(l2), "W2_nm": float(w2), "theta2_deg": float(t2 % 180), "center_dx_nm": float(dx), "center_dy_nm": 0.0, "gap_or_dx_nm": float(dx)}


def score(row: dict, duplicate: bool) -> float:
    base = {"B300_exploration": 400, "B240_exploration": 300, "global_escape_lhs": 250, "sixbin_balance": 200}[row["sampling_group"]]
    theta_contrast = abs(((row["theta2_deg"] - row["theta1_deg"] + 90) % 180) - 90)
    base += min(theta_contrast, 90) / 9
    if row["H_nm"] in {500, 600, 650}:
        base += 5
    aspect_penalty = max(row["H_nm"] / min(row["W1_nm"], row["W2_nm"]) - 8.0, 0) * 3
    boundary_penalty = 0 if 130 <= row["center_dx_nm"] <= 220 else 5
    return round(base - aspect_penalty - boundary_penalty - (20 if duplicate else 0), 3)


def make_rows() -> tuple[list[dict], list[dict]]:
    rng = random.Random(SEED)
    heights = HEIGHT_TARGETS[:]
    rng.shuffle(heights)
    hidx = 0
    rows: list[dict] = []
    rejects: list[dict] = []
    seen: dict[tuple, int] = {}
    seq = 0
    for group, count in GROUP_TARGETS.items():
        made = 0
        attempts = 0
        while made < count and attempts < count * 200:
            attempts += 1
            height = heights[hidx % len(heights)]
            hidx += 1
            family = family_for(group, made + attempts)
            target = target_for(group, made)
            g = geom(rng, group, family, made + attempts, height)
            ok, reason = valid(g)
            if not ok:
                rejects.append({"sampling_group": group, "sampling_family": family, "target_bin_deg": target, "geometry_reject_reason": reason, **g})
                continue
            key = tuple(round(g[k], 6) for k in ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm"])
            duplicate = key in seen
            if duplicate:
                rejects.append({"sampling_group": group, "sampling_family": family, "target_bin_deg": target, "geometry_reject_reason": "duplicate_full_geometry", **g})
                continue
            seen[key] = 1
            seq += 1
            s1, c1 = angle_features(g["theta1_deg"])
            s2, c2 = angle_features(g["theta2_deg"])
            row = {
                "candidate_id": f"LPML1A4_{seq:04d}_{group}_B{target}_H{height}",
                "target_bin_deg": target,
                "sampling_group": group,
                "sampling_family": family,
                "geometry_source": "LP-ML1A4_explicit_generator",
                "historical_geometry_recovered": "false",
                "source_candidate_id": "",
                "source_provenance": "new_explicit_geometry_not_old_candidate_geometry",
                **g,
                "theta1_sin2": s1,
                "theta1_cos2": c1,
                "theta2_sin2": s2,
                "theta2_cos2": c2,
                "intended_lambda_min_nm": 450,
                "intended_lambda_max_nm": 454,
                "intended_lambda_points": 9,
                "intended_wavelengths_nm": WAVELENGTHS,
                "run_policy": RUN_POLICY,
                "prepared_not_run": "true",
                "geometry_valid": "true",
                "geometry_reject_reason": "",
                "duplicate_group_id": "",
                "notes": "explicit numeric geometry; future Jones/phase extraction must use complex fields, not intensity-only farfield3d",
            }
            row["priority_score"] = score(row, False)
            row["pilot_rank"] = ""
            rows.append({c: row.get(c, "") for c in COLUMNS})
            made += 1
        if made != count:
            raise RuntimeError(f"Could not generate {count} valid rows for {group}; got {made}")
    rows.sort(key=lambda r: (-float(r["priority_score"]), r["candidate_id"]))
    for i, row in enumerate(rows, 1):
        row["pilot_rank"] = ""
    return rows, rejects


def pilot(rows: list[dict]) -> list[dict]:
    quotas = {"B300_exploration": 12, "B240_exploration": 8, "global_escape_lhs": 8, "sixbin_balance": 8}
    chosen: list[dict] = []
    used = set()
    for group, n in quotas.items():
        for r in [x for x in rows if x["sampling_group"] == group]:
            key = tuple(r[k] for k in ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm"])
            if key not in used:
                chosen.append(r.copy()); used.add(key)
            if sum(1 for x in chosen if x["sampling_group"] == group) >= n:
                break
    # ensure H700 and all bins if feasible by replacing lowest priority within same broad pool.
    def add_constraint(candidates, predicate):
        nonlocal chosen, used
        if any(predicate(c) for c in chosen):
            return
        for r in candidates:
            key = tuple(r[k] for k in ["H_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm"])
            if key not in used and predicate(r):
                chosen[-1] = r.copy(); used.add(key); return
    add_constraint(rows, lambda r: str(r["H_nm"]) == "700")
    for b in BINS:
        add_constraint(rows, lambda r, b=b: str(r["target_bin_deg"]) == str(b))
    chosen = chosen[:36]
    chosen.sort(key=lambda r: (-float(r["priority_score"]), r["candidate_id"]))
    for i, r in enumerate(chosen, 1):
        r["pilot_rank"] = i
    return chosen


def table(rows: list[dict], cols: list[str], limit: int) -> str:
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for r in rows[:limit]:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out)


def write_reports(rows: list[dict], rejects: list[dict], pilot_rows: list[dict], summary: dict) -> None:
    RULES.parent.mkdir(parents=True, exist_ok=True)
    RULES.write_text(f"""# LP-ML1A4 explicit geometry rules
period_rule:
  period_x_nm: {PERIOD}
  period_y_nm: {PERIOD}
  source: project_default_lp_pitch_from_prior_stage_q_times_4
  note: not experimentally optimized
height_allowed_set: [500, 600, 650, 700]
ranges:
  L_nm: [100, 250]
  W_nm: [60, 150]
  theta_deg: [0, 180)
  center_dx_nm: [120, 230]
angle_periodicity_rule: theta modulo 180 deg; ML features use sin(2theta), cos(2theta)
rotated_rectangle_legality_rule: direct Python vertices with separating-axis overlap check
no_overlap_rule: rotated rectangles must not overlap; conservative bbox clearance >= 20 nm
boundary_margin_rule: all vertices must stay within unit cell with >= 10 nm margin
aspect_ratio_caution: H_nm / min(W1_nm, W2_nm) <= 10.5
duplicate_tolerance: exact full-geometry duplicates rejected
provenance: new explicit geometry, not recovered historical geometry
fdtd_data_rules:
  - Future Jones/phase extraction must use complex fields.
  - farfield3d returns intensity |E|^2 and must not be used as Jones phase.
  - Use farfieldvector3d, farfieldpolar3d, or equivalent complex-field monitor data.
  - LP-ML1B pilot uses normal-incidence periodic plane-wave dimer simulations.
  - Later angled validation requires Bloch/BFAST rather than plain periodic.
  - Batch Lumerical script calls through lumapi.eval where appropriate.
""", encoding="utf-8")
    cols = ["candidate_id", "target_bin_deg", "sampling_group", "sampling_family", "H_nm", "L1_nm", "W1_nm", "L2_nm", "W2_nm", "center_dx_nm", "priority_score"]
    REPORT.write_text("\n".join([
        "# LP-ML1A4 Explicit Geometry Seed Plan", "",
        "Purpose: create a new explicit numeric geometry seed generator for LP-APCD dimer ML.", "",
        "LP-ML1B was blocked after A2/A3 because old LP-Hnew source rows had no recoverable numeric dimer geometry and LP-ML1A was default-range-only scaffold data.",
        "A4 creates new explicit geometry instead of more history archaeology because the historical search found zero run-ready rows.", "",
        f"Total generated final candidates: {len(rows)}", f"Total rejected geometry attempts: {len(rejects)}", "",
        "## Counts by sampling_group", "```json\n" + json.dumps(summary["count_by_sampling_group"], indent=2, sort_keys=True) + "\n```",
        "## Counts by target_bin_deg", "```json\n" + json.dumps(summary["count_by_target_bin_deg"], indent=2, sort_keys=True) + "\n```",
        "## Counts by H_nm", "```json\n" + json.dumps(summary["count_by_H_nm"], indent=2, sort_keys=True) + "\n```",
        "## Counts by sampling_family", "```json\n" + json.dumps(summary["count_by_sampling_family"], indent=2, sort_keys=True) + "\n```",
        "## Geometry range summary", "L: 100-250 nm; W: 60-150 nm; theta: 0-180 deg modulo; center_dx: 120-230 nm; period: 431.907786 nm.", "",
        "## Top 20 priority candidates", table(rows, cols, 20), "",
        "## 36-row pilot recommendation summary", table(pilot_rows, ["pilot_rank", *cols], 36), "",
        "No FDTD was run.", "No Lumerical GUI was opened.", "No model was trained.", "No K=6 was attempted.", "",
        "Next recommended step: LP-ML1B runner planning + 36-case pilot, not 600-case full run.",
    ]) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, rejects = make_rows()
    pilot_rows = pilot(rows)
    summary = {
        "candidate_count": len(rows),
        "rejected_geometry_attempt_count": len(rejects),
        "pilot_count": len(pilot_rows),
        "count_by_sampling_group": dict(sorted(Counter(r["sampling_group"] for r in rows).items())),
        "count_by_target_bin_deg": dict(sorted(Counter(str(r["target_bin_deg"]) for r in rows).items())),
        "count_by_H_nm": dict(sorted(Counter(str(r["H_nm"]) for r in rows).items())),
        "count_by_sampling_family": dict(sorted(Counter(r["sampling_family"] for r in rows).items())),
        "no_fdtd_run": True,
    }
    write_csv(OUT / "lp_ml1a4_explicit_seed_manifest.csv", rows, COLUMNS)
    write_csv(OUT / "lp_ml1a4_rejected_geometry.csv", rejects, ["sampling_group", "sampling_family", "target_bin_deg", "geometry_reject_reason", "H_nm", "period_x_nm", "period_y_nm", "L1_nm", "W1_nm", "theta1_deg", "L2_nm", "W2_nm", "theta2_deg", "center_dx_nm", "center_dy_nm", "gap_or_dx_nm"])
    write_csv(OUT / "lp_ml1a4_pilot_recommendation.csv", pilot_rows, COLUMNS)
    (OUT / "lp_ml1a4_explicit_seed_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_reports(rows, rejects, pilot_rows, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
