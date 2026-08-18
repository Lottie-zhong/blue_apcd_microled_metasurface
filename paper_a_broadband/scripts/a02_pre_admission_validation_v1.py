import csv,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1')
REPORT=ROOT/'paper_a_broadband/reports/lp_anisotropy_expanded_search_v1'
def load(name): return json.loads((REPORT/name).read_text(encoding='utf-8'))
def check(ok,msg):
    print(('PASS ' if ok else 'FAIL ')+msg)
    if not ok: raise SystemExit(msg)
def main():
    a=load('a02_pre_admission_geometry_audit.json'); d=load('planning_decision.json'); audit=load('audit.json'); plan=load('fdtd_execution_plan_before_benchmark.json'); doe=json.loads((ROOT/'paper_a_broadband/configs/anisotropy_expanded_doe_v1.json').read_text(encoding='utf-8'))
    check(a['decision']['status']=='PRE_ADMISSION_GEOMETRY_RISK','A02 risk status')
    check(abs(float(a['interpretation']['reported_canonical_min_edge_gap_nm'])-0.03199553012498768)<1e-12,'reported boundary margin')
    check(abs(float(a['interpretation']['independent_same_cell_pillar_pair_gap_nm'])-44.5319955301249939648606783467)<1e-10,'same-cell pair gap')
    check(abs(float(a['interpretation']['independent_periodic_seam_gap_nm'])-0.063991060249977929721356693304)<1e-10,'periodic seam gap')
    check(a['topology']['same_cell_polygon_intersection'] is False and a['topology']['two_distinct_pillar_objects_in_builder'] is True,'non-overlap and distinct builder objects')
    check(hashlib.sha256((ROOT/'paper_a_broadband/configs/anisotropy_expanded_doe_v1.json').read_bytes()).hexdigest()==a['source_doe_sha256'],'DOE hash unchanged')
    check(d['DOE_changed'] is False and audit['DOE_changed'] is False,'DOE changed=false')
    check(audit['solver_run_called'] is False and audit['solver_entered']==0 and audit['active_fdtd']==0 and audit['ready_for_auto_admission']==0 and audit['hidden_pending_auto_admission'] is False,'zero-solver audit counters')
    check(plan['a02_benchmark_admission_allowed'] is False,'A02 admission blocked')
    with (REPORT/'planned_fdtd_case_registry.csv').open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    check(all(r['pre_admission_status']=='PRE_ADMISSION_GEOMETRY_RISK' for r in rows if r['geometry_id']=='ANISO_A02'),'A02 case registry risk labels')
    s=subprocess.run(['git','diff','--check'],cwd=ROOT,text=True,capture_output=True); check(s.returncode==0,'git diff check')
    sys.path.insert(0,str(ROOT)); from paper_a_broadband.templates.lp_fulljones.apcd_global_fdtd_slot_v1 import live_job_snapshot
    snap=live_job_snapshot(); check(snap.get('active_fdtd_jobs')==0 and snap.get('global_active_jobs')==0 and len(snap.get('unknown_solver_jobs',[]))==0,'shared scheduler zero active/unknown')
    print(json.dumps({'status':'PASS','DOE_changed':False,'solver_run_called':False,'solver_entered':0,'active_fdtd':0,'ready_pending_hidden':0},indent=2))
if __name__=='__main__': main()
