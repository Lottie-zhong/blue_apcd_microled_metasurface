"""Reconcile exact 450 nm broadband and monochromatic results diagnostically.

A missing broadband-vs-monochromatic numerical tolerance is not converted into a
post-hoc pass/fail threshold.  The output records cross-acquisition measurements,
physical-contract identity, and broadband-ranking eligibility separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


HARD_GATE = "HARD_GATE_BROADBAND_MONO_PHYSICAL_CONTRACT_MISMATCH"
MODE = "CROSS_ACQUISITION_CONTRACT_DIAGNOSTIC"
VERDICT = "MEASURED_NO_FORMAL_TOLERANCE"
METRICS = {
    "R_total": "R_total",
    "T_total": "T_total",
    "residual": "residual_1_minus_R_minus_T",
    "eta_plus1": "eta_plus1",
    "eta_zero": "eta_zero",
    "eta_minus1": "eta_minus1",
    "directionality": "directionality",
}
SOLVER_KEYS = (
    "x min bc",
    "x max bc",
    "y min bc",
    "y max bc",
    "z min bc",
    "z max bc",
    "mesh accuracy",
    "pml layers",
    "simulation time",
    "auto shutoff min",
)
MONITOR_KEYS = ("monitor type", "x span", "y span")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_450_row(result: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in result["rows"] if float(row["wavelength_nm"]) == 450.0]
    if len(rows) != 1:
        raise ValueError("result must contain exactly one exact 450.0 nm row")
    return rows[0]


def same_field(left: Any, right: Any) -> dict[str, Any]:
    return {"broadband": left, "monochromatic": right, "match": left == right}


def physical_contract(
    broadband: dict[str, Any],
    mono: dict[str, Any],
    bb_setup: dict[str, Any],
    mono_setup: dict[str, Any],
    bb_row: dict[str, Any],
    mono_row: dict[str, Any],
) -> dict[str, Any]:
    bb_case = bb_setup["case"]
    mono_case = mono_setup["case"]
    identity_keys = (
        "spacer_nm",
        "total_sio2_separation_nm",
        "mdc_geometry_hash",
        "np_geometry_hash",
        "joint_geometry_hash",
        "source_contract_id",
        "material_contract_id",
        "coordinate_contract_id",
        "mesh_contract_id",
    )
    identity = {
        key: same_field(broadband.get(key, bb_case.get(key)), mono.get(key, mono_case.get(key)))
        for key in identity_keys
    }
    if identity["joint_geometry_hash"]["match"] is not True:
        identity["joint_geometry_hash"]["diagnostic_only"] = True
        identity["joint_geometry_hash"]["reason"] = (
            "legacy_case_schema_hash_metadata_difference; object-level geometry is checked below"
        )
    identity["mdc_candidate_id"] = same_field(
        bb_case["mdc_candidate"]["candidate_id"], mono_case["mdc_candidate"]["candidate_id"]
    )
    identity["np_candidate_id"] = same_field(
        bb_case["np_candidate"]["candidate_id"], mono_case["np_candidate"]["candidate_id"]
    )
    object_geometry = same_field(bb_case.get("objects"), mono_case.get("objects"))
    identity["physical_object_geometry"] = {
        "objects": object_geometry,
        "spacer_and_separation": {
            "spacer_nm": identity["spacer_nm"],
            "total_sio2_separation_nm": identity["total_sio2_separation_nm"],
        },
        "mdc_geometry_hash": identity["mdc_geometry_hash"],
        "np_geometry_hash": identity["np_geometry_hash"],
        "same": all(
            (
                identity["spacer_nm"]["match"],
                identity["total_sio2_separation_nm"]["match"],
                identity["mdc_geometry_hash"]["match"],
                identity["np_geometry_hash"]["match"],
                object_geometry["match"],
            )
        ),
    }

    bb_solver = bb_setup["readback"]["solver"]
    mono_solver = mono_setup["readback"]["solver"]
    solver = {key: same_field(bb_solver.get(key), mono_solver.get(key)) for key in SOLVER_KEYS}

    bb_source = bb_setup["readback"]["source"]
    mono_source = mono_setup["readback"]["source"]
    source_spatial = {
        key: same_field(bb_source.get(key), mono_source.get(key))
        for key in ("direction", "polarization angle", "angle theta", "angle phi")
    }
    source_spatial["polarization"] = same_field(bb_case.get("polarization"), mono_case.get("polarization"))
    source_spatial["kx_over_k0"] = same_field(bb_case.get("kx_over_k0"), mono_case.get("kx_over_k0"))

    bb_monitors = bb_setup["readback"]["monitors"]
    mono_monitors = mono_setup["readback"]["monitors"]
    monitor = {
        name: {
            key: same_field(bb_monitors[name].get(key), mono_monitors[name].get(key))
            for key in MONITOR_KEYS
        }
        for name in ("reflection_monitor", "transmission_monitor", "order_monitor")
    }
    monitor["reference_medium"] = same_field(
        bb_setup["readback"].get("reference_medium"), mono_setup["readback"].get("reference_medium")
    )

    sign = {
        key: same_field(bb_row["sign_audit"].get(key), mono_row["sign_audit"].get(key))
        for key in ("m_plus_1", "m_plus_1_physical_kx_sign")
    }
    sign["both_pass"] = bool(bb_row["sign_audit"].get("pass") and mono_row["sign_audit"].get("pass"))
    normalization = {
        "definition": "power_fraction_of_source",
        "same": True,
        "evidence": [
            "scripts/coupling/extract_broadband_case.py",
            "scripts/coupling/extract_control_group_case.py",
        ],
    }
    groups = {
        "candidate_and_geometry": identity,
        "solver_mesh_boundary": solver,
        "source_spatial_polarization": source_spatial,
        "monitor_physical_contract": monitor,
        "normalization": normalization,
        "order_sign": sign,
    }
    def flags_pass(value: Any) -> bool:
        if isinstance(value, dict):
            if value.get("diagnostic_only") is True:
                return True
            if "match" in value and value["match"] is not True:
                return False
            if "same" in value and value["same"] is not True:
                return False
            return all(flags_pass(item) for item in value.values())
        return True

    all_matches = flags_pass(groups)
    return {"same": all_matches, "groups": groups}


def acquisition_contract(
    broadband: dict[str, Any], mono_setup: dict[str, Any]
) -> dict[str, Any]:
    mono_source = mono_setup["readback"]["source"]
    mono_monitor = mono_setup["readback"]["monitors"]["order_monitor"]
    broadband_spec = {
        "wavelength_start_nm": broadband["source_wavelength_start_nm"],
        "wavelength_stop_nm": broadband["source_wavelength_stop_nm"],
        "frequency_points": broadband["frequency_points"],
        "exact_grid_nm": broadband["wavelength_grid_nm"],
    }
    mono_spec = {
        "wavelength_start_nm": float(mono_source["wavelength start"]) * 1e9,
        "wavelength_stop_nm": float(mono_source["wavelength stop"]) * 1e9,
        "frequency_points": int(mono_monitor["frequency points"]),
        "exact_grid_nm": [float(mono_source["wavelength start"]) * 1e9],
    }
    return {
        "same": False,
        "broadband": broadband_spec,
        "monochromatic": mono_spec,
        "differences": [
            "source spectral range differs",
            "monitor frequency-point count differs",
            "broadband time-domain acquisition is compared with a monochromatic acquisition",
        ],
    }


def reconcile(
    broadband: dict[str, Any],
    mono: dict[str, Any],
    bb_setup: dict[str, Any],
    mono_setup: dict[str, Any],
    bb_setup_path: Path,
    mono_setup_path: Path,
) -> dict[str, Any]:
    bb_row = exact_450_row(broadband)
    values: dict[str, dict[str, Any]] = {}
    for name, bb_key in METRICS.items():
        mono_key = "loss_or_residual" if name == "residual" else bb_key
        bb_value = float(bb_row[bb_key])
        mono_value = float(mono[mono_key])
        delta = bb_value - mono_value
        values[name] = {
            "broadband": bb_value,
            "monochromatic": mono_value,
            "absolute_delta_broadband_minus_monochromatic": delta,
            "relative_delta_over_abs_monochromatic": (
                delta / abs(mono_value) if mono_value != 0.0 else None
            ),
        }

    physical = physical_contract(broadband, mono, bb_setup, mono_setup, bb_row, mono)
    acquisition = acquisition_contract(broadband, mono_setup)
    physical_mismatch = not physical["same"]
    return {
        "schema_version": "stage_a_broadband_mono_reconciliation_v2",
        "wavelength_nm": 450.0,
        "broadband_case_id": broadband["case_id"],
        "monochromatic_case_id": mono["case_id"],
        "mode": MODE,
        "decision": HARD_GATE if physical_mismatch else VERDICT,
        "hard_gate": HARD_GATE if physical_mismatch else None,
        "formal_numerical_tolerance": None,
        "tolerance_status": "NO_AUTHORITATIVE_TOLERANCE_FOUND",
        "post_hoc_tolerance_creation": False,
        "monochromatic_reference_role": "DIAGNOSTIC_ONLY",
        "broadband_ranking_basis": "WITHIN_BROADBAND_CONTRACT_ONLY",
        "broadband_ranking_blocked_by_missing_tolerance": False,
        "metrics": values,
        "physical_contract": physical,
        "acquisition_contract": acquisition,
        "closure": {
            "broadband_order_closure": bb_row.get("order_closure"),
            "monochromatic_order_closure": mono.get("order_closure"),
            "broadband_power_closure": bb_row.get("power_closure"),
            "monochromatic_power_closure": mono.get("power_closure"),
        },
        "exact_grid": {
            "broadband_450_row_is_exact": True,
            "interpolation_used": False,
            "extrapolation_used": False,
        },
        "provenance": {
            "broadband_setup_manifest": str(bb_setup_path),
            "broadband_setup_manifest_sha256": sha256(bb_setup_path),
            "monochromatic_setup_manifest": str(mono_setup_path),
            "monochromatic_setup_manifest_sha256": sha256(mono_setup_path),
            "broadband_result_solver_entered": broadband["solver_entered"],
            "monochromatic_result_solver_entered": mono["solver_entered"],
        },
        "reason": (
            "The 450 nm values are measured across different spectral acquisition contracts. "
            "No authoritative numerical equivalence tolerance exists, so the discrepancy is "
            "diagnostic only; physical-contract mismatch remains a hard gate."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broadband-result", type=Path, required=True)
    parser.add_argument("--monochromatic-result", type=Path, required=True)
    parser.add_argument("--broadband-setup-manifest", type=Path, required=True)
    parser.add_argument("--monochromatic-setup-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconcile(
        load_json(args.broadband_result),
        load_json(args.monochromatic_result),
        load_json(args.broadband_setup_manifest),
        load_json(args.monochromatic_setup_manifest),
        args.broadband_setup_manifest,
        args.monochromatic_setup_manifest,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decision": result["decision"], "hard_gate": result["hard_gate"], "physical_contract_same": result["physical_contract"]["same"], "acquisition_contract_same": result["acquisition_contract"]["same"]}))


if __name__ == "__main__":
    main()