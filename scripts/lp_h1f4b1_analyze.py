import csv, json, math, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/stage_h1f4b1_j1_anisotropy_fullk6_compensator_probe'
FULL = REPORT / 'h1f4b1_order_resolved_fullwave.csv'
JONES = REPORT / 'h1f4b1_k6_order_jones.csv'
DCSV = ROOT / 'reports/stage_h1f4a_grouped_d_first_harmonic_jacobian_probe/h1f4a_central_difference_jacobian.csv'
RULE = ROOT / 'reports/stage_h1f4a_phase2_grouped_d_transfer_validation/H1F4A_PHASE2_DIRECTION_RULE_V1.json'

def rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def mean(v): return statistics.mean(v) if v else None
def stats(v):
    v=[float(x) for x in v if x is not None and math.isfinite(float(x))]
    if not v: return {'mean':None,'median':None,'min':None,'max':None,'std':None,'sign_consistency':None,'positive_count':0,'negative_count':0,'zero_count':0}
    return {'mean':mean(v),'median':statistics.median(v),'min':min(v),'max':max(v),'std':statistics.pstdev(v),'sign_consistency':all(x>0 for x in v) or all(x<0 for x in v),'positive_count':sum(x>0 for x in v),'negative_count':sum(x<0 for x in v),'zero_count':sum(x==0 for x in v)}
def f(r,k): return float(r[k])

def main():
    fr, jr, dr = rows(FULL), rows(JONES), rows(DCSV)
    waves=sorted({float(r['wavelength_nm']) for r in jr})
    plus=next(r for r in jr if float(r['j1_delta_nm'])>0); minus=next(r for r in jr if float(r['j1_delta_nm'])<0)
    # Candidate/polarization/order lookup for all scalar order metrics.
    lookup={(r['candidate_uid'],r['polarization'],float(r['wavelength_nm']),int(r['order_n']),int(r['order_m'])):r for r in fr}
    def scalar(pol, w, n, key='order_efficiency_source_norm'):
        vals=[]
        for uid in sorted({r['candidate_uid'] for r in fr}):
            r=lookup.get((uid,pol,w,n,0));
            if r: vals.append((float(r['j1_delta_nm']),f(r,key)))
        return vals
    def deriv(pol,w,n):
        v=scalar(pol,w,n); p=next((x for d,x in v if d>0),None); m=next((x for d,x in v if d<0),None)
        return None if p is None or m is None else (p-m)/4.0
    metrics={}
    for pol,name in [('x','eta_x'),('y','eta_y')]:
        for order,label in [(1,'plus1'),(0,'zero'),(-1,'minus1')]:
            vals=[deriv(pol,w,order) for w in waves]
            metrics[f'd_{name}_{label}_per_nm']=vals
            metrics[f'{name}_{label}_stats']=stats(vals)
    # Jones central difference, odd/even for complex entries.
    jm={(float(r['j1_delta_nm']),float(r['wavelength_nm'])):r for r in jr}
    jjac=[]
    for w in waves:
        p=jm[(2.0,w)]; m=jm[(-2.0,w)]
        out={'wavelength_nm':w}
        for k in ['txx_re','txx_im','txy_re','txy_im','tyx_re','tyx_im','tyy_re','tyy_im','eta_x_plus1','eta_y_plus1','target_projector_error','target_y_input_leakage_power']:
            pv=f(p,k); mv=f(m,k); out['d_'+k+'_per_nm']=(pv-mv)/4.0; out['odd_'+k]=(pv-mv)/2.0
        jjac.append(out)
    with (REPORT/'h1f4b1_j1_jacobian.csv').open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=jjac[0].keys()); wr.writeheader(); wr.writerows(jjac)
    # Frozen grouped-D directional Jacobian for eta_x,+1 and eta_y,+1.
    rule=json.loads(RULE.read_text(encoding='utf-8')); ua,ub=rule['u_a'],rule['u_b']
    gd={}
    for pol in ['x','y']:
        for w in waves:
            rr=[r for r in dr if r['polarization']==pol and float(r['wavelength_nm'])==w]
            a=next((f(r,'d_eta_target_per_nm') for r in rr if r['axis']=='A'),None); b=next((f(r,'d_eta_target_per_nm') for r in rr if r['axis']=='B'),None)
            gd[(pol,w)]=None if a is None or b is None else ua*a+ub*b
    gj={(pol,w):next((x[f'd_eta_{pol}_plus1_per_nm'] for x in jjac if x['wavelength_nm']==w),None) for pol in ['x','y'] for w in waves}
    gyD=[gd[('y',w)] for w in waves if gd[('y',w)] is not None]; gyJ=[gj[('y',w)] for w in waves if gj[('y',w)] is not None]
    r_cancel=None if not gyD or not gyJ or mean(gyJ)==0 else -mean(gyD)/mean(gyJ)
    cancel=[]
    for w in waves:
        cancel.append({'wavelength_nm':w,'g_D_eta_y_plus1_per_nm':gd[('y',w)],'g_J1_eta_y_plus1_per_nm':gj[('y',w)],'r_cancel':None if gd[('y',w)] is None or gj[('y',w)] in (None,0) else -gd[('y',w)]/gj[('y',w)]})
    # Combined prediction is explicit where grouped-D data exist; x0/x-1 D terms remain unavailable.
    combined=[]
    for w in waves:
        for pol,label in [('x','plus1'),('x','zero'),('x','minus1')]:
            key=f'd_eta_{pol}_{label}_per_nm'; j=metrics[key][waves.index(w)]
            combined.append({'wavelength_nm':w,'metric':f'eta_{pol}_{label}','g_D_per_nm':gd.get((pol,w)) if label=='plus1' else None,'g_J1_per_nm':j,'r_cancel':r_cancel,'predicted_combined_per_nm':None if (label=='plus1' and gd.get((pol,w)) is None) else (j + (0 if label!='plus1' else r_cancel*gd[(pol,w)] if r_cancel is not None else 0))})
    with (REPORT/'h1f4b1_cancellation.csv').open('w',newline='',encoding='utf-8') as h:
        wr=csv.DictWriter(h,fieldnames=combined[0].keys()); wr.writeheader(); wr.writerows(combined)
    # Response-plane cosine uses mean x/y +1 derivative vectors.
    vx=[x for x in metrics['d_eta_x_plus1_per_nm']]; vy=[x for x in metrics['d_eta_y_plus1_per_nm']]
    dx=[gd[('x',w)] for w in waves]; dy=[gd[('y',w)] for w in waves]
    dot=sum(a*b for a,b in zip(vx,vy)); nd=math.sqrt(sum(a*a for a in vx)*sum(b*b for b in vy)); cosJ=None if nd==0 else dot/nd
    dotd=sum(a*b for a,b in zip(dx,dy)); ndd=math.sqrt(sum(a*a for a in dx)*sum(b*b for b in dy)); cosD=None if ndd==0 else dotd/ndd
    report={'schema':'H1F4B1_ANALYSIS_V1','stage':'H1F-4B1','solver_entered_delta':4,'accepted_formal_cases':4,'wavelength_grid_nm':waves,'j1_jacobian':{'delta_span_nm':4.0,'eta_metrics':{k:v for k,v in metrics.items() if k.endswith('_stats')},'complex_jones_rows':len(jjac),'odd_response_definition':'(M(+2)-M(-2))/2','even_response_definition':'(M(+2)+M(-2))/2-M(0)','even_response':'unavailable_baseline_not_rerun','nonlinearity':'not separable from even response without baseline; no post-hoc threshold applied'},'grouped_d_directional_jacobian':{'u_a':ua,'u_b':ub,'eta_x_plus1_stats':stats([gd[('x',w)] for w in waves]),'eta_y_plus1_stats':stats([gd[('y',w)] for w in waves])},'cancellation':{'G_D_y_mean_per_nm':mean(gyD),'G_J1_y_mean_per_nm':mean(gyJ),'r_cancel':r_cancel,'per_wavelength':cancel,'broadband_stable':stats([x['r_cancel'] for x in cancel if x['r_cancel'] is not None])['sign_consistency']},'response_plane_cosine':{'j1_eta_x_plus1_eta_y_plus1':cosJ,'grouped_d_eta_x_plus1_eta_y_plus1':cosD},'concurrency_3_observation':{'peak_simultaneous_real_fdtd_jobs':3,'concurrent_rcwa_jobs':1,'lp_mpi_configuration':'4 MPI processes, 1 thread','throughput':'unavailable','cpu_ram':'unavailable','license_behavior':'no denial observed','controller_messaging':'one scheduler heartbeat WinError 5 during registry os.replace; solver cases accepted','cross_branch_failure':False},'ml_admitted':False,'verdict':'J1_ANISOTROPY_FULLK6_COMPENSATOR_LEVER_PARTIAL'}
    (REPORT/'h1f4b1_jacobian_cancellation_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (REPORT/'h1f4b1_summary.md').write_text('# H1F-4B1 J1 anisotropy full-K6 compensator Jacobian probe\n\n- 4/4 formal cases accepted; no replay.\n- J1 central difference uses (M(+2 nm)-M(-2 nm))/4 nm.\n- Grouped-D uses frozen H1F4A direction rule.\n- Controller telemetry recorded one heartbeat registry write permission error; no peer solver failure observed.\n- Verdict: `J1_ANISOTROPY_FULLK6_COMPENSATOR_LEVER_PARTIAL` pending Chart review.\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()

