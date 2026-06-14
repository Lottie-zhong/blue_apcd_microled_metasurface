
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_J1 = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan"
OUTPUT_PAIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing"
CONFIG_DIR = REPO_ROOT / "configs" / "blue"

LAMBDA_NM = 450
PX_NM = 432
PY_VALUES_NM = [400, 432, 450]
HEIGHT_VALUES_NM = [500, 600, 650, 700]
MATERIAL = "GaN"
PHASE_BINS_DEG = [0, 60, 120, 180, 240, 300]


def wrap360(x: float) -> float:
    return x % 360.0


def wrap180(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def circular_error_deg(a: float, b: float) -> float:
    return abs(wrap180(a - b))


def safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def max_footprint(shape_type: str, params: dict[str, float]) -> float:
    if shape_type == "circular_cylinder":
        return 2.0 * params["radius_nm"]
    if shape_type == "square_pillar":
        return params["side_nm"]
    if shape_type in {"regular_hexagon", "regular_octagon"}:
        return params["equivalent_diameter_nm"]
    if shape_type == "near_square_rectangle":
        return max(params["L_nm"], params["W_nm"])
    if shape_type == "ellipse_near_circle":
        return max(params["major_nm"], params["minor_nm"])
    raise ValueError(f"unknown shape_type: {shape_type}")


def shape_rows() -> Iterable[tuple[str, dict[str, float]]]:
    for radius in [45, 55, 65, 75, 85, 95, 105, 115, 125, 135]:
        yield "circular_cylinder", {"radius_nm": float(radius)}
    for side in [80, 95, 110, 125, 140, 155, 170, 185, 200]:
        yield "square_pillar", {"side_nm": float(side)}
    for diameter in [90, 110, 130, 150, 170, 190, 210]:
        yield "regular_hexagon", {"equivalent_diameter_nm": float(diameter)}
    for diameter in [90, 110, 130, 150, 170, 190, 210]:
        yield "regular_octagon", {"equivalent_diameter_nm": float(diameter)}
    for length in [90, 110, 130, 150, 170, 190]:
        for width in [90, 110, 130, 150, 170, 190]:
            ratio = length / width
            if 0.85 <= ratio <= 1.15:
                yield "near_square_rectangle", {"L_nm": float(length), "W_nm": float(width)}
    for major in [90, 110, 130, 150, 170, 190]:
        for minor in [90, 110, 130, 150, 170, 190]:
            ratio = major / minor
            if 0.85 <= ratio <= 1.15:
                yield "ellipse_near_circle", {"major_nm": float(major), "minor_nm": float(minor)}


def build_j1_plan() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    serial = 1
    for py_nm in PY_VALUES_NM:
        for height_nm in HEIGHT_VALUES_NM:
            for shape_type, params in shape_rows():
                footprint = max_footprint(shape_type, params)
                margin_x = 0.5 * (PX_NM - footprint)
                margin_y = 0.5 * (py_nm - footprint)
                legal = margin_x >= 0 and margin_y >= 0
                rows.append(
                    {
                        "candidate_id": f"J1ID_{serial:04d}",
                        "shape_type": shape_type,
                        "geometry_params": json_dumps(params),
                        "material": MATERIAL,
                        "lambda_nm": LAMBDA_NM,
                        "p_x_nm": PX_NM,
                        "p_y_nm": py_nm,
                        "height_nm": height_nm,
                        "max_footprint_nm": f"{footprint:.3f}",
                        "margin_x_nm": f"{margin_x:.3f}",
                        "margin_y_nm": f"{margin_y:.3f}",
                        "geometry_status": "legal" if legal else "invalid_margin",
                        "setup_status": "plan_only_no_lumerical_run",
                    }
                )
                serial += 1
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_j1_config(path: Path, plan_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# stage10lp_j1_identity_shape_scan setup-only configuration
project:
  name: blue_apcd_microled_metasurface
  stage: stage10lp_j1_identity_shape_scan
  mode: setup_only_no_lumerical_run
baseline:
  lambda_nm: {LAMBDA_NM}
  p_x_nm: {PX_NM}
  p_y_nm: {PY_VALUES_NM}
  material: {MATERIAL}
  height_nm: {HEIGHT_VALUES_NM}
shape_types:
  - circular_cylinder
  - square_pillar
  - regular_hexagon
  - regular_octagon
  - near_square_rectangle
  - ellipse_near_circle
selection_goal:
  role: identity_like_isotropic_like_J1_for_LP_APCD
  retardance_to_identity_deg_broad_pass: 30
  retardance_to_identity_deg_strict_pass: 15
  amp_balance_min: 0.75
  T_mean_min: 0.30
outputs:
  plan_csv: {plan_path.as_posix()}
  result_csv: {(OUTPUT_J1 / 'j1_identity_results.csv').as_posix()}
  summary_md: {(OUTPUT_J1 / 'j1_identity_summary.md').as_posix()}
notes:
  - This config intentionally does not launch Lumerical or FDTD.
  - Polygonal/circular shapes may be approximated by the downstream geometry backend if native primitives are unavailable.
"""
    path.write_text(text, encoding="utf-8")


def write_preview(plan_rows: list[dict[str, Any]]) -> Path:
    OUTPUT_J1.mkdir(parents=True, exist_ok=True)
    png_path = OUTPUT_J1 / "j1_identity_static_geometry_preview.png"
    svg_path = OUTPUT_J1 / "j1_identity_static_geometry_preview.svg"
    sample = plan_rows[:12]
    try:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Circle, Ellipse, Rectangle, RegularPolygon

        fig, axes = plt.subplots(3, 4, figsize=(10, 7), constrained_layout=True)
        for ax, row in zip(axes.flat, sample):
            params = json.loads(row["geometry_params"])
            shape = row["shape_type"]
            py_nm = float(row["p_y_nm"])
            ax.set_xlim(-PX_NM / 2, PX_NM / 2)
            ax.set_ylim(-py_nm / 2, py_nm / 2)
            ax.set_aspect("equal")
            ax.add_patch(Rectangle((-PX_NM / 2, -py_nm / 2), PX_NM, py_nm, fill=False, lw=0.8, color="0.35"))
            if shape == "circular_cylinder":
                ax.add_patch(Circle((0, 0), params["radius_nm"], color="#4c78a8", alpha=0.8))
            elif shape == "square_pillar":
                side = params["side_nm"]
                ax.add_patch(Rectangle((-side / 2, -side / 2), side, side, color="#f58518", alpha=0.8))
            elif shape == "regular_hexagon":
                ax.add_patch(RegularPolygon((0, 0), 6, radius=params["equivalent_diameter_nm"] / 2, color="#54a24b", alpha=0.8))
            elif shape == "regular_octagon":
                ax.add_patch(RegularPolygon((0, 0), 8, radius=params["equivalent_diameter_nm"] / 2, color="#b279a2", alpha=0.8))
            elif shape == "near_square_rectangle":
                ax.add_patch(Rectangle((-params["L_nm"] / 2, -params["W_nm"] / 2), params["L_nm"], params["W_nm"], color="#e45756", alpha=0.8))
            elif shape == "ellipse_near_circle":
                ax.add_patch(Ellipse((0, 0), params["major_nm"], params["minor_nm"], color="#72b7b2", alpha=0.8))
            ax.set_title(row["candidate_id"] + "\n" + shape, fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle("Stage10LP J1 identity-like setup-only geometry preview", fontsize=12)
        fig.savefig(png_path, dpi=160)
        plt.close(fig)
        return png_path
    except Exception:
        cells = []
        for idx, row in enumerate(sample):
            col = idx % 4
            r = idx // 4
            x0 = 20 + col * 180
            y0 = 30 + r * 170
            shape = row["shape_type"]
            params = json.loads(row["geometry_params"])
            body = f'<rect x="{x0}" y="{y0}" width="140" height="120" fill="none" stroke="#555" />'
            cx = x0 + 70
            cy = y0 + 60
            if shape == "circular_cylinder":
                body += f'<circle cx="{cx}" cy="{cy}" r="{params["radius_nm"]*0.35:.1f}" fill="#4c78a8" />'
            elif shape == "square_pillar":
                side = params["side_nm"] * 0.35
                body += f'<rect x="{cx-side/2:.1f}" y="{cy-side/2:.1f}" width="{side:.1f}" height="{side:.1f}" fill="#f58518" />'
            else:
                rad = max_footprint(shape, params) * 0.18
                body += f'<circle cx="{cx}" cy="{cy}" r="{rad:.1f}" fill="#54a24b" />'
            body += f'<text x="{x0}" y="{y0+140}" font-size="10">{row["candidate_id"]} {shape}</text>'
            cells.append(body)
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="560">' + "\n".join(cells) + "</svg>\n"
        svg_path.write_text(svg, encoding="utf-8")
        return svg_path


def write_j1_results_smoke(plan_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [
        row for row in plan_rows
        if row["p_y_nm"] == 432 and row["height_nm"] == 500 and row["shape_type"] in {"circular_cylinder", "square_pillar", "regular_hexagon"}
    ][:3]
    phases = [5.0, 62.0, 119.0]
    results: list[dict[str, Any]] = []
    for row, phase in zip(selected, phases):
        tx_amp = 0.62
        ty_amp = 0.60
        tx_phase = phase
        ty_phase = phase + 4.0
        retardance = wrap180(ty_phase - tx_phase)
        retardance_to_identity = min(abs(retardance), abs(360.0 - abs(retardance)))
        amp_balance = min(tx_amp, ty_amp) / max(tx_amp, ty_amp)
        t_mean = 0.5 * (tx_amp**2 + ty_amp**2)
        common_phase = wrap360(0.5 * (tx_phase + ty_phase))
        score = 100.0 * (0.35 * amp_balance + 0.30 * min(t_mean / 0.5, 1.0) + 0.35 * max(0.0, 1.0 - retardance_to_identity / 30.0))
        out = {
            "candidate_id": row["candidate_id"],
            "shape_type": row["shape_type"],
            "geometry_params": row["geometry_params"],
            "material": row["material"],
            "lambda_nm": row["lambda_nm"],
            "p_x_nm": row["p_x_nm"],
            "p_y_nm": row["p_y_nm"],
            "height_nm": row["height_nm"],
            "tx_amp": f"{tx_amp:.6f}",
            "ty_amp": f"{ty_amp:.6f}",
            "tx_phase_deg": f"{tx_phase:.6f}",
            "ty_phase_deg": f"{ty_phase:.6f}",
            "retardance_deg": f"{retardance:.6f}",
            "retardance_to_identity_deg": f"{retardance_to_identity:.6f}",
            "amp_balance": f"{amp_balance:.6f}",
            "T_mean": f"{t_mean:.6f}",
            "common_phase_deg": f"{common_phase:.6f}",
            "identity_like_score": f"{score:.6f}",
            "result_csv": "mock_smoke_only_no_lumerical_run",
            "status": "mock_smoke_identity_like",
        }
        results.append(out)
    fieldnames = [
        "candidate_id", "shape_type", "geometry_params", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
        "tx_amp", "ty_amp", "tx_phase_deg", "ty_phase_deg", "retardance_deg", "retardance_to_identity_deg",
        "amp_balance", "T_mean", "common_phase_deg", "identity_like_score", "result_csv", "status",
    ]
    write_csv(OUTPUT_J1 / "j1_identity_results.csv", results, fieldnames)
    return results


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def classify_j2_source(path: Path, row: dict[str, str]) -> str:
    text = str(path).lower() + " " + " ".join(str(v).lower() for v in row.values())
    wavelength = safe_float(row.get("lambda_nm") or row.get("wavelength_nm"), 450.0 if "450" in text or "blue" in text else float("nan"))
    period = safe_float(row.get("period_nm") or row.get("p_x_nm"), 348.0 if "p348" in text else (432.0 if "p432" in text or "blue10k6" in text else float("nan")))
    height = safe_float(row.get("height_nm"), 500.0 if "h500" in text else float("nan"))
    if not math.isnan(wavelength) and abs(wavelength - 450.0) > 1e-6:
        return "reusable_seed_only"
    if not math.isnan(period) and abs(period - 432.0) > 1e-6:
        return "reusable_seed_only"
    if not math.isnan(height) and height not in HEIGHT_VALUES_NM:
        return "reusable_seed_only"
    if "phase_delay" in path.name.lower() or "jones_role" in text or "hwp" in text:
        if (not math.isnan(period)) and abs(period - 432.0) <= 1e-6:
            return "reusable_final"
        return "reusable_seed_only"
    return "incompatible"


def build_j2_inventory() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    csv_paths = sorted((REPO_ROOT / "outputs").glob("**/*.csv")) if (REPO_ROOT / "outputs").exists() else []
    seen: set[str] = set()
    for path in csv_paths:
        name = path.name.lower()
        if not any(token in name for token in ["phase_delay", "jones_role", "xy_sweep_results", "results"]):
            continue
        for idx, row in enumerate(read_csv(path)[:80]):
            case_id = row.get("case_id") or path.parent.name
            key = f"{path}|{case_id}|{idx}"
            if key in seen:
                continue
            seen.add(key)
            status = classify_j2_source(path, row)
            if status == "incompatible" and len(rows) > 120:
                continue
            length = row.get("length_nm") or row.get("L_nm") or ""
            width = row.get("width_nm") or row.get("W_nm") or ""
            height = row.get("height_nm") or ("500" if "h500" in str(path).lower() else "")
            period = row.get("period_nm") or row.get("p_x_nm") or ("348" if "p348" in str(path).lower() else "")
            tx_amp = row.get("tx_amp") or row.get("amp_x") or ""
            ty_amp = row.get("ty_amp") or row.get("amp_y") or ""
            tx_phase = row.get("tx_phase_deg") or row.get("phase_x_deg") or ""
            ty_phase = row.get("ty_phase_deg") or row.get("phase_y_deg") or ""
            common_phase = row.get("common_phase_deg") or ""
            rows.append(
                {
                    "candidate_id": f"J2_{len(rows)+1:04d}",
                    "geometry_params": json_dumps({"case_id": case_id, "length_nm": length, "width_nm": width, "height_nm": height, "period_nm": period}),
                    "tx_amp": tx_amp,
                    "ty_amp": ty_amp,
                    "tx_phase_deg": tx_phase,
                    "ty_phase_deg": ty_phase,
                    "retardance_to_hwp_deg": row.get("hwp_role_error_deg") or row.get("retardance_to_hwp_deg") or "",
                    "amp_balance": row.get("amp_balance") or row.get("amp_balance_from_power") or "",
                    "T_mean": row.get("T_mean") or row.get("trans_mean") or "",
                    "common_phase_deg": common_phase,
                    "hwp_like_score": row.get("hwp_like_score") or row.get("role_score_no_common") or "",
                    "source_result_csv": str(path.relative_to(REPO_ROOT)),
                    "reusable_status": status,
                }
            )
            if len(rows) >= 180:
                break
        if len(rows) >= 180:
            break
    if not rows:
        rows = mock_j2_rows(prefix_status="reusable_seed_only")
    return rows


def mock_j2_rows(prefix_status: str = "mock_for_smoke") -> list[dict[str, Any]]:
    phases = [3.0, 64.0, 121.0]
    out = []
    for idx, phase in enumerate(phases, start=1):
        out.append(
            {
                "candidate_id": f"J2MOCK_{idx:02d}",
                "geometry_params": json_dumps({"L_nm": 180 + 20 * idx, "W_nm": 90 + 5 * idx, "height_nm": 500, "period_nm": 432}),
                "tx_amp": "0.610000",
                "ty_amp": "0.590000",
                "tx_phase_deg": f"{phase:.6f}",
                "ty_phase_deg": f"{wrap360(phase + 180.0):.6f}",
                "retardance_to_hwp_deg": "5.000000",
                "amp_balance": "0.967213",
                "T_mean": "0.360100",
                "common_phase_deg": f"{phase:.6f}",
                "hwp_like_score": "82.000000",
                "source_result_csv": "mock_smoke_only_no_lumerical_run",
                "reusable_status": prefix_status,
            }
        )
    return out


def numeric_or_default(text: Any, default: float) -> float:
    x = safe_float(text)
    return default if math.isnan(x) else x


def build_pair_candidates(j1_rows: list[dict[str, Any]], j2_inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable_j2 = [r for r in j2_inventory if r.get("reusable_status") in {"reusable_final", "reusable_seed_only"}]
    usable_j2 = [r for r in usable_j2 if str(r.get("common_phase_deg", "")).strip()]
    if len(usable_j2) < 3:
        usable_j2 = mock_j2_rows()
    usable_j2 = usable_j2[:3]
    rows: list[dict[str, Any]] = []
    pair_id = 1
    for j1 in j1_rows[:3]:
        for j2 in usable_j2:
            a1 = numeric_or_default(j1.get("tx_amp"), math.sqrt(numeric_or_default(j1.get("T_mean"), 0.35)))
            a2 = numeric_or_default(j2.get("tx_amp"), math.sqrt(numeric_or_default(j2.get("T_mean"), 0.35)))
            p1 = numeric_or_default(j1.get("common_phase_deg"), 0.0)
            p2 = numeric_or_default(j2.get("common_phase_deg"), p1)
            phase_actual = wrap360(0.5 * (p1 + p2))
            target_bin = min(PHASE_BINS_DEG, key=lambda b: circular_error_deg(phase_actual, b))
            phase_err = circular_error_deg(phase_actual, target_bin)
            phi = math.radians(wrap180(p2 - p1))
            target_x = abs(complex(a1, 0) + a2 * complex(math.cos(phi), math.sin(phi)))
            leak_y = abs(complex(a1, 0) - a2 * complex(math.cos(phi), math.sin(phi)))
            ratio = target_x / max(leak_y, 1e-9)
            amp_match = abs(a1 - a2) / max(a1, a2, 1e-9)
            common_match = circular_error_deg(p1, p2)
            geometry_gap = 26.70
            geometry_margin = 0.5 * (PX_NM - 190.0)
            rows.append(
                {
                    "pair_id": f"LPAIR_{pair_id:04d}",
                    "phase_bin_target_deg": target_bin,
                    "phase_bin_actual_deg": f"{phase_actual:.6f}",
                    "phase_error_deg": f"{phase_err:.6f}",
                    "J1_candidate_id": j1["candidate_id"],
                    "J1_shape_type": j1["shape_type"],
                    "J1_geometry": j1["geometry_params"],
                    "J2_candidate_id": j2["candidate_id"],
                    "J2_geometry": j2["geometry_params"],
                    "amp_match_error": f"{amp_match:.6f}",
                    "common_phase_match_error_deg": f"{common_match:.6f}",
                    "predicted_target_x": f"{target_x:.6f}",
                    "predicted_leak_y": f"{leak_y:.6f}",
                    "predicted_ratio": f"{ratio:.6f}",
                    "geometry_gap_nm": f"{geometry_gap:.6f}",
                    "geometry_margin_nm": f"{geometry_margin:.6f}",
                    "reusable_status": j2.get("reusable_status", ""),
                    "result_paths": json_dumps({"j1_result": "outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_results.csv", "j2_source": j2.get("source_result_csv", "")}),
                }
            )
            pair_id += 1
    rows.sort(key=lambda r: (float(r["phase_error_deg"]), float(r["amp_match_error"]), -float(r["predicted_ratio"])))
    return rows


def write_summary(plan_rows: list[dict[str, Any]], j1_results: list[dict[str, Any]], j2_rows: list[dict[str, Any]], pair_rows: list[dict[str, Any]], preview: Path) -> None:
    shape_counts: dict[str, int] = {}
    for row in plan_rows:
        shape_counts[row["shape_type"]] = shape_counts.get(row["shape_type"], 0) + 1
    j2_counts = {"reusable_final": 0, "reusable_seed_only": 0, "incompatible": 0, "mock_for_smoke": 0}
    for row in j2_rows:
        status = str(row.get("reusable_status", "incompatible"))
        j2_counts[status] = j2_counts.get(status, 0) + 1
    OUTPUT_J1.mkdir(parents=True, exist_ok=True)
    (OUTPUT_J1 / "j1_identity_summary.md").write_text(
        "\n".join(
            [
                "# Stage10LP J1 Identity-Like Shape Scan",
                "",
                "Status: setup-only plan plus mock smoke rows. No Lumerical/FDTD run was launched.",
                f"Plan rows: {len(plan_rows)}",
                "Supported shape_type: " + ", ".join(sorted(shape_counts)),
                "Shape counts: " + json_dumps(shape_counts),
                f"Smoke J1 result rows: {len(j1_results)}",
                f"Static preview: {preview.relative_to(REPO_ROOT).as_posix()}",
                "",
                "Early gate to apply after real extraction: amp_balance >= 0.75, T_mean >= 0.30 or 0.35, retardance_to_identity_deg <= 30 broad / <= 15 strict.",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    phase_counts: dict[str, int] = {}
    for row in pair_rows:
        key = str(row["phase_bin_target_deg"])
        phase_counts[key] = phase_counts.get(key, 0) + 1
    OUTPUT_PAIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_PAIR / "lp_phase_bin_summary.md").write_text(
        "\n".join(
            [
                "# Stage10LP LP-APCD Pairing Smoke Summary",
                "",
                "Status: smoke test only. Pairing uses mock J1 rows and existing or mock J2 rows to validate columns, scores, and phase-bin grouping.",
                f"Pair rows: {len(pair_rows)}",
                "Phase-bin counts: " + json_dumps(phase_counts),
                "J2 reusable_status counts: " + json_dumps(j2_counts),
                "",
                "Do not interpret these smoke rows as physically realized LP phase bins.",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_PAIR / "lp_pairing_static_validation.md").write_text(
        "\n".join(
            [
                "# LP Pairing Static Validation",
                "",
                "- No full K=6 FDTD was launched.",
                "- No Lumerical API call was made.",
                "- Pairing approximation uses J_dimer = J1 + J2 only as a ranking scaffold.",
                "- Geometry gap uses the current D190 repaired baseline placeholder until real pair placement is evaluated.",
                "- LP phase ramp should come from propagation/resonance/J1-J2 common phase matching, not PSHE or pure PB phase.",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_PAIR / "lp_k6_layout_topview.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="180">\n'
        '<text x="20" y="24" font-size="16">Stage10LP K=6 layout placeholder: phase bins 0,60,120,180,240,300 deg</text>\n'
        + "\n".join(
            f'<rect x="{40+i*130}" y="60" width="100" height="70" fill="#dbeafe" stroke="#1d4ed8"/><text x="{58+i*130}" y="100" font-size="14">{phase} deg</text>'
            for i, phase in enumerate(PHASE_BINS_DEG)
        )
        + "\n</svg>\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Stage10LP J1 identity scan and LP pairing smoke outputs without Lumerical.")
    parser.add_argument("--smoke", action="store_true", help="Generate mock J1 rows and LP pairing smoke outputs.")
    args = parser.parse_args()

    plan_rows = build_j1_plan()
    plan_path = OUTPUT_J1 / "j1_identity_plan.csv"
    write_csv(plan_path, plan_rows)
    write_j1_config(CONFIG_DIR / "stage10lp_j1_identity_shape_scan.yaml", plan_path)
    preview = write_preview(plan_rows)

    j1_results = write_j1_results_smoke(plan_rows) if args.smoke else []
    j2_rows = build_j2_inventory()
    j2_fields = [
        "candidate_id", "geometry_params", "tx_amp", "ty_amp", "tx_phase_deg", "ty_phase_deg",
        "retardance_to_hwp_deg", "amp_balance", "T_mean", "common_phase_deg", "hwp_like_score",
        "source_result_csv", "reusable_status",
    ]
    write_csv(OUTPUT_PAIR / "j2_reuse_inventory.csv", j2_rows, j2_fields)

    pair_rows: list[dict[str, Any]] = []
    if args.smoke:
        pair_rows = build_pair_candidates(j1_results, j2_rows)
        pair_fields = [
            "pair_id", "phase_bin_target_deg", "phase_bin_actual_deg", "phase_error_deg",
            "J1_candidate_id", "J1_shape_type", "J1_geometry", "J2_candidate_id", "J2_geometry",
            "amp_match_error", "common_phase_match_error_deg", "predicted_target_x", "predicted_leak_y",
            "predicted_ratio", "geometry_gap_nm", "geometry_margin_nm", "reusable_status", "result_paths",
        ]
        write_csv(OUTPUT_PAIR / "lp_pair_candidates.csv", pair_rows, pair_fields)
    write_summary(plan_rows, j1_results, j2_rows, pair_rows, preview)

    counts: dict[str, int] = {}
    for row in j2_rows:
        status = str(row.get("reusable_status", "incompatible"))
        counts[status] = counts.get(status, 0) + 1
    print(f"j1_plan_count={len(plan_rows)}")
    print("shape_types=" + ",".join(sorted({row["shape_type"] for row in plan_rows})))
    print("j2_inventory_counts=" + json_dumps(counts))
    print(f"lp_pair_candidates={len(pair_rows)}")
    print(f"preview={preview.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
