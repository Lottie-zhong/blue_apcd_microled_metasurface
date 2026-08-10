from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
E = ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1"
EXPECTED_POST = "a1ccf8e97fda1d0293ada30fa4b0ddb406da4f2db1a4f31e978455b7b036e397"
EXPECTED_SOURCE = "db666c715fe430080f0013e1bdbb03c42286095f97c880bcf404304f5307377c"
W = list(range(445, 456))


def load(name):
    return json.loads((E / name).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def validate():
    required = [
        "replacement_attempt_ledger.json", "replacement_post_fsp_manifest.json",
        "replacement_v2_gate.json", "g04p_extraction_summary.json",
        "logical_task_reconciliation.json", "solver_invocation_audit.json",
        "solver_budget_exception.json", "checksum_manifest.json",
        "process_provenance_audit.json", "replacement_lineage.json",
        "replacement_hf_observations_long.csv", "replacement_hf_transmitted_orders_long.csv",
    ]
    missing = [name for name in required if not (E / name).exists()]
    assert not missing, missing
    ledger = load("replacement_attempt_ledger.json")
    gate = load("replacement_v2_gate.json")
    post = load("replacement_post_fsp_manifest.json")
    logical = load("logical_task_reconciliation.json")
    inv = load("solver_invocation_audit.json")
    checksum = load("checksum_manifest.json")
    lineage = load("replacement_lineage.json")
    assert ledger["entered"] is True and ledger["run_invocation_count"] == 1
    assert ledger["engine_completed"] is True and ledger["controller_returned"] is True and ledger["post_saved"] is True
    assert ledger["quality_gate_pass"] is True and ledger["training_label"] is False
    assert gate["readonly_reload"] is True and gate["run_called"] is False and gate["save_called"] is False
    assert gate["exact_11_points"] is True and gate["all_finite"] is True and gate["quality_gate_pass"] is True
    assert all(isinstance(gate[key], bool) for key in ("gate_closure_pass", "gate_structure_pass", "gate_order_sum_pass", "gate_direct_normalization_pass"))
    assert float(gate["max_abs_closure_residual"]) <= 0.01
    assert float(gate["max_structure_interval_anomaly"]) <= 0.01
    assert float(gate["max_transmitted_order_sum_mismatch"]) <= 1e-8
    assert float(gate["max_direct_normalization_mismatch"]) <= 1e-8
    post_path = pathlib.Path(post["post_fsp_path"])
    assert post_path.exists() and sha(post_path) == EXPECTED_POST
    assert post["post_fsp_stability"]["stable"] is True
    assert checksum["source_prefsp_sha256"] == EXPECTED_SOURCE and checksum["post_fsp_sha256"] == EXPECTED_POST
    with (E / "replacement_hf_observations_long.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [int(row["wavelength_nm"]) for row in rows] == W
    for row in rows:
        for key in ("T_total", "R_total", "eta_plus1", "eta_0", "eta_minus1", "signed_closure_residual"):
            assert float(row[key]) == float(row[key])
    assert logical["logical_task_complete"] is True and logical["accepted_execution_count"] == 1
    assert logical["accepted_execution_id"] == "G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1"
    assert logical["physical_solver_invocation_count_batch1"] == 13
    assert logical["third_logical_task_created"] is False
    assert inv["replacement_run_invocations"] == 1 and inv["second_replacement"] == 0 and inv["attempt_002"] == 0
    assert inv["sealed_access"] == 0 and inv["training_started"] == 0
    assert lineage["logical_identity_shared"] is True and lineage["execution_identity_distinct"] is True
    g04s = ROOT / "outputs" / "np_k6_m2_batch1_hf_acquisition_v1" / "cases" / "NP_K6_M2_BATCH1_G04_S" / "attempt_ledger.json"
    next_ledger = json.loads(g04s.read_text(encoding="utf-8-sig"))
    assert next_ledger["entered"] is False and next_ledger["run_invocation_count"] == 0
    return {"status": "PASS", "post_fsp_sha256": EXPECTED_POST, "wavelength_count": len(rows), "batch1_physical_invocations": 13}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
