import csv,json
from pathlib import Path
def test_m11_exact_authority_and_zero_solver():
 root=Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
 out=root/"outputs"/"np_k6_m11_alt1_sparse_angular_provider_calibration_v1"
 rows=list(csv.DictReader(open(out/"m11_matched_55row.csv",encoding="utf-8-sig")))
 assert len(rows)==55
 assert len(set(r["case_id"] for r in rows))==5
 assert len(set((r["case_id"],round(float(r["wavelength_nm"]))) for r in rows))==55
 v=json.load(open(out/"m11_solver_budget_audit.json",encoding="utf-8"))
 assert v["FDTD"]==v["RCWA"]==v["external_HF"]==v["inverse"]==0
 d=json.load(open(out/"m11_decision.json",encoding="utf-8"))
 assert d["H1"]=="PASS" and d["H2"]=="NOT_PROVEN"
