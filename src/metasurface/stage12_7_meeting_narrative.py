from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_k6_fdtd import flt, read_csv_rows, write_csv_rows

OUTPUT_DIR_NAME = "stage12_7_h500_lp_k6_meeting_narrative"
QA_FIELDS = ["figure", "format", "path", "exists", "size_bytes", "non_empty", "status", "claim"]
REQUIRED_TEXT_FILES = [
    "stage12_7_figure_qa.csv",
    "stage12_7_meeting_narrative_cn.md",
    "stage12_7_result_abstract_en_cn.md",
    "stage12_7_slide_text_outline.md",
    "stage12_7_limitations_and_next_work.md",
    "stage12_7_core_claims_and_boundaries.md",
]

@dataclass(frozen=True)
class Stage12_7Paths:
    stage12_6_dir: Path
    output_dir: Path

def build_figure_qa_rows(manifest_rows: Sequence[dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in manifest_rows:
        for fmt in ("png", "svg"):
            path = Path(row[fmt])
            exists = path.exists()
            size = path.stat().st_size if exists else 0
            non_empty = exists and size > 0
            rows.append({
                "figure": row.get("figure", ""),
                "format": fmt,
                "path": str(path),
                "exists": exists,
                "size_bytes": size,
                "non_empty": non_empty,
                "status": "PASS" if non_empty else "FAIL",
                "claim": row.get("claim", ""),
            })
    return rows

def qa_pass(rows: Sequence[dict[str, object]]) -> bool:
    return bool(rows) and all(str(row.get("status")) == "PASS" for row in rows)

def metric_map(rows: Sequence[dict[str, str]]) -> dict[str, str]:
    return {row.get("metric", ""): row.get("value", "") for row in rows}

def load_stage12_6_metrics(stage12_6_dir: Path) -> dict[str, object]:
    metrics = metric_map(read_csv_rows(stage12_6_dir / "stage12_6_key_metrics.csv"))
    return {
        "official_period": metrics["official_diffraction_period_direction"],
        "axis": metrics["official_gradient_axis"],
        "plane": metrics["official_steering_plane"],
        "target_order": metrics["official_target_order"],
        "target_power": flt(metrics["x_LP_target_plus1_power"]),
        "steering_angle": flt(metrics["x_LP_steering_angle_deg"]),
        "leakage": flt(metrics["y_LP_target_plus1_leakage"]),
        "ratio": flt(metrics["target_order_selectivity_ratio"]),
        "global_blocking": metrics["global_y_LP_blocking"],
        "ygrad_ratio": flt(metrics["y_gradient_target_order_selectivity_ratio"]),
    }

def write_meeting_narrative(path: Path, m: dict[str, object]) -> None:
    text = f"""# Stage12-7 组会汇报叙事稿：H500 LP-APCD K=6 x-gradient metagrating

## 一句话结论

我们已经完成 H500 LP-APCD K=6 x-gradient metagrating 的 target-direction LP-selective steering 验证：x-LP selected channel 被偏转到 x-z plane 的 +10 deg 方向，目标级次为 x-order +1；y-LP 在目标级次的 leakage 被压低，但 global y-LP blocking 还不能声称已经完成。

## 1. 研究动机

这个阶段的目标不是做 MicroLED 耦合，也不是做 dipole-source 仿真，而是先把 LP-APCD dimer/metagrating 的基本 steering/selectivity 逻辑跑通。我们希望用一组实际 FDTD 筛出来的 H500 dimer phase bins，组合成 K=6 phase-gradient supercell，实现 selected x-LP channel 的定向出射。

## 2. 物理和设计逻辑

Stage11 冻结了 6 个 strict phase bins：0, 60, 120, 180, 240, 300 deg。每个 bin 都来自实际 dimer FDTD 结果，而不是理想相位点。这里 APCD-like 的核心是：不同 dimer 提供近似等步长 phase response，同时维持 selected channel transmission 和 blocked-channel leakage 的差异。

Stage12 的官方 convention 是 x-gradient，因为原始 K=6 diffraction period 从一开始就是沿 x 方向设计的：{m['official_period']}。因此 official gradient axis = {m['axis']}，steering plane = {m['plane']}，target diffraction order = {m['target_order']}。

## 3. 关键结果

官方 Stage12-2 x-gradient full-FDTD 结果显示：x-LP target +1 order power = {m['target_power']:.6f}，steering angle = {m['steering_angle']:.6f} deg，y-LP target-order leakage = {m['leakage']:.6f}，target_order_selectivity_ratio = {m['ratio']:.3f}。这个 ratio 明显高于 6 的阶段性判据，所以可以作为当前 LP metagrating milestone 的 PASS。

## 4. 为什么不采用 y-gradient

Stage12-4 做了 y-gradient coordinate-transfer diagnostic。它确实保留了 +10 deg steering，但是 target-order selectivity ratio 只有 {m['ygrad_ratio']:.3f}，没有达到判据。这个结果说明：gradient axis 虽然在理论上是 layout degree of freedom，但把已验证的 x-gradient 设计直接搬到 y 方向会改变 neighbor relation 和 supercell coupling，不能自动保持 APCD-like LP selectivity。因此 y-gradient 是 failed diagnostic branch，不是 official route。

## 5. 当前边界

可以说：target-direction LP-selective steering 已验证；x-LP selected channel 可以 steer 到 x-z plane 的 +10 deg；y-LP target-order leakage 被抑制。

不能说：global y-LP blocking 已验证；y-gradient 已验证；CP branch 已完成；MicroLED dipole-source integration 已完成。
"""
    path.write_text(text, encoding="utf-8")

def write_abstract(path: Path, m: dict[str, object]) -> None:
    text = f"""# Stage12-7 Result Abstract

## English

We validated an official H500 LP-APCD K=6 x-gradient metagrating using the frozen six-bin actual dimer library. The official diffraction period is {m['official_period']}, so the phase-gradient axis is x, the steering plane is x-z, and the target diffraction order is x-order +1. Minimal full-FDTD validation shows that x-LP input steers to +10 deg with target-order power {m['target_power']:.6f}, while y-LP target-order leakage is {m['leakage']:.6f}. The target-order selectivity ratio is {m['ratio']:.3f}. This validates target-direction LP-selective steering, but does not validate global y-LP blocking. The y-gradient coordinate-transfer diagnostic preserves steering but fails selectivity, and Stage13 is reserved for future dipole-source / MicroLED coupling.

## 中文

我们基于冻结的 H500 六档实际 dimer library，验证了官方 H500 LP-APCD K=6 x-gradient metagrating。官方衍射周期为 {m['official_period']}，因此 phase-gradient axis 为 x，steering plane 为 x-z，target diffraction order 为 x-order +1。最小 full-FDTD 验证显示，x-LP 入射可偏转到 +10 deg，目标级次功率为 {m['target_power']:.6f}；y-LP 在目标级次的 leakage 为 {m['leakage']:.6f}。target-order selectivity ratio 为 {m['ratio']:.3f}。这验证了 target-direction LP-selective steering，但不等于验证 global y-LP blocking。y-gradient 坐标转移诊断保留了偏转但选择性失败；Stage13 保留给后续 dipole-source / MicroLED coupling。
"""
    path.write_text(text, encoding="utf-8")

def write_slide_outline(path: Path, m: dict[str, object]) -> None:
    text = f"""# Stage12-7 Slide Text Outline

## 1. Research motivation
- Goal: validate LP-selective beam steering before MicroLED/dipole-source coupling.
- Current scope: H500 LP-APCD K=6 x-gradient metagrating.
- Boundary: no CP branch and no MicroLED coupling claim in Stage12.

## 2. APCD dimer physical logic
- APCD-like dimer response: selected x-LP channel high transmission and controlled phase.
- Use actual dimer FDTD library, not ideal phase states.
- K means six dimers in one supercell.

## 3. Stage11 six-bin actual dimer phase library
- Strict bins: 0, 60, 120, 180, 240, 300 deg.
- Report Tx, ratio, phase error and matrix_error.
- 240 deg bin is the key risk/weakest bin.

## 4. K=6 x-gradient design logic
- Official period: {m['official_period']}.
- Gradient axis: x.
- Steering plane: x-z.
- Target order: x-order +1.

## 5. Stage12 FDTD validation result
- x-LP target +1 power: {m['target_power']:.6f}.
- Steering angle: {m['steering_angle']:.6f} deg.
- y-LP target leakage: {m['leakage']:.6f}.
- target_order_selectivity_ratio: {m['ratio']:.3f}.

## 6. x-gradient vs y-gradient diagnostic
- x-gradient: official PASS.
- y-gradient: steering pass but selectivity fail.
- Interpretation: coordinate transfer changes neighbor/coupling relation.

## 7. Current conclusion and limitations
- Claim target-direction LP-selective steering.
- Do not claim global y-LP blocking.
- Do not claim y-gradient, CP branch or MicroLED integration completion.

## 8. Next work: Stage13 dipole-source / MicroLED coupling
- Keep official x-gradient convention as the starting structure.
- Move from plane-wave validation to dipole-source / MicroLED coupling.
- Add source-position, dipole-orientation and extraction-efficiency diagnostics.
"""
    path.write_text(text, encoding="utf-8")

def write_limitations(path: Path) -> None:
    text = """# Stage12-7 Limitations And Next Work

## Limitations

- Global y-LP blocking is not validated. Stage12 validates target-direction selectivity, not total-transmission extinction.
- y-gradient is not validated. Stage12-4 is a coordinate-transfer diagnostic that preserved steering but failed selectivity.
- CP branch is not completed in this Stage12 line.
- MicroLED dipole-source integration is not completed. The current validation is plane-wave full-FDTD.
- The 240 deg dimer remains the key library risk bin and should be monitored in any later refinement.

## Recommended next work

1. Use the Stage12-6 figures for group meeting and manuscript planning.
2. Reserve Stage13 for dipole-source / MicroLED coupling using the official x-gradient convention.
3. If needed before Stage13, run optional x-gradient efficiency refinement only, without changing the official convention.
4. Do not rescue y-gradient unless a new design is redefined around Lambda_y from the beginning.
"""
    path.write_text(text, encoding="utf-8")

def write_claims(path: Path) -> None:
    text = """# Stage12-7 Core Claims And Boundaries

## Claims We Can Make

- We can claim target-direction LP-selective steering.
- We can claim x-LP selected channel steers to +10 deg in the x-z plane.
- We can claim y-LP target-order leakage is suppressed.
- We can claim the official Stage12 convention is x-gradient with target x-order +1.

## Claims We Cannot Make

- We cannot claim global y-LP blocking.
- We cannot claim y-gradient is validated.
- We cannot claim CP branch is completed.
- We cannot claim MicroLED dipole-source integration is completed.

## Stage Boundary

Stage12 remains the LP-APCD K=6 x-gradient metagrating validation and result-package stage. Stage13 remains reserved for future dipole-source / MicroLED coupling.

No FDTD was run in Stage12-7. No optimization was performed. No new .fsp was created.
"""
    path.write_text(text, encoding="utf-8")

def run_stage12_7(paths: Stage12_7Paths) -> dict[str, object]:
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = read_csv_rows(paths.stage12_6_dir / "stage12_6_figure_manifest.csv")
    qa_rows = build_figure_qa_rows(manifest)
    metrics = load_stage12_6_metrics(paths.stage12_6_dir)
    write_csv_rows(qa_rows, paths.output_dir / "stage12_7_figure_qa.csv", QA_FIELDS)
    write_meeting_narrative(paths.output_dir / "stage12_7_meeting_narrative_cn.md", metrics)
    write_abstract(paths.output_dir / "stage12_7_result_abstract_en_cn.md", metrics)
    write_slide_outline(paths.output_dir / "stage12_7_slide_text_outline.md", metrics)
    write_limitations(paths.output_dir / "stage12_7_limitations_and_next_work.md")
    write_claims(paths.output_dir / "stage12_7_core_claims_and_boundaries.md")
    return {
        "output_dir": str(paths.output_dir),
        "qa_pass": qa_pass(qa_rows),
        "figure_file_count": len(qa_rows),
        "failed_figures": [row for row in qa_rows if row["status"] != "PASS"],
        "text_files": REQUIRED_TEXT_FILES,
    }
