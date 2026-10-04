import csv,json,hashlib,pathlib
import numpy as np
ROOT=pathlib.Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
BASE=ROOT/'reports'/'coupling'; OUT=BASE/'COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def loadj(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
assert sha(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2.json')=='4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a'
assert sha(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json')=='124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a'
archive=loadj(OUT/'PREAMENDMENT_01'/'PREAMENDMENT_SHA256_INVENTORY.json')
for name,meta in archive['files'].items(): assert sha(OUT/'PREAMENDMENT_01'/name)==meta['sha256'],name
authority=loadj(OUT/'AUTHORITY_HASHES_V2.json')
assert authority['schema'].endswith('AUTHORITY_HASHES_AMENDMENT_01')
assert authority['files']['base_protocol']['sha256']==sha(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2.json')
assert authority['files']['active_amendment_01']['sha256']==sha(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json')
assert authority['files']['pre_amendment_archive_index']['sha256']==sha(OUT/'PREAMENDMENT_01'/'PREAMENDMENT_SHA256_INVENTORY.json')
audit=loadj(OUT/'COVERAGE_AUDIT_V2.json')
assert audit['schema'].endswith('COVERAGE_AUDIT_AMENDMENT_01')
assert audit['preregistered_protocol_sha256']==sha(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json')
amend=loadj(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json')
assert amend['status']=='FROZEN_BEFORE_AMENDED_POINT_GENERATION'
assert amend['base_protocol']['sha256']==sha(OUT/'REVISED_PREREGISTERED_PROTOCOL_V2.json')
pts=rows(OUT/'GLOBAL_DATASET_CANDIDATES_V2.csv')
def vec(r):return tuple(int(r[f'D{i}_nm']) for i in range(1,7))
assert len(pts)==160 and len({r['case_id'] for r in pts})==160 and len({vec(r) for r in pts})==160
role_counts={}
for r in pts: role_counts[r['role']]=role_counts.get(r['role'],0)+1
assert role_counts=={'DEVELOPMENT_LOCAL_AXIS':12,'SEALED_LOCAL_COMBINATION':4,'DEVELOPMENT_GLOBAL':116,'SEALED_CONFIRMATION_GLOBAL':28},role_counts
for r in pts:
 v=vec(r); assert all(100<=x<=230 and (x-100)%5==0 for x in v)
 gaps=[290-(v[i]+v[(i+1)%6])/2 for i in range(6)]
 assert min(gaps)>=60 and 145-max(v)/2>=30
 assert all(r[k]=='false' for k in ('source_authority_enrolled','runner_approved','canonical_fsp_created_by_this_task','solver_authorized'))
 assert r['cohort']!='V2_STRATIFIED_MAXIMIN'
loc=loadj(BASE/'COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1'/'CANDIDATE_MANIFEST_V1.json')['cases']
local_expected={r['case_id']:tuple(r['ordered_D_nm']) for r in loc}
local_actual={r['case_id']:vec(r) for r in pts if r['cohort']=='FROZEN_LOCAL_DOE'}
assert local_actual==local_expected
assert {r['cohort'] for r in pts if r['role']=='DEVELOPMENT_GLOBAL' or r['role']=='SEALED_CONFIRMATION_GLOBAL'}=={'V2_STRATIFIED_MAXIMIN_AMENDMENT_01'}
globalrows=[r for r in pts if r['role'] in ('DEVELOPMENT_GLOBAL','SEALED_CONFIRMATION_GLOBAL')]
assert len(globalrows)==144
for r in globalrows:
 v=vec(r); exact=any(x in (100,230) for x in v); near=any(x<=110 or x>=220 for x in v)
 if r['global_stratum']=='DEEP_INTERIOR': assert all(115<=x<=215 for x in v) and not exact and not near
 elif r['global_stratum']=='NEAR_BOUNDARY_NONEXACT': assert not exact and near
 elif r['global_stratum'] in ('SINGLE_FACE','TWO_FACE_INTERSECTION','TRIPLE_FACE_STRESS'): assert exact and near
 else: raise AssertionError(r['global_stratum'])
 assert sum(x in (100,230) for x in v)==int(r['exact_boundary_coordinates'])
assert sum(r['global_stratum']=='DEEP_INTERIOR' for r in globalrows)==32
assert sum(r['global_stratum']=='NEAR_BOUNDARY_NONEXACT' for r in globalrows)==56
assert sum(int(r['exact_boundary_coordinates'])>0 for r in globalrows)==56

def bc(rs):
 vs=[vec(r) for r in rs];return sum(any(x in (100,230) for x in v) for v in vs),sum(any(x<=110 or x>=220 for x in v) for v in vs)
dev=[r for r in globalrows if r['role']=='DEVELOPMENT_GLOBAL'];conf=[r for r in globalrows if r['role']=='SEALED_CONFIRMATION_GLOBAL']
core=[r for r in conf if r['global_stratum']!='TRIPLE_FACE_STRESS'];stress=[r for r in conf if r['global_stratum']=='TRIPLE_FACE_STRESS']
assert (len(dev),bc(dev))==(116,(45,90))
assert (len(core),bc(core))==(27,(10,21))
assert (len(stress),bc(stress))==(1,(1,1))
assert (len(conf),bc(conf))==(28,(11,22))
# Identity exclusion across all protected/reference geometry sets.
with np.load(BASE/'PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1'/'dataset_truth_32g.npz',allow_pickle=False) as z: old={tuple(map(int,v)) for v in z['ordered_D_nm'].tolist()}
reserve={tuple(map(int,r['ordered_D_nm'])) for r in loadj(BASE/'PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json')['prospective_reserve_only']}
protected={tuple(map(int,r['ordered_D_nm'])) for r in loadj(BASE/'PW_K6_GEOMETRY_EXCLUSION_REGISTRY_V1.json')['entries']}
pool={tuple(map(int,r['ordered_D_nm'])) for r in loadj(BASE/'PW_K6_EXTENSION_ELIGIBLE_CANDIDATE_POOL_V1.json')['entries']}
v1=[vec(r) for r in rows(BASE/'COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1'/'GLOBAL_DATASET_CANDIDATES_V1.csv')]
ref=old|set(local_expected.values())|reserve|protected|pool|set(v1)
assert not ({vec(r) for r in globalrows}&ref)
# Outer, inner, and nested learning curve membership must remain geometry-grouped.
foldrows=rows(OUT/'DEVELOPMENT_FOLD_MANIFEST_V2.csv'); inner=rows(OUT/'INNER_FOLD_MANIFEST_V2.csv'); curve=rows(OUT/'LEARNING_CURVE_SUBSET_MANIFEST_V2.csv')
assert len(foldrows)==128 and len(inner)==512 and len(curve)==896
foldmap={r['case_id']:int(r['outer_fold']) for r in foldrows}
old_ids=set(np.load(BASE/'PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1'/'dataset_truth_32g.npz',allow_pickle=False)['case_ids'].tolist())
for f in range(1,5):
 val={cid for cid,k in foldmap.items() if k==f}; assert len(val)==32
 assert sum(next(r for r in foldrows if r['case_id']==cid)['role']=='DEVELOPMENT_LOCAL_AXIS' for cid in val)==3
 assert sum(next(r for r in foldrows if r['case_id']==cid)['role']=='DEVELOPMENT_GLOBAL' for cid in val)==29
 ir=[r for r in inner if int(r['outer_fold'])==f]; assert len(ir)==128 and len({r['case_id'] for r in ir})==128
 assert {r['case_id'] for r in ir}==old_ids|{cid for cid in foldmap if foldmap[cid]!=f}
 icount={i:sum(int(r['inner_fold'])==i for r in ir) for i in (1,2,3)};assert sorted(icount.values())==[42,43,43]
 sets={}
 for n in (32,64,128):
  rr=[r for r in curve if int(r['outer_fold'])==f and int(r['training_geometry_count'])==n]
  assert len(rr)==n and all(r['all_21_wavelengths_grouped']=='true' for r in rr)
  ids={r['case_id'] for r in rr}; assert len(ids)==n and not ids&val; sets[n]=ids
 assert sets[32]==old_ids and sets[32]<sets[64]<sets[128]
 assert len(sets[64]-sets[32])==32 and len(sets[128]-sets[64])==64
 added=[r for r in curve if int(r['outer_fold'])==f and int(r['training_geometry_count'])==64 and r['case_id'] not in old_ids]
 cnt={k:sum(r['global_stratum']==k for r in added) for k in ('LOCAL_AXIS','DEEP_INTERIOR','NEAR_BOUNDARY_NONEXACT')}
 assert cnt=={'LOCAL_AXIS':3,'DEEP_INTERIOR':7,'NEAR_BOUNDARY_NONEXACT':11},cnt
 assert sum(r['global_stratum'] not in ('LOCAL_AXIS','DEEP_INTERIOR','NEAR_BOUNDARY_NONEXACT') for r in added)==11
# Read-only Runner reconciliation: preserve the sampler-time record and validate the current formal state.
dep=loadj(OUT/'RUNNER_MONITOR_DEPENDENCIES_V2.json')
expected_counts={'solver_entries':0,'training_fits':0,'pscale_only_fits':0,'new_fsps':0,'runner_invocations':0,'reserve_launches':0}
assert dep['task_counts']==expected_counts,dep['task_counts']
runner=dep['current_runner']
assert runner['head']=='dc71f90d5836b6fab608ee322ff4889ea064b646'
assert runner['status']=='READY_FOR_EXISTING_12_CASE_ROUTE_AND_ONE_EXT02_SETUP_PREFLIGHT'
assert runner['v2_approved']==0 and runner['v2_canonical_fsp_count']==0 and runner['v2_case_manifest_count']==0
assert runner['current_authorized_geometry_sources']==[] and runner['worktree_clean'] is True
assert runner['slots']==1 and runner['serial_only'] is True and runner['no_replay'] is True
assert dep['geometry_authority']['new_ids_enrolled'] is False and dep['geometry_authority']['v2_geometry_authorities']==0
ext=dep['ext02']
assert ext['setup_preflight']=='PASS' and ext['scientific_entry_count']==0 and ext['solver_invocations']==0
assert ext['post_entry_truth_proved'] is False and ext['cross_height_complex_validation_complete'] is False
assert ext['actual_sampled_z_nm'] is None and ext['production_monitor_changed'] is False
assert ext['separate_explicit_solver_authorization_required'] is True
assert dep['load_only_is_runner_admission'] is False and dep['load_only_is_postentry_truth_recovery'] is False
# The earlier state is retained as historical generation-time evidence, not overwritten.
gen=loadj(OUT/'RUNNER_MONITOR_DEPENDENCIES_AT_GENERATION_V2.json')
assert gen['committed_runner']['head']=='2a6f515a1d28002bca3c4e30094dbf66e463fb17'
assert gen['runner_draft']['formal_authority'] is False
refresh=loadj(OUT/'RUNNER_AUTHORITY_REFRESH_POSTGENERATION_V1.json')
assert refresh['current_runner']['head']==runner['head']
assert refresh['current_runner']['working_tree_clean'] is True and refresh['current_runner']['upstream_ahead_behind']=='0/0'
assert refresh['current_runner']['official_handoff_markdown']['sha256']==runner['handoff_markdown_sha256']
assert refresh['ext02']['preflight']['preflight_v1']['result']=='PASS'
assert refresh['ext02']['preflight']['preflight_v2']['result']=='PASS'
assert refresh['ext02']['authorization_boundary']['this_revision_task_entries']==0
assert refresh['ext02']['production_monitor_changed'] is False
assert refresh['decision'].find('does not enroll')>=0
# Verify every non-self artifact against the current task SHA inventory.
import hashlib
inventory=loadj(OUT/'SHA256_INVENTORY_V2.json')
assert 'RUNNER_MONITOR_DEPENDENCIES_AT_GENERATION_V2.json' in inventory['files']
assert 'RUNNER_AUTHORITY_REFRESH_POSTGENERATION_V1.json' in inventory['files']
for rel,record in inventory['files'].items():
    raw=(OUT/rel).read_bytes()
    canonical=raw.replace(b'\r\n',b'\n')
    assert hashlib.sha256(canonical).hexdigest()==record['sha256'],rel
    assert len(canonical)==record['bytes'],rel
print(json.dumps({'status':'PASS','candidate_counts':role_counts,'global_strata':{'deep32':32,'near56':56,'exact56':56},'boundary':{'dev116':bc(dev),'confirm_core27':bc(core),'stress1':bc(stress),'confirm28':bc(conf)},'outer_folds':4,'inner_rows':len(inner),'learning_curve_rows':len(curve),'reference_overlap':0,'execution_counts':dep['task_counts']},ensure_ascii=False))
