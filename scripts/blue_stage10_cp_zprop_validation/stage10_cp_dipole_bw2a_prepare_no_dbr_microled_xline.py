from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_smoke_prepare"

PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
Q_NM = min(PERIOD_X_NM, PERIOD_Y_NM) / 4.0
SOURCE_Z_NM = -200.0
ARRAY_NX = 7
ARRAY_NY = 3
GAN_X_SPAN_NM = 3000.0
GAN_Y_SPAN_NM = 1200.0
FDTD_X_SPAN_NM = 20000.0
FDTD_Y_SPAN_NM = 20000.0
MONITOR_Z_NM = 1000.0
MONITOR_X_SPAN_NM = 22000.0
MONITOR_Y_SPAN_NM = 22000.0
CP_BASIS = "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); target is L-output dominance"

CANDIDATES = [
    {
        "candidate_id": "BW2_J1J2_D194_T90_PSI99_H525",
        "role": "primary robust CP candidate; all-band BW2 repair",
        "d_nm": 194.0,
        "theta_deg": 90.0,
        "psi_deg": 99.0,
        "J1_center_nm": "(0, 97)",
        "J1_rotation_deg": -9.0,
        "J2_center_nm": "(0, -97)",
        "J2_rotation_deg": 36.0,
    },
    {
        "candidate_id": "BW2_J1J2_D194_T90_PSI97_H525",
        "role": "baseline B4INT notch reference",
        "d_nm": 194.0,
        "theta_deg": 90.0,
        "psi_deg": 97.0,
        "J1_center_nm": "(0, 97)",
        "J1_rotation_deg": -7.0,
        "J2_center_nm": "(0, -97)",
        "J2_rotation_deg": 38.0,
    },
]
WAVELENGTHS_NM = [453.0]
POSITIONS = [{"source_position_label": "center", "source_x_nm": 0.0, "source_y_nm": 0.0}]
DIPOLES = ["x", "y"]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def manifest_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for candidate in CANDIDATES:
        for wavelength_nm in WAVELENGTHS_NM:
            for position in POSITIONS:
                for dipole_axis in DIPOLES:
                    expected_case_id = (
                        f"BW2A_SMOKE_{candidate['candidate_id']}_{int(wavelength_nm)}NM_"
                        f"{position['source_position_label'].upper()}_{dipole_axis.upper()}DIP"
                    )
                    rows.append({
                        "candidate_id": candidate["candidate_id"],
                        "wavelength_nm": wavelength_nm,
                        "source_position_label": position["source_position_label"],
                        "source_x_nm": position["source_x_nm"],
                        "source_y_nm": position["source_y_nm"],
                        "dipole_axis": dipole_axis,
                        "expected_case_id": expected_case_id,
                        "planned_only": "true",
                        "status": "PREPARED_NOT_RUN",
                    })
    return rows


def geometry_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for candidate in CANDIDATES:
        rows.append({
            **candidate,
            "wavelengths_nm": ";".join(str(w) for w in WAVELENGTHS_NM),
            "source_positions": "center:x=0,y=0 only",
            "dipole_axes": ";".join(DIPOLES),
            "q_nm_documented_not_used": Q_NM,
            "source_z_nm": SOURCE_Z_NM,
            "array_nx": ARRAY_NX,
            "array_ny": ARRAY_NY,
            "period_x_nm": PERIOD_X_NM,
            "period_y_nm": PERIOD_Y_NM,
            "gan_x_span_nm": GAN_X_SPAN_NM,
            "gan_y_span_nm": GAN_Y_SPAN_NM,
            "fdtd_x_span_nm": FDTD_X_SPAN_NM,
            "fdtd_y_span_nm": FDTD_Y_SPAN_NM,
            "monitor_z_nm": MONITOR_Z_NM,
            "monitor_x_span_nm": MONITOR_X_SPAN_NM,
            "monitor_y_span_nm": MONITOR_Y_SPAN_NM,
            "included_dbr_rcled_mqw": "false",
            "created_fsp_count": 0,
        })
    return rows


def write_report(rows: list[dict[str, object]]) -> None:
    report = f"""# Stage10-CP-DIPOLE-BW2A smoke prepare

## English
- No FDTD was run.
- No .fsp, .ldf, raw monitor data, DBR, RCLED, MQW, top DBR, bottom mirror, spacer scan, +/-q positions, 450 nm case, or full 36-case run was created.
- This helper was copied from the old mixed worktree single helper and narrowed to smoke scope inside the clean CP worktree.
- Smoke scope: 2 candidates x 1 wavelength x 1 center source position x 2 dipole axes = {len(rows)} planned cases.
- Candidates: BW2_J1J2_D194_T90_PSI99_H525 and BW2_J1J2_D194_T90_PSI97_H525.
- Wavelength: 453 nm only.
- Source position: center only, x=0 nm, y=0 nm, source_z={SOURCE_Z_NM:g} nm.
- Dipoles: x and y, to be combined later by incoherent power summation only.
- CP basis for future extraction: {CP_BASIS}.
- Setup-only FSP count: 0. Waiting for user approval before actual 4-case FDTD smoke run.

## 中文
- 没有运行 FDTD。
- 没有创建 .fsp、.ldf、raw monitor 数据，也没有加入 DBR、RCLED、MQW、顶 DBR、底镜、spacer scan、+/-q、450 nm 或完整 36-case run。
- 本 helper 从旧 mixed worktree 的单个 helper 复制而来，并在 clean CP worktree 中收窄为 smoke 范围。
- Smoke 范围：2 个候选 x 1 个波长 x 1 个中心源位置 x 2 个偶极方向 = {len(rows)} 个计划 case。
- 候选：BW2_J1J2_D194_T90_PSI99_H525 和 BW2_J1J2_D194_T90_PSI97_H525。
- 波长：仅 453 nm。
- 源位置：仅 center，x=0 nm，y=0 nm，source_z={SOURCE_Z_NM:g} nm。
- 偶极：x 与 y，后续只能做功率非相干相加。
- 后续提取 CP 基底：{CP_BASIS}。
- setup-only FSP 数量：0。等待用户确认后再运行实际 4-case FDTD smoke。
"""
    (OUT_DIR / "stage10_cp_dipole_bw2a_smoke_prepare_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = manifest_rows()
    geom = geometry_rows()
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_smoke_case_manifest.csv", rows)
    (OUT_DIR / "stage10_cp_dipole_bw2a_smoke_case_manifest.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_smoke_geometry_source_summary.csv", geom)
    summary = {
        "stage": "Stage10-CP-DIPOLE-BW2A-SMOKE",
        "fdtd_run": False,
        "fsp_created_count": 0,
        "old_helper_source": "D:/project/blue_apcd_microled_metasurface/scripts/blue_stage10_cp_zprop_validation/stage10_cp_dipole_bw2a_prepare_no_dbr_microled_xline.py",
        "new_helper_destination": str(Path(__file__).resolve()),
        "planned_case_count": len(rows),
        "candidates": [c["candidate_id"] for c in CANDIDATES],
        "wavelengths_nm": WAVELENGTHS_NM,
        "positions": POSITIONS,
        "dipoles": DIPOLES,
        "safety": {
            "no_dbr": True,
            "no_rcled": True,
            "no_mqw": True,
            "no_finite_patch_run": True,
            "manifest_only": True,
        },
    }
    (OUT_DIR / "stage10_cp_dipole_bw2a_smoke_prepare_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(rows)
    print(json.dumps({"planned_case_count": len(rows), "out_dir": str(OUT_DIR)}, indent=2))


if __name__ == "__main__":
    main()
