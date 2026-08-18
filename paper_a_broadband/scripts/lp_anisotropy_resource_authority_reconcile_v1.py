import hashlib,json
from pathlib import Path

ROOT=Path(r'D:/project/worktrees/blue_apcd_paper_a_lp_cp_broadband_v1')
AUTH=ROOT/'paper_a_broadband/authority/paper_a_exclusive_idle_fdtd_resource_authority_v1.json'
REPORT=ROOT/'paper_a_broadband/reports/lp_anisotropy_expanded_search_v1'
def load(name):
    p=REPORT/name; return p,json.loads(p.read_text(encoding='utf-8'))
def save(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
auth=json.loads(AUTH.read_text(encoding='utf-8')); authsha=hashlib.sha256(AUTH.read_bytes()).hexdigest()
p,d=load('planning_decision.json')
d['exclusive_idle_resource_authority']={'path':str(AUTH),'sha256':authsha,'cross_branch_active_fdtd_required':0,'hidden_pending_auto_admission':False,'current_active_fdtd':0,'current_solver_entered':0}; save(p,d)
p,d=load('audit.json')
d['exclusive_idle_resource_authority']={'path':str(AUTH),'sha256':authsha,'policy_id':auth['authority_id'],'cross_branch_active_fdtd_required':0,'current_cross_branch_active_fdtd':0}; save(p,d)
p,d=load('fdtd_execution_plan_before_benchmark.json')
d['future_resource_plan']['exclusive_idle_rule']=True; d['future_resource_plan']['cross_branch_active_fdtd_required']=0; d['future_resource_plan']['all_other_branches_must_be_idle']=True; d['future_resource_plan']['benchmark_gate_required']=True; d['future_resource_plan']['chart_authorization_required']=True; d['resource_authority']={'path':str(AUTH),'sha256':authsha}; save(p,d)
p,d=load('anisotropy_parameterization.json')
d['execution_authority_current']['exclusive_idle_rule']=True; d['execution_authority_current']['cross_branch_active_fdtd_required']=0; d['execution_authority_current']['resource_authority_path']=str(AUTH); d['execution_authority_current']['resource_authority_sha256']=authsha; save(p,d)
rp=REPORT/'planning_report.md'; text=rp.read_text(encoding='utf-8'); text += f"\n\n## Exclusive-idle resource authority\n\nPaper A future FDTD admission requires Chart authorization, benchmark release, and zero active FDTD in every other branch; cross-branch active FDTD must equal 0. The current stage remains solver-free and has no hidden pending admission. Canonical authority: `{AUTH}` (SHA256 `{authsha}`).\n"; rp.write_text(text,encoding='utf-8')
print(json.dumps({'status':'PASS','authority_path':str(AUTH),'authority_sha256':authsha,'current_fdtd_budget':0,'cross_branch_active_fdtd_required':0},indent=2))
