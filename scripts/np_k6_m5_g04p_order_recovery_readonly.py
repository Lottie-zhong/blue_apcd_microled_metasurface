import sys,json,csv,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
POST=ROOT/r'outputs\np_k6_m2_g04p_controlled_recompute_v1\runtime_replacement\G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1\attempt_001\G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1_attempt_001_post.fsp'
OUT=ROOT/r'outputs\np_k6_m5_fullk6_forward_v0\g04p_order_recovery'
W=list(range(445,456)); CASE='NP_K6_M2_BATCH1_G04_P'
def flat(x): return np.asarray(x).reshape(-1)
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def main():
 OUT.mkdir(parents=True,exist_ok=True); before=sha(POST)
 fd=lumapi.FDTD(str(POST),hide=True)
 rows=[]; meta={'case_id':CASE,'post_fsp_path':str(POST),'post_fsp_sha256_before':before,'readonly_reload':True,'run_called':False,'save_called':False,'solver_calls':0}
 try:
  tr=fd.getresult('transmission_monitor','T'); lam=flat(tr['lambda'])*1e9; t=np.real(flat(tr['T']))
  for i,wl in enumerate(W):
   fr=flat(fd.grating('transmission_monitor',i+1)); oo=np.rint(np.real(flat(fd.gratingn('transmission_monitor',i+1)))).astype(int); ux=np.real(flat(fd.gratingu1('transmission_monitor',i+1)))
   for j,n in enumerate(oo): rows.append({'case_id':CASE,'wavelength_nm':int(wl),'order_n':int(n),'u_x':float(ux[j]),'angle_deg':float(np.degrees(np.arcsin(np.clip(ux[j],-1,1)))),'transmitted_fraction':float(np.real(fr[j])),'absolute_efficiency':float(t[i]*np.real(fr[j]))})
  if list(np.rint(lam).astype(int))!=W: raise RuntimeError('wavelength axis mismatch')
 finally: fd.close()
 after=sha(POST); meta.update({'post_fsp_sha256_after':after,'post_fsp_unchanged':before==after,'rows':len(rows),'orders':sorted(set(x['order_n'] for x in rows)),'exact_11x7':len(rows)==77})
 with open(OUT/'hf_transmitted_orders_long.csv','w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 (OUT/'recovery_manifest.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8'); print(json.dumps(meta,indent=2))
if __name__=='__main__': main()
