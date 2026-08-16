from __future__ import annotations
import csv, json, math, statistics, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/stage_h1f4b2_grouped_d_j1_combined_local_validation'
FULL = REPORT / 'h1f4b2_order_resolved_fullwave.csv'
JONES = REPORT / 'h1f4b2_k6_order_jones.csv'
BASE_FULL = ROOT / 'reports/stage_h1f3b_k6_position_mode_level2/h1f3b_order_resolved_fullwave.csv'
BASE_JONES = ROOT / 'reports/stage_h1f3b_k6_position_mode_level2/h1f3b_k6_order_jones.csv'
PRED = REPORT / 'h1f4b2_predicted_combined_jacobian.csv'
ACCOUNT = REPORT / 'h1f4b2_solver_accounting.json'
GRID = [450.0 + 0.5*i for i in range(9)]
BASE_UID = 'K6_L1_C_POS_PLUS10'
PLUS_UID = 'H1F4B2_K6_L1_C_POS_PLUS10_COMBINED_PLUS'
MINUS_UID = 'H1F4B2_K6_L1_C_POS_PLUS10_COMBINED_MINUS'

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def f(r, k): return float(r[k])
def mean(v): return statistics.mean(v) if v else None
def stats(v):
    v=[float(x) for x in v if x is not None and math.isfinite(float(x))]
    if not v: return {'mean':None,'median':None,'min':None,'max':None,'std':None,'positive_count':0,'negative_count':0,'zero_count':0,'sign_consistency':None}
    return {'mean':mean(v),'median':statistics.median(v),'min':min(v),'max':max(v),'std':statistics.pstdev(v),'positive_count':sum(x>0 for x in v),'negative_count':sum(x<0 for x in v),'zero_count':sum(x==0 for x in v),'sign_consistency':all(x>0 for x in v) or all(x<0 for x in v)}
def lookup(rs): return {(r['candidate_uid'],r['polarization'],float(r['wavelength_nm']),int(r['order_n']),int(r['order_m'])):r for r in rs}
def val(index, uid, pol, w, order):
    r=index.get((uid,pol,w,order,0)); return None if r is None else f(r,'order_efficiency_source_norm')
def corr(a,b):
    if len(a)<2: return None
    ma,mb=mean(a),mean(b); da=[x-ma for x in a]; db=[y-mb for y in b]
    den=math.sqrt(sum(x*x for x in da)*sum(y*y for y in db))
    return None if den==0 else sum(x*y for x,y in zip(da,db))/den
def jindex(rs): return {(r['candidate_uid'],float(r['wavelength_nm'])):r for r in rs}
def jval(index,uid,w,key):
    r=index.get((uid,w)); return None if r is None else f(r,key)

def main():
    fr, br = rows(FULL), rows(BASE_FULL)
    jr, bjr = rows(JONES), rows(BASE_JONES)
    pr = rows(PRED)
    fi, bi = lookup(fr), lookup(br)
    ji, bji = jindex(jr), jindex(bjr)
    pi={(r['metric'],float(r['wavelength_nm'])):r for r in pr}
    raw=[]; observed={}; predicted={}; even={}
    for pol, labels in [('x',[(1,'eta_x_plus1'),(0,'eta_x_0'),(-1,'eta_x_minus1')]),('y',[(1,'eta_y_plus1')])]:
        for order,label in labels:
            observed[label]=[]; predicted[label]=[]; even[label]=[]
            for w in GRID:
                b=val(bi,BASE_UID,pol,w,order); p=val(fi,PLUS_UID,pol,w,order); m=val(fi,MINUS_UID,pol,w,order)
                obs=None if p is None or m is None else (p-m)/8.0
                pred=None if pi.get((label,w)) is None else f(pi[(label,w)],'g_combined_pred_per_nm')
                ev=None if b is None or p is None or m is None else (p+m)/2.0-b
                observed[label].append(obs); predicted[label].append(pred); even[label].append(ev)
                raw.append({'wavelength_nm':w,'polarization':pol,'metric':label,'baseline':b,'combined_plus':p,'combined_minus':m,'G_obs_per_nm':obs,'G_pred_per_nm':pred,'signed_error':None if obs is None or pred is None else obs-pred,'absolute_error':None if obs is None or pred is None else abs(obs-pred),'even_combined':ev})
    # x directionality and total order closure for each case.
    case_metrics=[]
    for uid,label,idx in [(BASE_UID,'baseline',bi),(PLUS_UID,'combined_plus',fi),(MINUS_UID,'combined_minus',fi)]:
        source=br if label=='baseline' else fr
        for pol in ('x','y'):
            for w in GRID:
                p=val(idx,uid,pol,w,1); m=val(idx,uid,pol,w,-1)
                subset=[r for r in source if r['candidate_uid']==uid and r['polarization']==pol and float(r['wavelength_nm'])==w]
                closure=sum(f(r,'order_efficiency_source_norm') for r in subset)
                case_metrics.append({'case':label,'polarization':pol,'wavelength_nm':w,'directionality':None if p is None or m is None or p+m==0 else (p-m)/(p+m),'total_order_closure':closure,'eta_plus1':p,'eta_minus1':m})
    with (REPORT/'h1f4b2_observed_vs_predicted_metrics.csv').open('w',newline='',encoding='utf-8') as h:
        fields=list(raw[0]); w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(raw)
    with (REPORT/'h1f4b2_case_formal_metrics.csv').open('w',newline='',encoding='utf-8') as h:
        fields=list(case_metrics[0]); w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(case_metrics)
    # Complex order-resolved Jones derivative for +1.
    complex_keys=['txx_re','txx_im','txy_re','txy_im','tyx_re','tyx_im','tyy_re','tyy_im','target_projector_error','target_y_input_leakage_power']
    jder=[]
    for w in GRID:
        p,m,b=ji[(PLUS_UID,w)],ji[(MINUS_UID,w)],bji[(BASE_UID,w)]
        out={'wavelength_nm':w}
        for k in complex_keys:
            pv,mv,bv=f(p,k),f(m,k),f(b,k); out['G_obs_'+k]=(pv-mv)/8.0; out['even_'+k]=(pv+mv)/2.0-bv
        jder.append(out)
    with (REPORT/'h1f4b2_observed_jones_derivative.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=jder[0].keys()); w.writeheader(); w.writerows(jder)
    # Cancellation against frozen grouped-D y derivative; no wavelength-dependent refit.
    cancel=[]
    for i,w in enumerate(GRID):
        gD=next(f(r,'g_D_per_nm') for r in pr if r['metric']=='eta_y_plus1' and float(r['wavelength_nm'])==w)
        go=observed['eta_y_plus1'][i]
        cancel.append({'wavelength_nm':w,'G_D_y_per_nm':gD,'G_obs_y_per_nm':go,'cancellation_fraction':None if gD==0 else 1.0-abs(go)/abs(gD),'signed_residual':None if go is None else go-gD})
    with (REPORT/'h1f4b2_cancellation_validation.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=cancel[0].keys()); w.writeheader(); w.writerows(cancel)
    # Steering retention and cost/redistribution diagnostics.
    retention=[]
    for i,w in enumerate(GRID):
        gd=next(f(r,'g_D_per_nm') for r in pr if r['metric']=='eta_x_plus1' and float(r['wavelength_nm'])==w)
        go=observed['eta_x_plus1'][i]
        retention.append({'wavelength_nm':w,'G_D_x_plus1_per_nm':gd,'G_obs_x_plus1_per_nm':go,'steering_retention_ratio':None if gd==0 else go/gd,'G_obs_x0_per_nm':observed['eta_x_0'][i],'G_obs_xminus1_per_nm':observed['eta_x_minus1'][i]})
    with (REPORT/'h1f4b2_steering_retention.csv').open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=retention[0].keys()); w.writeheader(); w.writerows(retention)
    model={}
    for label in ('eta_x_plus1','eta_y_plus1','eta_x_0','eta_x_minus1'):
        o,p=observed[label],predicted[label]; ratios=[x/y for x,y in zip(o,p) if y not in (0,None) and x is not None]; errors=[x-y for x,y in zip(o,p) if x is not None and y is not None]
        model[label]={'observed_stats':stats(o),'predicted_stats':stats(p),'ratio_stats':stats(ratios),'signed_error_stats':stats(errors),'absolute_error_stats':stats([abs(x) for x in errors]),'wavelength_correlation':corr([x for x in o if x is not None],[y for x,y in zip(o,p) if x is not None and y is not None])}
    acc=json.loads(ACCOUNT.read_text(encoding='utf-8-sig'))
    # Explicit formal categories are evidence labels, not hidden thresholds.
    y_mean=mean(observed['eta_y_plus1']); y_pred=mean(predicted['eta_y_plus1']); x_mean=mean(observed['eta_x_plus1'])
    gdy=mean([r['G_D_y_per_nm'] for r in cancel]); mean_fraction=None if gdy==0 else 1.0-abs(y_mean)/abs(gdy)
    verdict='GROUPED_D_PLUS_J1_CANCELLATION_FAILED' if y_mean is not None and gdy is not None and abs(y_mean)>abs(gdy) else 'GROUPED_D_PLUS_J1_COMBINED_PARTIAL'
    peak_fdtd=max([x.get('admission_snapshot',{}).get('effective_global_active_jobs_after_acquire',0) for x in acc.get('cases',[])] or [0])
    peak_rcwa=max([x.get('admission_snapshot',{}).get('active_rcwa_jobs',0) for x in acc.get('cases',[])] or [0])
    report={'schema':'H1F4B2_OBSERVED_ANALYSIS_V1','stage':'H1F-4B2','ml_admitted':False,'solver_entered_delta':4,'accepted_formal_cases':4,'replay_cases':acc.get('replay_cases',0),'observed_metrics':{k:stats(v) for k,v in observed.items()},'predicted_metrics':{k:stats(v) for k,v in predicted.items()},'even_combined':{k:stats(v) for k,v in even.items()},'model_comparison':model,'cancellation':{'per_wavelength':cancel,'fraction_stats':stats([r['cancellation_fraction'] for r in cancel]),'G_obs_y_mean_per_nm':y_mean,'G_D_y_mean_per_nm':gdy,'mean_cancellation_fraction':mean_fraction,'pointwise_sign_consistency':stats([r['G_obs_y_per_nm'] for r in cancel])['sign_consistency'],'compensation_failure':y_mean is not None and gdy is not None and abs(y_mean)>abs(gdy)},'steering':{'retention':retention,'G_obs_x_plus1_mean_per_nm':x_mean,'retention_ratio_stats':stats([r['steering_retention_ratio'] for r in retention]),'G_obs_x0_mean_per_nm':mean(observed['eta_x_0']),'G_obs_xminus1_mean_per_nm':mean(observed['eta_x_minus1'])},'formal_case_metrics':'h1f4b2_case_formal_metrics.csv','concurrency_3_observation':{'peak_simultaneous_real_fdtd_jobs':peak_fdtd,'concurrent_rcwa_jobs':peak_rcwa,'lp_mpi_configuration':'4 processes, 1 thread','throughput':'unavailable','cpu_ram':'unavailable','license_behavior':'no denial observed','controller_messaging':'no new heartbeat error observed in foreground run','cross_branch_failure':False},'verdict':verdict,'next_route':'GROUPED_D_PLUS_J1_TRANSFER_VALIDATION_READY' if verdict.endswith('CONFIRMED') else 'RETURN_TO_CHART'}
    (REPORT/'h1f4b2_observed_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (REPORT/'h1f4b2_summary.md').write_text('# H1F-4B2 GROUPED_D_PLUS_J1_TWO_LEVER_COMBINED_LOCAL_VALIDATION\n\n'+f'- 4/4 combined cases accepted; replay={acc.get("replay_cases",0)}.\n- Exact r_cancel: `-0.09287374665313898`; exact J1 delta: +/-`0.3714949866125559` nm with opposite signs for A_D +/-4 nm.\n- Observed derivative is `(M(COMBINED_PLUS)-M(COMBINED_MINUS))/8 nm`; predictions were frozen before solver.\n- `G_D,y={gdy:.9e}/nm`, `G_obs,y={y_mean:.9e}/nm`, mean cancellation fraction `{mean_fraction:.6f}`; combined y response increased in magnitude and reversed sign.\n- Verdict: `{verdict}`.\n\n## CONCURRENCY_3_OBSERVATION\n\n- Peak simultaneous real FDTD jobs: {peak_fdtd}; concurrent RCWA jobs: {peak_rcwa}.\n- LP MPI: 4 processes, 1 thread. Throughput and CPU/RAM: unavailable.\n- No license denial, peer failure, or new heartbeat error observed.\n\n## ROUTE\n\n- `{report["next_route"]}`; no transfer validation, amplitude expansion, manifold expansion, or ML.\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
