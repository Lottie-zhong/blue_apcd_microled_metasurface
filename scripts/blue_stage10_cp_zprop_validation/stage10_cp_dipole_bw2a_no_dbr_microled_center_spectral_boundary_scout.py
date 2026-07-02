from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SCRIPT_DIR))

import stage10_cp_dipole_bw2a_no_dbr_microled_xline_center_spectral_run as base

CANDIDATE_ID = "BW2_J1J2_D194_T90_PSI99_H525"
WAVELENGTHS = [440.0, 442.0, 444.0, 446.0, 455.0, 456.0, 458.0, 460.0]
EXISTING_COMBINED = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_center_spectral_run" / "stage10_cp_dipole_bw2a_center_spectral_combined_summary.csv"
OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_boundary_scout"
RUNTIME_DIR = Path(r"D:\project\bw2a_boundary_rt")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def configure_base() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base.OUT_DIR = OUT_DIR
    # Keep FSP paths short enough for Lumerical/Windows while leaving all
    # lightweight CSV/JSON/MD outputs in the requested Stage10 folder.
    base.SAVED_DIR = RUNTIME_DIR
    base.SETUP_DIR = base.SAVED_DIR / "setup"
    base.RESULT_DIR = base.SAVED_DIR / "results"
    base.WAVELENGTHS = WAVELENGTHS
    base.CANDIDATES = {
        CANDIDATE_ID: {
            "role": "primary robust CP candidate; no-DBR center spectral boundary scout",
            "J1_rotation_deg": -9.0,
            "J2_rotation_deg": 36.0,
            "J1_y_nm": 97.0,
            "J2_y_nm": -97.0,
        }
    }
    cases = base.planned_cases()
    if len(cases) != 16:
        raise RuntimeError(f"Refusing to run: expected exactly 16 cases, got {len(cases)}")
    print(json.dumps({
        "candidate_id": CANDIDATE_ID,
        "wavelengths_nm": WAVELENGTHS,
        "source_position": {"label": "center", "x_nm": 0.0, "y_nm": 0.0},
        "dipoles": ["x", "y"],
        "total_planned_new_case_count": len(cases),
        "output_directory": str(OUT_DIR),
    }, indent=2))


def copy_base_outputs() -> None:
    mapping = {
        "stage10_cp_dipole_bw2a_center_spectral_case_results.csv": "stage10_cp_dipole_bw2a_center_spectral_boundary_case_results.csv",
        "stage10_cp_dipole_bw2a_center_spectral_incoherent_summary.csv": "stage10_cp_dipole_bw2a_center_spectral_boundary_incoherent_summary.csv",
        "stage10_cp_dipole_bw2a_center_spectral_run_table.csv": "stage10_cp_dipole_bw2a_center_spectral_boundary_run_table.csv",
    }
    for src_name, dst_name in mapping.items():
        src = OUT_DIR / src_name
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copyfile(src, OUT_DIR / dst_name)


def combined_rows() -> list[dict[str, Any]]:
    existing = []
    for row in read_csv(EXISTING_COMBINED):
        if row.get("candidate_id") == CANDIDATE_ID and row.get("source_position_label") == "center" and float(row.get("wavelength_nm", "nan")) in [447.0, 448.0, 450.0, 453.0, 454.0]:
            row = dict(row)
            row["data_source"] = row.get("data_source") or "reused_existing_center_spectral"
            existing.append(row)
    new_rows = read_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_boundary_incoherent_summary.csv")
    for row in new_rows:
        row["data_source"] = "new_boundary_scout"
    rows = existing + new_rows
    rows.sort(key=lambda r: (float(r["wavelength_nm"]), float(r["cone_half_angle_deg"])))
    return rows


def write_boundary_report(rows: list[dict[str, Any]]) -> None:
    rows20 = [r for r in rows if abs(float(r["cone_half_angle_deg"]) - 20.0) < 1e-6]
    rows20.sort(key=lambda r: float(r["wavelength_nm"]))
    pass_rows = [r for r in rows20 if float(r["L_fraction_incoh"]) >= 0.60 and float(r["DoCP_RminusL_incoh"]) < 0]
    blue_pass = [r for r in pass_rows if float(r["wavelength_nm"]) <= 447.0]
    red_pass = [r for r in pass_rows if float(r["wavelength_nm"]) >= 454.0]
    blue_boundary = min(float(r["wavelength_nm"]) for r in blue_pass) if blue_pass else None
    red_boundary = max(float(r["wavelength_nm"]) for r in red_pass) if red_pass else None
    lower_extension = any(abs(float(r["wavelength_nm"]) - 440.0) < 1e-6 and float(r["L_fraction_incoh"]) >= 0.60 for r in rows20)
    upper_extension = any(abs(float(r["wavelength_nm"]) - 460.0) < 1e-6 and float(r["L_fraction_incoh"]) >= 0.60 for r in rows20)

    def table(metric: str) -> str:
        lines = ["|wavelength_nm|value|data_source|", "|---:|---:|---|"]
        for r in rows20:
            lines.append(f"|{float(r['wavelength_nm']):.0f}|{float(r[metric]):.6g}|{r.get('data_source','')}|")
        return "\n".join(lines)

    report = [
        "# Stage10 CP BW2A PSI99 Center Spectral Boundary Scout\n",
        "- Scope: PSI99 only, no-DBR ordinary MicroLED center dipole only.",
        "- New wavelengths: 440, 442, 444, 446, 455, 456, 458, 460 nm.",
        "- Reused existing center spectral rows: 447, 448, 450, 453, 454 nm.",
        "- No +/-q, no PSI97, no DBR/RCLED/MQW/mirror/spacer/full matrix.",
        "- CP basis: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); L_out dominance means DoCP_RminusL < 0.",
        "- Boundary pass threshold: 20 deg incoherent L_fraction >= 0.60.\n",
        "## Combined 20 deg L_fraction\n",
        table("L_fraction_incoh"),
        "\n## Combined 20 deg DoCP_RminusL\n",
        table("DoCP_RminusL_incoh"),
        "\n## Combined 20 deg total_cone_power\n",
        table("total_cone_power_incoh"),
        "\n## Boundary Interpretation\n",
        f"- Preliminary blue-side pass boundary: {'at least down to %.0f nm' % blue_boundary if blue_boundary is not None else 'not established'}.",
        f"- Preliminary red-side pass boundary: {'at least up to %.0f nm' % red_boundary if red_boundary is not None else 'not established'}.",
        f"- Current 447-454 nm verified window can be expanded: {'yes' if lower_extension or upper_extension else 'no'}.",
        f"- Lower-side extension scan recommended: {'yes, because 440 nm passes' if lower_extension else 'local refinement around blue-side transition'}.",
        f"- Upper-side extension scan recommended: {'yes, because 460 nm passes' if upper_extension else 'local refinement around red-side transition'}.",
    ]
    (OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_boundary_report.md").write_text("\n".join(report), encoding="utf-8")
    summary = {
        "stage": "Stage10-CP-BW2A-PSI99-CENTER-SPECTRAL-BOUNDARY-SCOUT",
        "candidate_id": CANDIDATE_ID,
        "new_wavelengths_nm": WAVELENGTHS,
        "reused_wavelengths_nm": [447.0, 448.0, 450.0, 453.0, 454.0],
        "new_fdtd_cases_requested": 16,
        "combined_20deg_rows": rows20,
        "pass_threshold": "20 deg incoherent L_fraction >= 0.60 and DoCP_RminusL < 0",
        "blue_side_pass_boundary_nm": blue_boundary,
        "red_side_pass_boundary_nm": red_boundary,
        "expand_447_454": bool(lower_extension or upper_extension),
        "recommend_lower_extension": bool(lower_extension),
        "recommend_upper_extension": bool(upper_extension),
    }
    (OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_boundary_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    if not EXISTING_COMBINED.exists():
        raise FileNotFoundError(EXISTING_COMBINED)
    configure_base()
    base.main()
    copy_base_outputs()
    rows = combined_rows()
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_boundary_combined_summary.csv", rows)
    write_boundary_report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


