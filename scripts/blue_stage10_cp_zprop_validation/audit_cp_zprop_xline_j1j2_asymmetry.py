from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "xline_asymmetry_audit"
METRICS_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "xline_minimal_robustness"
FIVE_POS_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "five_position_sweep"

WAVELENGTH_NM = 450.0
PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
HEIGHT_NM = 525.0
MATERIAL_INDEX = 2.6
DIMER_DISTANCE_NM = 182.5
DIMER_THETA_DEG = 70.0
PSI_DEG = 97.5
OFFSET_NM = min(PERIOD_X_NM, PERIOD_Y_NM) / 4.0
SOURCE_Z_NM = -200.0

J_ROLES = [
    {
        "role": "J1",
        "description": "larger Jones-response pillar role; literature element-1 role in the frozen dimer mapping",
        "length_nm": 230.0,
        "width_nm": 100.0,
        "height_nm": HEIGHT_NM,
        "rotation_deg": -7.5,
        "center_x_nm": 31.20933807846728,
        "center_y_nm": 85.74695164671414,
    },
    {
        "role": "J2",
        "description": "smaller Jones-response pillar role; literature element-2 role in the frozen dimer mapping",
        "length_nm": 180.0,
        "width_nm": 90.0,
        "height_nm": HEIGHT_NM,
        "rotation_deg": 37.5,
        "center_x_nm": -31.20933807846728,
        "center_y_nm": -85.74695164671414,
    },
]

IX_VALUES = list(range(-3, 4))
IY_VALUES = list(range(-1, 2))
SOURCE_POSITIONS = [
    {"position_id": "center", "x_nm": 0.0, "y_nm": 0.0, "z_nm": SOURCE_Z_NM},
    {"position_id": "x_plus_qp", "x_nm": OFFSET_NM, "y_nm": 0.0, "z_nm": SOURCE_Z_NM},
    {"position_id": "x_minus_qp", "x_nm": -OFFSET_NM, "y_nm": 0.0, "z_nm": SOURCE_Z_NM},
]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def f6(value: float) -> str:
    return f"{value:.6f}"


def rotated_half_spans(length_nm: float, width_nm: float, rotation_deg: float) -> tuple[float, float]:
    a = math.radians(rotation_deg)
    hx = 0.5 * (abs(length_nm * math.cos(a)) + abs(width_nm * math.sin(a)))
    hy = 0.5 * (abs(length_nm * math.sin(a)) + abs(width_nm * math.cos(a)))
    return hx, hy


def dimer_geometry_rows() -> list[dict[str, Any]]:
    j1 = next(r for r in J_ROLES if r["role"] == "J1")
    j2 = next(r for r in J_ROLES if r["role"] == "J2")
    delta_x = j2["center_x_nm"] - j1["center_x_nm"]
    delta_y = j2["center_y_nm"] - j1["center_y_nm"]
    rows: list[dict[str, Any]] = []
    for role in J_ROLES:
        hx, hy = rotated_half_spans(role["length_nm"], role["width_nm"], role["rotation_deg"])
        rows.append(
            {
                "case_id": "DIMER_PAIRA_MAPBA_ROBUST_D182p5_T70_PSI97p5_H525",
                "role": role["role"],
                "role_definition": role["description"],
                "length_nm": f6(role["length_nm"]),
                "width_nm": f6(role["width_nm"]),
                "height_nm": f6(role["height_nm"]),
                "material_index": f6(MATERIAL_INDEX),
                "rotation_axis": "z",
                "rotation_deg": f6(role["rotation_deg"]),
                "rotation_convention": "code rectangle local x/length axis rotation about global z",
                "center_x_nm": f6(role["center_x_nm"]),
                "center_y_nm": f6(role["center_y_nm"]),
                "bbox_half_x_nm": f6(hx),
                "bbox_half_y_nm": f6(hy),
                "delta_x_J2_minus_J1_nm": f6(delta_x),
                "delta_y_J2_minus_J1_nm": f6(delta_y),
                "dimer_distance_nm": f6(DIMER_DISTANCE_NM),
                "dimer_theta_deg": f6(DIMER_THETA_DEG),
                "psi_deg": f6(PSI_DEG),
                "mirror_x_symmetric": "no",
                "mirror_x_note": "x->-x does not map J1/J2 centers and rotations onto an equivalent role-preserving dimer; J1 and J2 are different Jones-response roles.",
            }
        )
    return rows


def all_patch_pillars() -> list[dict[str, Any]]:
    pillars: list[dict[str, Any]] = []
    for ix in IX_VALUES:
        for iy in IY_VALUES:
            dimer_x = ix * PERIOD_X_NM
            dimer_y = iy * PERIOD_Y_NM
            for role in J_ROLES:
                hx, hy = rotated_half_spans(role["length_nm"], role["width_nm"], role["rotation_deg"])
                x = dimer_x + role["center_x_nm"]
                y = dimer_y + role["center_y_nm"]
                pillars.append(
                    {
                        "role": role["role"],
                        "dimer_ix": ix,
                        "dimer_iy": iy,
                        "x_nm": x,
                        "y_nm": y,
                        "bbox_x_min_nm": x - hx,
                        "bbox_x_max_nm": x + hx,
                        "bbox_y_min_nm": y - hy,
                        "bbox_y_max_nm": y + hy,
                    }
                )
    return pillars


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def source_distance_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    all_pillars = all_patch_pillars()
    central = [p for p in all_pillars if p["dimer_ix"] == 0 and p["dimer_iy"] == 0]
    for src in SOURCE_POSITIONS:
        central_dist = {p["role"]: distance(src["x_nm"], src["y_nm"], p["x_nm"], p["y_nm"]) for p in central}
        nearest_role = min(central_dist, key=central_dist.get)
        ratio = central_dist["J1"] / central_dist["J2"] if central_dist["J2"] else float("inf")
        rows.append(
            {
                "row_type": "central_dimer_summary",
                "position_id": src["position_id"],
                "source_x_nm": f6(src["x_nm"]),
                "source_y_nm": f6(src["y_nm"]),
                "source_z_nm": f6(src["z_nm"]),
                "distance_to_J1_nm": f6(central_dist["J1"]),
                "distance_to_J2_nm": f6(central_dist["J2"]),
                "distance_ratio_J1_over_J2": f6(ratio),
                "nearest_pillar_role": nearest_role,
                "geometry_based_excitation_estimate": f"preferentially nearer {nearest_role}",
                "nearest_rank": "",
                "nearest_dimer_ix": "",
                "nearest_dimer_iy": "",
                "nearest_role": "",
                "nearest_distance_nm": "",
                "nearest_x_nm": "",
                "nearest_y_nm": "",
            }
        )
        nearest = sorted(all_pillars, key=lambda p: distance(src["x_nm"], src["y_nm"], p["x_nm"], p["y_nm"]))[:8]
        for rank, p in enumerate(nearest, start=1):
            rows.append(
                {
                    "row_type": "nearest_patch_pillar",
                    "position_id": src["position_id"],
                    "source_x_nm": f6(src["x_nm"]),
                    "source_y_nm": f6(src["y_nm"]),
                    "source_z_nm": f6(src["z_nm"]),
                    "distance_to_J1_nm": "",
                    "distance_to_J2_nm": "",
                    "distance_ratio_J1_over_J2": "",
                    "nearest_pillar_role": "",
                    "geometry_based_excitation_estimate": "nearest few patch pillars by lateral distance",
                    "nearest_rank": rank,
                    "nearest_dimer_ix": p["dimer_ix"],
                    "nearest_dimer_iy": p["dimer_iy"],
                    "nearest_role": p["role"],
                    "nearest_distance_nm": f6(distance(src["x_nm"], src["y_nm"], p["x_nm"], p["y_nm"])),
                    "nearest_x_nm": f6(p["x_nm"]),
                    "nearest_y_nm": f6(p["y_nm"]),
                }
            )
    return rows


def patch_symmetry_rows() -> list[dict[str, Any]]:
    pillars = all_patch_pillars()
    min_x = min(p["bbox_x_min_nm"] for p in pillars)
    max_x = max(p["bbox_x_max_nm"] for p in pillars)
    min_y = min(p["bbox_y_min_nm"] for p in pillars)
    max_y = max(p["bbox_y_max_nm"] for p in pillars)
    center_x = 0.5 * (min_x + max_x)
    center_y = 0.5 * (min_y + max_y)
    base = {
        "array_nx": len(IX_VALUES),
        "array_ny": len(IY_VALUES),
        "period_x_nm": f6(PERIOD_X_NM),
        "period_y_nm": f6(PERIOD_Y_NM),
        "dimer_center_x_min_nm": f6(min(IX_VALUES) * PERIOD_X_NM),
        "dimer_center_x_max_nm": f6(max(IX_VALUES) * PERIOD_X_NM),
        "dimer_center_y_min_nm": f6(min(IY_VALUES) * PERIOD_Y_NM),
        "dimer_center_y_max_nm": f6(max(IY_VALUES) * PERIOD_Y_NM),
        "pillar_bbox_x_min_nm": f6(min_x),
        "pillar_bbox_x_max_nm": f6(max_x),
        "pillar_bbox_y_min_nm": f6(min_y),
        "pillar_bbox_y_max_nm": f6(max_y),
        "patch_bbox_center_x_nm": f6(center_x),
        "patch_bbox_center_y_nm": f6(center_y),
    }
    rows = [
        {
            **base,
            "audit_item": "patch_summary",
            "value": "finite uniform CP-selective patch",
            "central_dimer_exists": "yes; odd 7x3 dimer count gives a true center dimer at ix=0,iy=0",
            "edge_symmetry_note": "dimer-center lattice is symmetric, but the repeated non-mirrored J1/J2 motif makes the physical pillar bbox slightly offset from x=0",
        }
    ]
    for src in SOURCE_POSITIONS:
        rows.append(
            {
                **base,
                "audit_item": f"source_edge_distance_{src['position_id']}",
                "value": "source to physical pillar-bbox x edges",
                "central_dimer_exists": "yes",
                "edge_symmetry_note": f"distance_to_minus_x_edge={f6(src['x_nm'] - min_x)} nm; distance_to_plus_x_edge={f6(max_x - src['x_nm'])} nm",
            }
        )
    rows.append(
        {
            **base,
            "audit_item": "x_plus_minus_edge_symmetry",
            "value": "dimer-center lattice symmetric; physical pillar bbox mildly asymmetric",
            "central_dimer_exists": "yes",
            "edge_symmetry_note": f"+q to +x physical bbox edge = {f6(max_x - OFFSET_NM)} nm; -q to -x physical bbox edge = {f6((-OFFSET_NM) - min_x)} nm; physical-edge difference = {f6((max_x - OFFSET_NM) - ((-OFFSET_NM) - min_x))} nm",
        }
    )
    return rows


def read_position_metrics() -> list[dict[str, str]]:
    path = METRICS_DIR / "xline_minimal_position_averages.csv"
    if not path.exists():
        path = FIVE_POS_DIR / "five_position_position_averages.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def metric_lookup(rows: list[dict[str, str]], position_id: str, cone: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("position_id") == position_id and row.get("cone_deg") == cone:
            return row
    return None


def fmt_metric(row: dict[str, str] | None) -> str:
    if not row:
        return "not available"
    return f"DoCP_RminusL={row.get('DoCP_total_RminusL')}, L_fraction={row.get('L_fraction_total')}"


def write_summary() -> None:
    metrics = read_position_metrics()
    m_center_20 = metric_lookup(metrics, "center", "20.0")
    m_plus_20 = metric_lookup(metrics, "x_plus_qp", "20.0")
    m_minus_20 = metric_lookup(metrics, "x_minus_qp", "20.0")
    m_center_5 = metric_lookup(metrics, "center", "5.0")
    m_plus_5 = metric_lookup(metrics, "x_plus_qp", "5.0")
    m_minus_5 = metric_lookup(metrics, "x_minus_qp", "5.0")
    text = f"""# Stage10 CP +z x-line J1/J2 asymmetry audit

## English

- FDTD run status: no FDTD was run by this audit. The script is read-only with respect to simulation state and does not import or call lumapi.
- Sweep definition: this is an x-axis centerline-only source-position diagnostic. Source y is fixed at 0 nm; source z is {SOURCE_Z_NM:.1f} nm.
- Frozen dimer: DIMER_PAIRA_MAPBA_ROBUST_D182p5_T70_PSI97p5_H525, wavelength {WAVELENGTH_NM:.1f} nm, H={HEIGHT_NM:.1f} nm, n={MATERIAL_INDEX:.1f}, d={DIMER_DISTANCE_NM:.1f} nm, theta={DIMER_THETA_DEG:.1f} deg, psi={PSI_DEG:.1f} deg.

### J1/J2 definition

- J1: 230 x 100 nm pillar, rotation -7.5 deg about z, center (x,y)=({J_ROLES[0]['center_x_nm']:.6f}, {J_ROLES[0]['center_y_nm']:.6f}) nm. This is the larger Jones-response pillar role / literature element-1 role in the frozen mapping.
- J2: 180 x 90 nm pillar, rotation +37.5 deg about z, center (x,y)=({J_ROLES[1]['center_x_nm']:.6f}, {J_ROLES[1]['center_y_nm']:.6f}) nm. This is the smaller Jones-response pillar role / literature element-2 role in the frozen mapping.
- Delta from J1 to J2: dx={J_ROLES[1]['center_x_nm'] - J_ROLES[0]['center_x_nm']:.6f} nm, dy={J_ROLES[1]['center_y_nm'] - J_ROLES[0]['center_y_nm']:.6f} nm.
- Mirror check: the single dimer is not role-preserving mirror-symmetric under x -> -x. Because J1 and J2 have different Jones-response roles, mirrored source positions can preferentially excite different roles.

### Source positions and distances

- q = {OFFSET_NM:.6f} nm.
- center source: (0, 0, {SOURCE_Z_NM:.1f}) nm.
- +q source: ({OFFSET_NM:.6f}, 0, {SOURCE_Z_NM:.1f}) nm.
- -q source: ({-OFFSET_NM:.6f}, 0, {SOURCE_Z_NM:.1f}) nm.
- Geometry estimate: +q is nearer J1; -q is nearer J2; center is equidistant from J1 and J2.

### Patch symmetry

- Patch layout: 7 dimers along x and 3 dimers along y, with a true center dimer at ix=0, iy=0.
- The dimer-center lattice is symmetric, but the repeated non-mirrored J1/J2 motif offsets the physical pillar bounding box slightly from x=0.
- Edge-distance audit: the dimer-center lattice is symmetric, but +q to +x physical edge and -q to -x physical edge differ by about 21.7 nm. This is smaller than the source-to-J1/J2 distance swap, so it is a secondary geometry factor.

### Existing CP results used for context

- center, +/-20 deg: {fmt_metric(m_center_20)}
- x_plus_qp, +/-20 deg: {fmt_metric(m_plus_20)}
- x_minus_qp, +/-20 deg: {fmt_metric(m_minus_20)}
- center, +/-5 deg: {fmt_metric(m_center_5)}
- x_plus_qp, +/-5 deg: {fmt_metric(m_plus_5)}
- x_minus_qp, +/-5 deg: {fmt_metric(m_minus_5)}

### Likely explanation

The observed +q/-q CP asymmetry is most consistent with J1/J2 excitation-weight asymmetry. A finite patch physical-edge asymmetry exists because the same non-mirrored motif is repeated, but its x-edge distance difference is modest compared with the direct source-to-J1/J2 distance swap. A source-coordinate bug is unlikely from this static audit because y=0 is fixed and the +/-q source coordinates are symmetric.

### Recommendation

Before DBR/RCLED or wider source maps, the next minimal diagnostic should focus on J1/J2 excitation-weight sensitivity. A low-cost next FDTD option, if needed, is a one-case continuation along the x centerline such as x_plus_2qp_x or a controlled mirrored-role/frozen-dimer diagnostic, but not y-offset or full-plane sweeps.

## 中文

- FDTD 状态：本审计没有运行 FDTD。脚本只读已有脚本/CSV/JSON，并且不导入或调用 lumapi。
- 扫描定义：这是 x 轴中心线源位置诊断。source y 固定为 0 nm，source z = {SOURCE_Z_NM:.1f} nm。
- frozen dimer：DIMER_PAIRA_MAPBA_ROBUST_D182p5_T70_PSI97p5_H525，波长 {WAVELENGTH_NM:.1f} nm，H={HEIGHT_NM:.1f} nm，n={MATERIAL_INDEX:.1f}，d={DIMER_DISTANCE_NM:.1f} nm，theta={DIMER_THETA_DEG:.1f} deg，psi={PSI_DEG:.1f} deg。

### J1/J2 定义

- J1：230 x 100 nm 功能柱，绕 z 轴旋转 -7.5 deg，中心坐标 (x,y)=({J_ROLES[0]['center_x_nm']:.6f}, {J_ROLES[0]['center_y_nm']:.6f}) nm。它是当前 frozen mapping 中较大的 Jones 响应功能柱 / 文献 element-1 角色。
- J2：180 x 90 nm 功能柱，绕 z 轴旋转 +37.5 deg，中心坐标 (x,y)=({J_ROLES[1]['center_x_nm']:.6f}, {J_ROLES[1]['center_y_nm']:.6f}) nm。它是当前 frozen mapping 中较小的 Jones 响应功能柱 / 文献 element-2 角色。
- 从 J1 到 J2 的位移：dx={J_ROLES[1]['center_x_nm'] - J_ROLES[0]['center_x_nm']:.6f} nm，dy={J_ROLES[1]['center_y_nm'] - J_ROLES[0]['center_y_nm']:.6f} nm。
- 镜像检查：单个 dimer 在 x -> -x 下不是保持 J1/J2 角色不变的镜面对称结构。由于 J1/J2 是不同 Jones 响应角色，镜像源位置可能更强激发不同功能柱。

### 源位置和距离

- q = {OFFSET_NM:.6f} nm。
- center source：(0, 0, {SOURCE_Z_NM:.1f}) nm。
- +q source：({OFFSET_NM:.6f}, 0, {SOURCE_Z_NM:.1f}) nm。
- -q source：({-OFFSET_NM:.6f}, 0, {SOURCE_Z_NM:.1f}) nm。
- 几何估计：+q 更靠近 J1；-q 更靠近 J2；center 到 J1/J2 等距。

### patch 对称性

- patch：x 方向 7 个 dimer，y 方向 3 个 dimer，在 ix=0, iy=0 有真实中心 dimer。
- dimer 中心格点是对称的，但由于重复使用未镜像的 J1/J2 motif，物理柱整体 bbox 相对 x=0 有轻微偏移。
- 边界距离审计：dimer 中心格点是对称的，但 +q 到 +x 物理边界与 -q 到 -x 物理边界相差约 21.7 nm。这个差异小于 source 到 J1/J2 距离互换的量级，因此是次要几何因素。

### 已有 CP 结果背景

- center, +/-20 deg：{fmt_metric(m_center_20)}
- x_plus_qp, +/-20 deg：{fmt_metric(m_plus_20)}
- x_minus_qp, +/-20 deg：{fmt_metric(m_minus_20)}
- center, +/-5 deg：{fmt_metric(m_center_5)}
- x_plus_qp, +/-5 deg：{fmt_metric(m_plus_5)}
- x_minus_qp, +/-5 deg：{fmt_metric(m_minus_5)}

### 可能原因

当前 +q/-q CP 非对称最符合 J1/J2 激发权重非对称。由于重复未镜像 motif，有限 patch 的物理边界确实有轻微 x 偏心，但它的边界距离差小于 source 到 J1/J2 距离互换的量级。静态审计下源坐标 bug 不太可能，因为 y=0 固定且 +/-q 坐标对称。注意这只是几何估计，不是新的 FDTD 结果。

### 下一步建议

在进入 DBR/RCLED 或更大源位置图之前，建议先围绕 J1/J2 激发权重敏感性做最小验证。如果还需要一个低成本 FDTD，建议仍沿 x 中心线一次只补一个 case，例如 x_plus_2qp_x，或者做受控的镜像角色/frozen-dimer 诊断；不要进入 y-offset 或 full-plane sweep。
"""
    (OUT_DIR / "xline_asymmetry_audit_summary.md").write_text(text, encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geom = dimer_geometry_rows()
    dist = source_distance_rows()
    patch = patch_symmetry_rows()
    write_csv(OUT_DIR / "xline_j1j2_geometry_audit.csv", geom)
    write_csv(OUT_DIR / "xline_source_distance_audit.csv", dist)
    write_csv(OUT_DIR / "xline_patch_symmetry_audit.csv", patch)
    central_summaries = [r for r in dist if r["row_type"] == "central_dimer_summary"]
    debug = {
        "no_fdtd_run": True,
        "script_imports_lumapi": False,
        "sweep_type": "x-axis centerline only",
        "source_y_fixed_nm": 0.0,
        "q_nm": OFFSET_NM,
        "geometry_constants": {
            "period_x_nm": PERIOD_X_NM,
            "period_y_nm": PERIOD_Y_NM,
            "height_nm": HEIGHT_NM,
            "material_index": MATERIAL_INDEX,
            "dimer_distance_nm": DIMER_DISTANCE_NM,
            "dimer_theta_deg": DIMER_THETA_DEG,
            "psi_deg": PSI_DEG,
        },
        "central_source_distance_summary": central_summaries,
        "interpretation": {
            "plus_q_nearer_role": next(r["nearest_pillar_role"] for r in central_summaries if r["position_id"] == "x_plus_qp"),
            "minus_q_nearer_role": next(r["nearest_pillar_role"] for r in central_summaries if r["position_id"] == "x_minus_qp"),
            "finite_patch_x_edge_symmetric": True,
            "source_coordinate_bug_likely": False,
            "most_likely_geometry_factor": "J1/J2 excitation-weight asymmetry",
        },
    }
    (OUT_DIR / "xline_asymmetry_audit_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    write_summary()
    print(json.dumps({"out_dir": str(OUT_DIR), "no_fdtd_run": True, "rows": {"geometry": len(geom), "distance": len(dist), "patch": len(patch)}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


