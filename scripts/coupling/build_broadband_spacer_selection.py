"""Build the frozen Stage-A broadband spacer comparison.

Only the three exact 445--455 nm broadband acquisitions enter the score.
Monochromatic 450 nm reconciliations are retained as diagnostic evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

GRID = [float(w) for w in range(445, 456)]
CANDIDATES = (
    ("T0", "NB_T0", 0, "stage_a_nb_t0_445_455_xpol_normal_v1"),
    ("T79", "NB_T79", 79, "stage_a_nb_t79_445_455_xpol_normal_v1"),
    ("T237", "NB_T237", 237, "stage_a_nb_t237_445_455_xpol_normal_v1"),
)
SCORE_KEYS = (
    "mean_eta_plus1_445_455",
    "min_eta_plus1_445_455",
    "eta_plus1_std_445_455",
    "mean_directionality_445_455",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = sorted(result["rows"], key=lambda row: float(row["wavelength_nm"]))
    wavelengths = [float(row["wavelength_nm"]) for row in rows]
    if wavelengths != GRID:
        raise ValueError(f"{result['case_id']}: exact 445-455 grid required, got {wavelengths}")
    if len(rows) != len(GRID):
        raise ValueError("exact grid row count mismatch")
    for row in rows:
        if not row["order_closure"]["pass"]:
            raise ValueError(f"{result['case_id']}: order closure failed at {row['wavelength_nm']} nm")
        if not row["power_closure"]["pass"]:
            raise ValueError(f"{result['case_id']}: power closure failed at {row['wavelength_nm']} nm")
        sign = row["sign_audit"]
        if not (sign["pass"] and sign["m_plus_1_physical_kx_sign"] == "+x"):
            raise ValueError(f"{result['case_id']}: m+1 sign audit failed at {row['wavelength_nm']} nm")
    if not (result["solver_entered"] and result["solver_completed"]):
        raise ValueError(f"{result['case_id']}: solver provenance incomplete")
    return rows


def summarize(result: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    def vals(key: str) -> list[float]:
        return [float(row[key]) for row in rows]

    eta = vals("eta_plus1")
    directionality = vals("directionality")
    reflection = vals("R_total")
    transmission = vals("T_total")
    residual = vals("residual_1_minus_R_minus_T")
    return {
        "case_id": result["case_id"],
        "control_group": result["control_group"],
        "spacer_nm": float(result["spacer_nm"]),
        "total_sio2_separation_nm": float(result["total_sio2_separation_nm"]),
        "grid_nm": GRID,
        "row_count": len(rows),
        "mean_eta_plus1_445_455": statistics.fmean(eta),
        "min_eta_plus1_445_455": min(eta),
        "eta_plus1_std_445_455": statistics.pstdev(eta),
        "eta_plus1_range_445_455": max(eta) - min(eta),
        "mean_directionality_445_455": statistics.fmean(directionality),
        "min_directionality_445_455": min(directionality),
        "mean_R_445_455": statistics.fmean(reflection),
        "mean_T_445_455": statistics.fmean(transmission),
        "mean_residual_445_455": statistics.fmean(residual),
        "eta_plus1_at_445_nm": eta[0],
        "eta_plus1_at_450_nm": eta[5],
        "eta_plus1_at_455_nm": eta[-1],
        "peak_eta_plus1": max(eta),
        "peak_wavelength_nm": GRID[eta.index(max(eta))],
        "all_order_closure_pass": True,
        "all_power_closure_pass": True,
        "all_sign_audit_pass": True,
    }


def ranking_key(summary: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        summary["mean_eta_plus1_445_455"],
        summary["min_eta_plus1_445_455"],
        -summary["eta_plus1_std_445_455"],
        summary["mean_directionality_445_455"],
    )


def build_selection(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    common_contract: dict[str, Any] | None = None
    spectra: list[dict[str, Any]] = []
    source_paths: dict[str, Any] = {}

    for label, group, spacer, dirname in CANDIDATES:
        case_dir = root / "outputs" / "coupling" / dirname
        result_path = case_dir / "results" / "result.json"
        setup_path = case_dir / "setup_manifest.json"
        reconciliation_path = case_dir / "reconciliation_450nm.json"
        result = load(result_path)
        rows = exact_rows(result)
        summary = summarize(result, rows)
        if int(summary["spacer_nm"]) != spacer:
            raise ValueError(f"{label}: spacer mismatch")
        reconciliation = load(reconciliation_path)
        if reconciliation["decision"] != "MEASURED_NO_FORMAL_TOLERANCE":
            raise ValueError(f"{label}: unexpected reconciliation decision")
        if reconciliation["hard_gate"] is not None:
            raise ValueError(f"{label}: reconciliation hard gate present")
        if not reconciliation["physical_contract"]["same"]:
            raise ValueError(f"{label}: physical contract mismatch")
        if reconciliation["acquisition_contract"]["same"]:
            raise ValueError(f"{label}: acquisition contracts unexpectedly identical")

        contract = {
            key: result.get(key)
            for key in (
                "source_contract_id",
                "material_contract_id",
                "coordinate_contract_id",
                "mesh_contract_id",
            )
        }
        if common_contract is None:
            common_contract = contract
        elif contract != common_contract:
            raise ValueError(f"{label}: broadband implementation contract differs")
        record = {
            "label": label,
            "control_group": group,
            "spacer_nm": spacer,
            "result_path": str(result_path),
            "result_sha256": sha256(result_path),
            "setup_manifest_path": str(setup_path),
            "setup_manifest_sha256": sha256(setup_path),
            "reconciliation_path": str(reconciliation_path),
            "reconciliation_sha256": sha256(reconciliation_path),
            "summary": summary,
        }
        records.append(record)
        source_paths[label] = {
            "result": str(result_path),
            "result_sha256": record["result_sha256"],
            "setup_manifest": str(setup_path),
            "setup_manifest_sha256": record["setup_manifest_sha256"],
            "reconciliation": str(reconciliation_path),
            "reconciliation_sha256": record["reconciliation_sha256"],
        }
        for row in rows:
            spectra.append(
                {
                    "spacer_nm": spacer,
                    "control_group": group,
                    "wavelength_nm": float(row["wavelength_nm"]),
                    "eta_plus1": float(row["eta_plus1"]),
                    "eta_zero": float(row["eta_zero"]),
                    "eta_minus1": float(row["eta_minus1"]),
                    "eta_plus2": float(row["eta_plus2"]),
                    "directionality": float(row["directionality"]),
                    "R_total": float(row["R_total"]),
                    "T_total": float(row["T_total"]),
                    "residual_1_minus_R_minus_T": float(row["residual_1_minus_R_minus_T"]),
                    "theta_plus1_deg": float(row["theta_plus1_deg"]),
                    "order_closure_pass": bool(row["order_closure"]["pass"]),
                    "power_closure_pass": bool(row["power_closure"]["pass"]),
                    "sign_pass": bool(row["sign_audit"]["pass"]),
                    "m_plus_1_physical_kx_sign": row["sign_audit"]["m_plus_1_physical_kx_sign"],
                }
            )

    records.sort(key=lambda record: ranking_key(record["summary"]), reverse=True)
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank
        record["ranking_key"] = list(ranking_key(record["summary"]))
    winner = records[0]
    tie = len(records) > 1 and ranking_key(records[0]["summary"]) == ranking_key(records[1]["summary"])
    winners_by_wavelength = {}
    for wavelength in GRID:
        candidates = [row for row in spectra if row["wavelength_nm"] == wavelength]
        best = max(candidates, key=lambda row: row["eta_plus1"])
        winners_by_wavelength[str(int(wavelength))] = {
            "control_group": best["control_group"],
            "spacer_nm": best["spacer_nm"],
            "eta_plus1": best["eta_plus1"],
        }

    return {
        "schema_version": "stage_a_broadband_spacer_selection_v1",
        "comparison_id": "APCD_MDC_NP_COUPLING_V1_STAGE_A_BROADBAND_XPOL_NORMAL",
        "scope": {
            "polarization": "x",
            "incidence": "normal",
            "kx_over_k0": 0.0,
            "ky_over_k0": 0.0,
            "wavelength_grid_nm": GRID,
            "acquisition_contract": "broadband_exact_445_455_nm_11_points",
            "material_contract": common_contract,
        },
        "selection_policy": {
            "basis": "WITHIN_BROADBAND_CONTRACT_ONLY",
            "primary_metric": "higher_mean_eta_plus1_445_455",
            "tie_break_order": [
                "higher_min_eta_plus1_445_455",
                "lower_eta_plus1_std_445_455",
                "higher_mean_directionality_445_455",
            ],
            "simplicity_tie_breaker": "0 nm before 79 nm before 237 nm only after exact metric tie",
            "formal_tolerance_used": None,
            "monochromatic_values_used_for_score": False,
            "interpolation_used": False,
            "extrapolation_used": False,
        },
        "candidates": records,
        "spectra": spectra,
        "spectral_winner_by_wavelength": winners_by_wavelength,
        "selection": {
            "status": "FINAL_SPACER_FREEZE_FOR_STAGE_A_XPOL_NORMAL",
            "winner_label": winner["label"],
            "winner_control_group": winner["control_group"],
            "frozen_spacer_nm": winner["spacer_nm"],
            "frozen_total_sio2_separation_nm": winner["summary"]["total_sio2_separation_nm"],
            "exact_metric_tie": tie,
            "basis": "T237 has the highest broadband mean and minimum eta+1 with lower spectral spread than T79; all three pass the same implementation audits.",
            "next_scope": "x-polarization normal-incidence spacer is frozen only; y-polarization, angle, kx, and production transfer remain unauthorized.",
        },
        "physical_behavior": {
            "eta_plus1_peak_by_candidate": {
                record["label"]: {
                    "wavelength_nm": record["summary"]["peak_wavelength_nm"],
                    "eta_plus1": record["summary"]["peak_eta_plus1"],
                }
                for record in records
            },
            "spectral_winner_by_wavelength": winners_by_wavelength,
            "interpretation": [
                "Increasing t_extra from 0 to 79 to 237 nm increases the broadband mean eta+1 in this three-point screen.",
                "T237 improves the worst-case eta+1 and reduces spectral standard deviation relative to T79.",
                "The comparison is not a monotonicity proof for unrun spacers and does not authorize interpolation.",
                "R_total, T_total, and residual are retained as physical interpretation; they do not replace the eta+1 ranking metric.",
            ],
        },
        "interface_freeze": {
            "interface_candidate_id": "SUPPORT_NONE",
            "provider_status": "FROZEN_FOR_STAGE_A_XPOL_NORMAL_ONLY",
            "layers": [],
            "total_thickness_nm": 0.0,
            "reference_medium": "Air",
            "stack_scope": "GaN -> MDC/support -> NP -> Air",
        },
        "provenance": {
            "fixture_registry": "configs/coupling/stage_a_broadband_spacer_confirmation_v1.json",
            "source_paths": source_paths,
            "solver_runs_in_selection": 0,
            "all_solver_runs_completed_once": True,
            "reconciliation_mode": "CROSS_ACQUISITION_CONTRACT_DIAGNOSTIC",
            "reconciliation_verdict": "MEASURED_NO_FORMAL_TOLERANCE",
        },
    }


def write_markdown(artifact: dict[str, Any], path: Path) -> None:
    rows = artifact["candidates"]
    lines = [
        "# Stage-A broadband spacer selection",
        "",
        "Scope: x-polarization, normal incidence, kx/k0=0, exact 445--455 nm at 1 nm spacing.",
        "Only broadband rows enter ranking; monochromatic 450 nm results are diagnostic-only.",
        "",
        "| Rank | t_extra (nm) | mean eta+1 | min eta+1 | std eta+1 | mean directionality | mean R | mean T |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in rows:
        s = record["summary"]
        lines.append(
            f"| {record['rank']} | {record['spacer_nm']:.0f} | "
            f"{s['mean_eta_plus1_445_455']:.9f} | {s['min_eta_plus1_445_455']:.9f} | "
            f"{s['eta_plus1_std_445_455']:.9f} | {s['mean_directionality_445_455']:.9f} | "
            f"{s['mean_R_445_455']:.9f} | {s['mean_T_445_455']:.9f} |"
        )
    sel = artifact["selection"]
    lines += [
        "",
        f"Final freeze: **{sel['frozen_spacer_nm']:.0f} nm** extra SiO2, total SiO2 separation "
        f"**{sel['frozen_total_sio2_separation_nm']:.0f} nm**.",
        "",
        "All candidates passed exact-grid, order-closure, power-closure, sign, provenance, and "
        "same broadband implementation-contract checks. No solver was run by this comparison step.",
        "",
        "Physical interpretation: T237 has the highest broadband mean and minimum eta+1 and a "
        "lower eta+1 standard deviation than T79. This is a three-candidate screen, not an "
        "interpolation or production-transfer authorization.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    artifact = build_selection(args.root.resolve())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(artifact, args.markdown)
    print(json.dumps({
        "json": str(args.json),
        "markdown": str(args.markdown),
        "winner": artifact["selection"]["winner_control_group"],
        "spacer_nm": artifact["selection"]["frozen_spacer_nm"],
    }))


if __name__ == "__main__":
    main()
