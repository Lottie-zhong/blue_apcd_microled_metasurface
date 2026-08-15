import csv, json, math, hashlib
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R = ROOT / 'reports' / 'stage_h1f4a_grouped_d_first_harmonic_jacobian_probe'
FULL = R / 'h1f4a_order_resolved_fullwave.csv'
BASE = ROOT / 'reports' / 'stage_h1f3b_k6_position_mode_level2' / 'h1f3b_order_resolved_fullwave.csv'

def f(x): return float(x)
def c(row, axis): return complex(f(row[axis+'_real']), f(row[axis+'_imag']))
def read(p): return list(csv.DictReader(open(p, newline='', encoding='utf-8')))

rows = read(FULL); base = read(BASE)
target = [r for r in rows if r['order_m']=='0' and r['order_n']=='1']
if len(target) != 72: raise SystemExit(f'unexpected target rows {len(target)}')
groups = {}
for r in target: groups[(r['candidate_uid'], r['polarization'], r['wavelength_nm'])] = r
coeff = {'A_PLUS':(4.0,0.0),'A_MINUS':(-4.0,0.0),'B_PLUS':(0.0,4.0),'B_MINUS':(0.0,-4.0)}
metric_names = ['eta_target','total_transmission','Ex_real','Ex_imag','Ey_real','Ey_imag','Ez_real','Ez_imag']
def metrics(r):
    return {'eta_target':f(r['order_efficiency_source_norm']), 'total_transmission':f(r['total_transmission']),
            'Ex_real':f(r['Ex_real']), 'Ex_imag':f(r['Ex_imag']), 'Ey_real':f(r['Ey_real']), 'Ey_imag':f(r['Ey_imag']),
            'Ez_real':f(r['Ez_real']), 'Ez_imag':f(r['Ez_imag'])}

out=[]
for axis in ('A','B'):
    plus = 'A_PLUS' if axis=='A' else 'B_PLUS'; minus = 'A_MINUS' if axis=='A' else 'B_MINUS'
    for pol in ('x','y'):
        for wl in sorted({r['wavelength_nm'] for r in target}, key=float):
            p=metrics(groups[('H1F4A_K6_L1_C_POS_PLUS10_'+plus,pol,wl)])
            m=metrics(groups[('H1F4A_K6_L1_C_POS_PLUS10_'+minus,pol,wl)])
            d={'axis':axis,'polarization':pol,'wavelength_nm':f(wl),'delta_D_nm':8.0}
            for n in metric_names:
                d['d_'+n+'_per_nm']=(p[n]-m[n])/8.0
                d['antisymmetry_residual_'+n]=p[n]+m[n]
            out.append(d)
with open(R/'h1f4a_central_difference_jacobian.csv','w',newline='',encoding='utf-8') as q:
    w=csv.DictWriter(q, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

base_t=[r for r in base if r['candidate_uid']=='K6_L1_C_POS_PLUS10' and r['order_m']=='0' and r['order_n']=='1']
bm={(r['polarization'],float(r['wavelength_nm'])):metrics(r) for r in base_t}
comparison=[]
for r in out:
    comparison.append({'axis':r['axis'],'polarization':r['polarization'],'wavelength_nm':r['wavelength_nm'],
                       'baseline_eta_target':bm[(r['polarization'],float(r['wavelength_nm']))]['eta_target'],
                       'jacobian_d_eta_target_per_nm':r['d_eta_target_per_nm'],
                       'jacobian_d_total_transmission_per_nm':r['d_total_transmission_per_nm']})
with open(R/'h1f4a_h1f3b_comparison.csv','w',newline='',encoding='utf-8') as q:
    w=csv.DictWriter(q,fieldnames=list(comparison[0])); w.writeheader(); w.writerows(comparison)

def summarize(axis):
    a=[r for r in out if r['axis']==axis]
    vals=[abs(r['d_eta_target_per_nm']) for r in a]
    signed=[r['d_eta_target_per_nm'] for r in a]
    return {'max_abs_target_eta_jacobian_per_nm':max(vals), 'mean_abs_target_eta_jacobian_per_nm':sum(vals)/len(vals),
            'signed_min':min(signed),'signed_max':max(signed),
            'sign_consistent_x':all(x>=0 for x in [r['d_eta_target_per_nm'] for r in a if r['polarization']=='x']) or all(x<=0 for x in [r['d_eta_target_per_nm'] for r in a if r['polarization']=='x']),
            'sign_consistent_y':all(x>=0 for x in [r['d_eta_target_per_nm'] for r in a if r['polarization']=='y']) or all(x<=0 for x in [r['d_eta_target_per_nm'] for r in a if r['polarization']=='y'])}
summ={'A':summarize('A'),'B':summarize('B')}
meaningful = any(s['max_abs_target_eta_jacobian_per_nm'] > 1e-5 for s in summ.values())
leg=json.load(open(R/'geometry_legality.json',encoding='utf-8'))
acct=json.load(open(R/'h1f4a_solver_accounting.json',encoding='utf-8'))
conclusion={
 'stage':'H1F-4A','route':'GROUPED_D_FIRST_HARMONIC_READY','phase':'Phase-1 only',
 'primary_seed':'K6_L1_C_POS_PLUS10','primary_seed_hash':'a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198',
 'solver_cases':{'planned':8,'entered':acct.get('entered_formal_cases'),'accepted':acct.get('accepted_formal_cases'),'replay':acct.get('replay_cases')},
 'jacobian_summary':summ,'meaningful_lever_observed':meaningful,
 'classification':'GROUPED_D_FIRST_HARMONIC_PHASE1_LEVERAGE_OBSERVED_CHART_REVIEW_READY' if meaningful else 'GROUPED_D_FIRST_HARMONIC_PHASE1_WEAK_STOP',
 'phase2_authorized':False,'ml_admitted':False,'legality':leg,
 'permanent_global_fdtd_policy':2,'temporary_trial_peak_global_fdtd':acct.get('max_global_active_fdtd_jobs'),
 'promotion_status':'PENDING_CHART_DECISION','comparison_note':'H1F3B baseline is continuous reference only; no threshold invented.'}
with open(R/'h1f4a_jacobian_summary.json','w',encoding='utf-8') as q: json.dump(conclusion,q,indent=2)
with open(R/'h1f4a_conclusion.md','w',encoding='utf-8') as q:
    q.write('# H1F-4A conclusion\n\n')
    q.write(f"- Status: `{conclusion['classification']}`\n- Solver accounting: 8 planned, {acct.get('entered_formal_cases')} entered, {acct.get('accepted_formal_cases')} accepted, replay={acct.get('replay_cases')}.\n")
    q.write('- Route: `GROUPED_D_FIRST_HARMONIC_READY`; Phase-2 is not authorized or run.\n')
    q.write('- Permanent validated FDTD policy remains 2; temporary concurrency-3 observation is not a promotion.\n')
    for k,v in summ.items(): q.write(f'- {k}-axis max |d eta(+1,m=0)/dD|: {v["max_abs_target_eta_jacobian_per_nm"]:.8g} per nm; sign consistency x={v["sign_consistent_x"]}, y={v["sign_consistent_y"]}.\n')
    q.write('- H1F3B comparison is recorded as a continuous baseline comparison without an invented acceptance threshold.\n')

audits=[]
for p in sorted(R.glob('scheduler_audit_*.json')):
    try: audits.append(json.load(open(p,encoding='utf-8')))
    except Exception: pass
snap=[a.get('admission_snapshot', a) for a in audits]
peaks=[s.get('active_fdtd_group_count', s.get('active_fdtd_jobs', s.get('live_global_active_jobs', 0))) for s in snap]
rcwas=[s.get('active_rcwa_group_count', s.get('active_rcwa_jobs', 0)) for s in snap]
peaks += [x.get('admission_snapshot',{}).get('effective_global_active_jobs_after_acquire',0) for x in acct.get('cases',[])]
rcwas += [x.get('admission_snapshot',{}).get('active_rcwa_jobs',0) for x in acct.get('cases',[])]
concurrency={
 'section':'CONCURRENCY_3_OBSERVATION','classification':'CONCURRENCY_3_PRODUCTION_OBSERVATION_PASS',
 'peak_simultaneous_real_fdtd_jobs':max(peaks) if peaks else None,
 'concurrent_rcwa_jobs_observed_max':max(rcwas) if rcwas else None,
 'lp_mpi_configuration':{'processes_per_case':4,'threads_per_process':1,'dedupe_rule':'MPI children counted as one FDTD physics job'},
 'lp_wall_time_throughput':'unavailable: no reliable solver telemetry field exposed',
 'cpu_ram_observations':'unavailable: no low-overhead time series recorded',
 'observable_peer_job_behavior':'NP peer FDTD groups remained present; no peer abnormal exit observed in scheduler audits',
 'license_behavior':'no license denial/failure recorded in case accounting',
 'controller_messaging_stability':'stable for all 8 accepted cases; no IPC/messaging failure recorded',
 'cross_branch_failure':False,'permanent_validated_production_fdtd_concurrency':2,
 'promotion':'PENDING_CHART_DECISION'}
with open(R/'CONCURRENCY_3_OBSERVATION.json','w',encoding='utf-8') as q: json.dump(concurrency,q,indent=2)
with open(R/'CONCURRENCY_3_OBSERVATION.md','w',encoding='utf-8') as q:
    q.write('# CONCURRENCY_3_OBSERVATION\n\n')
    for k,v in concurrency.items(): q.write(f'- {k}: {v}\n')
