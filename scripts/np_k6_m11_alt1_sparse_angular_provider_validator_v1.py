from pathlib import Path
import json,csv,sys
root=Path(__file__).resolve().parents[1]
out=root/"outputs"/"np_k6_m11_alt1_sparse_angular_provider_calibration_v1"
def main():
 m=list(csv.DictReader(open(out/"m11_matched_55row.csv",encoding="utf-8-sig")))
 assert len(m)==55
 assert len(set(r["case_id"] for r in m))==5
 assert all(int(round(float(r["wavelength_nm"]))) in range(445,456) for r in m)
 assert len({(r["case_id"],round(float(r["wavelength_nm"]))) for r in m})==55
 v=json.load(open(out/"m11_solver_budget_audit.json",encoding="utf-8"))
 assert all(v[k]==0 for k in ["FDTD","RCWA","TMM","BFAST","external_HF","inverse"])
 d=json.load(open(out/"m11_decision.json",encoding="utf-8"))
 assert d["H1"]=="PASS" and d["H2"]=="NOT_PROVEN"
 print(json.dumps({"validator_pass":True,"rows":len(m),"cases":5,"solver_budget":v}))
if __name__=="__main__": main()
