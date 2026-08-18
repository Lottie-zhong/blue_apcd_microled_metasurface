import csv,json,hashlib
from pathlib import Path

ROOT=Path(r'D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1')
REPORT=ROOT/'paper_a_broadband/reports/lp_anisotropy_expanded_search_v1'
AUDIT=REPORT/'a02_pre_admission_geometry_audit.json'
def load(name):
    p=REPORT/name; return p,json.loads(p.read_text(encoding='utf-8'))
def save(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def csv_load(name):
    p=REPORT/name
    with p.open(encoding='utf-8',newline='') as f: return p,list(csv.DictReader(f))
def csv_save(p,rows):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(rows)
a02=json.loads(AUDIT.read_text(encoding='utf-8')); a02_sha=hashlib.sha256(AUDIT.read_bytes()).hexdigest()
ref={'path':str(AUDIT),'sha256':a02_sha,'status':'PRE_ADMISSION_GEOMETRY_RISK','reported_min_edge_gap_nm':a02['interpretation']['reported_canonical_min_edge_gap_nm'],'same_cell_pillar_gap_nm':a02['interpretation']['independent_same_cell_pillar_pair_gap_nm'],'periodic_seam_gap_nm':a02['interpretation']['independent_periodic_seam_gap_nm'],'benchmark_admission_safe':False,'DOE_changed':False,'replacement_applied':False}
p,d=load('audit.json'); d['a02_pre_admission_geometry_audit']=ref; d['DOE_changed']=False; d['benchmark_admission_safe_for_A02']=False; save(p,d)
p,d=load('planning_decision.json'); d['a02_pre_admission_status']='PRE_ADMISSION_GEOMETRY_RISK'; d['a02_benchmark_admission_safe']=False; d['a02_audit_ref']=ref; d['DOE_changed']=False; d['next_minimum_authority']='Scientific decision required before A02 benchmark admission; no replacement authorized'; save(p,d)
p,d=load('fdtd_execution_plan_before_benchmark.json'); d['a02_pre_admission_status']='PRE_ADMISSION_GEOMETRY_RISK'; d['a02_benchmark_admission_allowed']=False; d['a02_audit_ref']=ref; save(p,d)
p,rows=csv_load('geometry_validity.csv')
for r in rows:
    r['pre_admission_status']='PRE_ADMISSION_GEOMETRY_RISK' if r.get('geometry_id')=='ANISO_A02' else 'PLANNED'
    r['min_edge_gap_definition']='aggregate_polygon_pair_and_cell_boundary_clearance'
    if r.get('geometry_id')=='ANISO_A02':
        r['same_cell_pillar_pair_gap_nm']=a02['interpretation']['independent_same_cell_pillar_pair_gap_nm']; r['periodic_seam_gap_nm']=a02['interpretation']['independent_periodic_seam_gap_nm']; r['risk_note']='0.0319955 nm is half periodic seam clearance, not pillar-pair gap'
csv_save(p,rows)
p,rows=csv_load('planned_geometry_registry.csv')
for r in rows: r['pre_admission_status']='PRE_ADMISSION_GEOMETRY_RISK' if r.get('geometry_id')=='ANISO_A02' else 'PLANNED'
csv_save(p,rows)
p,rows=csv_load('planned_fdtd_case_registry.csv')
for r in rows: r['pre_admission_status']='PRE_ADMISSION_GEOMETRY_RISK' if r.get('geometry_id')=='ANISO_A02' else 'PLANNED'
csv_save(p,rows)
rp=REPORT/'planning_report.md'; t=rp.read_text(encoding='utf-8'); t += f"\n\n## A02 pre-admission geometry risk\n\nThe reported `0.03199553012498768 nm` is the aggregate validity field's minimum cell-boundary clearance: pillar_2 vertex 2 is `{a02['interpretation']['reported_canonical_min_edge_gap_nm']} nm` above the lower periodic boundary. The same-cell pillar_1/pillar_2 gap is `{a02['interpretation']['independent_same_cell_pillar_pair_gap_nm']} nm`; the implied pillar_2 periodic seam gap is `{a02['interpretation']['independent_periodic_seam_gap_nm']} nm`. A02 is mathematically non-overlapping but not benchmark-safe because of periodic seam near-contact. DOE unchanged; no replacement applied; solver authority remains zero. See `{AUDIT}`.\n"; rp.write_text(t,encoding='utf-8')
print(json.dumps({'status':'PASS','a02_status':'PRE_ADMISSION_GEOMETRY_RISK','DOE_changed':False,'audit_sha256':a02_sha},indent=2))
