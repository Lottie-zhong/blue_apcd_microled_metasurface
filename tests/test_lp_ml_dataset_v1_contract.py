from pathlib import Path
import csv,json
import numpy as np
R=Path(__file__).resolve().parents[1]
P=R/"outputs/lp_ml_dataset_v1/plans"; A=R/"outputs/lp_ml_dataset_v1/analysis"; S=R/"outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_v1"
def rows(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def test_plan_composition_and_smoke():
    r=rows(P/"lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv"); s=rows(P/"lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv")
    assert len(r)==256 and len({q["exact_geometry_hash_sha256"] for q in r})==256
    assert {k:sum(q["category"]==k for q in r) for k in ["GLOBAL_SOBOL","PHASE_REGION","PROJECTOR_REGION","BOUNDARY_FAILURE"]}=={"GLOBAL_SOBOL":128,"PHASE_REGION":64,"PROJECTOR_REGION":32,"BOUNDARY_FAILURE":32}
    assert len(s)==16 and {k:sum(q["category"]==k for q in s) for k in ["GLOBAL_SOBOL","PHASE_REGION","PROJECTOR_REGION","BOUNDARY_FAILURE"]}=={"GLOBAL_SOBOL":8,"PHASE_REGION":4,"PROJECTOR_REGION":2,"BOUNDARY_FAILURE":2}
    assert min(float(q["direct_gap_nm"]) for q in r)>=60 and min(float(q["periodic_gap_nm"]) for q in r)>=60
    assert all(q["planning_status"]=="PLANNED_NOT_RUN" for q in r) and all("D9" not in q["candidate_id"] for q in r+s)
def test_projection_error_scalar_invariant():
    c=json.loads((P/"lp_ml_dataset_v1_projection_error_apcd_v1.json").read_text()); assert c["continuous_metric_only"] and not c["absolute_guard"]
    J=np.array([[1+2j,.1-.2j],[.3+.4j,.05+.01j]]); a=2.3*np.exp(.7j); t=np.array([[1+0j,0j],[0j,0j]])
    def e(M): return 1-abs(np.vdot(t,M))**2/(np.linalg.norm(t)**2*np.linalg.norm(M)**2)
    assert abs(e(J)-e(a*J))<1e-12
def test_smoke_stopped_without_model_fill_or_heavy():
    q=json.loads((S/"quality_audit_v1.json").read_text()); ent=json.loads((S/"entered_accounting_v1.json").read_text())
    assert q["outcome"]=="LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED" and q["solver_entered"]==1 and q["successful_accepted_subruns"]==0
    assert q["model_filled_rows"]==0 and q["no_d9_generated"] and q["no_remaining_240_executed"]
    assert not [p for p in S.rglob("*") if p.suffix.lower() in {".fsp",".fspx",".ldf",".log",".h5",".mat",".npy",".npz"}]
    assert ent["solver_entries"][0]["solver_entered"] is True
    assert len(rows(S/"geometry_records_v1.csv"))==16 and len(rows(S/"subrun_records_v1.csv"))==32
def test_d9_closeout_and_historical_gate():
    c=json.loads((P/"lp_ml_dataset_v1_contract_v1.json").read_text()); d=json.loads((A/"lp_d9_evidence_gap_closeout_decision_ledger_v1.json").read_text())
    assert d["D9_decision"]=="CONTRACT_EVIDENCE_GAP" and d["solver_authorized"] is False and c["d9_closeout"]["historical_hard_gate"]=="HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"
def test_staging_checksums():
    m=json.loads((S/"checksums_v1.json").read_text())
    import hashlib
    for rel,h in m["files"].items():
        assert hashlib.sha256((S/rel).read_bytes()).hexdigest()==h
