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
WAVELENGTHS = [436.0, 438.0, 462.0, 464.0]
EXISTING_COMBINED = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_boundary_scout" / "stage10_cp_dipole_bw2a_center_spectral_boundary_combined_summary.csv"
OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_center_spectral_boundary_extend"
RUNTIME_DIR = Path(r"D:\project\bw2a_boundary_extend_rt")


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



def planned_cases_8() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wavelength_nm in WAVELENGTHS:
        for candidate_id in base.CANDIDATES:
            for dip in ["x", "y"]:
                rows.append({
                    "case_id": f"BW2A_SPEC_{candidate_id}_{int(wavelength_nm)}NM_CENTER_{dip.upper()}DIP",
                    "candidate_id": candidate_id,
                    "wavelength_nm": wavelength_nm,
                    "source_position_label": "center",
                    "position_id": "center",
                    "x_nm": 0.0,
                    "y_nm": 0.0,
                    "z_nm": base.b2.SOURCE_Z_NM,
                    "orientation": dip,
                    "enabled_source": base.b2.X_SOURCE if dip == "x" else base.b2.Y_SOURCE,
                    "disabled_source": base.b2.Y_SOURCE if dip == "x" else base.b2.X_SOURCE,
                    "theta_deg": 90.0,
                    "phi_deg": 0.0 if dip == "x" else 90.0,
                })
    if len(rows) != 8:
        raise RuntimeError(f"Refusing to run: expected exactly 8 cases, got {len(rows)}")
    return rows


def fix_base_summary() -> None:
    path = OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_run_summary.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stage"] = "Stage10-CP-DIPOLE-BW2A-CENTER-SPECTRAL-BOUNDARY-EXTEND"
    data["new_fdtd_cases_requested"] = 8
    data["runtime_artifact_dir"] = str(RUNTIME_DIR)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

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
            "role": "primary robust CP candidate; no-DBR center spectral boundary outward extension",
            "J1_rotation_deg": -9.0,
            "J2_rotation_deg": 36.0,
            "J1_y_nm": 97.0,
            "J2_y_nm": -97.0,
        }
    }
    base.planned_cases = planned_cases_8
    cases = base.planned_cases()
    if len(cases) != 8:
        raise RuntimeError(f"Refusing to run: expected exactly 8 cases, got {len(cases)}")
    print(json.dumps({
        "candidate_id": CANDIDATE_ID,
        "wavelengths_nm": WAVELENGTHS,
        "source_position": {"label": "center", "x_nm": 0.0, "y_nm": 0.0},
        "dipoles": ["x", "y"],
        "total_planned_new_case_count": len(cases),
        "runtime_artifact_directory": str(base.SAVED_DIR),
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
        if row.get("candidate_id") == CANDIDATE_ID and row.get("source_position_label") == "center" and float(row.get("wavelength_nm", "nan")) in [440.0, 442.0, 444.0, 446.0, 447.0, 448.0, 450.0, 453.0, 454.0, 455.0, 456.0, 458.0, 460.0]:
            row = dict(row)
            row["data_source"] = row.get("data_source") or "reused_previous_boundary_or_center_spectral"
            existing.append(row)
    new_rows = read_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_boundary_incoherent_summary.csv")
    for row in new_rows:
        row["data_source"] = "new_boundary_extend"
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
        "# Stage10 CP BW2A PSI99 Center Spectral Boundary Extension\n",
        "- Scope: PSI99 only, no-DBR ordinary MicroLED center dipole only.",
        "- New wavelengths: 436, 438, 462, 464 nm.",
        "- Reused existing center/boundary rows: 440, 442, 444, 446, 447, 448, 450, 453, 454, 455, 456, 458, 460 nm.",
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
        "stage": "Stage10-CP-BW2A-PSI99-CENTER-SPECTRAL-BOUNDARY-EXTEND",
        "candidate_id": CANDIDATE_ID,
        "new_wavelengths_nm": WAVELENGTHS,
        "reused_wavelengths_nm": [440.0, 442.0, 444.0, 446.0, 447.0, 448.0, 450.0, 453.0, 454.0, 455.0, 456.0, 458.0, 460.0],
        "new_fdtd_cases_requested": 8,
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
    fix_base_summary()
    copy_base_outputs()
    rows = combined_rows()
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_boundary_combined_summary.csv", rows)
    write_boundary_report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


