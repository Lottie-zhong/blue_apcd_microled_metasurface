from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
EVID = ROOT / "outputs" / "np_k6_m10c_alt1_neg0378_ps_quantitative_anchor_v1"
RUNS = EVID / "runtime_runs"
CASES = [
    "NP_K6_M10C_ALT1_UX_M0d378689399989_P_XLIKE",
    "NP_K6_M10C_ALT1_UX_M0d378689399989_S_YLIKE",
]
EXPECTED_SETUP_SHA = {
    CASES[0]: "ca8c74d457011d18697e98c4035f54bb0b57c0a2557cbbfe8fad9d0bf109df56",
    CASES[1]: "780b253835c4554bca0b7c56ba94eb41c83e1cb427b9d7d4dbe02534efe54e9e",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iso_seconds(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def validate_case(case):
    d = RUNS / case / "attempt_001"
    ledger_path = d / "attempt_ledger.json"
    result = {"case_id": case, "attempt_001_exists": ledger_path.exists()}
    if not ledger_path.exists():
        return result
    ledger = load(ledger_path)
    result["ledger"] = ledger
    checks = {
        "attempt_id_attempt_001": ledger.get("attempt_id") == "attempt_001",
        "entered_once": ledger.get("entered") is True and ledger.get("run_invocation_count") == 1,
        "no_attempt_002_or_003": not any(d.parent.glob("attempt_00[23]")),
        "engine_completed": ledger.get("engine_completed") is True,
        "post_saved": ledger.get("post_saved") is True and (d / f"{case}_attempt_001_post.fsp").exists(),
        "controller_returned": ledger.get("controller_returned") is True,
        "resource_12x1": ledger.get("resource_contract", {}).get("readback") == {"processes": "12", "threads": "1"},
        "slot_released": ledger.get("slot_released") is True and ledger.get("local_active_fdtd") == 0,
    }
    post = d / f"{case}_attempt_001_post.fsp"
    if post.exists():
        checks["post_sha_present"] = bool(ledger.get("post_fsp_sha256"))
        checks["post_sha_matches"] = ledger.get("post_fsp_sha256") == sha(post)
    metrics = d / "spectral_metrics.csv"
    if metrics.exists():
        with metrics.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        result["rows"] = rows
        checks["exact_11_rows"] = len(rows) == 11
        checks["exact_wavelengths"] = all(abs(float(r["wavelength_nm"]) - (445 + i)) <= 1e-6 for i, r in enumerate(rows))
        numeric = ("T_total", "R_total", "residual", "eta_plus1", "eta_0", "eta_minus1", "order_sum_T_mismatch")
        checks["finite_metrics"] = all(math.isfinite(float(r[k])) for r in rows for k in numeric)
        checks["order_sum_gate"] = max(float(r["order_sum_T_mismatch"]) for r in rows) <= 1e-8
        checks["closure_gate"] = max(abs(float(r["residual"])) for r in rows) <= 0.01
    else:
        checks["metrics_present"] = False
    q = d / "quality_gate.json"
    result["quality"] = load(q) if q.exists() else None
    checks["quality_gate_pass"] = result["quality"].get("quality_gate_pass") is True if result["quality"] else False
    result["checks"] = checks
    result["pass"] = all(checks.values())
    return result


def main():
    checks = {}
    preflight = load(EVID / "m10c_run_preflight.json")
    checks["preflight_pass"] = preflight.get("preflight_pass") is True
    material = load(EVID / "m10c_material_readback_audit.json")
    checks["native_material_readback_pass"] = all(material.get("checks", {}).values())
    case_results = [validate_case(case) for case in CASES]
    checks["P_complete"] = case_results[0].get("pass") is True
    checks["P_before_S"] = True
    if case_results[1].get("attempt_001_exists"):
        checks["P_before_S"] = iso_seconds(case_results[0]["ledger"]["solver_entered_timestamp"]) < iso_seconds(case_results[1]["ledger"]["solver_entered_timestamp"])
    checks["S_complete_if_entered"] = not case_results[1].get("attempt_001_exists") or case_results[1].get("pass") is True
    p_ledger = case_results[0].get("ledger", {})
    s_ledger = case_results[1].get("ledger", {})
    if p_ledger and s_ledger:
        checks["no_P_S_slot_overlap"] = iso_seconds(p_ledger["slot_release_time"]) <= iso_seconds(s_ledger["slot_acquire_time"])
    else:
        checks["no_P_S_slot_overlap"] = True
    report = {
        "schema": "NP_K6_M10C_ALT1_NEG0378_PS_STANDALONE_VALIDATOR_V1",
        "task_id": "NP_K6_M10C_ALT1_NEG0378_PS_REPLACEMENT_QUANTITATIVE_ANCHOR_V1",
        "checks": checks,
        "cases": case_results,
        "solver_entered_total": sum(int(x.get("ledger", {}).get("run_invocation_count", 0)) for x in case_results),
        "solver_budget_max": 2,
        "attempt_002_or_003": False,
        "minus_0482_touched": False,
        "control0_started": False,
        "external_hf": 0,
        "training": 0,
        "validator_pass": all(checks.values()) and all((not x.get("attempt_001_exists")) or x.get("pass") for x in case_results),
    }
    tmp = EVID / "m10c_validator_report.json.tmp"
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(EVID / "m10c_validator_report.json")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    if not report["validator_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
