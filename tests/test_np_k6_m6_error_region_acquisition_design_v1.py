import csv, hashlib, json
from datetime import datetime
from pathlib import Path

ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
OUT=ROOT/"outputs"/"np_k6_m6_error_region_acquisition_design_v1"

def j(name): return json.loads((OUT/name).read_text(encoding="utf-8"))

def test_m6_candidate_universe_and_exclusions():
    a=j("candidate_universe_audit.json")
    with (OUT/"m6_candidate_scores.csv").open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    ids={r["geometry_id"] for r in rows}
    assert len(ids)==35
    assert not ids.intersection(a["hf13_ids"])
    assert a["external_overlap_after_exclusion"]==[]
    assert a["duplicate_geometry_hash"] is False

def test_primary4_role_quota_and_expansion():
    s=j("m6_primary4_selection.json"); e=j("m6_expansion_order.json")
    assert len(s["primary4"])==4
    assert {x["role"] for x in s["primary4"]}=={"ERROR-1","POLARIZATION-STRESS","COVERAGE-EXTRAPOLATION-CONTROL","PERFORMANCE+ERROR"}
    assert len(e["backups_ranked"])>=8
    assert e["first6"]==e["primary4"]+e["backups_ranked"][:2]
    assert e["first8"]==e["primary4"]+e["backups_ranked"][:4]

def test_prereg_hash_and_precedence():
    p=j("m6_preregistration_sha256.json"); h=hashlib.sha256((OUT/"NP_K6_M6_ERROR_REGION_ACQUISITION_PREREG_V1.json").read_bytes()).hexdigest()
    assert h==p["sha256"]
    assert datetime.fromisoformat(p["created_utc"]).timestamp() < (OUT/"m6_primary4_selection.json").stat().st_mtime

def test_coverage_and_cost_artifacts():
    c=j("m6_coverage_summary.json"); k=j("m6_solver_cost_package.json")
    assert {x["set"] for x in c["comparisons"]} >= {"proposed_primary4","random4_seed_20260812","performance_only_top4","coverage_only_top4","proposed_first6","proposed_first8"}
    assert [x["logical_cases_p_s"] for x in k["costs"]]==[8,12,16]

def test_external_registry_metadata_only():
    e=j("m6_external_registry_audit.json")
    assert e["metadata_only"] is True
    assert e["sealed_hf_target_read"]==0
    assert e["used_as_m6_candidate"] is False

def test_solver_zero_and_no_inverse():
    z=j("m6_solver_zero_audit.json"); d=j("m6_decision.json")
    assert all(z[k]==0 for k in ["solver_calls","fdtd_run_calls","lumapi_solver_run_calls","external_hf_calls","sealed_target_reads","inverse_design_artifacts"])
    assert d["status"]=="NP_K6_M6_ERROR_REGION_ACQUISITION_DESIGN_READY_FOR_SOLVER_AUTHORIZATION"
