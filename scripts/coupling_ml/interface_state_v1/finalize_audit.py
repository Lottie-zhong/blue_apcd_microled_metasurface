from pathlib import Path
import json,sys,subprocess
sys.path.insert(0,str(Path(__file__).parent))
import prototype as p
import numpy as np
from run_analysis import R,O,Q,M,OUT,snapshot

def main():
    s=json.loads((OUT/'SUMMARY.json').read_text());verified=[]
    for root,name in [(M,'M2R_SHA256_MANIFEST_V1.json'),(Q/'M2Q_R1_ZERO_SOLVER_RECOVERY_V2','M2Q_R1_SHA256_MANIFEST_V1.json')]:
        m=json.loads((root/name).read_text());pairs=[]
        pairs.extend((root/x['path'],x['sha256']) for x in m.get('entries',[]))
        pairs.extend((root/f,h) for f,h in m.get('new_recovery_files',{}).items())
        rows=m['immutable_inputs'];rows=rows.values() if isinstance(rows,dict) else rows
        for row in rows:
            for key,val in row.items():
                if key.endswith('_path') and key[:-5]+'_sha256' in row:pairs.append((Path(val),row[key[:-5]+'_sha256']))
        for f,h in pairs:
            actual=p.sha(f);assert actual==h,str(f)
            verified.append({'path':str(f),'sha256':actual,'PASS':True})
    p.write_json(OUT/'FULL_HISTORICAL_MANIFEST_VERIFICATION.json',verified)
    pwroot=next(O.glob('M2I_G7_G8_*'));campaign=pwroot/'M2I_LEVEL2A_CAMPAIGN_MANIFEST_V1.json'
    manifest=json.loads(campaign.read_text());examples=[];pwinputs={str(campaign):p.sha(campaign)}
    for filename in manifest['case_manifest_paths'][:3]:
        f=Path(filename);m=json.loads(f.read_text());pwinputs[str(f)]=p.sha(f)
        wave=np.asarray(m['wavelength_grid_nm'])*1e-9;kx=2*np.pi/wave*m['ux'];ky=np.zeros_like(kx)
        bx,ox,gx=p.fold(kx,p.PERIOD[0]);by,oy,gy=p.fold(ky,p.PERIOD[1])
        examples.append({'schema_version':'APCD_COUPLING_INTERFACE_STATE_V1','case_id':m['case_uid'],'authority_status':'PROTOTYPE','source_contract_id':m['case_uid'],'wavelength':wave.tolist(),'physical_kx':kx.tolist(),'physical_ky':ky.tolist(),'k_Bx':bx.tolist(),'k_By':by.tolist(),'Gx':gx.tolist(),'Gy':gy.tolist(),'physical_order_x':ox.tolist(),'physical_order_y':oy.tolist(),'polarization':m['polarization'],'propagation_direction':p.UNRESOLVED,'complex_amplitude_real':p.UNRESOLVED,'complex_amplitude_imag':p.UNRESOLVED,'source_position':p.UNRESOLVED,'source_orientation':m['source_polarization'],'logical_reference_plane_z':1212e-9,'actual_sample_plane_z':p.UNRESOLVED,'normalization_type':m['normalization_contract_id'],'reference_quantity':p.UNRESOLVED,'solver_order':p.UNRESOLVED,'original_mapping_text':m['physical_order_mapping'],'boundary':'single incident channel labels only; no actual interface amplitude, integrated MDC can generate backward waves; no quantitative transfer from transmitted-side monitor to logical incident plane'})
    p.write_json(OUT/'PLANE_WAVE_SCHEMA_COMPATIBILITY.json',{'status':'SCHEMA_ONLY','frozen_metadata_hashes':pwinputs,'examples':examples,'inconsistent_order_mapping':'n=physical x order conflicts with m=+1 physical +x in the same frozen manifest; do not resolve by guessing','amplitude_measure':'plane-wave spectral delta coefficient differs from finite-aperture quadrature coefficients; conversion not validated'})
    diagnostics={};normalized=[]
    for case in ['CENTROID_X','CENTROID_Z']:
        d=OUT/case;meta=json.loads((d/'metadata.json').read_text());mg=json.loads((d/'multi_g.json').read_text())
        dist={}
        for row in mg['rows']:
            for channel in row['channels']:dist[(row['bin'],*channel['order'])]=channel['weight']
        total=sum(dist.values());normalized.append({k:v/total for k,v in dist.items()})
        spectral_control=[]
        with np.load(d/'state.npz') as a:
            kx=a['physical_kx'];ky=a['physical_ky'];close=max(float(np.max(abs(kx-a['k_Bx']-a['Gx']))),float(np.max(abs(ky-a['k_By']-a['Gy']))))
            wx=p.weights(a['x']);wy=p.weights(a['y']);dx=abs(kx[1]-kx[0]);dy=abs(ky[1]-ky[0])
            synthx=np.exp(1j*a['x'][:,None]*kx[None,:])*dx/(2*np.pi)
            synthy=np.exp(1j*a['y'][:,None]*ky[None,:])*dy/(2*np.pi)
            with np.load(meta['raw_path']) as raw:
                # Direct inverse Fourier quadrature control does not amplify a truncated SVD inverse.
                for fi,ff in enumerate(a['frequency']):
                    b=p.basis(kx[:,None],ky[None,:],2*np.pi*ff/p.C0)
                    e,h=p.reconstruct(a['sample_complex_amplitude'][fi],b)
                    fields=np.stack([raw[n][:,:,0,fi] for n in ['Ex','Ey','Ez','Hx','Hy','Hz']])
                    spectra=np.concatenate([e,h])+a['sample_spectral_residual'][fi]
                    g0=(a['physical_order_x'][:,None]==0)&(a['physical_order_y'][None,:]==0)
                    spectral_control.append({'wavelength_nm':float(p.C0/ff*1e9),'direct_full':{n:p.metrics(fields[j],synthx@spectra[j]@synthy.T) for j,n in enumerate(['Ex','Ey','Ez','Hx','Hy','Hz'])},'direct_G0':{n:p.metrics(fields[j],synthx@(spectra[j]*g0)@synthy.T) for j,n in enumerate(['Ex','Ey','Ez','Hx','Hy','Hz'])}})
        diagnostics[case]={'k_closure_max_rad_per_m':close,'G0_weight_fraction':sum(v for k,v in normalized[-1].items() if k[1:]==(0,0)),'support_weight_is_power':False,'direct_inverse_quadrature':spectral_control,'note':'SVD inverse errors on modified spectra can be dramatically amplified; do not interpret huge G0 or longitudinal SVD errors as physical gain.'}
    keys=set(normalized[0])|set(normalized[1]);diagnostics['X_Z_normalized_support_L1']=sum(abs(normalized[0].get(k,0)-normalized[1].get(k,0)) for k in keys)
    p.write_json(OUT/'ADDITIONAL_NUMERICAL_AUDIT.json',diagnostics)
    life={};root=O/'M2S_CENTROID_XZ_3D_SOURCE_LATERAL_DOMAIN_ROBUSTNESS_V1_ATTEMPT_002'
    for case in ['CENTROID_X_ENLARGED_DOMAIN','CENTROID_Z_ENLARGED_DOMAIN']:
        rows=[json.loads(x) for x in (root/case/'events.jsonl').read_text().splitlines() if x.strip()]
        states=[x['state'] for x in rows];life[case]={'last_state':states[-1],'solver_entered_count':states.count('SCIENTIFIC_SOLVER_ENTERED'),'solver_returned': 'SOLVER_RETURNED' in states,'persistence_validated':any(x in states for x in ['POST_FSP_LOAD_ONLY_VALIDATED','POST_FSP_VALIDATED']),'completed':'COMPLETED' in states}
    now=snapshot();before=json.loads((OUT/'before.json').read_text());assert before['production_hashes']==now['production_hashes']
    codepaths=list((R/'scripts/coupling_ml/interface_state_v1').glob('*.py'))+list((R/'tests/coupling_ml/interface_state_v1').glob('*.py'))
    code={str(f):p.sha(f) for f in codepaths}
    audit={'current':now,'M2S_lifecycle_only':life,'new_source_files_sha256':code,'existing_production_files_unchanged':True,'solver_training_rerun_delta':[0,0,0],'commit_push_delta':[0,0]}
    p.write_json(OUT/'FINAL_NONINTERFERENCE_GIT_AUDIT.json',audit)
    # Report intentionally retains failed scientific checks; no threshold loosening.
    text=['# INTERFACE_STATE_V1_ZERO_SOLVER_PROTOTYPE','', '### STATUS','', 'PARTIAL — COMMON_INTERFACE_REPRESENTATION_PARTIAL. Not a production interface or validated scattering operator.','', '### AUTHORITY_RECONCILIATION','',f'{len(verified)} manifest references verified. Original M2Q projection failure and successful M2Q-R1 V2 recovery are different stages; evidence preserved. M2R freezes 1212 nm logical plane. A–M field authority and provenance are in INTERFACE_STATE_V1_CONTRACT_DRAFT.json. Temporal solver convention and universal solver-order mapping remain UNRESOLVED. Historical M2R assumes uniform raw grid but actual grid is nonuniform. No frozen artifacts changed.','', '### RAW_FIELD_INVENTORY','', 'X and Z: complex128 Ex/Ey/Ez/Hx/Hy/Hz, shape 401×401×1×11; 445–455 nm; one z=1225 nm sample. Raw fields unscaled; dipolepower reference, sourcepower auxiliary. No missing-H excuse for failed flux closure.','', '### INTERFACE_STATE_SCHEMA','', 'NPZ+JSON: physical k, k_B, signed reciprocal G/orders, P/S, ±, propagating/evanescent/grazing, complex amplitudes, source/plane/provenance. Spectral longitudinal residual is explicitly auxiliary, not a Maxwell channel. Amplitudes are finite-aperture field-integral coefficients, not unit-power amplitudes.','', '### REFERENCE_PLANE_CONTRACT','', 'Frozen logical plane 1212 nm, sampled 1225 nm; delta=-13 nm in homogeneous Air n=1. Principal kz with Im(kz)>=0; up exp(+i kz delta), down exp(-i kz delta). See per-wavelength complex/amplitude/phase roundtrip metrics.','', '### FOURIER_AND_BLOCH_CONVENTION','', 'Forward exp(-i k.r), origin (0,0); inverse exp(+i k.r). Lx=1740 nm, Ly=290 nm; first BZ half-open; k=k_B+G. Actual coordinate trapezoid NUDFT, historical k nodes only for comparison. Grid spacing 2–17.400881 nm, not uniform; each inverse rank=349/401 at rcond=1e-6. Ordinary FFT array roundtrip cannot validate physical k-space.','', '### MULTI_G_ANALYSIS','', 'All G retained. Per-bin rankings, cumulative fractions, dominant G, significant-G counts in each multi_g.json. Threshold=0.001 global max bin/G weight. Weight is modal support, NOT flux; different from historical M2R weighted score. No forced significant-bin fallback.','', '### POLARIZATION_DECOMPOSITION','', 'S=(-qy,qx,0); P_d=(d*w*qx,d*w*qy,-rho), normal q=(1,0). P_up=+x, P_down=-x. Tangential E/H resolves four directional coefficients algebraically; longitudinal residual remains explicit. Real-data Maxwell reconstruction has not passed.','', '### COMPLEX_FIELD_RECONSTRUCTION','', 'All 11 wavelengths and six components audited for complex L2, amplitude correlation, phase RMS/p95/max, complex correlation and overlap. Full regularized basis, G0-only and Maxwell-only reported separately. Failed real-source tests retained. ADDITIONAL_NUMERICAL_AUDIT.json supplies direct inverse-quadrature controls; large SVD errors after spectrum modification are numerical amplification, not physical gain.','', '```json',json.dumps(s['cases'],indent=2),'```','', '### POWER_FLUX_VALIDATION','', 'Actual real-space Poynting versus spectral net flux and propagating signed modal power computed at sampled plane, per wavelength. Logical-plane absolute flux closure is NOT validated. Evanescent interference/finite aperture cannot be relabeled propagating power. Not power-normalized.','', '### PLANE_WAVE_SCHEMA_COMPATIBILITY','', 'Three frozen M2I case manifests provide ux=0.37868939998860307, ky=0, P_XLIKE/S_YLIKE. Sparse incident-channel label examples share k_B/G schema. Absolute amplitude, direction provenance and interface transfer unresolved; no numerical plane-wave/dipole equivalence. Delta-distribution versus finite-aperture spectral measure also requires reconciliation.','', '### SOURCE_INVARIANCE_BOUNDARY','', 'Schema compatibility is not operator validation. SOURCE_INVARIANT_OPERATOR_VALIDATED is forbidden and not claimed.','', '### ZERO_SOLVER_TESTS','', '```json',json.dumps(s['tests'],indent=2),'```','', '### ARTIFACTS','',str(OUT),'', 'See SHA256_MANIFEST.json, FULL_HISTORICAL_MANIFEST_VERIFICATION.json, per-source state.npz/metadata.json/multi_g.json and regeneration copies.','', '### GIT_AUDIT','',f"Branch {now['git']['branch']}; HEAD {now['git']['HEAD']}. Existing dirty preserved. No upstream assumed; commit=0, push=0. New analysis/test file hashes in FINAL_NONINTERFERENCE_GIT_AUDIT.json.",'','```',now['git']['status'],'```','', '### M2S_NONINTERFERENCE_AUDIT','',f"{len(before['production_hashes'])} existing code/config hashes unchanged. New stage solver=0, training=0, rerun=0. No M2S scientific result read; lifecycle-only snapshot:",'','```json',json.dumps(life,indent=2),'```','', '### LIMITATIONS','', 'Nonuniform historical grid invalidates unqualified ordinary-FFT physical interpretation. Prototype spectral inversion is rank-deficient; real-field/Maxwell closure fails. Finite aperture, longitudinal consistency, normalization and time convention need a reviewed numerical contract. Do not interpret residual as defective Maxwell physics in original solver; it diagnoses this representation.','', '### PROPOSED_VERDICT','', 'COMMON_INTERFACE_REPRESENTATION_PARTIAL. Highest requested PASS not earned.','', '### NEXT','', 'CHART_REVIEW_NONUNIFORM_GRID_AND_MAXWELL_RECONSTRUCTION_CONTRACT — review representation/inversion and order/time authority before promoting V1. No new solver requested.']
    (OUT/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    p.write_json(OUT/'FINAL_SHA256_MANIFEST.json',{str(f.relative_to(OUT)):p.sha(f) for f in OUT.rglob('*') if f.is_file() and f.name!='FINAL_SHA256_MANIFEST.json'})
    print(json.dumps({'manifest_verified':len(verified),'diagnostics':{k:{x:v for x,v in row.items() if x!='direct_inverse_quadrature'} if isinstance(row,dict) else row for k,row in diagnostics.items()},'M2S':life,'source_files':code},indent=2))

if __name__=='__main__':main()
