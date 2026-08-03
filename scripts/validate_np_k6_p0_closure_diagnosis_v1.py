"""Validate read-only P0 closure diagnosis and its single-variable proposal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(stage: Path) -> list[str]:
    errors: list[str] = []
    p = stage / "closure_diagnostic_audit.json"
    if not p.exists():
        return ["missing closure_diagnostic_audit.json"]
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("readonly_post_fsp") is not True or data.get("run_called") or data.get("save_called"):
        errors.append("diagnosis is not read-only")
    if data.get("formal_max_abs_closure_residual", 0.0) <= 0.02:
        errors.append("closure failure is not evidenced")
    fdt = data.get("fdtd_runtime_readback", {})
    if fdt.get("simulation time") != 1e-12:
        errors.append("baseline simulation time mismatch")
    if data.get("auto_shutoff_reached_before_fixed_time") is not False:
        errors.append("auto-shutoff termination evidence mismatch")
    b = data.get("flux_balance_448nm", {})
    structure = abs(float(b.get("structure_interval_delta_upper_inside_minus_lower_inside", 0.0)))
    transition = max(abs(float(b.get("lower_transition_jump_inside_minus_outside", 0.0))), abs(float(b.get("upper_transition_jump_outside_minus_inside", 0.0))))
    if structure <= 10.0 * transition:
        errors.append("structure interval deficit is not dominant over transitions")
    proposal = data.get("minimal_correction_proposal", {})
    required = {
        "single_variable": True,
        "object": "FDTD",
        "property": "simulation time",
        "from_s": 1e-12,
        "to_s": 2e-12,
        "requires_new_solver_authorization": True,
        "executed": False,
    }
    for key, value in required.items():
        if proposal.get(key) != value:
            errors.append(f"proposal field mismatch: {key}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, default=Path("outputs/np_k6_hf_p0_label_generator_recovery_v1"))
    args = ap.parse_args()
    errors = validate(args.stage)
    if errors:
        print(json.dumps({"status": "FAIL_NP_K6_P0_CLOSURE_DIAGNOSIS_VALIDATOR", "errors": errors}, indent=2))
        return 1
    print(json.dumps({"status": "PASS_NP_K6_P0_CLOSURE_DIAGNOSIS_VALIDATOR", "proposal": "NP_K6_P0_SIMULATION_TIME_EXTENSION_V1", "solver_entered": 0}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
