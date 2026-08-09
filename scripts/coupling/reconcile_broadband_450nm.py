"""Reconcile one exact 450 nm broadband row against an existing mono result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HARD_GATE = "HARD_GATE_NUMERICAL_RECONCILIATION_TOLERANCE_UNDEFINED"
METRICS = {
    "R_total": "R_total",
    "T_total": "T_total",
    "residual": "residual_1_minus_R_minus_T",
    "eta_plus1": "eta_plus1",
    "eta_zero": "eta_zero",
    "eta_minus1": "eta_minus1",
    "directionality": "directionality",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def exact_450_row(result: dict) -> dict:
    rows = [row for row in result["rows"] if float(row["wavelength_nm"]) == 450.0]
    if len(rows) != 1:
        raise ValueError("result must contain exactly one exact 450.0 nm row")
    return rows[0]


def reconcile(broadband: dict, mono: dict) -> dict:
    row = exact_450_row(broadband)
    values = {}
    for name, bb_key in METRICS.items():
        mono_key = "loss_or_residual" if name == "residual" else bb_key
        bb_value = float(row[bb_key])
        mono_value = float(mono[mono_key])
        values[name] = {
            "broadband": bb_value,
            "monochromatic": mono_value,
            "delta_broadband_minus_monochromatic": bb_value - mono_value,
        }

    identity_keys = (
        "spacer_nm",
        "mdc_geometry_hash",
        "np_geometry_hash",
        "joint_geometry_hash",
        "source_contract_id",
        "material_contract_id",
        "coordinate_contract_id",
        "mesh_contract_id",
    )
    identity = {
        key: {
            "broadband": broadband.get(key),
            "monochromatic": mono.get(key),
            "match": broadband.get(key) == mono.get(key),
        }
        for key in identity_keys
    }
    identity["same_geometry_material_source_mesh_readback"] = all(
        item["match"] for item in identity.values()
    )
    closure = {
        "broadband_order_closure": row.get("order_closure"),
        "monochromatic_order_closure": mono.get("order_closure"),
        "broadband_power_closure": row.get("power_closure"),
        "monochromatic_power_closure": mono.get("power_closure"),
    }
    return {
        "schema_version": "stage_a_broadband_mono_reconciliation_v1",
        "wavelength_nm": 450.0,
        "broadband_case_id": broadband["case_id"],
        "monochromatic_case_id": mono["case_id"],
        "metrics": values,
        "identity": identity,
        "closure": closure,
        "tolerance_status": "NO_SEPARATE_FORMAL_BROADBAND_VS_MONO_TOLERANCE_FOUND_IN_CURRENT_REPO",
        "decision": "HARD_GATE",
        "hard_gate": HARD_GATE,
        "reason": (
            "Exact discrepancies and order-closure evidence are recorded, but the repository "
            "does not define a formal broadband-versus-monochromatic numerical tolerance; "
            "numerical equivalence cannot be safely decided without inventing one."
        ),
        "interpolation_used": False,
        "extrapolation_used": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broadband-result", type=Path, required=True)
    parser.add_argument("--monochromatic-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = reconcile(load_json(args.broadband_result), load_json(args.monochromatic_result))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decision": result["decision"], "hard_gate": result["hard_gate"]}))


if __name__ == "__main__":
    main()
