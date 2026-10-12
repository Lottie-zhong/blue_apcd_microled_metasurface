from pathlib import Path
import json,re,csv,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');D=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1';O=R/'reports/coupling/APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1';L=json.loads((D/'v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json').read_text());rg=json.loads(Path(r'D:\apcd_runtime\gpu_v3_identity_recovery_20261011_v1\V3_REGISTERED_BATCH_INTERFACE_02.json').read_text());out={}
for cid in L['entered_case_ids']:
 r=L['case_records'][cid];b=Path(r['evidence']['bundle']['path']);p=b.parent.parent/'attempts'/r['request_sha256']/'run_p0.log';lines=p.read_text(errors='replace').splitlines();safe=[s for s in lines if not any(x in s.lower() for x in ['license','context','command']) and (re.search(r'^\s*\d+\s+',s) or 'time steps' in s.lower() or 'time step' in s.lower() or 'iterations' in s.lower() or 'simulation time' in s.lower())]
 print(cid,safe[:4],safe[-3:]);out[cid]={'safe_progress_first':safe[:4],'safe_progress_last':safe[-3:]}
 npz=np.load(r['evidence']['validation']['record']['raw_npz']['path']);row=next(x for x in rg['cases'] if x['case_id']==cid);proof=json.loads(Path(row['artifacts']['load_proof']['path']).read_text());rb=proof.get('actual_readback',proof['canonical_readback']);out[cid]['actual_readback']=rb
 x=npz['POSTNP_x'].ravel()*1e9;y=npz['POSTNP_y'].ravel()*1e9;ds=row['ordered_D_nm'];out[cid]['analytic_circle_node_counts']=[int(np.sum((x[:,None]-(-725+290*i))**2+y[None,:]**2<=(d/2)**2)) for i,d in enumerate(ds)]
out['interpretation']='Circle node counts describe a CAD indicator evaluated on saved monitor transverse coordinates, NOT the actual conformal permittivity mask. Full volume grid/material coefficients not saved; cannot locate high-field hotspot.'
(O/'ACTUAL_GRID_AND_CAD_EVIDENCE.json').write_text(json.dumps(out,indent=2)+'\n')
