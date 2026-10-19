import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import prototype as p
import numpy as np
import json,subprocess,gc
from datetime import datetime,timezone

R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
O=R/'outputs/coupling_ml'
Q=O/'M2Q_CENTROID_XZ_3D_COMPLEX_SOURCE_PILOT_ACQUISITION_V1'
M=next(O.glob('M2R_*'))
OUT=O/'INTERFACE_STATE_V1_ZERO_SOLVER_PROTOTYPE'

def snapshot():
    paths=list((R/'scripts/coupling_ml').glob('*.py'))+list((R/'configs').rglob('*'))
    paths += [Path(r'D:\project\blue_apcd_microled_metasurface\scripts\apcd_global_fdtd_slot_v1.py'),Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\scripts\coupling\apcd_global_fdtd_slot_v3.py')]
    hashes={str(x):p.sha(x) for x in paths if x.is_file()}
    git={key:subprocess.check_output(['git','-C',str(R)]+args,text=True).strip() for key,args in [('branch',['branch','--show-current']),('HEAD',['rev-parse','HEAD']),('status',['status','--short'])]}
    return {'time':datetime.now(timezone.utc).isoformat(),'production_hashes':hashes,'git':git}

def main():
    OUT.mkdir(exist_ok=False)
    before=snapshot();p.write_json(OUT/'before.json',before)
    # Only explicit historical trees; never scan/read M2S scientific artifacts.
    immutable={str(f):p.sha(f) for root in [Q,M] for f in root.rglob('*') if f.is_file()}
    checks=[]
    for root,name in [(M,'M2R_SHA256_MANIFEST_V1.json'),(Q/'M2Q_R1_ZERO_SOLVER_RECOVERY_V2','M2Q_R1_SHA256_MANIFEST_V1.json')]:
        j=json.loads((root/name).read_text(encoding='utf-8-sig'))
        def walk(v):
            if isinstance(v,dict):
                if 'path' in v and 'sha256' in v:
                    f=Path(v['path']);f=f if f.is_absolute() else root/f
                    checks.append({'path':str(f),'expected':v['sha256'],'actual':p.sha(f)})
                for key,val in v.items():
                    if key.endswith('_path') and key[:-5]+'_sha256' in v:
                        f=Path(val);checks.append({'path':str(f),'expected':v[key[:-5]+'_sha256'],'actual':p.sha(f)})
                for key,val in v.items():
                    if isinstance(val,str) and len(val)==64 and all(c in '0123456789abcdef' for c in val):
                        f=Path(key);f=f if f.is_absolute() else root/f
                        if f.is_file():checks.append({'path':str(f),'expected':val,'actual':p.sha(f)})
                    else:walk(val)
            elif isinstance(v,list):
                for val in v:walk(val)
        walk(j)
    assert checks and all(x['expected']==x['actual'] for x in checks),'historical SHA conflict'
    p.write_json(OUT/'historical_input_audit.json',{'all_frozen_tree_hashes':immutable,'manifest_checks':checks})
    sys.path.insert(0,str(R/'tests/coupling_ml/interface_state_v1'))
    import test_prototype
    tests=test_prototype.run()
    p.write_json(OUT/'INTERFACE_STATE_V1_CONTRACT_DRAFT.json',p.schema(M))
    summaries={}
    for case,expected in [('CENTROID_X','72c97c904fb01651969ec1a69e562e0957994b3fa6800e5ec66379676fc6afc6'),('CENTROID_Z','4b094aadb9d3adac73d5a112c405b6c7da4e11f558a8a0574cddaf1cf9f93362')]:
        raw=Q/('M2Q_'+case+'_COMPLEX_SOURCE_RAW_V1.npz');assert p.sha(raw)==expected
        prov=json.loads((Q/('M2Q_'+case+'_SOURCE_PROVENANCE_V1.json')).read_text())
        contract=json.loads((Q/case/'attempt_001'/(case+'_PHYSICAL_CONTRACT_V1.json')).read_text())
        dest=OUT/case;dest.mkdir()
        report,arrays=p.analyze(raw,prov,contract,dest)
        # Independent full recomputation, not merely serializing cached coefficients.
        repeat=dest/'regeneration';repeat.mkdir()
        del arrays;gc.collect()
        again,arrays=p.analyze(raw,prov,contract,repeat)
        assert again['state_sha256']==report['state_sha256']
        tests[case+'_deterministic_regeneration']='PASS'
        assert report['source_contract']==contract and report['source_provenance']==prov
        tests[case+'_provenance']='PASS'
        assert np.max(abs(arrays['physical_kx']-arrays['k_Bx']-arrays['Gx']))<1e-7
        assert np.any(arrays['physical_order_x']!=0) and np.any(arrays['physical_order_y']!=0)
        tests[case+'_multi_G_preservation']='PASS'
        def worst(key,metric):return max(row[key][name][metric] for row in report['rows'] for name in ['Ex','Ey','Ez'])
        summary={key:{metric:worst(key,metric) for metric in ['complex_relative_L2','phase_rms_rad']} for key in ['full_basis_regularized_reconstruction','G0_truncated_reconstruction','Maxwell_modal_only_reconstruction']}
        summary['max_modal_flux_relative_error']=max(row['power_flux']['modal_relative_closure_error'] for row in report['rows'])
        summary['max_deembedding_L2']=max(row['deembedding_roundtrip']['complex_relative_L2'] for row in report['rows'])
        mg=json.loads((dest/'multi_g.json').read_text());summary['multi_G_bins']=mg['multi_G_bins'];summary['max_significant_G']=mg['max_significant_G']
        summaries[case]=summary
        tests[case+'_full_complex_reconstruction']='PASS' if summary['full_basis_regularized_reconstruction']['complex_relative_L2']<1e-4 else 'FAIL'
        tests[case+'_Maxwell_channel_reconstruction']='PASS' if summary['Maxwell_modal_only_reconstruction']['complex_relative_L2']<1e-4 else 'FAIL'
        del arrays;gc.collect()
    after=snapshot();assert before['production_hashes']==after['production_hashes']
    assert all(Path(f).is_file() and p.sha(f)==h for f,h in immutable.items())
    p.write_json(OUT/'after.json',after)
    p.write_json(OUT/'TEST_RESULTS.json',tests)
    p.write_json(OUT/'SUMMARY.json',{'status':'PARTIAL','verdict':'COMMON_INTERFACE_REPRESENTATION_PARTIAL','cases':summaries,'tests':tests,'manifest_checks':len(checks),'historical_files_preserved':len(immutable),'production_files_unchanged':len(before['production_hashes']),'solver_entered_delta':0,'training_delta':0,'rerun_delta':0,'commit_delta':0,'push_delta':0,'M2S_scientific_outputs_read':False})
    p.write_json(OUT/'SHA256_MANIFEST.json',{str(f.relative_to(OUT)):p.sha(f) for f in OUT.rglob('*') if f.is_file()})
    print(json.dumps(summaries,indent=2),flush=True)

if __name__=='__main__':main()
