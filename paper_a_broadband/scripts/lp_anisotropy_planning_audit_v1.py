import json, hashlib, subprocess, sys
from pathlib import Path

ROOT=Path(r'D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1')
REPORT=ROOT/'paper_a_broadband/reports/lp_anisotropy_expanded_search_v1'
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,text=True,capture_output=True)
    return {'rc':p.returncode,'out':p.stdout.strip(),'err':p.stderr.strip()}
def compact_git(path):
    return {'path':str(path),'branch':run(['git','branch','--show-current'],path)['out'],'head':run(['git','rev-parse','HEAD'],path)['out'],'status_count':len([x for x in run(['git','status','--short'],path)['out'].splitlines() if x.strip()])}
def main():
    sys.path.insert(0,str(ROOT)); from paper_a_broadband.templates.lp_fulljones.apcd_global_fdtd_slot_v1 import live_job_snapshot
    snap=live_job_snapshot(); d=json.loads((REPORT/'planning_decision.json').read_text(encoding='utf-8')); a=json.loads((REPORT/'audit.json').read_text(encoding='utf-8')); doe=json.loads((ROOT/'paper_a_broadband/configs/anisotropy_expanded_doe_v1.json').read_text(encoding='utf-8'))
    forbidden=['broadband_jones_spectra.csv','mdc_weighted_metrics.csv','final_candidate.json']
    fsp=[]
    for p in (ROOT/'paper_a_broadband/runtime/search_anisotropy_v1').rglob('*.fsp'):
        fsp.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'ignored':run(['git','check-ignore','-q',str(p)],ROOT)['rc']==0,'tracked':str(p) in run(['git','ls-files'],ROOT)['out'].splitlines()})
    old=[compact_git(Path(x)) for x in [r'D:/project/worktrees/blue_apcd_lp_global_h_manifold_v1',r'D:/project/worktrees/blue_apcd_cp_stage10_bw2a',r'D:/project/worktrees/blue_apcd_mdc_defect_450']]
    required=['anisotropy_parameterization.json','anisotropy_doe.csv','geometry_validity.csv','planned_geometry_registry.csv','planned_fdtd_case_registry.csv','midpoint_gate_preregistration.json','fdtd_execution_plan_before_benchmark.json','prepared_fsp_provenance.json','planning_decision.json','planning_report.md','audit.json']
    print(json.dumps({'stage_git':compact_git(ROOT),'scheduler':{'global_active_jobs':snap.get('global_active_jobs'),'active_fdtd_jobs':snap.get('active_fdtd_jobs'),'active_rcwa_jobs':snap.get('active_rcwa_jobs'),'unknown_solver_jobs':len(snap.get('unknown_solver_jobs',[])),'jobs':snap.get('jobs',[])},'decision':{'status':d.get('status'),'solver_entered_cases':d.get('solver_entered_cases'),'active_fdtd':d.get('active_fdtd'),'ready_for_auto_admission':d.get('ready_for_auto_admission'),'hidden_pending_auto_admission':d.get('hidden_pending_auto_admission')},'audit':a,'doe':{'count':len(doe.get('geometries',[])),'initial':doe.get('initial_geometry_ids'),'conditional':doe.get('conditional_geometry_ids'),'solver_calls':doe.get('solver_calls'),'all_valid':all(x.get('validity',{}).get('geometry_valid') for x in doe.get('geometries',[]))},'required_artifacts':{x:(REPORT/x).exists() for x in required},'forbidden_truth_artifacts':{x:(REPORT/x).exists() for x in forbidden},'fsp':fsp,'old_worktrees':old},indent=2,ensure_ascii=False))
if __name__=='__main__': main()
