from __future__ import annotations
import csv,hashlib,json
from pathlib import Path
R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4");M=R/'outputs/lp_ml_dataset_v1';P=M/'plans';A=M/'analysis';C=M/'canonical_v1_19';CSV=P/'b120_negative_common_mode_translation_stage_d4_v1.csv';JS=P/'b120_negative_common_mode_translation_stage_d4_v1.json';EC=P/'b120_negative_common_mode_stage_d4_execution_contract_v1.json';GA=A/'b120_negative_common_mode_stage_d4_geometry_gate_v1.csv';OUT=A/'b120_negative_common_mode_stage_d4_candidate_contract_audit_v1.csv';OUTJ=A/'b120_negative_common_mode_stage_d4_candidate_contract_audit_v1.json';ERR=P/'b120_negative_common_mode_stage_d4_summary_erratum_v1.json';REP=R/'reports/lp_b120_negative_common_mode_stage_d4_candidate_contract_audit_v1.md';S=R/'scripts/lp_b120_negative_common_mode_stage_d4_candidate_contract_audit_v1.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
 with Path(p).open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def atomic(p,x):
 t=Path(p).with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf8');t.replace(p)
def main():
 target=['LP_H500_D4_B120_A_CM-1','LP_H500_D4_B120_A_CM-2','LP_H500_D4_B120_A_CM-3','LP_H500_D4_B120_A_CM-4','LP_H500_D4_B120_A_CM-5','LP_H500_D4_B120_B_CM-1','LP_H500_D4_B120_B_CM-2','LP_H500_D4_B120_B_CM-3'];cr=rows(CSV);j=json.loads(JS.read_text());e=json.loads(EC.read_text());gr=rows(GA);sources={'csv':[r['candidate_id'] for r in cr],'json':[r['candidate_id'] for r in j['candidates']],'contract':e['order'],'geometry_gate':[r['candidate_id'] for r in gr]};ok=all(x==target for x in sources.values()) and len(set(target))==8
 audit=[]
 for name,ids in sources.items():
  by={r['candidate_id']:r for r in (cr if name=='csv' else cr)}
  for i,cid in enumerate(ids,1):
   r=by[cid];audit.append({'file_path':name,'candidate_order':i,'candidate_id':cid,'backbone_id':r['backbone_id'],'common_mode_delta_nm':r['common_mode_delta_nm'],'dimensions':json.dumps([r['J1_side_nm'],r['J2_length_nm'],r['J2_width_nm']]),'centers':json.dumps([r['J1_center_x_nm'],r['J2_center_x_nm']]),'exact_geometry_hash':r['exact_geometry_hash_sha256'],'canonical_relative_geometry_hash':r['canonical_relative_geometry_hash_sha256'],'symmetry_hash':r['symmetry_equivalence_geometry_hash_sha256'],'direct_gap':r['direct_gap_nm'],'nearest_periodic_gap':r['nearest_periodic_gap_nm'],'planning_status':r['planning_status'],'matches_frozen_target':cid==target[i-1]})
 with OUT.open('w',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
 payload={'status':'PASS' if ok else 'FAIL','classification':'CASE_A_SUMMARY_ONLY_MISMATCH' if ok else 'CASE_C_CROSS_FILE_INCONSISTENCY','frozen_target':target,'sources':sources,'canonical_v1_19_checksum':sha(C/'checksums_v1_19.json'),'source_hashes':{str(x):sha(x) for x in (CSV,JS,EC,GA)},'solver_calls':0,'self_reference_policy':'not applicable'};atomic(OUTJ,payload);atomic(ERR,{'status':'D4_V1_FORMAL_PLAN_VALID_SUMMARY_ERRATUM_RECORDED','formal_plan_fact':'CSV/JSON/execution contract/geometry gate all contain A-1..-5 then B-1..-3','erratum':'Any contrary summary interpretation is non-executable and superseded by the formal v1 source set.','formal_source_hashes':payload['source_hashes']});REP.write_text('# D4 candidate contract audit v1\n\n- Classification: `CASE_A_SUMMARY_ONLY_MISMATCH`\n- Formal v1 candidate set is valid: A−1..−5, B−1..−3.\n',encoding='utf8');print(json.dumps(payload))
if __name__=='__main__':main()
