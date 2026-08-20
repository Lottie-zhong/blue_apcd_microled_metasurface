from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_m11b_control0_neg0378_p_marginal_closure_forensic_v1"
W = list(range(445, 456))


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def rows(name: str):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


closure = rows("closure_profile_11points.csv")
check([int(r["wavelength_nm"]) for r in closure] == W, "closure wavelengths")
audit = load("closure_profile_audit.json")
check(audit["CONTROL0_pass_count"] == 10 and audit["CONTROL0_fail_count"] == 1, "CONTROL0 marginal count")
check(audit["ALT1_pass_count"] == 11 and audit["ALT1_fail_count"] == 0, "ALT1 pass count")
check(abs(audit["CONTROL0_abs"]["max"] - 0.012351796077454041) < 1e-12, "CONTROL0 max closure")
check(audit["CONTROL0_worst_wavelength"] == 453, "CONTROL0 worst wavelength")

matched = rows("matched_alt1_p_comparison_11points.csv")
check([int(r["wavelength_nm"]) for r in matched] == W, "matched ALT1 wavelengths")
cutoff = load("order_cutoff_audit.json")
check(cutoff["order_set_changes"] is False and cutoff["exact_crossings_in_band"] is False, "cutoff stability")
for case in ("CONTROL0", "ALT1"):
    check(cutoff["cases"][case]["open_order_sets"] == [[-1, 0, 1, 2, 3, 4, 5]], f"{case} open orders")
    check(cutoff["cases"][case]["min_air_cutoff_distance"] > 0, f"{case} cutoff distance")

contract = load("matched_numerical_contract_diff.json")
check(contract["all_common_numeric_fields_equal"] is True, "reliable common fields")
check(contract["non_geometry_difference_found"] is False, "non-geometry difference")
check(contract["formal_setup_unexpected_differences"] == [], "formal unexpected differences")
check(contract["contract_classification"] == "CONTROL0_ALT1_MATCHED_NUMERICAL_CONTRACT_IDENTICAL", "contract classification")
check(set(contract["unreliable_fields_skipped"]) == {"angle theta", "injection axis"}, "readback exclusions")
check(contract["readback_incomplete_but_no_positive_contract_difference"] is True, "readback-gap note")

termination = load("termination_and_shutoff_audit.json")
for case in ("CONTROL0", "ALT1"):
    check(termination[case]["early_termination"] is True, f"{case} early termination")
    check(termination[case]["completion_recorded"] is True, f"{case} completion")

provider = load("provider_error_closure_correlation.json")
check(provider["classification"], "provider classification")
budget = load("solver_budget_audit.json")
for key in ("new_solver_calls", "new_rcwa_calls", "control0_s_entered", "attempt_002_started", "replay", "external_hf", "training", "inverse"):
    check(budget[key] == 0, f"zero budget {key}")
check(load("attempt002_value_decision.json")["no_auto_run"] is True, "attempt002 no-auto-run")
check(load("attempt002_value_decision.json")["solver_authorized_now"] is False, "attempt002 not authorized")
check(load("control0_s_status.json")["status"] == "NOT_ENTERED_REMAINS_BLOCKED", "CONTROL0-S status")
check(load("np_handoff_value_decision.json")["alt1_h1"] == "NP_ALT1_ANGULAR_COMPONENT_PROVIDER_HANDOFF_READY", "H1 handoff")
prov = load("provenance_audit.json")
check(prov["solver_calls"] == 0 and prov["rcwa_calls"] == 0 and prov["read_only"] is True, "provenance budget")
check(not list(OUT.rglob("*.fsp")), "forensic evidence must not contain FSP")

print(json.dumps({"status": "PASS", "artifact": "NP_K6_M11B_CONTROL0_NEG0378_P_MARGINAL_CLOSURE_FORENSIC_V1", "wavelengths": 11, "control0_fail_count": 1, "alt1_fail_count": 0, "new_solver_calls": 0, "provider_classification": provider["classification"]}, indent=2))
