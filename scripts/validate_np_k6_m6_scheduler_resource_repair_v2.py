from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs" / "np_k6_m6_error_region_acquisition_design_v1"
REPAIR = OUT / "m6_scheduler_resource_repair_v2"
M6 = ROOT / "outputs" / "np_k6_m6_primary4_hf_acquisition_v1"
CASES = M6 / "cases"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: object = None) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    evidence = read_json(REPAIR / "resource_repair_evidence_v3.json")
    check("policy_identity", evidence.get("policy") == "APCD_GLOBAL_FDTD_PARALLEL_POLICY_V1")
    check("expected_resources", evidence.get("expected_per_job") == {"processes": 4, "threads": 1})
    check("repair_solver_calls_zero", evidence.get("formal_solver_calls_this_repair") == 0)
    check("formal_tasks_not_started", evidence.get("formal_tasks_started") is False)
    smokes = evidence.get("constructor_smokes", [])
    check("five_constructor_smokes", len(smokes) == 5, len(smokes))
    check("constructor_smokes_zero_solver", all(
        x.get("passed") is True
        and x.get("run_called") is False
        and x.get("save_called") is False
        and x.get("solver_run_invocations") == 0
        for x in smokes
    ))
    static = evidence.get("static_runner_audit", {})
    check("runner_resource_gate", static.get("resource_gate_function") is True)
    check("runner_setresource_4", static.get("set_processes_4") is True)
    check("runner_getresource_readback", static.get("getresource_readback") is True)
    check("runner_gate_before_entry", static.get("entered_after_gate") is True)
    check("runner_single_run_site", static.get("single_run_call") == 1)
    check("all_repair_sources_compile", all(v.get("pass") for v in evidence.get("compile", {}).values()))

    unit = read_json(REPAIR / "resource_gate_unit_test.json")
    check("resource_gate_positive", unit.get("good_pass", {}).get("pass") is True)
    check("resource_gate_rejects_52", unit.get("bad_mismatch_rejected") is True)
    check("unit_solver_zero", unit.get("solver_calls") == 0 and unit.get("run_called") is False)

    final = read_json(REPAIR / "final_zero_solver_audit.json")
    check("repair_final_solver_zero", final.get("solver_calls_this_repair") == 0)
    check("only_original_case_entered", final.get("entered_total") == 1)
    check("only_original_run_invocation", final.get("run_invocation_total") == 1)
    check("no_later_case_entered", final.get("later_cases_entered") is False)

    ledgers = {}
    for path in sorted(CASES.glob("*/attempt_ledger.json")):
        data = read_json(path)
        ledgers[data.get("case_id", path.parent.name)] = data
    g01p = ledgers.get("NP_K6_M6_PRIMARY4_G01_P", {})
    check("g01p_preserved_entered", g01p.get("entered") is True and g01p.get("run_invocation_count") == 1)
    check("g01p_resource_violation_adjudicated", g01p.get("resource_contract_violation") is True)
    check("g01p_not_formal_label", g01p.get("quality_gate_pass") is False and g01p.get("training_label") is False)
    later = [v for k, v in ledgers.items() if k != "NP_K6_M6_PRIMARY4_G01_P"]
    check("later_cases_unentered", all(v.get("entered") is False and v.get("run_invocation_count", 0) == 0 for v in later))

    forbidden = [p for p in REPAIR.rglob("*") if p.is_file() and p.suffix.lower() in {".fsp", ".npz", ".log"}]
    check("repair_evidence_no_large_runtime_artifacts", not forbidden, [str(p) for p in forbidden])

    report = {
        "schema_version": "np_k6_m6_scheduler_resource_repair_validator_v2",
        "status": "PASS" if all(x["pass"] for x in checks) else "FAIL",
        "checks": checks,
        "solver_calls_this_repair": 0,
    }
    (REPAIR / "resource_repair_validator_report_v2.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
