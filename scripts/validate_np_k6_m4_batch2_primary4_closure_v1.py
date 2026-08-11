from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / r"outputs\np_k6_m4_batch2_primary4_hf_acquisition_v1"
CASES = [
    "NP_K6_M4_B2_G01_P", "NP_K6_M4_B2_G01_S", "NP_K6_M4_B2_G02_P", "NP_K6_M4_B2_G02_S",
    "NP_K6_M4_B2_G03_P", "NP_K6_M4_B2_G03_S", "NP_K6_M4_B2_G04_P", "NP_K6_M4_B2_G04_S",
]


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def rows(p: Path):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    report = read_json(OUT / "batch2_standalone_validator_report.json")
    ledger = read_json(OUT / "batch2_execution_ledger.json")
    checks = dict(report.get("checks", {}))
    checks["execution_accepted_8"] = ledger.get("accepted_case_count") == 8
    checks["execution_invocations_8"] = ledger.get("solver_run_invocations_total") == 8
    checks["execution_logical_8"] = ledger.get("logical_case_count") == 8
    checks["execution_no_replacements"] = ledger.get("replacement_count") == 0
    checks["batch2_rows_recount"] = len(rows(OUT / "batch2_hf_observations_long.csv")) == 88
    checks["merged_rows_recount"] = len(rows(OUT / "merged_development_hf_observations_long.csv")) == 286
    for case in CASES:
        m = read_json(OUT / "cases" / case / "extraction_manifest.json")
        checks[f"{case}_11_points"] = m.get("exact_11_points") is True and len(m.get("wavelengths_nm", [])) == 11
        checks[f"{case}_read_only"] = m.get("readonly_reload") is True and m.get("run_called") is False and m.get("save_called") is False
        checks[f"{case}_quality"] = m.get("quality_gate_pass") is True
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {"schema_version": "np_k6_m4_batch2_primary4_standalone_validator_v1", "status": status, "checks": checks}
    (OUT / "batch2_independent_validator_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
