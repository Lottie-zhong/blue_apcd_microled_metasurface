"""Read-only custodian diagnostic gate over the independent Coupling ledger.

No solver, LOAD session, fitting, sealed-response reader, or release writer.
"""
from pathlib import Path
import argparse, hashlib, json, os, sys
import numpy as np

ROOT = Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
REPORT = ROOT/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1'
PROTOCOL = REPORT/'science_admission_v1/NUMERICAL_ADVANCEMENT_PROTOCOL.json'
PROTOCOL_SHA = '7407bfb3df56501a4b5b178caa0b7a7777b785f34dbb4fdd6eed65f8e7272d8e'
PINFILE = REPORT/'science_admission_v1/BASELINE_REFERENCE_PINS.json'
sys.path.insert(0,str(ROOT/'scripts/coupling_ml'))
sys.path.insert(0,str(REPORT/'science_admission_v1'))
from k6_v2_pipeline import v3_ingest as V, ingest as I, h1, contracts as C
import v3_numerical_advancement as M

def need(value, message):
    if not value: raise ValueError(message)

def checked(pin):
    p=Path(pin['path'])
    need(I.sha256_file(p)==pin['sha256'],'artifact_sha_mismatch:'+str(p))
    return p

def verified_bundle(pin):
    p=checked(pin); doc=I._json(p)
    need(doc.get('schema')=='APCD_V2_NATIVE_PAIR_V1','bundle_receipt_schema')
    base=p.parent.resolve(); files=doc['files']
    need('run.fsp' in files and 'run/run_output.h5' in files,'native_pair_missing')
    for name,d in files.items():
        target=(base/name).resolve()
        need(target.is_relative_to(base) and not Path(name).is_absolute(),'bundle_path_escape')
        need(target.stat().st_size==d['bytes'],'bundle_size_mismatch')
        checked({'path':str(target),'sha256':d['sha256']})
    # Check raw native fields without invoking any API session.
    import h5py
    with h5py.File(base/'run/run_output.h5','r') as f:
        groups=[f[k] for k in f if k.startswith('Monitor') and isinstance(f[k],h5py.Group)]
        need(bool(groups),'native_monitor_missing')
        for g in groups:
            for key in ('Ex','Ey','Ez','Hx','Hy','Hz'):
                ds=g.get(key)
                need(isinstance(ds,h5py.Dataset) and ds.size>0,'native_component_missing')
                for index in range(ds.shape[0] if ds.ndim else 1):
                    need(np.isfinite(ds[index] if ds.ndim else ds[()]).all(),'native_component_nonfinite')
    return doc

def label_arrays(pin, cid, role, geometry):
    with np.load(checked(pin),allow_pickle=False) as z:
        need(str(z['case_id'].item())==cid and str(z['attempt_id'].item())=='attempt_001','label_case_attempt')
        need(str(z['role'].item())==role and np.array_equal(z['ordered_D_nm'],geometry),'label_role_geometry')
        need(np.array_equal(z['wavelengths_nm'],C.WAVELENGTHS_NM)
             and np.array_equal(z['order_m'],C.ORDER_M)
             and list(z['polarization'])==list(C.POLARIZATIONS),'label_coordinates')
        c=z['C_hat_real']+1j*z['C_hat_imag']; p=z['P_scale']
        C.pack_model_target(c,p)
        return c,p

def evaluate_ledger(ledger_pin, registry_pin, identity_pin):
    need(I.sha256_file(PROTOCOL)==PROTOCOL_SHA,'protocol_changed')
    # Source pins protect old baselines and evaluator; never derive references from new truth.
    source_path=REPORT/'science_admission_v1/SOURCE_PINS.json'
    checked({'path':str(source_path),'sha256':'25474ec8612b8d939477001159c96c1fe850273b10ddd94eb3e3f51aabdb124d'})
    for descriptor in I._json(source_path): checked(descriptor)
    checked({'path':str(PINFILE),'sha256':'98220541b76bff84710f0786c471a39b23dae59edd9054ac22f9468cf2e7deb8'})
    checked({'path':str(REPORT/'science_admission_v1/v3_numerical_advancement.py'),
             'sha256':'497ea35a425b92293b30caddd1c299ae817220e9b743dbfb16866e8348439ea4'})
    pins=I._json(PINFILE)
    registry=V.load_registry(checked(registry_pin),registry_pin['sha256'],root=ROOT,identity_authority=identity_pin)
    V._verify_access_identity(registry,'PRODUCTION_CUSTODIAN')
    ledger=I._json(checked(ledger_pin))
    need(ledger.get('scope')=='V3_DOE56' and ledger.get('authorized_case_count')==56,'ledger_scope')
    need(ledger.get('frozen_manifest_sha256')==V.DOE_SHA,'ledger_manifest')
    results={}; decoder=h1.load_h2_decoder()
    bases={b['case_id']:b for b in pins['baselines']}
    for cid,(bid,mesh) in M.EXPECTED.items():
        need(cid in ledger['truth_valid_case_ids'] and cid in ledger['labels_valid_case_ids'],'diagnostic_not_truth_and_label_valid:'+cid)
        rec=ledger['case_records'].get(cid,{})
        need(rec.get('phase') in ('V2_TRUTH_VALID','V3_TRUTH_VALID') and rec.get('entry_consumed') is True,'diagnostic_entry_or_terminal_missing')
        evidence=rec['evidence']; validation=evidence['validation']; record=validation['record']
        need(validation.get('verdict')=='PASS' and validation.get('outputs')==609
             and validation.get('fresh_load_verified') is True
             and validation.get('actual_importer')=='load_verified_runner_case'
             and bool(validation.get('native_session')),'fresh_load_validation_missing')
        lp=validation['labels_artifact']; vp=Path(lp['path']).parent/'validation.json'
        need(I._json(vp)==validation,'validation_receipt_ledger_mismatch')
        vpin={'path':str(vp),'sha256':I.sha256_file(vp)}
        bundle=evidence['bundle']; bpin={'path':str(Path(bundle['path'])/'bundle_receipt.json'),'sha256':bundle['receipt_sha256']}
        bd=verified_bundle(bpin); need(bd['files']==bundle['files'],'bundle_ledger_mismatch')
        row=registry.cases[cid]
        imported=V.load_numerical_diagnostic_case(record,registry=registry,root=ROOT)
        manifest=I._json(checked(record['source_manifest']))
        need(manifest.get('pre_fsp_sha256')==row['artifacts']['pre_fsp']['sha256'],'source_pre_fsp_binding')
        c,p=label_arrays(lp,cid,row['frozen_role'],row['ordered_D_nm'])
        need(np.array_equal(c,imported.c_hat) and np.array_equal(p,imported.p_scale),'label_importer_parity')
        base=bases[bid]
        for d in base['artifacts'].values(): checked(d)
        a,q=label_arrays(base['artifacts']['label'],bid,'DEVELOPMENT_GLOBAL',base['ordered_D_nm'])
        def identity(case,geom,contract,label,truth,fresh,step):
            return dict(case_id=case,attempt_id='attempt_001',ordered_D_nm=list(geom),
                wavelengths_nm=list(C.WAVELENGTHS_NM),orders_m=list(C.ORDER_M),polarizations=list(C.POLARIZATIONS),
                reference_plane_nm=1722,normalization='incident_+z_(0,0)_TM_power_at_IN_REF',
                contract_sha256=contract,label_sha256=label,truth_sha256=truth,fresh_load_receipt_sha256=fresh,
                mesh_nm=step,truth_valid=True,six_component_eh_valid=True,solver_entry_count=1,replay_count=0,
                setup_contract_verified=True,original_source_pins_verified=True)
        bi=identity(bid,base['ordered_D_nm'],C.PHYSICAL_CONTRACT_SHA256,base['artifacts']['label']['sha256'],
                    base['artifacts']['truth_h5']['sha256'],base['artifacts']['runner_status']['sha256'],5)
        ci=identity(cid,row['ordered_D_nm'],row['contract_sha256'],lp['sha256'],record['truth_h5']['sha256'],vpin['sha256'],mesh)
        M.verify_pair_identity(bi,ci)
        results[cid]=dict(case_id=cid,pair_identity_verified=True,durable_receipts_verified=True,
            protocol_sha256=PROTOCOL_SHA,comparison=M.compare_arrays(a,q,c,p,decode=lambda c,p:h1.reconstruct_h2(c,p,decoder)),
            input_pins=dict(label=lp,validation=vpin,bundle_receipt=bpin,truth=record['truth_h5']))
    gate=M.advancement(results,PROTOCOL_SHA)
    return dict(schema='V3_COUPLING_NUMERICAL_GATE_RECEIPT_V1',**gate,comparisons=results,
                inputs=dict(ledger=ledger_pin,registry=registry_pin,identity=identity_pin),
                no_solver_or_fit=True,sealed_response_access=0)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True);p.add_argument('--input-sha256',required=True);p.add_argument('--output',required=True)
    args=p.parse_args(); inp=I._json(checked({'path':args.input,'sha256':args.input_sha256}))
    need(inp.get('schema')=='V3_COUPLING_NUMERICAL_GATE_INPUT_V1','gate_input_schema')
    out=Path(args.output);need(not out.exists(),'receipt_already_exists_no_overwrite')
    result=evaluate_ledger(inp['ledger'],inp['registry'],inp['identity_authority'])
    result['input_manifest_sha256']=args.input_sha256;result['evaluator_sha256']=I.sha256_file(__file__)
    with out.open('xb') as f:f.write((json.dumps(result,sort_keys=True,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
    print(json.dumps({'status':result['status'],'receipt':str(out),'sha256':I.sha256_file(out)}))
    return 0 if result['advance_to_development'] else 3

if __name__=='__main__':raise SystemExit(main())
