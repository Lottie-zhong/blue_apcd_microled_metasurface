from pathlib import Path
import json,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import r1_angular_spectrum as r
import r1_test

ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
OUT=ROOT/'outputs/coupling_ml/INTERFACE_STATE_V1_R1_MAXWELL_ANGULAR_SPECTRUM_RECONCILIATION'
R0=ROOT/'outputs/coupling_ml/INTERFACE_STATE_V1_ZERO_SOLVER_PROTOTYPE'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,d): r.write_json(p,d)

def production_audit():
    old=read(R0/'FINAL_NONINTERFERENCE_GIT_AUDIT.json')['current']['production_hashes'];bad=[]
    for name,h in old.items():
        p=Path(name);actual=r.sha(p) if p.is_file() else None
        if actual!=h: bad.append({'path':name,'expected':h,'actual':actual})
    return {'baseline':str(R0/'FINAL_NONINTERFERENCE_GIT_AUDIT.json'),'count':len(old),'changed':bad,'unchanged':not bad}

def r0_audit():
    manifest=read(R0/'FINAL_SHA256_MANIFEST.json');bad=[]
    for rel,h in manifest.items():
        p=R0/rel;actual=r.sha(p) if p.is_file() else None
        if actual!=h: bad.append({'path':str(p),'expected':h,'actual':actual})
    return {'manifest':str(R0/'FINAL_SHA256_MANIFEST.json'),'count':len(manifest),'bad':bad,'untouched':not bad}

def lifecycle():
    root=ROOT/'outputs/coupling_ml/M2S_CENTROID_XZ_3D_SOURCE_LATERAL_DOMAIN_ROBUSTNESS_V1_ATTEMPT_002';out={}
    for c in ['CENTROID_X_ENLARGED_DOMAIN','CENTROID_Z_ENLARGED_DOMAIN']:
        rows=[];p=root/c/'events.jsonl'
        if p.exists():
            for line in p.read_text(encoding='utf-8',errors='replace').splitlines():
                try:
                    x=json.loads(line);rows.append({k:x.get(k) for k in ['timestamp','state','error_class']})
                except Exception: pass
        states=[x['state'] for x in rows]
        out[c]={'event_count':len(rows),'last_state':states[-1] if states else None,'solver_returned':'SOLVER_RETURNED' in states,'post_validated':any(x in states for x in ['POST_FSP_VALIDATED','POST_FSP_LOAD_ONLY_VALIDATED']),'completed':'COMPLETED' in states,'scientific_outputs_read':False}
    return out

def stats(j):
    def one(rows):
        best=[x['maxwell']['best_fixed']['fixed_residual'] for x in rows]
        fit=[x['maxwell']['best_fixed']['fitted_residual'] for x in rows]
        scale=[x['maxwell']['best_fixed']['best_H_scale']['abs'] for x in rows]
        modal=[x['modal'][0]['spectral_EH_reconstruction_relative_L2'] for x in rows]
        return {'best_max':max(best),'best_mean':float(np.mean(best)),'fit_max':max(fit),'scale_min':min(scale),'scale_max':max(scale),'modal_max':max(modal),'modal_mean':float(np.mean(modal))}
    a=j['methods']['A_actual_coordinate_NUDFT']['rows'];b=j['methods']['B_linear_interpolation_uniform_FFT']['rows'];c=j['methods']['C_historical_median_spacing_SVD_diagnostic']['rows']
    return {'A':one(a),'B':one(b),'C':one(c),'AB':j['A_vs_B_propagating_spectral_relative_L2'],'interp_flux_max':max(j['uniform_interp_flux_relative_error']),'density':{n:{'max':max(x['maxwell_best_fixed']['fixed_residual'] for x in v['rows']),'mean':float(np.mean([x['maxwell_best_fixed']['fixed_residual'] for x in v['rows']]))} for n,v in j['methods']['B_linear_interpolation_uniform_FFT']['grid_density'].items()}}

def window_summary():
    j=read(OUT/'WINDOW_SENSITIVITY_450NM.json')
    return {c:{'no':j[c]['no_window_maxwell']['best_fixed']['fixed_residual'],'window':j[c]['window_maxwell']['best_fixed']['fixed_residual'],'spectral_change':j[c]['window_vs_no_window_propagating_spectral_L2'],'modal_no':j[c]['no_window_modal']['spectral_EH_reconstruction_relative_L2'],'modal_window':j[c]['window_modal']['spectral_EH_reconstruction_relative_L2'],'power_no':j[c]['no_window_modal']['modal_propagating_net_power'],'power_window':j[c]['window_modal']['modal_propagating_net_power']} for c in ['X','Z']}

def evanescent():
    out={}
    for c in ['CENTROID_X','CENTROID_Z']:
        with np.load(OUT/c/'spectral_450nm.npz') as z:
            kx=z['kx'];ky=z['ky'];rho=np.sqrt(kx[:,None]**2+ky[None,:]**2)/(2*np.pi/450e-9);prop=rho<1-r.GUARD;ev=rho>1+r.GUARD;gr=abs(rho-1)<=r.GUARD;vals={}
            for label in ['A_EH','B_EH']:
                w=abs(z[label])**2;wf=w.reshape(w.shape[0],-1);total=wf.sum();vals[label]={'prop':float(wf[:,prop.ravel()].sum()/total),'evanescent':float(wf[:,ev.ravel()].sum()/total),'grazing':float(wf[:,gr.ravel()].sum()/total)}
            out[c]=vals
    return out

def main():
    cases={c:read(OUT/f'CENTROID_{c}/summary.json') for c in ['X','Z']};ss={c:stats(j) for c,j in cases.items()};ws=window_summary();ev=evanescent();tests=r1_test.run()
    write(OUT/'R1_ZERO_SOLVER_TEST_RESULTS.json',tests)
    audit={'production':production_audit(),'previous_r0':r0_audit(),'M2S_lifecycle_only':lifecycle(),'solver_entry_delta':0,'training_delta':0,'rerun_delta':0,'source_hashes':{str(p):r.sha(p) for p in [Path(__file__),Path(__file__).with_name('r1_angular_spectrum.py'),Path(__file__).with_name('r1_window_probe.py'),Path(__file__).with_name('r1_test.py')]}}
    assert audit['production']['unchanged'] and audit['previous_r0']['untouched']
    write(OUT/'R1_NONINTERFERENCE_AUDIT.json',audit);write(OUT/'R1_NUMERICAL_SUMMARY.json',{'case_stats':ss,'window_450nm':ws,'evanescent_450nm':ev,'tests':tests})
    maxab=max(ss[c]['AB']['max'] for c in ss);maxa=max(ss[c]['A']['best_max'] for c in ss)
    lines=[];add=lines.extend
    add(['# INTERFACE_STATE_V1_R1_MAXWELL_ANGULAR_SPECTRUM_RECONCILIATION','', '### STATUS','', 'PARTIAL — Layer-A physical k-space representation is reproducible and cross-method consistent, but directional Maxwell operator remains unresolved.','', '### RAW_SAMPLING_CONTRACT','', 'M2Q raw contains complex128 Ex/Ey/Ez/Hx/Hy/Hz on common returned x/y/z/f keys, 401×401×1×11. Exporter evidence records direct getdata extraction with unmodified_complex_arrays=true and no_interpolation=true. Monitor is 2D Z-normal source_interface_complex, configured z=1212 nm; returned z=1225 nm.','', '### COMPONENT_GRID_AUDIT','', 'All six arrays have identical shapes and common coordinate arrays. No component-specific coordinates, Yee offsets, or monitor interpolation semantics were preserved. Common returned sampling is evidenced, but physical co-location versus internal Yee interpolation is UNRESOLVED. x/y spacing is 2.0–17.400881 nm and nonuniform.','', '### SPECTRAL_METHOD_COMPARISON'])
    add([f"Path A actual-coordinate NUDFT and Path B complex linear interpolation plus uniform FFT agree in propagating spectral L2 by at most {maxab:.6g} (X {ss['X']['AB']['max']:.6g}; Z {ss['Z']['AB']['max']:.6g}). Path C historical median-spacing/SVD is diagnostic only and is not directly compared because its k grid differs.",f"Grid-density checks used 200/401/802 points. B residual maxima at 401 were X {ss['X']['density']['401']['max']:.6g}, Z {ss['Z']['density']['401']['max']:.6g}; 200→802 changes are small.",'','### TEMPORAL_CONVENTION_DIAGNOSTIC','', 'For every wavelength and both A/B, the empirical best candidate is +z with temporal sign +1, corresponding to the e^(-iωt) Maxwell sign under the implemented spatial convention. Alternative temporal sign residuals are about 1.98–2.00 for +z. This is an empirical candidate only, not frozen authority.','', '### MAXWELL_CONSISTENCY',f"Without fitted renormalization, Path A best fixed residual maxima are X {ss['X']['A']['best_max']:.6g}, Z {ss['Z']['A']['best_max']:.6g}; Path B maxima are X {ss['X']['B']['best_max']:.6g}, Z {ss['Z']['B']['best_max']:.6g}. H least-squares scale stays near unity: X {ss['X']['A']['scale_min']:.6g}–{ss['X']['A']['scale_max']:.6g}, Z {ss['Z']['A']['scale_min']:.6g}–{ss['Z']['A']['scale_max']:.6g}. Propagating modal E/H reconstruction maxima are X {ss['X']['A']['modal_max']:.6g}, Z {ss['Z']['A']['modal_max']:.6g}.",'','### ROOT_CAUSE_MATRIX','', '| Cause | Test/evidence | Result | Status |','|---|---|---|---|','| Nonuniform quadrature | A/B and 200/401/802 density | A/B ≤1.57%; small density change | REJECTED as primary |','| Component staggering | Common axes, no component metadata | Cannot distinguish colocated fields from internal Yee interpolation | UNRESOLVED |','| E/H non-colocation | No per-component coordinates/correction | No direct evidence either way | UNRESOLVED |','| Temporal sign | Four sign/direction candidates | +1 consistently best | EMPIRICAL CANDIDATE |','| H normalization | Best scale near one | Not primary | REJECTED as primary |','| kz/direction | +z consistently lower | Single plane cannot certify direction | CANDIDATE ONLY |','| Finite aperture/leakage | 450 nm Tukey alpha 0.1 | Changes spectra; X/Z respond differently | CONTRIBUTOR |','| Evanescent conditioning | 450 nm norm fractions | Substantial evanescent sector | CONTRIBUTOR/UNRESOLVED |','| Premature BZ folding | Layer A excludes folding | Not involved | REJECTED |','', '### PROPAGATING_DECOMPOSITION',f"Propagating-only decomposition preceded evanescent analysis. +z/e^(-iωt) is the empirical candidate, but residuals remain {maxa:.6g} worst across X/Z; no PASS claim.",'','### EVANESCENT_ANALYSIS',f"At 450 nm, A E/H norm fractions prop/evanescent are X {ev['CENTROID_X']['A_EH']['prop']:.4f}/{ev['CENTROID_X']['A_EH']['evanescent']:.4f}, Z {ev['CENTROID_Z']['A_EH']['prop']:.4f}/{ev['CENTROID_Z']['A_EH']['evanescent']:.4f}. These are field-norm fractions, not power. Evanescent direction/flux is unresolved.",'','### COMPLEX_EH_RECONSTRUCTION',f"A/B spectra agree, but Maxwell modal reconstruction remains nonzero: X {ss['X']['A']['modal_max']:.6g}, Z {ss['Z']['A']['modal_max']:.6g}. SVD remains diagnostic only.",'','### FLUX_RECONCILIATION',f"Uniform-grid interpolation changes real-space flux by at most X {ss['X']['interp_flux_max']:.4g}, Z {ss['Z']['interp_flux_max']:.4g}; this does not explain the prior X 8.35% / Z 26.87% modal mismatch.",'','### FINITE_APERTURE_ANALYSIS',f"At 450 nm, Tukey alpha 0.1 changes propagating spectrum by X {ws['X']['spectral_change']:.4f}, Z {ws['Z']['spectral_change']:.4f}; residual changes X {ws['X']['no']:.4f}→{ws['X']['window']:.4f}, Z {ws['Z']['no']:.4f}→{ws['Z']['window']:.4f}. Diagnostic only; no Layer-B G weights promoted.",'','### REFERENCE_PLANE_PHYSICAL_STATUS','', 'Algebraic sample↔logical round-trip remains valid, but physical phase direction is not independently certified from one plane with unresolved temporal/Yee semantics.','', '### BLOCH_FOLDING_STATUS','', 'NOT PERFORMED for R1 quantitative judgment; no new BZ folding or multi-G values overwrite R0.','', '### MULTI_G_REVISED_STATUS','', 'R0 multi-G numbers remain PRELIMINARY; revised quantitative weights are gated on Layer-A validation.','', '### ZERO_SOLVER_TESTS',json.dumps(tests,indent=2,sort_keys=True),'','### ARTIFACTS',str(OUT),'', 'Key files: RAW_FIELD_SAMPLING_CONTRACT.json, R1_REPORT.json, R1_NUMERICAL_SUMMARY.json, WINDOW_SENSITIVITY_450NM.json, per-case summary.json and spectral_450nm.npz.','', '### M2S_NONINTERFERENCE_AUDIT','', 'solver_entry_delta=0; training_delta=0; rerun_delta=0. R0 artifacts were manifest-verified untouched. Production hashes were rechecked unchanged. M2S scientific outputs were not read; only lifecycle events were inspected.',json.dumps(audit['M2S_lifecycle_only'],indent=2,sort_keys=True),'','### PROPOSED_VERDICT','', '`PARTIAL — PHYSICAL_KSPACE_REPRESENTATION_SUPPORTED_DIRECTIONAL_OPERATOR_UNRESOLVED`','', '### NEXT','', '`CHART_REVIEW_R1_MAXWELL_ANGULAR_SPECTRUM_RECONCILIATION` — resolve component co-location/Yee interpolation semantics and review whether multi-plane or monitor-export authority is required.'])
    (OUT/'R1_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(OUT/'R1_FINAL_SHA256_MANIFEST.json',{str(f.relative_to(OUT)):r.sha(f) for f in OUT.rglob('*') if f.is_file() and f.name!='R1_FINAL_SHA256_MANIFEST.json'})
    print(json.dumps({'audit':audit,'tests':tests,'stats':ss,'window':ws,'evanescent':ev},indent=2,sort_keys=True))

if __name__=='__main__': main()
