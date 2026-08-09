import csv, json, math, os, glob, hashlib, statistics, itertools, subprocess, datetime, re

ROOT = r'D:\project\worktrees\blue_apcd_lp_stage11_4'
ANALYSIS = os.path.join(ROOT, 'outputs', 'lp_ml_dataset_v1', 'analysis')
PLANS = os.path.join(ROOT, 'outputs', 'lp_ml_dataset_v1', 'plans')
REPORTS = os.path.join(ROOT, 'reports')
SCRIPT_NAME = 'scripts/lp_ml_inverse_stage1_5d_phase_reachability_audit_v1.py'
EXPECTED_MATRIX_SHA = 'accd073c7d27086debc80e21056dade6b534080bc6e5d4fbb7025821587348f0'
EXPECTED_CONTRACT_SHA = '7f3ecb0468bb29a86f5bd5ff1da4cd833ee057acf9fb41fc6ad0346e630ff926'
PROTECTED = [
    'reports/lp_ml1a3_git_history_geometry_reconstruction.md',
    'reports/stage11_4a20_legacy_fsp_object_inventory.md',
]
OUT = {
    'ledger_csv': 'lp_ml_inverse_stage1_5d_phase_compatibility_ledger_v1.csv',
    'ledger_json': 'lp_ml_inverse_stage1_5d_phase_compatibility_ledger_v1.json',
    'phase_csv': 'lp_ml_inverse_stage1_5d_all_compatible_phase_table_v1.csv',
    'envelope_json': 'lp_ml_inverse_stage1_5d_observed_phase_envelope_v1.json',
    'conditioned_json': 'lp_ml_inverse_stage1_5d_projector_conditioned_envelope_v1.json',
    'leverage_json': 'lp_ml_inverse_stage1_5d_geometry_phase_leverage_v1.json',
    'boundary_json': 'lp_ml_inverse_stage1_5d_boundary_coverage_v1.json',
    'surrogate_csv': 'lp_ml_inverse_stage1_5d_508_surrogate_phase_forensics_v1.csv',
    'surrogate_json': 'lp_ml_inverse_stage1_5d_508_surrogate_phase_forensics_v1.json',
    'dense_json': 'lp_ml_inverse_stage1_5d_dense_surrogate_reachability_v1.json',
    'decision_json': 'lp_ml_inverse_stage1_5d_reachability_decision_v1.json',
    'checksums_json': 'lp_ml_inverse_stage1_5d_reachability_checksums_v1.json',
    'plan_csv': 'lp_5d_phase_reachability_probe_v1.csv',
    'plan_json': 'lp_5d_phase_reachability_probe_v1.json',
    'route_contract': 'lp_5d_phase_reachability_probe_route_contract_v1.json',
}

def ensure_dirs():
    os.makedirs(ANALYSIS, exist_ok=True); os.makedirs(PLANS, exist_ok=True); os.makedirs(REPORTS, exist_ok=True)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))

def write_csv(path, rows, fields=None):
    if fields is None:
        fields=[]
        for r in rows:
            for k in r:
                if k not in fields: fields.append(k)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f: json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True)

def n(v, default=None):
    try:
        if v is None or str(v).strip()=='': return default
        x=float(v); return x if math.isfinite(x) else default
    except Exception: return default

def b(v): return str(v).strip().lower() in ('1','true','yes','pass','accepted','complete','admitted')

def first(row, names, default=None):
    for k in names:
        if k in row and str(row[k]).strip()!='': return row[k]
    return default

def phase(row):
    re=n(first(row,['txx_real','real_txx','txx_re'])); im=n(first(row,['txx_imag','imag_txx','txx_im']))
    if re is None or im is None: return None
    x=math.degrees(math.atan2(im,re))%360.0
    return x

def jmetric(row):
    p=phase(row)
    return {
        'phase_deg': p,
        'abs_txx': math.hypot(n(first(row,['txx_real'])) or 0.0,n(first(row,['txx_imag'])) or 0.0),
        'Txx': n(first(row,['Txx','target_transmission'])),
        'Tyy': n(first(row,['Tyy'])),
        'projector_error': n(first(row,['projection_error_apcd_v1','matrix_projection_error','projection_error','projection_error_apcd'])),
        'sigma2_sigma1': n(first(row,['sigma2_over_sigma1','sigma2_sigma1'])),
        'leakage': n(first(row,['combined_leakage','leakage_sum','leakage'])),
        'throughput': n(first(row,['target_transmission','Txx'])),
    }

def is054(row):
    # Only explicit candidate/quarantine identity is authoritative. Never
    # search opaque geometry hashes for the substring "054".
    ids=' '.join(str(row.get(k,'')) for k in ('candidate_id','legacy_case_id','logical_candidate_id','candidate_instance_id','supersedes_candidate_id'))
    # quarantine_identity in clean-v3 is a manifest-level annotation repeated
    # on every row; it is deliberately not used as an exclusion predicate.
    qstatus=str(row.get('quarantine_status','')).upper()
    if 'LPML_R1_GLOBAL_SOBOL_054' in ids: return True
    if 'QUARANTINED' in qstatus and re.search(r'(^|[_\-\s])054($|[_\-\s])', ids): return True
    return bool(re.search(r'(^|[_\-\s])054($|[_\-\s])', ids))

def finite_jones(row):
    return all(n(row.get(k)) is not None for k in ('txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag'))

def normrow(row, source, cls, reason):
    rr=dict(row); m=jmetric(row)
    rr.update({'source_name':source,'compatibility_class':cls,'compatibility_reason':reason,'phase_deg_calc':m['phase_deg']})
    rr['exact_hash_norm']=first(row,['exact_geometry_hash_sha256','exact_geometry_hash','geometry_hash_sha256','geometry_hash','geometry_hash_sha256']) or ''
    rr['J1_side_nm']=first(row,['J1_side_nm','J1_side']); rr['J2_length_nm']=first(row,['J2_length_nm','J2_length'])
    rr['J2_width_nm']=first(row,['J2_width_nm','J2_width']); rr['D_nm']=first(row,['D_nm','D']); rr['Psi_deg']=first(row,['Psi_deg','Psi'])
    for k,v in m.items(): rr[k]=v
    return rr

def spearman(xs, ys):
    z=[(x,y) for x,y in zip(xs,ys) if x is not None and y is not None]
    if len(z)<3: return None
    def ranks(a):
        order=sorted(range(len(a)), key=lambda i:a[i]); out=[0.0]*len(a); i=0
        while i<len(a):
            j=i
            while j+1<len(a) and a[order[j+1]]==a[order[i]]: j+=1
            r=(i+j)/2+1
            for k in range(i,j+1): out[order[k]]=r
            i=j+1
        return out
    rx,ry=ranks([q[0] for q in z]),ranks([q[1] for q in z]); mx=sum(rx)/len(rx); my=sum(ry)/len(ry)
    nume=sum((a-mx)*(b-my) for a,b in zip(rx,ry)); den=math.sqrt(sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))
    return nume/den if den else 0.0

def quantile(vals,q):
    vals=sorted(v for v in vals if v is not None)
    if not vals: return None
    return vals[min(len(vals)-1,max(0,int(round((len(vals)-1)*q))))]

def phase_summary(rows):
    vals=sorted(r['phase_deg'] for r in rows if r.get('phase_deg') is not None)
    if not vals: return {'count':0}
    gaps=[]
    for a,bv in zip(vals,vals[1:]): gaps.append(bv-a)
    gaps.append(vals[0]+360-vals[-1])
    lg=max(gaps); return {'count':len(vals),'min_phase_deg':min(vals),'max_phase_deg':max(vals),'linear_span_deg':max(vals)-min(vals),'circular_coverage_deg':360-lg,'largest_uncovered_circular_arc_deg':lg,'phase_values_deg':vals[:5]+(['...'] if len(vals)>10 else [])+vals[-5:]}

def pareto(rows):
    if not rows: return []
    lo=min(r['phase_deg'] for r in rows); hi=max(r['phase_deg'] for r in rows)
    def score(r):
        return min(r['phase_deg']-lo, hi-r['phase_deg'])
    # Keep phase extremes not dominated by lower error/leakage and higher throughput.
    out=[]
    for r in rows:
        dominated=False
        for q in rows:
            if q is r: continue
            if score(q)<=score(r) and (q.get('projector_error') or 1e9)<=(r.get('projector_error') or 1e9) and (q.get('leakage') or 1e9)<=(r.get('leakage') or 1e9) and (q.get('sigma2_sigma1') or 1e9)<=(r.get('sigma2_sigma1') or 1e9) and (q.get('throughput') or -1)>=(r.get('throughput') or -1) and (score(q)<score(r) or q.get('projector_error')!=r.get('projector_error')):
                dominated=True; break
        if not dominated: out.append(r)
    return out

def git(cmd):
    try: return subprocess.check_output(cmd,cwd=ROOT,shell=True,text=True,stderr=subprocess.STDOUT).strip()
    except Exception as e: return 'ERROR:'+str(e)

def main():
    ensure_dirs(); created=datetime.datetime.utcnow().isoformat()+'Z'
    matrix=os.path.join(ROOT,'outputs/lp_ml_dataset_v1/contracts/lp_linear_x_projector_target_matrix_v1.json')
    try: contract_obj=json.load(open(matrix,encoding='utf-8'))
    except Exception: contract_obj={}
    matrix_file_sha=sha(matrix) if os.path.exists(matrix) else None
    matrix_payload_sha=contract_obj.get('matrix_sha256')
    contract_sha=matrix_file_sha
    protected_hashes={p:(sha(os.path.join(ROOT,p)) if os.path.exists(os.path.join(ROOT,p)) else None) for p in PROTECTED}
    # Sources are explicit; other historical artefacts are inventoried but never silently admitted.
    source_paths={
        'clean_v3': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv'),
        'stage1_prospective': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/staging/lp_ml_inverse_stage1_fdt_validation_v1/candidate_wavelength_jones_v1.csv'),
        'canonical_v1_21': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/canonical_v1_21/candidate_wavelength_jones_v1_17.csv'),
        'd6': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/staging/b120_j2lm06_positional_jacobian_stage_d6_v1_attempt1_lp_ml_schema_v1_22/candidate_wavelength_jones_v1_22.csv'),
        'd5': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/staging/b120_j2lm06_stage_d5_perturbation_data_finalized_lp_ml_schema_v1_21/candidate_wavelength_jones_v1_21.csv'),
        'legacy_h500': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/staging/legacy_h500_formal_replay_450_v1/candidate_wavelength_jones_v1.csv'),
        'original22': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_original22_complete_jones_manifest_after_regeneration_v1.csv'),
        'bounded6': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_bounded6_full_jones_retrospective_candidate_residuals_v1.csv'),
        'delta_batches': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_stage_d7_d8_joint_candidate_metrics_v1.csv'),
        'stage11_12_13': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/analysis/stage11_12_13_lp_compatibility_inventory_v1.csv'),
        'surrogate_508': os.path.join(ROOT,'outputs/lp_ml_dataset_v1/analysis/lp_ml_round3_recalibrated_508_candidate_table_v1.csv'),
    }
    classes={
        'clean_v3':('FORMAL_CONTRACT_EXACT_COMPATIBLE','clean-v3 admitted formal weighted-G0, 450nm rows with complete x/y and frozen Native-M1/H500/period metadata'),
        'stage1_prospective':('FORMAL_CONTRACT_NUMERICALLY_TRANSFORMABLE','formal weighted-G0 Jones fields and 450nm complete x/y; package omits some immutable setup metadata'),
        'canonical_v1_21':('HISTORICAL_REFERENCE_ONLY','canonical rows are retained for comparison only because their stored phase reference is not uniquely transformable to the frozen P_APCD gauge'),
        'd6':('FORMAL_CONTRACT_EXACT_COMPATIBLE','D6 formal_full_dimer_450 rows with hashes, weighted-G0 and checkpoint provenance'),
        'd5':('HISTORICAL_REFERENCE_ONLY','derived D5 table lacks a complete immutable setup contract for independent reachability admission'),
        'legacy_h500':('HISTORICAL_REFERENCE_ONLY','legacy replay requires historical provenance and is not used to override the frozen hard gate'),
        'original22':('HISTORICAL_REFERENCE_ONLY','original22 full-Jones reconstruction permanently unavailable; HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE preserved'),
        'bounded6':('HISTORICAL_REFERENCE_ONLY','retrospective bounded6 evidence is not historical primary validation'),
        'delta_batches':('FORMAL_CONTRACT_NUMERICALLY_TRANSFORMABLE','delta artifacts may be numeric references only; no admission without complete immutable x/y provenance'),
        'stage11_12_13':('INCOMPATIBLE_EXCLUDE','different stage/configuration or no unique frozen weighted-G0 contract'),
    }
    contract_fields={
        'clean_v3':{'material':'APCD_TIO2_NATIVE_M1','wavelength_nm':'450','H_nm':'500','period_nm':'432x432','reference_plane':'transmission-side z=1000 nm','monitor_extraction':'field_monitor full-period','weighted_G0':'YES','endpoint_dedup':'YES','periodic_reclosure':'YES','normalization':'sqrt(T)/norm(weighted Ex,Ey)','jones_basis':'linear_xy [[txx,txy],[tyx,tyy]]','xy_completeness':'complete','geometry_convention':'native exact geometry/hash','phase_reference':'P_APCD arg(txx)'},
        'd6':{'material':'APCD_TIO2_NATIVE_M1','wavelength_nm':'450','H_nm':'500','period_nm':'432x432','reference_plane':'transmission-side z=1000 nm','monitor_extraction':'field_monitor full-period','weighted_G0':'YES','endpoint_dedup':'YES','periodic_reclosure':'YES','normalization':'sqrt(T)/norm(weighted Ex,Ey)','jones_basis':'linear_xy','xy_completeness':'complete','geometry_convention':'native exact geometry/hash','phase_reference':'P_APCD arg(txx)'},
        'stage1_prospective':{'material':'PACKAGE_METADATA_REQUIRED','wavelength_nm':'450','H_nm':'PACKAGE_METADATA_REQUIRED','period_nm':'PACKAGE_METADATA_REQUIRED','reference_plane':'PACKAGE_METADATA_REQUIRED','monitor_extraction':'FORMAL_WEIGHTED_G0_DECLARED','weighted_G0':'YES','endpoint_dedup':'PACKAGE_METADATA_REQUIRED','periodic_reclosure':'PACKAGE_METADATA_REQUIRED','normalization':'FORMAL_DECLARED; setup fields absent','jones_basis':'linear_xy','xy_completeness':'complete','geometry_convention':'exact hash present','phase_reference':'P_APCD arg(txx)'},
        'canonical_v1_21':{'material':'PACKAGE_METADATA_REQUIRED','wavelength_nm':'450','H_nm':'PACKAGE_METADATA_REQUIRED','period_nm':'PACKAGE_METADATA_REQUIRED','reference_plane':'PACKAGE_METADATA_REQUIRED','monitor_extraction':'HISTORICAL_PACKAGE','weighted_G0':'DECLARED','endpoint_dedup':'PACKAGE_METADATA_REQUIRED','periodic_reclosure':'PACKAGE_METADATA_REQUIRED','normalization':'PACKAGE_METADATA_REQUIRED','jones_basis':'linear_xy','xy_completeness':'checkpoint rows','geometry_convention':'hash only','phase_reference':'NOT_UNIQUELY_TRANSFORMABLE'},
        'd5':{'material':'UNKNOWN','wavelength_nm':'450','H_nm':'UNKNOWN','period_nm':'UNKNOWN','reference_plane':'UNKNOWN','monitor_extraction':'UNKNOWN','weighted_G0':'DERIVED_TABLE_ONLY','endpoint_dedup':'UNKNOWN','periodic_reclosure':'UNKNOWN','normalization':'UNKNOWN','jones_basis':'linear_xy fields','xy_completeness':'derived','geometry_convention':'hash fields incomplete','phase_reference':'UNKNOWN'},
        'legacy_h500':{'material':'LEGACY/UNKNOWN','wavelength_nm':'450','H_nm':'500','period_nm':'UNKNOWN','reference_plane':'UNKNOWN','monitor_extraction':'LEGACY','weighted_G0':'HISTORICAL','endpoint_dedup':'UNKNOWN','periodic_reclosure':'UNKNOWN','normalization':'LEGACY/UNKNOWN','jones_basis':'linear_xy','xy_completeness':'historical','geometry_convention':'legacy','phase_reference':'HISTORICAL_REFERENCE_ONLY'},
        'original22':{'material':'MIXED/HISTORICAL','wavelength_nm':'450','H_nm':'UNKNOWN','period_nm':'UNKNOWN','reference_plane':'UNKNOWN','monitor_extraction':'HISTORICAL','weighted_G0':'NOT_RECONSTRUCTABLE','endpoint_dedup':'UNKNOWN','periodic_reclosure':'UNKNOWN','normalization':'UNKNOWN','jones_basis':'linear_xy','xy_completeness':'historical hard gate','geometry_convention':'original22','phase_reference':'HISTORICAL_HARD_GATE'},
        'bounded6':{'material':'MIXED/HISTORICAL','wavelength_nm':'450','H_nm':'UNKNOWN','period_nm':'UNKNOWN','reference_plane':'UNKNOWN','monitor_extraction':'RETROSPECTIVE','weighted_G0':'RETROSPECTIVE','endpoint_dedup':'UNKNOWN','periodic_reclosure':'UNKNOWN','normalization':'UNKNOWN','jones_basis':'linear_xy','xy_completeness':'retrospective','geometry_convention':'bounded6','phase_reference':'NOT_PRIMARY_VALIDATION'},
        'delta_batches':{'material':'PACKAGE_DEPENDENT','wavelength_nm':'450','H_nm':'PACKAGE_DEPENDENT','period_nm':'PACKAGE_DEPENDENT','reference_plane':'PACKAGE_DEPENDENT','monitor_extraction':'DELTA_ONLY','weighted_G0':'DELTA_ONLY','endpoint_dedup':'PACKAGE_DEPENDENT','periodic_reclosure':'PACKAGE_DEPENDENT','normalization':'PACKAGE_DEPENDENT','jones_basis':'linear_xy','xy_completeness':'delta','geometry_convention':'hash-dependent','phase_reference':'REFERENCE_ONLY'},
        'stage11_12_13':{'material':'DIFFERENT_STAGE','wavelength_nm':'VARIES','H_nm':'VARIES','period_nm':'VARIES','reference_plane':'VARIES','monitor_extraction':'VARIES','weighted_G0':'NOT_UNIQUE','endpoint_dedup':'UNKNOWN','periodic_reclosure':'UNKNOWN','normalization':'VARIES','jones_basis':'VARIES','xy_completeness':'VARIES','geometry_convention':'VARIES','phase_reference':'INCOMPATIBLE'},
        'surrogate_508':{'material':'NONE','wavelength_nm':'450 target metadata','H_nm':'prediction table','period_nm':'prediction table','reference_plane':'NONE','monitor_extraction':'NONE','weighted_G0':'NONE','endpoint_dedup':'NONE','periodic_reclosure':'NONE','normalization':'NONE','jones_basis':'predicted fields absent','xy_completeness':'NONE','geometry_convention':'surrogate coordinates','phase_reference':'NOT_PHYSICS'},
    }
    ledger=[]; admitted=[]; source_counts={}
    priority={'clean_v3':0,'d6':1,'stage1_prospective':2}
    for name,path in source_paths.items():
        rows=read_csv(path); cls,reason=classes.get(name,('INCOMPATIBLE_EXCLUDE','not admitted'))
        total=len(rows); cand=[]; bad054=0; bad054_all=sum(1 for rr in rows if is054(rr)); good=0
        for row in rows:
            if n(row.get('wavelength_nm'),450.0)!=450.0: continue
            if is054(row): bad054+=1; continue
            if not finite_jones(row): continue
            h=first(row,['exact_geometry_hash_sha256','exact_geometry_hash','geometry_hash_sha256','geometry_hash'])
            complete=b(row.get('Jones_complete')) or (b(row.get('candidate_checkpoint_reload_pass')) and bool(h))
            xok=b(row.get('source_polarization_x_status')) or b(row.get('x_status')) or True
            yok=b(row.get('source_polarization_y_status')) or b(row.get('y_status')) or True
            if cls in ('FORMAL_CONTRACT_EXACT_COMPATIBLE','FORMAL_CONTRACT_NUMERICALLY_TRANSFORMABLE') and complete and h:
                rr=normrow(row,name,cls,reason); cand.append(rr); good+=1
        source_counts[name]={'path':path,'exists':os.path.exists(path),'sha256':sha(path) if os.path.exists(path) else None,'rows_total':total,'rows_450_complete_non054':good,'rows_054_excluded_450':bad054,'rows_054_excluded_all_wavelengths':bad054_all,'classification':cls,'reason':reason,**contract_fields.get(name,{})}
        ledger.append(source_counts[name])
        if name in priority:
            admitted.extend(cand)
    # Deduplicate formal candidates by exact hash; retain highest source priority.
    byhash={}
    for r in admitted:
        h=r.get('exact_hash_norm') or (r.get('candidate_id')+'|'+r.get('source_name'))
        if h not in byhash or priority.get(r['source_name'],99)<priority.get(byhash[h]['source_name'],99): byhash[h]=r
    admitted=list(byhash.values()); admitted.sort(key=lambda r:(str(r.get('exact_hash_norm')),str(r.get('candidate_id'))))
    for r in admitted: r['admitted_formal_reachability_physics']=True; r['physics_label']='OBSERVED_PHYSICS_PHASE_ENVELOPE'; r['solver_calls']=0
    write_csv(os.path.join(ANALYSIS,OUT['phase_csv']),admitted)
    ledger_fields=['path','exists','sha256','rows_total','rows_450_complete_non054','rows_054_excluded_450','rows_054_excluded_all_wavelengths','classification','reason','material','wavelength_nm','H_nm','period_nm','reference_plane','monitor_extraction','weighted_G0','endpoint_dedup','periodic_reclosure','normalization','jones_basis','xy_completeness','geometry_convention','phase_reference']
    write_csv(os.path.join(ANALYSIS,OUT['ledger_csv']),ledger,fields=ledger_fields)
    ledger_obj={'created_utc':created,'formal_phase_definition':'arg(txx)=atan2(Im(txx),Re(txx)) in degrees modulo 360','matrix_payload_sha256':matrix_payload_sha,'matrix_payload_expected_sha256':EXPECTED_MATRIX_SHA,'matrix_payload_hash_pass':matrix_payload_sha==EXPECTED_MATRIX_SHA,'formal_contract_file_sha256':contract_sha,'formal_contract_expected_sha256':EXPECTED_CONTRACT_SHA,'formal_contract_hash_pass':contract_sha==EXPECTED_CONTRACT_SHA,'formal_target':'P_APCD=diag(1,0)','historical_hard_gate':'HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE','sources':ledger,'admitted_unique_geometry_count':len(admitted),'geometry054_admitted_rows':sum(1 for r in admitted if is054(r)),'solver_calls':0,'protected_hashes':protected_hashes}
    write_json(os.path.join(ANALYSIS,OUT['ledger_json']),ledger_obj)
    env=phase_summary(admitted); env.update({'label':'OBSERVED_PHYSICS_PHASE_ENVELOPE','not_true_5d_limit':True,'source_counts':{k:v['rows_450_complete_non054'] for k,v in source_counts.items()},'formal_contract_exact_geometry_count':len(admitted)})
    write_json(os.path.join(ANALYSIS,OUT['envelope_json']),env)
    # Projector-conditioned, threshold-free descriptive slices.
    pe=[r.get('projector_error') for r in admitted if r.get('projector_error') is not None]; medpe=quantile(pe,.5)
    ordered=sorted(admitted,key=lambda r:(r.get('projector_error') if r.get('projector_error') is not None else 1e9))
    slices={'all':admitted,'best25':ordered[:max(1,int(math.ceil(len(ordered)*.25)))],'best50':ordered[:max(1,int(math.ceil(len(ordered)*.5)))]}
    cond={k:phase_summary(v) for k,v in slices.items()}; thr=quantile([r.get('throughput') for r in admitted],.5)
    cond['throughput_ge_median']=phase_summary([r for r in admitted if r.get('throughput') is not None and r.get('throughput')>=thr])
    pf=pareto(admitted); cond['pareto_front_count']=len(pf); cond['pareto_front_ids']=[r.get('candidate_id') for r in pf[:100]]
    cond['median_projector_error']=medpe; cond['conditioning_rule']='quantile slices only; no new absolute PASS threshold'; cond['tradeoff_classification']='PHASE_PROJECTOR_TRADEOFF' if cond['best25'].get('min_phase_deg')!=cond['all'].get('min_phase_deg') or cond['best25'].get('linear_span_deg',0)<cond['all'].get('linear_span_deg',0)-2 else 'NO_CLEAR_PROJECTOR_TRADEOFF'
    write_json(os.path.join(ANALYSIS,OUT['conditioned_json']),cond)
    # Geometry leverage on rows with explicit 5D coordinates.
    dims=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg']; geo=[]
    for r in admitted:
        if all(n(r.get(d)) is not None for d in dims) and r.get('phase_deg') is not None:
            q=dict(r); [q.__setitem__(d,n(q[d])) for d in dims]; geo.append(q)
    leverage={'n_rows_with_5d_coordinates':len(geo),'spearman_phase_deg':{},'binned_stats':{},'local_finite_differences':{},'extrema':{}}
    for d in dims:
        xs=[q[d] for q in geo]; ys=[q['phase_deg'] for q in geo]; leverage['spearman_phase_deg'][d]=spearman(xs,ys)
        lo,hi=min(xs),max(xs); bins=[]
        for j in range(4):
            a=lo+(hi-lo)*j/4; z=hi if j==3 else lo+(hi-lo)*(j+1)/4; vv=[q['phase_deg'] for q in geo if a<=q[d] and (q[d]<=z if j==3 else q[d]<z)]
            bins.append({'bin':j,'range':[a,z],'count':len(vv),'mean_phase_deg':statistics.mean(vv) if vv else None,'min_phase_deg':min(vv) if vv else None,'max_phase_deg':max(vv) if vv else None})
        leverage['binned_stats'][d]={'min':lo,'max':hi,'bins':bins}
        # pairs differing only one dimension
        dif=[]; idx={tuple(q[x] for x in dims):q for q in geo}
        for key,q in idx.items():
            for step in sorted(set([abs(v) for v in xs if v!=0]))[:0]: pass
            for j in range(len(dims)):
                if dims[j]!=d: continue
                for s in (-1,1):
                    vals=list(key); vals[j]=key[j]+s
                    if tuple(vals) in idx:
                        q2=idx[tuple(vals)]; dif.append({'delta_coordinate':s,'phase_delta_deg':q2['phase_deg']-q['phase_deg']})
        leverage['local_finite_differences'][d]={'count':len(dif),'median_phase_delta_deg':statistics.median([x['phase_delta_deg'] for x in dif]) if dif else None,'samples':dif[:50]}
        leverage['extrema'][d]={'min_phase_rows':sorted(geo,key=lambda q:q['phase_deg'])[:3] and [{'candidate_id':q.get('candidate_id'),'phase_deg':q['phase_deg'],'value':q[d]} for q in sorted(geo,key=lambda q:q['phase_deg'])[:3]],'max_phase_rows':[{'candidate_id':q.get('candidate_id'),'phase_deg':q['phase_deg'],'value':q[d]} for q in sorted(geo,key=lambda q:q['phase_deg'],reverse=True)[:3]]}
    leverage['interpretation']={'J1_side':'correlation is descriptive only','J2_length':'no surrogate gradients used','J2_width':'local differences require actual nearby rows','D':'primarily interference/projector proxy if weak phase correlation','Psi':'effective only if actual finite differences support it'}
    write_json(os.path.join(ANALYSIS,OUT['leverage_json']),leverage)
    # Boundary coverage relative to observed support; frozen manufacturing bounds are not inferred.
    boundary={'label':'OBSERVED_SUPPORT_BOUNDARY_COVERAGE_NOT_TRUE_MANUFACTURING_LIMIT','dims':{},'phase_extreme_distance_to_observed_boundary':{},'frozen_bounds_status':'NOT_RESOLVED_FROM_SINGLE_CANONICAL_ARTIFACT','n_unique_5d':len(geo)}
    for d in dims:
        vals=[q[d] for q in geo]; lo,hi=min(vals),max(vals); boundary['dims'][d]={'observed_min':lo,'observed_max':hi,'min_occupancy':sum(1 for q in geo if q[d]==lo),'max_occupancy':sum(1 for q in geo if q[d]==hi),'normalized_boundary_distance_min':0.0,'normalized_boundary_distance_max':0.0}
    phase_lo=min((q['phase_deg'] for q in geo),default=None); phase_hi=max((q['phase_deg'] for q in geo),default=None)
    for tag,fun in [('min_phase',lambda q:q['phase_deg']==phase_lo),('max_phase',lambda q:q['phase_deg']==phase_hi)]:
        qs=[q for q in geo if fun(q)]; boundary['phase_extreme_distance_to_observed_boundary'][tag]=[{'candidate_id':q.get('candidate_id'),'coordinate':{d:q[d] for d in dims},'distance_to_observed_support_boundary':min(min(abs(q[d]-boundary['dims'][d]['observed_min']) for d in dims),min(abs(q[d]-boundary['dims'][d]['observed_max']) for d in dims))} for q in qs[:10]]
    write_json(os.path.join(ANALYSIS,OUT['boundary_json']),boundary)
    # 508 surrogate forensic: use stored prediction fields only; never substitute target phase.
    s508=read_csv(source_paths['surrogate_508']); pred_candidates=[]
    for p in glob.glob(os.path.join(ANALYSIS,'**','*.csv'),recursive=True):
        if p==source_paths['surrogate_508']: continue
        try:
            with open(p,encoding='utf-8-sig',newline='') as f:
                h=next(csv.reader(f),[])
            if any('predicted_txx' in x.lower() or ('txx' in x.lower() and 'pred' in x.lower()) for x in h): pred_candidates.append(p)
        except Exception: pass
    headers=list(s508[0].keys()) if s508 else []
    txx_fields=[h for h in headers if 'txx' in h.lower() and ('pred' in h.lower() or 'model' in h.lower())]
    sur_rows=[]
    envlo=env.get('min_phase_deg'); envhi=env.get('max_phase_deg')
    for r in s508:
        tp=n(r.get('target_phase_deg')); cls='TARGET_PHASE_ONLY_NOT_PREDICTED'
        if tp is not None and envlo is not None and envhi is not None:
            if tp<envlo or tp>envhi: cls='TARGET_PHASE_OUTSIDE_OBSERVED_SUPPORT_NOT_SURROGATE_PHYSICS'
            elif tp-envlo<2 or envhi-tp<2: cls='TARGET_PHASE_NEAR_SUPPORT_EDGE_NOT_SURROGATE_PHYSICS'
        sur_rows.append({'candidate_id':r.get('candidate_id'),'target_phase_deg':tp,'predicted_phase_deg':None,'beyond_support_distance_deg':max(envlo-tp if tp is not None and envlo is not None else 0,tp-envhi if tp is not None and envhi is not None else 0,0),'classification':cls,'txx_prediction_fields':','.join(txx_fields),'c0_c1_c5_disagreement':'UNAVAILABLE','physics_claim':'NONE_SURROGATE_ONLY','source_row':r.get('candidate_id')})
    write_csv(os.path.join(ANALYSIS,OUT['surrogate_csv']),sur_rows)
    sur_summary={'n_508_rows':len(s508),'stored_prediction_fields':txx_fields,'alternate_prediction_tables':pred_candidates[:20],'prediction_phase_recomputable':bool(txx_fields),'classification_counts':{},'b3_b4_b5_surrogate_extrapolation':'INDETERMINATE_WITHOUT_PREDICTED_TXX_FIELDS','training_cloud_distance':'UNAVAILABLE','origin_crossing':'UNAVAILABLE','low_abs_txx_shortcut':'UNAVAILABLE','label':'SURROGATE_FORENSIC_NOT_FORMAL_PHYSICS'}
    for r in sur_rows: sur_summary['classification_counts'][r['classification']]=sur_summary['classification_counts'].get(r['classification'],0)+1
    write_json(os.path.join(ANALYSIS,OUT['surrogate_json']),sur_summary)
    dense={'requested_points':200000,'executed_points':0,'status':'DENSE_SCAN_NOT_EXECUTED_MODEL_UNAVAILABLE','label':'SURROGATE_REACHABILITY_HYPOTHESIS_ONLY','reason':'No stored C0/C1/C5/planning-blend predicted complex txx fields were found; target_phase is not substituted for prediction. No physics claim and no solver.','solver_calls':0}
    write_json(os.path.join(ANALYSIS,OUT['dense_json']),dense)
    # Offline-only probe plan; no geometry hash or runnable execution package.
    coords=[]
    for q in geo:
        coords.append(tuple(q[d] for d in dims))
    unique=list(dict.fromkeys(coords)); low=sorted(geo,key=lambda q:q['phase_deg'])[:6]; high=sorted(geo,key=lambda q:q['phase_deg'],reverse=True)[:6];
    plan=[]; roles=[('LOW_PHASE_EXTREME',low),('HIGH_PHASE_EXTREME',high)]
    used=set()
    def add(role,q,idx):
        base=tuple(q[d] for d in dims); candidate=list(base); j=idx%len(dims); vals=sorted(set(x[j] for x in coords));
        if vals:
            pos=min(range(len(vals)),key=lambda k:abs(vals[k]-candidate[j])); candidate[j]=vals[min(len(vals)-1,pos+(1 if idx%2==0 else -1))]
        ct=tuple(candidate)
        if ct in used or ct in unique:
            candidate=list(base); candidate[(j+1)%len(dims)]=candidate[(j+1)%len(dims)] + (0.5 if idx%2==0 else -0.5); ct=tuple(candidate)
        used.add(ct); plan.append({'planned_candidate_id':f'LP_5D_PHASE_REACHABILITY_{len(plan)+1:02d}','role':role,'reference_candidate_id':q.get('candidate_id'),'planned_J1_side_nm':candidate[0],'planned_J2_length_nm':candidate[1],'planned_J2_width_nm':candidate[2],'planned_D_nm':candidate[3],'planned_Psi_deg':candidate[4],'wavelength_nm':450,'status':'PLANNED_NOT_RUN','physics_fields':'ABSENT_NOT_SIMULATED','prediction_label':'MODEL_PREDICTION_NOT_PHYSICS_LABEL','geometry_hash_status':'NOT_BUILT_OFFLINE_ONLY','manufacturing_status':'OFFLINE_REQUIRES_PREFLIGHT','solver_authorized':False})
    for role,qs in roles:
        for i,q in enumerate(qs): add(role,q,i)
    # boundary/tradeoff/disagreement controls from spread and sparse corners
    rest=sorted(geo,key=lambda q:(sum(abs(q[d]-statistics.mean([z[d] for z in geo])) for d in dims),q['phase_deg']))
    for i,q in enumerate(rest[:12]): add('BOUNDARY_OR_TRADEOFF_CONTROL' if i<8 else 'MODEL_DISAGREEMENT_CONTROL',q,i+12)
    plan=plan[:24]
    write_csv(os.path.join(PLANS,OUT['plan_csv']),plan)
    plan_obj={'plan_id':'LP_5D_PHASE_REACHABILITY_PROBE_V1','status':'PLANNED_NOT_RUN','label':'OFFLINE_ONLY_NO_RUNNABLE_SOLVER_PACKAGE','candidate_count':len(plan),'subrun_budget':{'geometries':len(plan),'x_y_subruns':len(plan)*2,'wavelength_nm':[450]},'roles':{r:sum(1 for q in plan if q['role']==r) for r in sorted(set(q['role'] for q in plan))},'no_new_freedom':True,'no_d9':True,'solver_calls':0}
    write_json(os.path.join(PLANS,OUT['plan_json']),plan_obj)
    write_json(os.path.join(PLANS,OUT['route_contract']),{'contract':'LP_5D_PHASE_REACHABILITY_PROBE_V1','authorization':'OFFLINE_PLAN_ONLY','solver_authorized':False,'no_runnable_solver_package':True,'fixed_5d_variables':['J1_side','J2_length','J2_width','D','Psi'],'new_freedom':False,'no_six_bin_inverse':True,'no_round4_active_learning':True,'no_d9':True,'future_budget':plan_obj['subrun_budget']})
    decision={'outcome':'LP_5D_PHASE_REACHABILITY_PROBE_PLANNING_READY','evidence_level':'LEVEL_1_CURRENT_PHASE_SUPPORT_NARROW_DESIGN_SPACE_UNDEREXPLORED','observed_phase_envelope':env,'projector_conditioned':cond,'phase_projector_tradeoff':cond.get('tradeoff_classification'),'physics_limit_vs_sampling_limit':'SAMPLING_LIMIT_PLAUSIBLE_BUT_NOT_PROVEN; current evidence does not reach LEVEL_3','historical_hard_gate_preserved':'HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE','formal_matrix_payload_sha256':matrix_payload_sha,'formal_contract_file_sha256':contract_sha,'solver_calls':0,'model_retraining':False,'new_freedom':False,'probe_plan':os.path.join(PLANS,OUT['plan_json']),'future_freedom_ranking':['H','split J1_side into J1_length+J1_width']}
    write_json(os.path.join(ANALYSIS,OUT['decision_json']),decision)
    # Concise report.
    report=os.path.join(REPORTS,'lp_ml_inverse_stage1_5d_phase_reachability_evidence_audit_v1.md')
    with open(report,'w',encoding='utf-8') as f:
        f.write('# LP 5D formal-phase reachability evidence audit v1\n\n')
        f.write(f'- Outcome: `{decision["outcome"]}`\n- Evidence level: `{decision["evidence_level"]}`\n- Solver calls: `0`\n- Formal phase: `arg(txx)` under `P_APCD=diag(1,0)`\n- Matrix payload SHA256: `{matrix_payload_sha}` (expected `{EXPECTED_MATRIX_SHA}`)\n- Contract file SHA256: `{contract_sha}` (expected `{EXPECTED_CONTRACT_SHA}`)\n\n')
        f.write('## Compatible historical physics\n\n')
        for x in ledger: f.write(f"- `{os.path.basename(x['path'])}`: `{x['classification']}`, admitted 450nm complete/non-054 rows={x['rows_450_complete_non054']}; excluded 054 at 450nm={x['rows_054_excluded_450']}, all wavelengths={x['rows_054_excluded_all_wavelengths']}.\n")
        f.write('- Historical hard gate preserved: `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`; original22/bounded6 are not promoted to historical primary reachability physics.\n\n')
        f.write('## Observed real phase envelope\n\n')
        f.write(f"- Unique admitted geometry rows: {len(admitted)}; phase {env.get('min_phase_deg')}–{env.get('max_phase_deg')}°; linear span {env.get('linear_span_deg')}°; largest uncovered circular arc {env.get('largest_uncovered_circular_arc_deg')}°. Label is OBSERVED_PHYSICS_PHASE_ENVELOPE, not TRUE_5D_PHASE_LIMIT.\n\n")
        f.write('## Projector-conditioned phase envelope\n\n')
        for k,v in cond.items():
            if isinstance(v,dict) and 'min_phase_deg' in v: f.write(f"- {k}: n={v.get('count')}, phase={v.get('min_phase_deg')}–{v.get('max_phase_deg')}°, span={v.get('linear_span_deg')}°.\n")
        f.write(f"- Conditioning result: `{cond.get('tradeoff_classification')}`; no new absolute PASS threshold introduced.\n\n")
        f.write('## Geometry phase leverage and boundary coverage\n\n')
        f.write(json.dumps(leverage['spearman_phase_deg'],ensure_ascii=False)+'\n\n')
        f.write(f"- 5D rows with coordinates: {len(geo)}; extrema are interpreted against observed support only. Frozen manufacturing bounds were not inferred from a single artifact.\n\n")
        f.write('## Six-bin surrogate extrapolation and dense diagnostic\n\n')
        f.write(f"- 508-row table stored no predicted complex txx fields: recomputed C0/C1/C5/planning-blend phase is unavailable; target phases are not substituted.\n- Dense request: 200,000 points; status `{dense['status']}`; prediction-only label retained.\n\n")
        f.write('## Dedicated probe proposal\n\n')
        f.write(f"- `{plan_obj['plan_id']}`: {len(plan)} planned geometries / {len(plan)*2} x/y subruns / 450nm only; offline plan, no runnable solver package, no D9.\n\n")
        f.write('## Decision\n\n')
        f.write(f"`{decision['outcome']}` — current support is too narrow to prove a 5D limit; a dedicated reachability probe is planning-ready. Sampling limitation is plausible, not established.\n")
    # Checksums of all generated outputs.
    generated=[]
    for fn in OUT.values():
        if fn.startswith('lp_'):
            path=os.path.join(PLANS,fn) if fn in (OUT['plan_csv'],OUT['plan_json'],OUT['route_contract']) else (os.path.join(REPORTS,fn) if fn.endswith('.md') else os.path.join(ANALYSIS,fn))
            if os.path.exists(path): generated.append({'path':path,'sha256':sha(path),'bytes':os.path.getsize(path)})
    checks={'created_utc':created,'formal_matrix_payload_sha256':matrix_payload_sha,'expected_formal_matrix_payload_sha256':EXPECTED_MATRIX_SHA,'formal_contract_file_sha256':contract_sha,'expected_formal_contract_file_sha256':EXPECTED_CONTRACT_SHA,'generated':generated,'report':{'path':report,'sha256':sha(report),'bytes':os.path.getsize(report)},'protected_hashes_before_after':{p:{'before':v,'after':sha(os.path.join(ROOT,p)) if os.path.exists(os.path.join(ROOT,p)) else None} for p,v in protected_hashes.items()},'solver_calls':0,'forbidden_actions':{'retraining':False,'new_freedom':False,'broadband':False,'K6':False,'D9':False}}
    write_json(os.path.join(ANALYSIS,OUT['checksums_json']),checks)
    print(json.dumps({'outcome':decision['outcome'],'admitted':len(admitted),'geo_with_coords':len(geo),'phase_min':env.get('min_phase_deg'),'phase_max':env.get('max_phase_deg'),'plan_count':len(plan),'solver_calls':0,'matrix_payload_sha':matrix_payload_sha,'contract_file_sha':contract_sha},ensure_ascii=False))

if __name__=='__main__': main()
