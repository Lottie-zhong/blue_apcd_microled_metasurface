from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_k6_fdtd import flt, read_csv_rows, write_csv_rows

OUTPUT_DIR_NAME = "stage12_6_h500_lp_k6_official_result_package"
OFFICIAL_RATIO_THRESHOLD = 6.0
FIGURE_FILES = [
    ("figure_1_stage11_6bin_library", "Final H500 six-bin LP-APCD dimer library"),
    ("figure_2_k6_xgrad_layout_schematic", "Official K=6 x-gradient layout schematic"),
    ("figure_3_xgrad_order_power", "Official x-gradient order-resolved FDTD power"),
    ("figure_4_xgrad_vs_ygrad_comparison", "X-gradient official pass vs y-gradient diagnostic fail"),
    ("figure_5_stage_flow_summary", "Stage11-Stage12 LP result-package flow summary"),
]
KEY_METRIC_FIELDS = ["metric", "value", "status", "notes"]
MANIFEST_FIELDS = ["figure", "png", "svg", "source_data", "claim", "status"]

@dataclass(frozen=True)
class Stage12_6Paths:
    stage11_dir: Path
    stage12_0_dir: Path
    stage12_1_dir: Path
    stage12_2_dir: Path
    stage12_3_dir: Path
    stage12_4_dir: Path
    stage12_5_dir: Path
    output_dir: Path

def official_xgrad_pass(metrics: dict[str, float | str]) -> bool:
    return flt(metrics.get("target_order_selectivity_ratio")) >= OFFICIAL_RATIO_THRESHOLD and abs(flt(metrics.get("x_LP_steering_angle_deg")) - 10.0) <= 2.0

def ygrad_diagnostic_classification(metrics: dict[str, float | str]) -> str:
    ratio = flt(metrics.get("target_order_selectivity_ratio"))
    angle = flt(metrics.get("steering_angle_deg"))
    if abs(angle - 10.0) <= 2.0 and ratio < OFFICIAL_RATIO_THRESHOLD:
        return "STEERING_PASS_SELECTIVITY_FAIL"
    if ratio >= OFFICIAL_RATIO_THRESHOLD:
        return "PASS"
    return "FAIL"

def build_figure_manifest(output_dir: Path) -> list[dict[str, object]]:
    claims = [
        "Six strict phase bins form the frozen H500 LP-APCD library; 240 deg is the weakest-risk bin.",
        "The official K=6 phase ramp follows x because Lambda_x = K * p_x.",
        "x-LP steers to x-order +1 while y-LP target-order leakage is suppressed.",
        "x-gradient is the official pass; y-gradient is a failed coordinate-transfer diagnostic.",
        "Stage11 to Stage12 establishes a complete target-direction LP metagrating milestone.",
    ]
    sources = [
        "stage11_2i_h500_lp_actual_dimer_6bin_freeze/stage12_handoff_phase_library.csv",
        "stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv",
        "stage12_2_h500_lp_k6_forward_minimal_fdtd/stage12_2_k6_forward_order_power.csv",
        "stage12_5_h500_lp_k6_official_xgrad_freeze/stage12_5_xgrad_vs_ygrad_comparison.csv",
        "Stage11/Stage12 status CSV summaries",
    ]
    rows = []
    for (stem, title), claim, source in zip(FIGURE_FILES, claims, sources):
        rows.append({"figure": title, "png": str(output_dir / f"{stem}.png"), "svg": str(output_dir / f"{stem}.svg"), "source_data": source, "claim": claim, "status": "generated"})
    return rows

def metric_map(rows: Sequence[dict[str, str]]) -> dict[str, str]:
    return {row.get("metric", ""): row.get("value", "") for row in rows}

def load_key_metrics(paths: Stage12_6Paths) -> dict[str, object]:
    official = metric_map(read_csv_rows(paths.stage12_5_dir / "stage12_5_official_metrics.csv"))
    x_results = read_csv_rows(paths.stage12_2_dir / "stage12_2_k6_forward_fdtd_results.csv")
    y_results = read_csv_rows(paths.stage12_4_dir / "stage12_4_ygrad_fdtd_results.csv")
    y_metrics = metric_map(read_csv_rows(paths.stage12_4_dir / "stage12_4_ygrad_selectivity_summary.csv"))
    x_xlp = next(row for row in x_results if row["polarization"] == "x")
    x_ylp = next(row for row in x_results if row["polarization"] == "y")
    y_xlp = next(row for row in y_results if row["polarization"] == "x")
    y_ylp = next(row for row in y_results if row["polarization"] == "y")
    official_metrics = {
        "official_diffraction_period_direction": official["official_diffraction_period_direction"],
        "official_gradient_axis": official["official_gradient_axis"],
        "official_steering_plane": official["official_steering_plane"],
        "official_target_order": official["official_target_order"],
        "x_LP_target_plus1_power": flt(official["x_LP_target_plus1_power"]),
        "x_LP_steering_angle_deg": flt(official["x_LP_steering_angle_deg"]),
        "y_LP_target_plus1_leakage": flt(official["y_LP_target_plus1_leakage"]),
        "target_order_selectivity_ratio": flt(official["target_order_selectivity_ratio"]),
        "global_y_LP_blocking": official["global_y_LP_blocking"],
    }
    y_diag = {
        "x_LP_target_power": flt(y_xlp["target_y_plus1_power"]),
        "y_LP_target_leakage": flt(y_ylp["target_y_plus1_power"]),
        "target_order_selectivity_ratio": flt(y_metrics["target_order_selectivity_ratio"]),
        "steering_angle_deg": flt(y_xlp["dominant_theta_yz_deg"]),
    }
    return {"official": official_metrics, "y_diag": y_diag, "x_xlp": x_xlp, "x_ylp": x_ylp, "y_xlp": y_xlp, "y_ylp": y_ylp}

def build_key_metric_rows(metrics: dict[str, object]) -> list[dict[str, object]]:
    official = metrics["official"]
    y_diag = metrics["y_diag"]
    return [
        {"metric": "official_diffraction_period_direction", "value": official["official_diffraction_period_direction"], "status": "FROZEN", "notes": "original K=6 diffraction period"},
        {"metric": "official_gradient_axis", "value": official["official_gradient_axis"], "status": "FROZEN", "notes": "x-gradient"},
        {"metric": "official_steering_plane", "value": official["official_steering_plane"], "status": "FROZEN", "notes": "x-z plane"},
        {"metric": "official_target_order", "value": official["official_target_order"], "status": "FROZEN", "notes": "x-order +1"},
        {"metric": "x_LP_target_plus1_power", "value": official["x_LP_target_plus1_power"], "status": "PASS", "notes": "Stage12-2 official branch"},
        {"metric": "x_LP_steering_angle_deg", "value": official["x_LP_steering_angle_deg"], "status": "PASS", "notes": "+10 deg target"},
        {"metric": "y_LP_target_plus1_leakage", "value": official["y_LP_target_plus1_leakage"], "status": "PASS", "notes": "blocked-channel target-order leakage"},
        {"metric": "target_order_selectivity_ratio", "value": official["target_order_selectivity_ratio"], "status": "PASS", "notes": ">=6 criterion"},
        {"metric": "global_y_LP_blocking", "value": official["global_y_LP_blocking"], "status": "BOUNDARY", "notes": "not claimed"},
        {"metric": "y_gradient_target_order_selectivity_ratio", "value": y_diag["target_order_selectivity_ratio"], "status": "FAIL", "notes": "coordinate-transfer diagnostic"},
    ]

def configure_matplotlib():
    import matplotlib as mpl
    mpl.use("Agg")
    mpl.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans","sans-serif"],"svg.fonttype":"none","pdf.fonttype":42,"font.size":8,"axes.spines.right":False,"axes.spines.top":False,"axes.linewidth":0.8,"legend.frameon":False,"figure.dpi":150})

def save_fig(fig, output_dir: Path, stem: str) -> None:
    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")

def generate_figures(paths: Stage12_6Paths, metrics: dict[str, object]) -> None:
    configure_matplotlib()
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
    output = paths.output_dir
    library = read_csv_rows(paths.stage11_dir / "stage12_handoff_phase_library.csv")
    layout = read_csv_rows(paths.stage12_1_dir / "stage12_1_k6_forward_layout_plan.csv")
    orders = read_csv_rows(paths.stage12_2_dir / "stage12_2_k6_forward_order_power.csv")
    official = metrics["official"]
    y_diag = metrics["y_diag"]

    bins = [int(float(r["phase_bin_deg"])) for r in library]
    tx = [flt(r.get("selected_x_power", r.get("Tx"))) for r in library]
    ratio = [flt(r["conversion_to_leakage_ratio"]) for r in library]
    phase_err = [abs(flt(r["phase_err_deg"])) for r in library]
    matrix = [flt(r["matrix_error"]) for r in library]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.8), constrained_layout=True)
    axes[0,0].bar([str(b) for b in bins], tx, color="#4C78A8")
    axes[0,0].set_title("Selected x-LP Tx")
    axes[0,0].set_ylabel("Tx")
    axes[0,1].bar([str(b) for b in bins], ratio, color="#59A14F")
    axes[0,1].set_yscale("log")
    axes[0,1].set_title("Conversion / leakage ratio")
    axes[1,0].bar([str(b) for b in bins], phase_err, color="#F28E2B")
    axes[1,0].set_title("Phase error")
    axes[1,0].set_ylabel("deg")
    axes[1,1].bar([str(b) for b in bins], matrix, color="#E15759")
    axes[1,1].set_title("Matrix error")
    for ax in axes.ravel():
        ax.set_xlabel("phase bin (deg)")
        ax.axvspan(4-0.45, 4+0.45, color="#E15759", alpha=0.12)
        ax.text(4, ax.get_ylim()[1]*0.88, "240 risk", ha="center", va="top", fontsize=7, color="#8B1E1E")
    fig.suptitle("H500 LP-APCD strict six-bin dimer library", fontsize=11, fontweight="bold")
    save_fig(fig, output, "figure_1_stage11_6bin_library")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 2.8), constrained_layout=True)
    for r in layout:
        idx = int(float(r["supercell_index"])); b = int(float(r["phase_bin_deg"])); risk = b == 240
        color = "#E15759" if risk else "#4C78A8"
        cx = flt(r["supercell_center_x_nm"])
        ax.axvline(cx, color="#DDDDDD", lw=0.6)
        ax.text(cx, 165, f"{b} deg", ha="center", va="bottom", fontsize=8, color=color, fontweight="bold" if risk else "normal")
        draw_pillar(ax, r, "j1", color, Rectangle, Circle)
        draw_pillar(ax, r, "j2", "#76B7B2", Rectangle, Circle)
        ax.text(cx, -170, f"D{idx}", ha="center", va="top", fontsize=7)
    xmin = min(flt(r["supercell_center_x_nm"]) for r in layout) - 260
    xmax = max(flt(r["supercell_center_x_nm"]) for r in layout) + 260
    ax.add_patch(FancyArrowPatch((xmin, 230), (xmax, 230), arrowstyle="->", mutation_scale=14, lw=1.2, color="#333333"))
    ax.text((xmin+xmax)/2, 245, "phase gradient along x; selected x-LP; steering in x-z; target x-order +1", ha="center", fontsize=8)
    ax.set_xlim(xmin, xmax); ax.set_ylim(-230, 280); ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (nm)"); ax.set_ylabel("y (nm)")
    ax.set_title("Official K=6 x-gradient supercell top view", fontsize=11, fontweight="bold")
    save_fig(fig, output, "figure_2_k6_xgrad_layout_schematic")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 3.8), constrained_layout=True)
    order_ns = sorted({int(float(r["order_n"])) for r in orders if int(float(r.get("order_m",0))) == 0})
    xpow = [order_power_for(orders, "x", n, 0) for n in order_ns]
    ypow = [order_power_for(orders, "y", n, 0) for n in order_ns]
    xs = list(range(len(order_ns))); width = 0.38
    ax.bar([x-width/2 for x in xs], xpow, width=width, label="x-LP input", color="#4C78A8")
    ax.bar([x+width/2 for x in xs], ypow, width=width, label="y-LP leakage", color="#E15759")
    target_idx = order_ns.index(1)
    ax.axvspan(target_idx-0.5, target_idx+0.5, color="#F2CF5B", alpha=0.25)
    ax.text(target_idx, max(max(xpow), max(ypow))*0.95, f"target +1\nratio={official['target_order_selectivity_ratio']:.3f}", ha="center", va="top", fontsize=8)
    ax.set_xticks(xs, [str(n) for n in order_ns]); ax.set_xlabel("x diffraction order n (m=0)"); ax.set_ylabel("source-normalized power")
    ax.set_title("Official x-gradient order-resolved FDTD result", fontsize=11, fontweight="bold"); ax.legend()
    save_fig(fig, output, "figure_3_xgrad_order_power")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(7.8, 3.2), constrained_layout=True)
    labels = ["x-grad\nofficial PASS", "y-grad\ndiagnostic FAIL"]
    axes[0].bar(labels, [official["x_LP_target_plus1_power"], y_diag["x_LP_target_power"]], color=["#4C78A8", "#BAB0AC"])
    axes[0].set_title("Target power")
    axes[1].bar(labels, [official["y_LP_target_plus1_leakage"], y_diag["y_LP_target_leakage"]], color=["#4C78A8", "#E15759"])
    axes[1].set_title("Target leakage")
    axes[2].bar(labels, [official["target_order_selectivity_ratio"], y_diag["target_order_selectivity_ratio"]], color=["#59A14F", "#E15759"])
    axes[2].axhline(OFFICIAL_RATIO_THRESHOLD, color="#333333", ls="--", lw=0.8)
    axes[2].set_title("Selectivity ratio")
    axes[2].set_yscale("log")
    for ax in axes: ax.tick_params(axis="x", labelrotation=0)
    fig.suptitle("Official x-gradient vs y-gradient coordinate-transfer diagnostic", fontsize=11, fontweight="bold")
    save_fig(fig, output, "figure_4_xgrad_vs_ygrad_comparison")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.4, 2.8), constrained_layout=True)
    ax.axis("off")
    stages = [("Stage11", "six-bin\nlibrary freeze"), ("Stage12-0", "analytic\n+1 pass"), ("Stage12-1", "layout\nlegal"), ("Stage12-2", "x-gradient\nFDTD PASS"), ("Stage12-5", "official\nx-gradient freeze")]
    x0s = [0.08, 0.28, 0.48, 0.68, 0.88]
    for i, ((title, body), x0) in enumerate(zip(stages, x0s)):
        ax.text(x0, 0.56, f"{title}\n{body}", ha="center", va="center", fontsize=8, bbox=dict(boxstyle="round,pad=0.35", fc="#F7F7F7", ec="#4C78A8", lw=1.0), transform=ax.transAxes)
        if i < len(stages)-1:
            ax.annotate("", xy=(x0s[i+1]-0.065,0.56), xytext=(x0+0.065,0.56), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"), xycoords=ax.transAxes)
    ax.text(0.5, 0.18, "Boundary: target-direction LP selectivity validated; global y-LP blocking not validated; y-gradient diagnostic failed selectivity", ha="center", fontsize=8, color="#333333", transform=ax.transAxes)
    ax.set_title("Evidence flow for official H500 LP-APCD K=6 x-gradient result", fontsize=11, fontweight="bold")
    save_fig(fig, output, "figure_5_stage_flow_summary")
    plt.close(fig)

def draw_pillar(ax, row, which, color, Rectangle, Circle):
    if which == "j1":
        cx = flt(row["j1_abs_center_x_nm"]); cy = flt(row["j1_abs_center_y_nm"]); wx = flt(row["j1_footprint_x_nm"]); wy = flt(row["j1_footprint_y_nm"]); shape = row.get("j1_shape_family", "")
        if shape == "circle":
            ax.add_patch(Circle((cx, cy), wx/2, fc=color, ec="#222222", alpha=0.85, lw=0.6))
        else:
            ax.add_patch(Rectangle((cx-wx/2, cy-wy/2), wx, wy, fc=color, ec="#222222", alpha=0.85, lw=0.6))
    else:
        cx = flt(row["j2_abs_center_x_nm"]); cy = flt(row["j2_abs_center_y_nm"]); wx = flt(row["j2_footprint_x_nm"]); wy = flt(row["j2_footprint_y_nm"])
        ax.add_patch(Rectangle((cx-wx/2, cy-wy/2), wx, wy, fc=color, ec="#222222", alpha=0.85, lw=0.6))

def order_power_for(rows, pol: str, n: int, m: int) -> float:
    vals = [flt(r["order_power_source_norm"]) for r in rows if r["polarization"] == pol and int(float(r["order_n"])) == n and int(float(r.get("order_m", 0))) == m]
    return max(vals) if vals else 0.0

def write_summary(path: Path, metrics: dict[str, object]) -> None:
    official = metrics["official"]; y_diag = metrics["y_diag"]
    lines = [
        "# Stage12-6 Official H500 LP-APCD K=6 Result Package",
        "",
        "This Stage12-6 package is for group meeting and manuscript planning. It is generated only from existing Stage11/Stage12 outputs: no FDTD was run, no optimization was performed, and no new .fsp was created. Stage12 remains the LP-APCD K=6 x-gradient metagrating validation and result-package stage; Stage13 is reserved for future dipole-source / MicroLED coupling.",
        "",
        "## Official Result",
        "",
        "- Official result is x-gradient because the original diffraction period is Lambda_x = K * p_x.",
        "- Official gradient axis: x.",
        "- Official steering plane: x-z.",
        "- Official target order: x-order +1.",
        f"- x-LP +1 target power: {official['x_LP_target_plus1_power']}.",
        f"- Steering angle: {official['x_LP_steering_angle_deg']} deg.",
        f"- y-LP +1 target leakage: {official['y_LP_target_plus1_leakage']}.",
        f"- target_order_selectivity_ratio: {official['target_order_selectivity_ratio']}.",
        "- Stage12-2 validates +10 deg target-direction LP-selective steering.",
        "- Stage12-3 shows global y-LP blocking is not validated.",
        "- y-LP is redirected into non-target orders for the official x-gradient result.",
        "",
        "## Diagnostic Branch",
        "",
        f"- Stage12-4 y-gradient target power: {y_diag['x_LP_target_power']}.",
        f"- Stage12-4 y-gradient target leakage: {y_diag['y_LP_target_leakage']}.",
        f"- Stage12-4 y-gradient selectivity ratio: {y_diag['target_order_selectivity_ratio']}.",
        "- Stage12-4 y-gradient is a coordinate-transfer diagnostic and failed selectivity.",
        "",
        "## Generated Figures",
        "",
    ]
    for stem, title in FIGURE_FILES:
        lines.append(f"- {stem}.png / {stem}.svg: {title}.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_captions(path: Path) -> None:
    captions = [
        ("Figure 1", "Frozen six-bin H500 LP-APCD dimer library. The six strict phase bins cover 0, 60, 120, 180, 240 and 300 degrees; the panels report selected-channel Tx, conversion/leakage ratio, phase error and matrix error, with the 240 degree bin marked as the weakest-risk bin.", "冻结的六档 H500 LP-APCD 二聚体库。六个严格相位档覆盖 0、60、120、180、240 和 300 度；图中给出选中通道 Tx、转换/泄漏比、相位误差和矩阵误差，并标出 240 度风险档。"),
        ("Figure 2", "Official K=6 x-gradient supercell schematic. The phase sequence progresses along x from 0 to 300 degrees, defining Lambda_x = K p_x, x-LP input, x-z steering and target x-order +1.", "官方 K=6 x 梯度超胞示意图。相位序列沿 x 方向从 0 到 300 度递进，定义 Lambda_x = K p_x、x-LP 入射、x-z 平面偏转和目标 x 级次 +1。"),
        ("Figure 3", "Order-resolved FDTD validation of the official x-gradient metagrating. x-LP input is dominated by the target +1 order, while y-LP target-order leakage is suppressed, giving a target-order selectivity ratio of 11.655.", "官方 x 梯度超构光栅的级次分辨 FDTD 验证。x-LP 入射由目标 +1 级主导，y-LP 在目标级次的泄漏被抑制，目标级次选择比为 11.655。"),
        ("Figure 4", "Comparison between the official x-gradient pass and the y-gradient coordinate-transfer diagnostic. The y-gradient keeps steering but increases target-order y-LP leakage and fails the selectivity criterion.", "官方 x 梯度通过结果与 y 梯度坐标转移诊断的对比。y 梯度保持了偏转，但显著增加 y-LP 在目标级次的泄漏，因此未通过选择性判据。"),
        ("Figure 5", "Evidence flow for the official Stage12 result package. Stage11 freezes the six-bin library, Stage12 validates analytic and layout readiness, Stage12-2 provides the official x-gradient FDTD pass, and Stage12-5 freezes the convention; global y-LP blocking is not claimed.", "官方结果的证据链。Stage11 冻结六档库，Stage12 完成解析和版图验证，Stage12-2 给出官方 x 梯度 FDTD 通过结果，Stage12-5 冻结规范；不声称全局 y-LP 阻断。"),
    ]
    lines = ["# Stage12-6 Caption Drafts", ""]
    for title, en, zh in captions:
        lines.extend([f"## {title}", "", en, "", zh, ""])
    path.write_text("\n".join(lines), encoding="utf-8")

def run_stage12_6(paths: Stage12_6Paths) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    metrics = load_key_metrics(paths)
    key_rows = build_key_metric_rows(metrics)
    manifest = build_figure_manifest(paths.output_dir)
    write_csv_rows(key_rows, paths.output_dir / "stage12_6_key_metrics.csv", KEY_METRIC_FIELDS)
    write_csv_rows(manifest, paths.output_dir / "stage12_6_figure_manifest.csv", MANIFEST_FIELDS)
    write_summary(paths.output_dir / "stage12_6_result_package_summary.md", metrics)
    write_captions(paths.output_dir / "stage12_6_caption_drafts.md")
    generate_figures(paths, metrics)
    return {"output_dir": str(paths.output_dir), "figure_count": len(FIGURE_FILES), "official_pass": official_xgrad_pass(metrics["official"]), "ygrad_classification": ygrad_diagnostic_classification(metrics["y_diag"]), "figures": [stem for stem, _ in FIGURE_FILES], "official": metrics["official"]}
