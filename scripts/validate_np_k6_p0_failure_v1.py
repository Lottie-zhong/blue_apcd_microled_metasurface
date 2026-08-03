"""Validate strict early-stop evidence after the first P0 numerical gate failure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CASES = [
    "RUN3C_P_PILOT_HF_V1",
    "RUN3C_S_PILOT_HF_V1",
    "RUN3A_P_PILOT_HF_V1",
    "RUN3A_S_PILOT_HF_V1",
    "RUN3B_P_PILOT_HF_V1",
    "RUN3B_S_PILOT_HF_V1",
]


def validate(stage: Path) -> list[str]:
    errors: list[str] = []
    state = json.loads((stage / "state.json").read_text(encoding="utf-8"))
    failure = json.loads((stage / "pilot_numerical_gate_failure.json").read_text(encoding="utf-8"))
    if state.get("state") != "NP_K6_HF_P0_BLOCKED_BY_LABEL_GENERATOR_NUMERICAL_FIDELITY":
        errors.append("state is not numerical-fidelity blocked")
    if failure.get("state") != state.get("state"):
        errors.append("failure/state mismatch")
    if failure.get("failed_case") != EXPECTED_CASES[0]:
        errors.append("failed case is not first strict-order case")
    if failure.get("solver_entered_total") != 1 or failure.get("solver_run_invocation_total") != 1:
        errors.append("solver budget is not exactly one entered/run")
    gates = failure.get("gates", {})
    if gates.get("closure_pass") is not False or gates.get("max_abs_closure_residual", 0.0) <= 0.02:
        errors.append("closure failure evidence missing")
    if not gates.get("transmitted_order_sum_pass", False):
        errors.append("transmitted order-sum gate unexpectedly failed")
    if failure.get("no_partial_promotion") is not True or failure.get("dataset_created") is not False:
        errors.append("partial promotion was not blocked")
    entered = []
    for case_id in EXPECTED_CASES:
        p = stage / "cases" / case_id / "attempt_ledger.json"
        if not p.exists():
            errors.append(f"missing attempt ledger {case_id}")
            continue
        ledger = json.loads(p.read_text(encoding="utf-8"))
        if ledger.get("entered"):
            entered.append(case_id)
        if case_id != EXPECTED_CASES[0] and (ledger.get("entered") or ledger.get("run_invocation_count", 0) != 0):
            errors.append(f"later case was entered/run: {case_id}")
    if entered != [EXPECTED_CASES[0]]:
        errors.append(f"entered case list mismatch: {entered}")
    if (stage / "../np_k6_hf_pilot_dataset_v1").exists():
        errors.append("pilot dataset exists after early stop")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, default=Path("outputs/np_k6_hf_p0_label_generator_recovery_v1"))
    args = ap.parse_args()
    errors = validate(args.stage)
    if errors:
        print(json.dumps({"status": "FAIL_NP_K6_P0_FAILURE_VALIDATOR", "errors": errors}, indent=2))
        return 1
    print(json.dumps({
        "status": "PASS_NP_K6_P0_FAILURE_VALIDATOR",
        "state": "NP_K6_HF_P0_BLOCKED_BY_LABEL_GENERATOR_NUMERICAL_FIDELITY",
        "entered_cases": [EXPECTED_CASES[0]],
        "untouched_cases": EXPECTED_CASES[1:],
        "partial_promotion": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
