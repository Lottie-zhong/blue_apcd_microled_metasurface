"""Revalidate the sealed audit inventory, optionally including large native byte hashes. No fits/LOAD."""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
O=R/'reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1'
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import contracts as C,ingest,h1
def sha(p):return ingest.sha256_file(p)
def main(full_native=False):
 d=json.loads((O/'DEVELOPMENT_156G_DATASET_INVENTORY.json').read_text(encoding='utf-8'));reg=ingest.load_frozen_case_registry(R)
 assert d['status']=='DATASET_READY' and d['valid_count']==156 and len(d['cases'])==156 and not d['errors']
 assert len({q['case_id'] for q in d['cases']})==len({tuple(q['ordered_D_nm']) for q in d['cases']})==156
 assert set(q['case_id'] for q in d['cases']).isdisjoint(reg.confirmation)
 old={c.case_id:c for c in ingest._old32(R,reg)};dec=h1.load_h2_decoder();h1.load_h1_authority();checked=0
 for q in d['cases']:
  assert q['role'] in C.DEVELOPMENT_ROLES and q['physical_contract_sha256']==C.PHYSICAL_CONTRACT_SHA256 and q['reference_plane_nm']==1722.
  assert q['wavelength_points']==list(C.WAVELENGTHS_NM) and q['orders_mn']==[list(x) for x in C.ORDER_MN] and q['polarizations']==['TE','TM']
  if q['case_id'] in old:c=old[q['case_id']];chat=c.c_hat;ps=c.p_scale
  else:
   p=q['artifacts']['label'];assert sha(p['path'])==p['sha256']
   with np.load(p['path'],allow_pickle=False) as z:
    assert str(z['case_id'])==q['case_id'] and str(z['attempt_id'])==q['attempt_id']
    if 'C_hat_real' in z.files:chat=z['C_hat_real']+1j*z['C_hat_imag'];ps=z['P_scale']
    elif 'C_hat' in z.files:chat=z['C_hat'];ps=z['P_scale']
    else:chat=z['c_hat'];ps=z['p_scale']
  assert C.pack_model_target(chat,ps).shape==(1,609)
  h1.reconstruct_h2(chat,ps,dec)
  for art in q['native_files']:
   p=Path(art['path']);assert p.is_file() and p.stat().st_size==art['bytes']
   if full_native:assert sha(p)==art['sha256']
  assert q['native_EH_datasets'];checked+=1
 assert sha(d['ledger']['path'])==d['ledger']['sha256']
 return {'status':'PASS','cases_verified':checked,'label_SHA_rechecked':124,'native_SHA_rechecked_this_invocation':full_native,
 'native_SHA_initial_audit':'All native156 bytes measured in closure audit; archive/source receipt hashes checked separately',
 'solver':0,'fits':0,'confirmation_response_access':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--full-native-sha',action='store_true');a=p.parse_args();print(json.dumps(main(a.full_native_sha)))
