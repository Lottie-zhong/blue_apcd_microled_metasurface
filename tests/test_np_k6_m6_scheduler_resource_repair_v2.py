import json
from pathlib import Path


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
REPAIR = ROOT / "outputs" / "np_k6_m6_error_region_acquisition_design_v1" / "m6_scheduler_resource_repair_v2"


def test_resource_repair_validator_report_passes():
    report = json.loads((REPAIR / "resource_repair_validator_report_v2.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert all(item["pass"] for item in report["checks"])


def test_constructor_smoke_count_and_zero_solver():
    evidence = json.loads((REPAIR / "resource_repair_evidence_v3.json").read_text(encoding="utf-8"))
    smokes = evidence["constructor_smokes"]
    assert len(smokes) == 5
    assert all(item["passed"] and not item["run_called"] and not item["save_called"] and item["solver_run_invocations"] == 0 for item in smokes)


def test_only_g01p_consumed_and_disqualified():
    final = json.loads((REPAIR / "final_zero_solver_audit.json").read_text(encoding="utf-8"))
    assert final["entered_total"] == 1
    assert final["run_invocation_total"] == 1
    assert final["later_cases_entered"] is False
