from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
CENTER_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_power_audit"
OFF_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_offcenter_edge_power_validation"
OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_psi99_synthesis_freeze"

CENTER_ALL = CENTER_DIR / "center_spectral_power_audit_all_cones.csv"
CENTER_RANK20 = CENTER_DIR / "center_spectral_power_audit_rank_20deg.csv"
CENTER_WINDOWS = CENTER_DIR / "center_spectral_power_audit_best_windows.csv"
CENTER_SUMMARY = CENTER_DIR / "center_spectral_power_audit_summary.json"
OFF_INCOH = OFF_DIR / "offcenter_edge_power_incoherent_summary.csv"
OFF_RETENTION = OFF_DIR / "offcenter_edge_power_retention_summary.csv"
OFF_SUMMARY = OFF_DIR / "offcenter_edge_power_summary.json"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def sfloat(value: float) -> str:
    if abs(value) < 1e-3 or abs(value) >= 1e4:
        return f"{value:.6e}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def write_csv(path: Path, fieldnames: list[str], out_rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)


def main() -> None:
    for path in [CENTER_ALL, CENTER_RANK20, CENTER_WINDOWS, CENTER_SUMMARY, OFF_INCOH, OFF_RETENTION, OFF_SUMMARY]:
        if not path.exists():
            raise FileNotFoundError(path)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    center20 = [r for r in rows(CENTER_ALL) if abs(f(r, "cone_deg") - 20.0) < 1e-9]
    off20 = [r for r in rows(OFF_INCOH) if abs(f(r, "cone_half_angle_deg") - 20.0) < 1e-9]
    retention20 = [r for r in rows(OFF_RETENTION) if abs(f(r, "cone_half_angle_deg") - 20.0) < 1e-9]
    windows20 = [r for r in rows(CENTER_WINDOWS) if abs(f(r, "cone_deg") - 20.0) < 1e-9]

    center_total_max = max(center20, key=lambda r: f(r, "total_cone_power"))
    center_usable_max = max(center20, key=lambda r: f(r, "usable_L_power"))
    center_cp_max = max(center20, key=lambda r: f(r, "L_fraction"))
    off_usable_max = max(off20, key=lambda r: f(r, "usable_L_power"))
    off_retention_best = max(retention20, key=lambda r: f(r, "min_offcenter_retention_vs_center"))
    off_min_lfrac = min(off20, key=lambda r: f(r, "L_fraction_incoh"))

    wavelengths = sorted({f(r, "wavelength_nm") for r in center20})
    verified_window = {"min_nm": min(wavelengths), "max_nm": max(wavelengths), "sample_count": len(wavelengths)}

    def center_at(wl: float) -> dict[str, str] | None:
        return next((r for r in center20 if abs(f(r, "wavelength_nm") - wl) < 1e-9), None)

    def retention_at(wl: float) -> dict[str, str] | None:
        return next((r for r in retention20 if abs(f(r, "wavelength_nm") - wl) < 1e-9), None)

    roles = [
        (422.0, "center usable L_out power maximum / blue-side stress case", "highest 20 deg center usable L_out power; off-center +q passes but is not best after displacement"),
        (453.0, "project-center reference", "existing project-center wavelength for later source-module and RCLED-coupled validation"),
        (480.0, "off-center robustness reference", "highest off-center usable L_out power and best 20 deg min retention among validated off-center wavelengths"),
        (420.0, "blue-edge selectivity reference", "highest center CP selectivity and blue-side edge stress point in current 420-480 nm scan"),
    ]
    role_rows = []
    for wl, role, note in roles:
        c = center_at(wl)
        rr = retention_at(wl)
        role_rows.append({
            "wavelength_nm": sfloat(wl),
            "frozen_role": role,
            "center_total_cone_power_20deg": sfloat(f(c, "total_cone_power")) if c else "",
            "center_usable_L_power_20deg": sfloat(f(c, "usable_L_power")) if c else "",
            "center_L_fraction_20deg": sfloat(f(c, "L_fraction")) if c else "",
            "min_offcenter_L_fraction_20deg": sfloat(f(rr, "min_offcenter_L_fraction")) if rr else "",
            "min_offcenter_retention_20deg": sfloat(f(rr, "min_offcenter_retention_vs_center")) if rr else "",
            "avg_offcenter_usable_L_power_20deg": sfloat(f(rr, "avg_offcenter_usable_L_power")) if rr else "",
            "note": note,
        })

    key_rows = [
        {"metric": "verified_center_only_window_nm", "wavelength_nm": "420-480", "source_position": "center", "value": "420-480", "note": "20 deg incoherent L_out dominance verified over sampled center-only no-DBR PSI99 range"},
        {"metric": "center_total_power_max_20deg", "wavelength_nm": center_total_max["wavelength_nm"], "source_position": "center", "value": sfloat(f(center_total_max, "total_cone_power")), "note": "maximum total cone power at 20 deg"},
        {"metric": "center_usable_L_power_max_20deg", "wavelength_nm": center_usable_max["wavelength_nm"], "source_position": "center", "value": sfloat(f(center_usable_max, "usable_L_power")), "note": "maximum usable L_out power at 20 deg"},
        {"metric": "center_cp_selectivity_max_20deg", "wavelength_nm": center_cp_max["wavelength_nm"], "source_position": "center", "value": sfloat(f(center_cp_max, "L_fraction")), "note": "maximum L_fraction at 20 deg"},
        {"metric": "offcenter_usable_L_power_max_20deg", "wavelength_nm": off_usable_max["wavelength_nm"], "source_position": off_usable_max["source_position_label"], "value": sfloat(f(off_usable_max, "usable_L_power")), "note": "maximum off-center usable L_out power at 20 deg"},
        {"metric": "offcenter_best_min_retention_20deg", "wavelength_nm": off_retention_best["wavelength_nm"], "source_position": "x_minus_q/x_plus_q", "value": sfloat(f(off_retention_best, "min_offcenter_retention_vs_center")), "note": "best worst-position retention relative to center"},
        {"metric": "offcenter_worst_L_fraction_20deg", "wavelength_nm": off_min_lfrac["wavelength_nm"], "source_position": off_min_lfrac["source_position_label"], "value": sfloat(f(off_min_lfrac, "L_fraction_incoh")), "note": "all off-center rows remain L_out dominant; this is the closest-to-threshold row"},
    ]

    write_csv(OUT_DIR / "psi99_center_offcenter_synthesis_key_metrics.csv", ["metric", "wavelength_nm", "source_position", "value", "note"], key_rows)
    write_csv(
        OUT_DIR / "psi99_center_offcenter_synthesis_wavelength_roles.csv",
        ["wavelength_nm", "frozen_role", "center_total_cone_power_20deg", "center_usable_L_power_20deg", "center_L_fraction_20deg", "min_offcenter_L_fraction_20deg", "min_offcenter_retention_20deg", "avg_offcenter_usable_L_power_20deg", "note"],
        role_rows,
    )

    summary = {
        "task": "Stage10 CP BW2A PSI99 no-DBR center+offcenter synthesis freeze",
        "candidate_id": "BW2_J1J2_D194_T90_PSI99_H525",
        "fdtd_run": False,
        "runtime_files_touched": False,
        "verified_center_only_window_nm": verified_window,
        "center_20deg": {
            "total_cone_power_max": center_total_max,
            "usable_L_power_max": center_usable_max,
            "cp_selectivity_max": center_cp_max,
            "best_windows": windows20,
        },
        "offcenter_20deg": {
            "usable_L_power_max": off_usable_max,
            "best_min_retention": off_retention_best,
            "worst_L_fraction": off_min_lfrac,
        },
        "answers": {
            "does_422_remain_best_after_offcenter_displacement": False,
            "does_480_fail_by_cp_selectivity": False,
            "next_simulation_stage": "Stop no-DBR center/offcenter scouting; wait for RCLED/source-module design; later validate RCLED-coupled cases at 453 and 480 first, with 422/420 as stress checks.",
        },
        "cautions": [
            "Do not claim full device bandwidth yet.",
            "Do not claim RCLED-coupled bandwidth yet.",
            "Current conclusion is for PSI99 no-DBR ordinary MicroLED, center and x-axis off-center positions only.",
            "No y-offset or full 2D source-position sweep was performed.",
            "No DBR, RCLED, or MQW-coupled validation was performed.",
        ],
    }
    with (OUT_DIR / "psi99_center_offcenter_synthesis_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    report = f"""# Stage10 CP BW2A PSI99 no-DBR center+offcenter synthesis freeze

## English technical summary

No FDTD was run for this synthesis. The package reads existing CSV/JSON summaries from the center spectral power audit and the off-center edge/power validation only.

The verified center-only PSI99 no-DBR CP-selection window is at least **{sfloat(verified_window['min_nm'])}-{sfloat(verified_window['max_nm'])} nm** over the sampled range. At 20 deg, the center total cone-power maximum is **{center_total_max['wavelength_nm']} nm** with total power **{sfloat(f(center_total_max, 'total_cone_power'))}**. The center usable L_out power maximum is **{center_usable_max['wavelength_nm']} nm** with usable L_out power **{sfloat(f(center_usable_max, 'usable_L_power'))}**. The center CP-selectivity maximum is **{center_cp_max['wavelength_nm']} nm** with L_fraction **{sfloat(f(center_cp_max, 'L_fraction'))}**.

For off-center x-axis validation at 20 deg, all tested x_minus_q and x_plus_q cases remain L_out dominant. The highest off-center usable L_out power is **{off_usable_max['wavelength_nm']} nm / {off_usable_max['source_position_label']}** with usable L_out power **{sfloat(f(off_usable_max, 'usable_L_power'))}**. The best retention relative to center is **{off_retention_best['wavelength_nm']} nm**, with min off-center retention **{sfloat(f(off_retention_best, 'min_offcenter_retention_vs_center'))}**.

422 nm remains the center usable-power maximum, but it is **not** the best wavelength after off-center displacement because its x_plus_q retention is weak. 480 nm does **not** fail by CP selectivity; it remains robust and is currently the best off-center retention / usable-power reference.

Frozen wavelength roles:

- **422 nm**: center-power maximum / blue-side stress case.
- **453 nm**: project-center reference.
- **480 nm**: off-center robustness reference.
- **420 nm**: blue-edge selectivity reference.

Next simulation stage: stop no-DBR center/offcenter scouting. Wait for RCLED/source-module design, then run RCLED-coupled validation at 453 and 480 first, with 422/420 as stress checks.

## Cautions

- Do not claim full device bandwidth yet.
- Do not claim RCLED-coupled bandwidth yet.
- Current conclusion is for PSI99 no-DBR ordinary MicroLED, center and x-axis off-center positions only.
- No y-offset or full 2D source-position sweep was performed.
- No DBR, RCLED, or MQW-coupled validation was performed.

## ????

???? CSV/JSON/MD ????????? FDTD????????? FSP/LDF/runtime ???

PSI99 no-DBR ?? MicroLED ? center-only CP ?????????????? **{sfloat(verified_window['min_nm'])}-{sfloat(verified_window['max_nm'])} nm**?20 deg ??center ? cone power ??? **{center_total_max['wavelength_nm']} nm**?center ?? L_out power ??? **{center_usable_max['wavelength_nm']} nm**?center CP ?????? **{center_cp_max['wavelength_nm']} nm**?

?? x_minus_q / x_plus_q ??????????? 20 deg ???? L_out ????????? L_out power ??? **{off_usable_max['wavelength_nm']} nm / {off_usable_max['source_position_label']}**??? center ??????????? **{off_retention_best['wavelength_nm']} nm**?

???**422 nm ? center power ??????????????**?**480 nm ???? CP ?????????????????????**??????? no-DBR center/offcenter ??????? RCLED/source-module ??????? 453 nm ? 480 nm??? 422/420 nm ??????
"""
    (OUT_DIR / "psi99_center_offcenter_synthesis_report.md").write_text(report, encoding="utf-8")

    print(f"Wrote {OUT_DIR}")
    for path in sorted(OUT_DIR.iterdir()):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
