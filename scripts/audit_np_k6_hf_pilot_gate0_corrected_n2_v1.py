import json,hashlib,sys,math
from pathlib import Path
sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python'); import lumapi
R=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); E=R/'outputs/np_k6_hf_pilot_gate0_n2_production_mesh_v1_corrected_monitor_contract_v1'; old=R/r'outputs/np_k6_p1d4b_k6x_fullwave_v1/runtime_prefsp_run3c_fixed_nested_mesh_v1/N2/BROADBAND_PARETO_K6X_FIXED_NESTED_N2.fsp'; src=E/'BROADBAND_PARETO_K6X_FIXED_NESTED_N2_WITH_N1_DIAGNOSTIC_MONITORS.fsp'
REQ=['N1_DIAG_LOWER_INSIDE','N1_DIAG_LOWER_OUTSIDE','N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_LOWER','N1_DIAG_PML_UPPER','N1_DIAG_XZ_INDEX_449']; PWR={'N1_DIAG_LOWER_INSIDE':-90,'N1_DIAG_LOWER_OUTSIDE':-110,'N1_DIAG_UPPER_INSIDE':590,'N1_DIAG_UPPER_OUTSIDE':610,'N1_DIAG_PML_LOWER':-500,'N1_DIAG_PML_UPPER':1100}
CASES=['RUN3C_N2_NATIVE_M1_X_PRODUCTION_GATE','RUN3C_N2_NATIVE_M1_Y_PRODUCTION_GATE','RUN3A_N2_NATIVE_M1_X_PRODUCTION_GATE','RUN3A_N2_NATIVE_M1_Y_PRODUCTION_GATE','RUN3B_N2_NATIVE_M1_X_PRODUCTION_GATE','RUN3B_N2_NATIVE_M1_Y_PRODUCTION_GATE']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(f,n,p):
 try:
  x=f.getnamed(n,p); return x.tolist() if hasattr(x,'tolist') else x
 except Exception as e:return 'UNAVAILABLE:'+str(e)
def close(a,b,tol=1e-12):
 try:return abs(float(a)-float(b))<=tol
 except:return False
def names(f):
 f.eval("groupscope('::model'); unselectall; selectall;"); out=[]
 for o in f.getAllSelectedObjects():
  try:out.append(str(getattr(o,'name')))
  except:pass
 return out
def audit(p):
 f=lumapi.FDTD(str(p),hide=True)
 try:
  ns=names(f); mesh={x:get(f,'RUN3C_FIXED_NESTED_N2',x) for x in ['x','y','z','x span','y span','z span','dx','dy','dz']}; srcd={x:get(f,'source_x_forward',x) for x in ['direction','injection axis','polarization angle','wavelength start','wavelength stop']}; mats={m:{'type':str(f.getmaterial(m,'type')),'sampled_rows':len(f.getmaterial(m,'sampled data'))} for m in ['APCD_TIO2_NATIVE_M1','APCD_SIO2_NATIVE_M1']}
  pm={n:{x:get(f,n,x) for x in ['z','x span','y span','monitor type','frequency points','use source limits','use wavelength spacing','spatial interpolation']} for n in REQ[:-1]}; xz={x:get(f,REQ[-1],x) for x in ['x','y','z','x span','y span','z span','monitor type','frequency points','use source limits','use wavelength spacing','spatial interpolation','frequency center','frequency span','wavelength center','wavelength span','down sample X','down sample Z']}
 finally:f.close()
 checks={'required_objects':all(x in ns for x in REQ),'power_z':all(close(pm[n]['z']*1e9,PWR[n]) for n in PWR),'power_spans':all(close(pm[n]['x span']*1e9,1740) and close(pm[n]['y span']*1e9,290) for n in PWR),'power_contract':all(pm[n]['monitor type']=='2D Z-normal' and close(pm[n]['frequency points'],11) and close(pm[n]['use source limits'],1) and close(pm[n]['use wavelength spacing'],1) and pm[n]['spatial interpolation']=='nearest mesh cell' for n in PWR),'xz_contract':xz['monitor type']=='2D Y-normal' and close(xz['y'],0) and close(xz['x span']*1e9,1740) and close(xz['z span']*1e9,1800) and close(xz['frequency points'],1) and close(xz['use source limits'],0) and xz['spatial interpolation']=='none' and close(xz['wavelength center']*1e9,449) and close(xz['wavelength span']*1e9,0) and close(xz['down sample X'],1) and close(xz['down sample Z'],1),'mesh_contract':all(close(mesh[k],v) for k,v in {'x':0,'y':0,'z':250e-9,'x span':1740e-9,'y span':290e-9,'z span':700e-9,'dx':5e-9,'dy':5e-9,'dz':5e-9}.items()),'material_contract':all(v['type']=='Sampled 3D data' and v['sampled_rows']>1 for v in mats.values())}
 return {'path':str(p),'sha256':sha(p),'object_names':ns,'mesh':mesh,'source':srcd,'materials':mats,'power_monitors':pm,'xz_monitor':xz,'checks':checks,'pass':all(checks.values())}
def main():
 assert sha(old)=='5847aadcc4da2279e71de85c952287442b21e9ca2fae552f5ae1b6eeca05ac51'; out={'corrected_source':audit(src),'cases':{c:audit(E/'runtime_prefsp'/(c+'.fsp')) for c in CASES}}
 out['all_pass']=out['corrected_source']['pass'] and all(x['pass'] for x in out['cases'].values()); out['solver_entered']=0; out['old_n2_unchanged']=sha(old)=='5847aadcc4da2279e71de85c952287442b21e9ca2fae552f5ae1b6eeca05ac51'
 (E/'corrected_monitor_contract_audit.json').write_text(json.dumps(out,indent=2,sort_keys=True,default=str),encoding='utf-8'); (E/'corrected_setup_state.json').write_text(json.dumps({'state':'READY_FOR_GATE0_SOLVER_AUTHORIZATION' if out['all_pass'] else 'HARD_GATE_CORRECTED_N2_MONITOR_CONTRACT_READBACK_FAILED','corrected_source_sha256':sha(src),'all_setup_audit_pass':out['all_pass'],'solver_entered':0,'production_mesh_frozen':False},indent=2),encoding='utf-8'); print(json.dumps({'all_pass':out['all_pass'],'solver_entered':0,'corrected_source_sha256':sha(src)},default=str))
if __name__=='__main__':main()
