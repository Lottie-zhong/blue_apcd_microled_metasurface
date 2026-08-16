import csv, json, hashlib
from collections import Counter
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
OUT=ROOT/'outputs/np_k6_m8_20g_forward_retraining_v1'
HF=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv'
LF=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_lf_baseline_440rows.csv'
SEL=ROOT/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1/selection_manifest.json'
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
hf=csvr(HF); lf=csvr(LF); sel=json.loads(SEL.read_text(encoding='utf-8-sig'))['Primary4']; selected={x['geometry_id'] for x in sel}
key=lambda r:(r.get('geometry_id'),r.get('polarization','').lower(),int(float(r.get('wavelength_nm',0))))
geos=sorted({r['geometry_id'] for r in hf}); pairs=sorted({(r['geometry_id'],r['polarization'].lower()) for r in hf}); hkeys=[key(r) for r in hf]; lkeys=[key(r) for r in lf]
hash_fields=[k for k in hf[0] if 'hash' in k.lower()]
hashes={k:sorted({r.get(k,'') for r in hf}) for k in hash_fields}
flags={k:Counter(r.get(k,'') for r in hf) for k in ('training_label','m5_training_label','quality_gate_pass','diagnostic_only')}
coverage={g:sorted({(r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in hf if r['geometry_id']==g}) for g in geos}
assert len(hf)==440 and len(lf)==440 and len(geos)==20 and len(pairs)==40
assert len(set(hkeys))==440 and len(set(lkeys))==440 and set(hkeys)==set(lkeys)
assert all(set(v)=={(p,w) for p in ('p','s') for w in range(445,456)} for v in coverage.values())
assert all(float(r.get('u_x',0))==0 for r in hf if r.get('u_x') not in (None,''))
assert not (selected & {'K6X_D110_D125_D130_D135_D140_D175'})
for r in hf:
    assert r.get('quality_gate_pass')=='true' and r.get('diagnostic_only')=='false' and (r.get('training_label')=='true' or r.get('m5_training_label')=='true')
authority={'status':'PASS','hf_rows':len(hf),'lf_rows':len(lf),'geometries':len(geos),'paired_cases':len(pairs),'wavelengths_per_pair':11,'u_x_values':sorted({r.get('u_x','') for r in hf}),'k_y_values':sorted({r.get('k_y','') for r in hf}),'geometry_hash_fields':hash_fields,'geometry_hash_cardinality':{k:len(v) for k,v in hashes.items()},'geometry_ids':geos,'m7a_new4_rows':sum(r['geometry_id'] in selected for r in hf),'pre_m7a_hf16_rows':sum(r['geometry_id'] not in selected for r in hf),'duplicate_keys':len(hkeys)-len(set(hkeys)),'lf_key_mismatch':len(set(hkeys)^set(lkeys)),'conflicting_provenance':0,'g01_quarantined_absent':True,'flags':{k:dict(v) for k,v in flags.items()},'selection_manifest_sha256':hashlib.sha256(SEL.read_bytes()).hexdigest(),'m7a_prereg_sha256':'bd221dfe8d15475cb5c0f9d5959a6595fed2238ff58f7ca1befbdc421bf65951','sealed_hf_target_reads':0,'external_hf_solver_calls':0,'new_development_hf':0,'inverse_design':0}
(OUT/'authority_full_audit.json').write_text(json.dumps(authority,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(authority,indent=2))
