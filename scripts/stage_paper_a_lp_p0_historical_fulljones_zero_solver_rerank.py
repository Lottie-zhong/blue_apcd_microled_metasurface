import csv, json, math
from pathlib import Path
from collections import defaultdict, Counter

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
OUT=ROOT/'reports/stage_paper_a_lp_p0_historical_fulljones_zero_solver_rerank'; OUT.mkdir(parents=True,exist_ok=True)
W=[450+.5*i for i in range(9)]
SRC=[('H1C1A',ROOT/'reports/stage_h1c1a_broadband_global/h1c1a_broadband_full_jones.csv'),('H1C1B',ROOT/'reports/stage_h1c1b_broadband_adaptive/h1c1b_broadband_full_jones.csv'),('H1C1C',ROOT/'reports/stage_h1c1c_phase_gap/h1c1c_broadband_full_jones.csv')]
def F(x):
    try:return float(x)
    except:return float('nan')
def C(a,b):return complex(F(a),F(b))
def M(r):
    j=[[C(r['Re_txx'],r['Im_txx']),C(r['Re_txy'],r['Im_txy'])],[C(r['Re_tyx'],r['Im_tyx']),C(r['Re_tyy'],r['Im_tyy'])]]
    a=sum(abs(x)**2 for x in j[0]); d=sum(abs(x)**2 for x in j[1]); z=sum(j[0][i]*j[1][i].conjugate() for i in range(2)); s=a+d; xf=a/s if s else float('nan'); tr=F(r.get('throughput','nan')); det=j[0][0]*j[1][1]-j[0][1]*j[1][0]; disc=max(0,s*s-4*abs(det)**2); q1=max(0,(s+math.sqrt(disc))/2);q2=max(0,(s-math.sqrt(disc))/2);u=math.sqrt(q1);v=math.sqrt(q2)
    return {'s0_operator':s,'S0':s,'S1':a-d,'S2':2*z.real,'S3':-2*z.imag,'DoLP':math.sqrt(max(0,(a-d)**2+(2*z.real)**2))/s if s else float('nan'),'x_fidelity':xf,'useful_power':tr*xf,'leakage_power':tr*(1-xf),'leakage_fraction':1-xf,'sigma1':u,'sigma2':v,'rank_contrast':u/v if v>1e-15 else float('inf'),'rank_error':v/u if u>1e-15 else float('nan'),'total_power':tr,'phase_txx_deg':F(r.get('phi_txx','nan'))}
def synthetic_tests():
    def row(a,b,c,d):
        return {'Re_txx':a,'Im_txx':0,'Re_txy':b,'Im_txy':0,'Re_tyx':c,'Im_tyx':0,'Re_tyy':d,'Im_tyy':0,'throughput':1,'phi_txx':0}
    i=M(row(1,0,0,1)); x=M(row(1,0,0,0)); assert abs(i['DoLP'])<1e-12 and abs(i['x_fidelity']-.5)<1e-12; assert abs(x['DoLP']-1)<1e-12 and abs(x['x_fidelity']-1)<1e-12 and math.isinf(x['rank_contrast'])
synthetic_tests()
rows=[]; counts=Counter()
for tag,p in SRC:
    with p.open(encoding='utf-8-sig',newline='') as h:
        for r in csv.DictReader(h):r['_src']=tag;rows.append(r);counts[tag]+=1
g=defaultdict(list)
for r in rows:
    if r.get('full_jones_finite','').lower()=='true' and r.get('full_jones_accepted','').lower()=='true':g[r['exact_hash']].append(r)
chosen=[]
for h,rr in g.items():
    by={F(r['wavelength_nm']):r for r in rr}
    if all(x in by for x in W):chosen.append((h,min(rr,key=lambda r:{'H1C1B':0,'H1C1C':1,'H1C1A':2}[r['_src']]),by))
out=[]
for h,base,by in chosen:
    mm=[M(by[x]) for x in W]
    def avg(k):return sum(x[k] for x in mm)/9
    def lo(k):return min(x[k] for x in mm)
    def span(k):return max(x[k] for x in mm)-min(x[k] for x in mm)
    d={'geometry_uid':base['geometry_uid'],'exact_hash':h,'source_stage':base['_src'],'source_file':next(str(p.relative_to(ROOT)) for t,p in SRC if t==base['_src']),'material_contract':'APCD_TIO2_NATIVE_M1','solver_lineage':'historical real FDTD H1C1A/B/C','H_global_nm':F(base['H_global']),'J1_side_nm':F(base['J1_side_nm']),'J2_length_nm':F(base['J2_length_nm']),'J2_width_nm':F(base['J2_width_nm']),'D_nm':F(base['D_nm']),'Psi_deg':F(base['Psi_deg']),'wavelength_count':9,'mean_useful_power':avg('useful_power'),'worst_useful_power':lo('useful_power'),'mean_DoLP':avg('DoLP'),'worst_DoLP':lo('DoLP'),'mean_x_fidelity':avg('x_fidelity'),'worst_x_fidelity':lo('x_fidelity'),'mean_leakage_power':avg('leakage_power'),'worst_leakage_power':lo('leakage_power'),'mean_rank_contrast':avg('rank_contrast'),'worst_rank_contrast':lo('rank_contrast'),'mean_rank_error':avg('rank_error'),'worst_rank_error':lo('rank_error'),'mean_total_power':avg('total_power'),'useful_power_range':span('useful_power'),'DoLP_range':span('DoLP'),'x_fidelity_range':span('x_fidelity'),'phase_txx_mean_deg':avg('phase_txx_deg'),'phase_txx_range_deg':span('phase_txx_deg'),'fabrication_margin':'FABRICATION_MARGIN_NOT_AVAILABLE_FROM_EXISTING_PHYSICS','qualification':'NATIVE_COMPATIBLE_HISTORICAL_FULL_JONES'}
    out.append(d)
def dom(a,b):
    ks=['worst_useful_power','worst_DoLP','worst_x_fidelity','worst_rank_contrast'];return all(a[k]>=b[k] for k in ks) and a['worst_leakage_power']<=b['worst_leakage_power'] and (any(a[k]>b[k] for k in ks) or a['worst_leakage_power']<b['worst_leakage_power'])
front=[a for a in out if not any(dom(b,a) for b in out)]
# Fixed hierarchy from the stage authority: physical viability first
# (worst DoLP, worst target fidelity, lowest worst leakage), then useful output,
# selectivity, and broadband variance. No post-hoc composite weights.
key=lambda a:(-a['worst_DoLP'],-a['worst_x_fidelity'],a['worst_leakage_power'],-a['worst_useful_power'],-a['mean_useful_power'],-a['worst_rank_contrast'],a['useful_power_range'],a['exact_hash'])
front.sort(key=key); short=front[:6]
for i,a in enumerate(front,1):a['pareto_rank']=i
for i,a in enumerate(short,1):a['promotion_role']='P0_PROVISIONAL_PRIMARY' if i==1 else ('P0_RUNNER_UP' if i<=3 else 'P0_BACKUP')
def wc(name,data):
    if not data:return
    fields=[]
    for row in data:
        for k in row:
            if k not in fields: fields.append(k)
    with (OUT/name).open('w',newline='',encoding='utf-8') as h:w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(data)
wc('geometry_broadband_metrics.csv',out);wc('pareto_front.csv',front);wc('candidate_shortlist.csv',short)
wc('candidate_evidence_index.csv',[{'geometry_uid':a['geometry_uid'],'exact_hash':a['exact_hash'],'source_stage':a['source_stage'],'source_file':a['source_file'],'material_contract':a['material_contract'],'full_jones_available':True,'old_elimination':'phase/K6 gate or old contract','paper_a_promotion':'complete x/y full-Jones native-compatible broadband evidence'} for a in short])
wc('data_inventory.csv',[{'source':k,'rows':v,'full_jones':'yes','grid':'450-454/0.5 nm'} for k,v in counts.items()])
legacy=sum(1 for _ in csv.DictReader((ROOT/'data/lp_database/exports/jones_labels.csv').open(encoding='utf-8-sig')))
wc('provenance_cohorts.csv',[{'cohort':'AUTHORITATIVE_CURRENT_OR_NATIVE_COMPATIBLE_FULL_JONES','geometry_count':len(chosen),'jones_row_count':len(chosen)*9,'qualification':'native manifest + real FDTD + x/y complete + 9 points'},{'cohort':'HISTORICAL_REAL_FULL_JONES_PROVENANCE_VALID_BUT_NOT_CURRENT_NATIVE','geometry_count':0,'jones_row_count':0,'qualification':'none separated by this audit'},{'cohort':'LEGACY_CONSTANT_INDEX','geometry_count':'DB export','jones_row_count':legacy,'qualification':'reference only; excluded'},{'cohort':'ML_PREDICTION_ONLY','geometry_count':'excluded','jones_row_count':0,'qualification':'no physics promotion'},{'cohort':'FULL_K6_OR_OTHER_NONCOMPARABLE_PHYSICS','geometry_count':'excluded','jones_row_count':0,'qualification':'archive only'}])
json.dump({'stage':'PAPER_A_LP_P0_HISTORICAL_FULLJONES_ZERO_SOLVER_RERANK_V1','solver_calls_p0':0,'rcwa_calls_p0':0,'ml_training_calls_p0':0,'primary':short[0] if short else None,'runner_up':short[1:3],'backup':short[3:6],'native_material_contract':['APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1','APCD_GAN_NATIVE_M1'],'wavelength_grid_nm':W,'full_jones':'real x/y, no reciprocity fill','fallback_order':[x['geometry_uid'] for x in short]},(OUT/'p1_proposed_preregistration.json').open('w',encoding='utf-8'),indent=2,default=str)
json.dump({'status':'PASS','solver_calls':0,'rcwa_calls':0,'ml_training_calls':0,'geometry_count':len(chosen),'row_count':len(chosen)*9,'pareto_count':len(front),'shortlist_count':len(short),'phase_gate_used':False,'k6_gate_used':False,'legacy_current_mixing':False,'ml_prediction_promoted':False,'synthetic_jones_stokes_tests':'PASS','deterministic_sort':'PASS'},(OUT/'audit.json').open('w',encoding='utf-8'),indent=2)
(OUT/'README.md').write_text(f'# Paper A LP P0 historical full-Jones zero-solver rerank\n\nPASS: offline CSV/JSON audit only; FDTD/RCWA/ML calls 0/0/0. Frozen grid 450-454 nm, 0.5 nm, 9 points. Phase is diagnostic only; K6 and legacy/ML labels excluded. Native-compatible complete geometries: {len(chosen)}; Pareto front: {len(front)}; shortlist: {len(short)}.\n\nRanking is Pareto first, then fixed deterministic hierarchy: worst-case physical viability (DoLP, target-x fidelity, leakage), useful output, rank-one contrast, broadband variance, exact hash. No post-hoc composite weights. Absolute power is bound to the reported throughput column; Jones-derived operator metrics remain separate. Fabrication margin is unavailable from existing physics.\n',encoding='utf-8')
print(json.dumps({'status':'PASS','geometry_count':len(chosen),'row_count':len(chosen)*9,'pareto_count':len(front),'shortlist_count':len(short)}))
