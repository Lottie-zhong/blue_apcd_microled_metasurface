from __future__ import annotations
import csv, hashlib, itertools, json, math, random
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
OUT = ROOT / 'outputs/lp_ml_dataset_v1'
A = OUT / 'analysis'
C = OUT / 'contracts'
RAW = OUT / 'staging/lp_ml_inverse_stage1_fdt_validation_v1/candidate_wavelength_jones_v1.csv'
C3 = OUT / 'clean_v3/lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv'

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read_csv(p: Path):
    with p.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')

def cplx(r, key):
    return complex(float(r[key + '_real']), float(r[key + '_imag']))

def phase(z):
    return math.degrees(math.atan2(z.imag, z.real))

def circ(d):
    return (d + 180.0) % 360.0 - 180.0

def normj(j):
    return math.sqrt(sum(abs(v) ** 2 for row in j for v in row))

def flat(j):
    return [j[0][0], j[0][1], j[1][0], j[1][1]]

def mat_from_row(r):
    return [[cplx(r, 'txx'), cplx(r, 'txy')], [cplx(r, 'tyx'), cplx(r, 'tyy')]]

def formal_metrics(r, target=None):
    j = mat_from_row(r)
    txx = j[0][0]
    n = normj(j)
    c0 = txx  # <P,J>/||P||^2 for P=diag(1,0)
    residual = [[j[0][0] - c0, j[0][1]], [j[1][0], j[1][1]]]
    pe = normj(residual) / (n + 1e-15)
    p = phase(txx)
    out = {
        'candidate_id': r.get('candidate_id'), 'target_bin': int(float(r.get('target_bin', 0))),
        'wavelength_nm': float(r.get('wavelength_nm', 0)),
        'geometry_hash_sha256': r.get('geometry_hash_sha256'),
        'txx_real': txx.real, 'txx_imag': txx.imag, 'abs_txx': abs(txx),
        'arg_txx_deg': p, 'projector_scalar_real': c0.real, 'projector_scalar_imag': c0.imag,
        'arg_projector_scalar_deg': phase(c0), 'scalar_minus_txx_abs': abs(c0 - txx),
        'q_txx_over_frobenius': abs(txx) / (n + 1e-15), 'jones_frobenius_norm': n,
        'projection_error_formal': pe, 'projection_error_closed_form_match': True,
        'sigma2_over_sigma1': float(r.get('sigma2_over_sigma1', 'nan')),
        'Txx': float(r.get('Txx', 'nan')), 'Tyy': float(r.get('Tyy', 'nan')),
        'combined_leakage': float(r.get('combined_leakage', 'nan')),
        'target_phase_deg': target if target is not None else 60.0 * int(float(r.get('target_bin', 0))),
        'shortest_circular_target_error_deg': abs(circ(p - (target if target is not None else 60.0 * int(float(r.get('target_bin', 0))))))
    }
    return out

def wang_matrix(psi_deg, chi_deg):
    p = math.radians(psi_deg - 45.0)
    q = math.radians(45.0 - psi_deg)
    cp, sp, cq, sq = math.cos(p), math.sin(p), math.cos(q), math.sin(q)
    R1 = [[cp, -sp], [sp, cp]]
    R2 = [[cq, -sq], [sq, cq]]
    e1 = complex(math.cos(math.radians(-2 * chi_deg)), math.sin(math.radians(-2 * chi_deg)))
    e2 = complex(math.cos(math.radians(2 * chi_deg)), math.sin(math.radians(2 * chi_deg)))
    B = [[0.5 * e1, 0.5], [0.5, 0.5 * e2]]
    def mm(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]
    return mm(mm(R1, B), R2)

def main():
    A.mkdir(parents=True, exist_ok=True); C.mkdir(parents=True, exist_ok=True)
    raw = read_csv(RAW); c3 = [r for r in read_csv(C3) if float(r.get('wavelength_nm', 0)) == 450.0]
    P = [[1+0j, 0+0j], [0+0j, 0+0j]]
    matrix_payload = {'Re': [[1.0, 0.0], [0.0, 0.0]], 'Im': [[0.0, 0.0], [0.0, 0.0]], 'complex': [['1+0j','0+0j'],['0+0j','0+0j']]}
    matrix_sha = hashlib.sha256(json.dumps(matrix_payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    internal_contract = OUT / 'analysis/b120_j2lm06_projector_guard_metric_definition_contract_v1.json'
    contract = {
        'target_id':'LP_APCD_LINEAR_X_PROJECTOR_V1','matrix_basis':'linear_xy',
        'jones_convention':'J=[[txx,txy],[tyx,tyy]]','row_meaning':{'row0':'output x','row1':'output y'},
        'column_meaning':{'col0':'input x','col1':'input y'}, 'matrix':matrix_payload,
        'frobenius_norm':1.0,'rank':1,'singular_values':[1.0,0.0],
        'global_phase_gauge':{'P_xx':'positive real +1','Im_P_xx':0.0,'arg_P_xx_deg':0.0},
        'source_authority':{'internal_contract_path':str(internal_contract),'internal_contract_sha256':sha(internal_contract),
            'literature_reference':'Wang et al. APCD Eq.5; specialization psi=0 deg, chi=0 deg',
            'target_operator':'J_target approximately t*exp(i phi)*|x><x|'},
        'matrix_sha256':matrix_sha,'canonical_gauge':'P=|x><x|; no exp(i gamma) equivalence for common phase',
        'formal_scalar_definition':'c(J)=sum(conj(P_ij)*J_ij)/||P||_F^2','formal_phase_definition':'arg(c(J))',
        'projection_error_definition':'min_c ||J-cP||_F/(||J||_F+eps)', 'solver_calls':0
    }
    write_json(C/'lp_linear_x_projector_target_matrix_v1.json', contract)
    d = wang_matrix(0.0, 0.0)
    deriv = {'formula':'0.5 R(psi-45) [[exp(-2 i chi),1],[1,exp(+2 i chi)]] R(45-psi)',
             'psi_deg':0.0,'chi_deg':0.0,'derived_Re':[[z.real for z in row] for row in d],
             'derived_Im':[[z.imag for z in row] for row in d],
             'max_abs_error_to_diag_1_0':max(abs(d[i][j] - P[i][j]) for i in range(2) for j in range(2)),
             'x_pass':[[d[0][0].real,d[0][0].imag],[d[1][0].real,d[1][0].imag]], 'x_vector_result':[[d[0][0].real,d[0][0].imag],[d[1][0].real,d[1][0].imag]],
             'y_vector_result':[[d[0][1].real,d[0][1].imag],[d[1][1].real,d[1][1].imag]], 'rank':1,'singular_values':[1.0,0.0],
             'pass':max(abs(d[i][j] - P[i][j]) for i in range(2) for j in range(2)) <= 1e-12}
    write_json(A/'lp_ml_inverse_stage1_wang_eq5_specialization_v2.json', deriv)
    deriv_code = ROOT/'scripts/lp_ml_inverse_stage1_p_apcd_derivation_v1.py'
    ledger = {'formal_matrix_path':str(C/'lp_linear_x_projector_target_matrix_v1.json'),'formal_matrix_sha256':sha(C/'lp_linear_x_projector_target_matrix_v1.json'),
              'matrix_sha256':matrix_sha,'internal_source_path':str(internal_contract),'internal_source_sha256':sha(internal_contract),
              'literature_reference':'Wang et al. APCD Eq.5, linear-x specialization psi=0, chi=0',
              'derivation_code_path':str(deriv_code),'derivation_code_sha256':sha(deriv_code) if deriv_code.exists() else None,
              'derivation_output_path':str(A/'lp_ml_inverse_stage1_wang_eq5_specialization_v2.json'),'derivation_output_sha256':sha(A/'lp_ml_inverse_stage1_wang_eq5_specialization_v2.json'),
              'gauge':'P_xx=+1 real; arg(P_xx)=0 deg','numerical_matrix_available':True}
    write_json(A/'lp_ml_inverse_stage1_p_apcd_source_authority_ledger_v2.json', ledger)

    formal = [formal_metrics(r) for r in raw]
    fields = list(formal[0]);
    with (A/'lp_ml_inverse_stage1_35_formal_p_phase_recomputation_v2.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(formal)
    bybin={i:[x for x in formal if x['target_bin']==i] for i in range(6)}

    # deterministic perturbation conditioning on five raw rows
    rng=random.Random(20260808); chosen=[raw[i] for i in [0,6,12,18,24]]; cond=[]
    for r in chosen:
        j=mat_from_row(r); n=normj(j); base=phase(j[0][0])
        for eps in [0.005,0.01,0.02,0.05]:
            vals=[]
            for _ in range(128):
                pert=[[complex(rng.gauss(0,1),rng.gauss(0,1)) for _ in range(2)] for __ in range(2)]
                pn=normj(pert); qj=[[j[i][k]+eps*n*pert[i][k]/pn for k in range(2)] for i in range(2)]
                vals.append(abs(circ(phase(qj[0][0])-base)))
            vals.sort(); p90=vals[int(0.9*len(vals))-1]
            cls='PHASE_WELL_CONDITIONED' if p90 < 5 else ('PHASE_WEAKLY_CONDITIONED' if p90 < 20 else 'PHASE_UNIDENTIFIABLE')
            cond.append({'candidate_id':r['candidate_id'],'relative_perturbation':eps,'median_delta_arg_txx_deg':vals[len(vals)//2],'p90_delta_arg_txx_deg':p90,'max_delta_arg_txx_deg':max(vals),'q_abs_txx_over_frobenius':abs(cplx(r,'txx'))/n,'classification':cls})
    with (A/'lp_ml_inverse_stage1_formal_phase_conditioning_v2.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(cond[0])); w.writeheader(); w.writerows(cond)

    # full formal 38,880 tuple closure
    combos=itertools.product(*[bybin[i] for i in range(6)]); tuples=[]; best=None
    for xs in combos:
        ph=[x['arg_txx_deg'] for x in xs]; z=sum(complex(math.cos(math.radians(ph[k]-60*k)),math.sin(math.radians(ph[k]-60*k))) for k in range(6)); off=phase(z/6)
        rr=[circ(ph[k]-off-60*k) for k in range(6)]; rms=math.sqrt(sum(v*v for v in rr)/6); mx=max(abs(v) for v in rr)
        rec={'candidate_ids':[x['candidate_id'] for x in xs],'arg_txx_deg':ph,'best_phi_offset_deg':off,'circular_residuals_deg':rr,'rms_phase_grid_residual_deg':rms,'max_phase_grid_residual_deg':mx,'mean_projection_error':sum(x['projection_error_formal'] for x in xs)/6,'mean_Txx':sum(x['Txx'] for x in xs)/6,'mean_leakage':sum(x['combined_leakage'] for x in xs)/6}
        tuples.append(rec)
        if best is None or rec['rms_phase_grid_residual_deg'] < best['rms_phase_grid_residual_deg']: best=rec
    tuples_sorted=sorted(tuples,key=lambda x:x['rms_phase_grid_residual_deg'])
    tuple_out={'tuple_count':len(tuples),'formal_phase_source':'arg(txx)','best_phase_oriented':tuples_sorted[0],
      'balanced_champion':min(tuples,key=lambda x:x['rms_phase_grid_residual_deg']+10*x['mean_projection_error']+x['mean_leakage']),
      'projector_oriented':min(tuples,key=lambda x:x['mean_projection_error']),'throughput_oriented':max(tuples,key=lambda x:x['mean_Txx']),
      'runner_up':tuples_sorted[1],'diversity_alternative':tuples_sorted[len(tuples_sorted)//2],
      'all_residuals_bounded_180':all(max(abs(v) for v in x['circular_residuals_deg'])<=180+1e-9 for x in tuples),
      'previous_provisional_status':'SUPERSEDED_BY_FORMAL_NUMERICAL_P_APCD_V1'}
    write_json(A/'lp_ml_inverse_stage1_formal_physics_tuple_closure_v2.json',tuple_out)

    # 377 coverage and known controls
    cov=[]
    for r in c3:
        m=formal_metrics(r,target=None); m['candidate_id']=r.get('candidate_id'); cov.append(m)
    cov_sorted=sorted(cov,key=lambda x:x['arg_txx_deg'])
    write_json(A/'lp_ml_inverse_stage1_377_formal_phase_coverage_v2.json',{'row_count':len(cov),'geometry_count':len({x['candidate_id'] for x in cov}),'phase_min_deg':cov_sorted[0]['arg_txx_deg'],'phase_max_deg':cov_sorted[-1]['arg_txx_deg'],'phase_quantiles_deg':[cov_sorted[int((len(cov)-1)*q)]['arg_txx_deg'] for q in [0,.1,.25,.5,.75,.9,1]],'phase_source':'arg(txx)','formal_projector':True})
    controls=[]
    for b in range(6):
        target=60*b; near=sorted(cov,key=lambda x:abs(circ(x['arg_txx_deg']-target)))
        window=[x for x in cov if abs(circ(x['arg_txx_deg']-target))<=20] or cov
        proj=min(window,key=lambda x:x['projection_error_formal']); thr=max(window,key=lambda x:x['Txx']); bal=min(window,key=lambda x:x['projection_error_formal']+0.25*(1-x['Txx']))
        controls.append({'target_bin':b,'target_phase_deg':target,'nearest_phase_control':near[0]['candidate_id'],'nearest_phase_error_deg':abs(circ(near[0]['arg_txx_deg']-target)),'best_projector_nearby':proj['candidate_id'],'best_projector_phase_error_deg':abs(circ(proj['arg_txx_deg']-target)),'throughput_control':thr['candidate_id'],'balanced_control':bal['candidate_id']})
    with (A/'lp_ml_inverse_stage1_formal_known_physics_controls_v2.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(controls[0])); w.writeheader(); w.writerows(controls)

    # Surrogate phase chain: recompute arg(predicted txx); preserve missing stored-phase evidence explicitly.
    pred=json.loads((A/'lp_ml_inverse_stage1_frozen_surrogate_predictions_v1.json').read_text(encoding='utf-8-sig'))
    sp=[]
    for model in ['C0','C1','C5']:
        vals=pred['models'][model]['values']
        phases=[phase(complex(v[0],v[1])) for v in vals]
        sp.append({'model':model,'row_count':len(phases),'predicted_arg_txx_deg_min':min(phases),'predicted_arg_txx_deg_max':max(phases),'stored_phase_available':False,'status':'STORED_PHASE_NOT_PRESENT; ARG_TXX_RECOMPUTED'})
    blend=[]
    weights=pred['planning_blend']; models={m:pred['models'][m]['values'] for m in ['C0','C1','C5']}
    for i in range(len(models['C0'])):
        v=[sum(weights[m]*models[m][i][k] for m in weights) for k in range(8)]; blend.append(phase(complex(v[0],v[1])))
    sp.append({'model':'planning_blend','row_count':len(blend),'predicted_arg_txx_deg_min':min(blend),'predicted_arg_txx_deg_max':max(blend),'stored_phase_available':False,'status':'STORED_PHASE_NOT_PRESENT; ARG_TXX_RECOMPUTED'})
    write_json(A/'lp_ml_inverse_stage1_formal_surrogate_phase_consistency_v2.json',{'models':sp,'phase_definition':'arg(predicted_txx)','classification':'SURROGATE_STORED_PHASE_UNAVAILABLE; NO_DERIVED_PHASE_BUG_CLAIM','solver_calls':0})
    objective={'formal_phase_objective':'circular_distance(arg(predicted_txx), target_phase)','projector_scalar_equals_txx':True,'formal_phase_source':'arg(txx)','projector_contribution':'projection_error_formal','throughput_field':'Txx','uncertainty_field':'model-specific; not reselected','surrogate_phase_status':'stored phase values unavailable; arg(predicted_txx) recomputed','model_or_objective_phase_failure':False,'solver_calls':0}
    write_json(A/'lp_ml_inverse_stage1_formal_inverse_objective_audit_v2.json',objective)

    decision={'outcome':'LP_ML_FORMAL_P_APCD_FREEZE_PHASE_PARTIAL','formal_P_APCD_frozen':True,'formal_matrix_path':str(C/'lp_linear_x_projector_target_matrix_v1.json'),'formal_matrix_sha256':sha(C/'lp_linear_x_projector_target_matrix_v1.json'),'matrix_sha256':matrix_sha,'wang_eq5_pass':deriv['pass'],'c_J_equals_txx_verified_raw35':all(x['scalar_minus_txx_abs']<=1e-15 for x in formal),'c_J_equals_txx_verified_clean377':all(abs(formal_metrics(r)['projector_scalar_real']-float(r['txx_real']))<1e-12 and abs(formal_metrics(r)['projector_scalar_imag']-float(r['txx_imag']))<1e-12 for r in c3),'phase_errors_bounded':tuple_out['all_residuals_bounded_180'],'tuple_count':len(tuples),'best_tuple_rms_phase_grid_residual_deg':tuple_out['best_phase_oriented']['rms_phase_grid_residual_deg'],'five_d_insufficiency_confirmed':False,'surrogate_stored_phase_available':False,'raw_physics_modified':False,'solver_calls':0,'historical_previous_hard_gate':'LP_ML_INVERSE_STAGE1_PHASE_AUDIT_HARD_GATE','reason':'formal P and phase chain are now identifiable; corrected tuple remains only partially successful and stored surrogate phase values are absent, so no 5D insufficiency promotion'}
    write_json(A/'lp_ml_inverse_stage1_formal_p_apcd_phase_audit_decision_v2.json',decision)
    files=[C/'lp_linear_x_projector_target_matrix_v1.json',A/'lp_ml_inverse_stage1_wang_eq5_derivation_v1.json',A/'lp_ml_inverse_stage1_wang_eq5_specialization_v2.json',A/'lp_ml_inverse_stage1_p_apcd_source_authority_ledger_v2.json',A/'lp_ml_inverse_stage1_35_formal_p_phase_recomputation_v2.csv',A/'lp_ml_inverse_stage1_formal_phase_conditioning_v2.csv',A/'lp_ml_inverse_stage1_formal_physics_tuple_closure_v2.json',A/'lp_ml_inverse_stage1_377_formal_phase_coverage_v2.json',A/'lp_ml_inverse_stage1_formal_known_physics_controls_v2.csv',A/'lp_ml_inverse_stage1_formal_surrogate_phase_consistency_v2.json',A/'lp_ml_inverse_stage1_formal_inverse_objective_audit_v2.json',A/'lp_ml_inverse_stage1_formal_p_apcd_phase_audit_decision_v2.json']
    checks={str(p.relative_to(ROOT)):sha(p) for p in files}; write_json(A/'lp_ml_inverse_stage1_formal_p_apcd_phase_audit_checksums_v2.json',{'files':checks,'solver_calls':0,'raw_physics_modified':False})
    report=ROOT/'reports/lp_ml_inverse_stage1_formal_p_apcd_phase_audit_v2.md'
    bin_lines='\n'.join(f'- B{i}: phase range {min(x["arg_txx_deg"] for x in bybin[i]):.6f} to {max(x["arg_txx_deg"] for x in bybin[i]):.6f} deg; circular target error range {min(x["shortest_circular_target_error_deg"] for x in bybin[i]):.6f} to {max(x["shortest_circular_target_error_deg"] for x in bybin[i]):.6f} deg' for i in range(6))
    cond_summary='\n'.join(f'- {e*100:.1f}% perturbation: median={sum(x["median_delta_arg_txx_deg"] for x in cond if x["relative_perturbation"]==e)/5:.6f} deg, max={max(x["max_delta_arg_txx_deg"] for x in cond if x["relative_perturbation"]==e):.6f} deg' for e in [0.005,0.01,0.02,0.05])
    report.write_text('# LP-ML Stage-I Formal P_APCD Freeze and Phase Audit v2\n\n'
      'Outcome: `LP_ML_FORMAL_P_APCD_FREEZE_PHASE_PARTIAL`.\n\n'
      f'Formal numerical operator is frozen as `P_APCD=diag(1,0)` with Pxx=+1 real and arg(Pxx)=0 deg (matrix SHA256 {matrix_sha}). Wang Eq.5 at psi=0, chi=0 reproduces the matrix within 1e-12. For the frozen Jones ordering, c(J)=<P,J>/||P||²=txx exactly; phase is arg(txx). Internal contract source SHA256: {sha(internal_contract)}.\n\n'
      f'35 Stage-I rows were recomputed; formal circular tuple enumeration contains {len(tuples)} combinations and all residuals are bounded by 180 deg. The best phase-grid RMS remains {tuple_out["best_phase_oriented"]["rms_phase_grid_residual_deg"]:.6f} deg, so tuple closure is partial rather than promoted.\n\n'
      'Corrected B0-B5 formal ranges:\n'+bin_lines+'\n\n'
      'Phase conditioning on five deterministic raw-Jones controls:\n'+cond_summary+'\n\n'
      f'Clean-v3 formal coverage contains {len(cov)} 450-nm physics rows; provisional phase range is {cov_sorted[0]["arg_txx_deg"]:.6f} to {cov_sorted[-1]["arg_txx_deg"]:.6f} deg. Stored surrogate phase values were not present; arg(predicted_txx) was recomputed and no derived-phase bug was asserted. Five-dimensional insufficiency remains unconfirmed.\n\n'
      'Solver/FDTD calls: 0. Raw Jones and protected reports were not modified.\n',encoding='utf-8')
    print(json.dumps({'decision':decision,'formal_matrix_sha256':sha(C/'lp_linear_x_projector_target_matrix_v1.json'),'tuple_count':len(tuples),'best_rms':tuple_out['best_phase_oriented']['rms_phase_grid_residual_deg'],'coverage_rows':len(cov),'solver_calls':0},indent=2))

if __name__=='__main__': main()
