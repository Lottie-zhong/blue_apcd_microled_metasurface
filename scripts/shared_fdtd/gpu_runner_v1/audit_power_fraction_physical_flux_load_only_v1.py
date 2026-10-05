# -*- coding: utf-8 -*-
"""Independent Poynting, modal and source-power audit of one archived run; LOAD only."""
import hashlib, importlib, json, pathlib, subprocess, sys
import numpy as np

REPO=pathlib.Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
RUN=pathlib.Path(r"D:\apcd_runtime\gpu_production_runner_v1\runs\K6LDA1_DEV_D1_M05\attempt_001\K6V2_D1M05_20261004T175055Z_449c4f94")
CASE=pathlib.Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6LDA1_DEV_D1_M05\attempt_001")
REPORT=REPO/"reports"/"gpu_runner_v1_power_fraction_normalization_v1"/"INDEPENDENT_PHYSICAL_POWER_AUDIT.json"
AREA_X_EXPECT=1740e-9
AREA_Y_EXPECT=290e-9
C0=299792458.0
Z0=376.730313668
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open("rb") as f:
  for block in iter(lambda:f.read(8*1024*1024),b""): h.update(block)
 return h.hexdigest()
def vec(x): return np.asarray(x).reshape(-1)
def canonical_fields(raw):
 x=vec(raw["x"]).astype(float); y=vec(raw["y"]).astype(float); f=vec(raw["f"]).astype(float)
 fields={}
 for k in ("Ex","Ey","Hx","Hy"):
  v=np.asarray(raw[k],dtype=complex)
  if v.shape==(x.size,y.size,1,f.size): v=v[:,:,0,:]
  elif v.shape!=(x.size,y.size,f.size): raise ValueError("FIELD_SHAPE:"+k+":"+str(v.shape))
  fields[k]=v
 return x,y,f,fields
def trap_weights(c):
 d=np.diff(c)
 if len(c)<2 or not np.all(np.isfinite(c)) or np.any(d<=0): raise ValueError("BAD_COORDINATES")
 w=np.empty_like(c)
 w[0]=d[0]/2; w[-1]=d[-1]/2
 if c.size>2: w[1:-1]=(d[:-1]+d[1:])/2
 return w
def integrate_plane(raw):
 x,y,f,fields=canonical_fields(raw)
 wx,wy=trap_weights(x),trap_weights(y)
 sz=.5*np.real(fields["Ex"]*np.conj(fields["Hy"])-fields["Ey"]*np.conj(fields["Hx"]))
 flux=np.einsum("i,j,ijf->f",wx,wy,sz)
 area=(x[-1]-x[0])*(y[-1]-y[0])
 order=np.argsort(C0/f*1e9)
 return {"x":x,"y":y,"f":f,"fields":fields,"flux_W":flux[order],"wavelength_nm":(C0/f[order])*1e9,
         "frequency_hz":f[order],"area_m2":area,"x_span_m":x[-1]-x[0],"y_span_m":y[-1]-y[0],"frequency_order":order}
def surface_mean(z,field,x,y,area):
 wx,wy=trap_weights(x),trap_weights(y)
 return np.einsum("i,j,ij->",wx,wy,field[:,:,z])/area

def modal_flux_from_canonical(state, plane, native_frequencies, state_mod):
 plane_index=list(state["planes"]).index(plane)
 wavelengths=np.asarray(state["wavelengths_nm"],dtype=float)
 coefficients=np.asarray(state["coefficients"])[plane_index]
 orders=np.asarray(state["orders"],dtype=int)
 normalization=np.asarray(state["normalization"]["incident_power_per_area"],dtype=float)
 local_index_native=np.asarray(state["plane_metadata"][plane]["local_index"],dtype=complex)
 raw_wavelengths=C0/np.asarray(native_frequencies,dtype=float).reshape(-1)*1e9
 if local_index_native.size!=raw_wavelengths.size or normalization.size!=wavelengths.size:
  raise ValueError("CANONICAL_MODAL_NORMALIZATION_SHAPE")
 sort=np.argsort(raw_wavelengths)
 local_index=local_index_native[sort]
 if not np.allclose(raw_wavelengths[sort],wavelengths,rtol=0,atol=1e-9):
  raise ValueError("CANONICAL_MODAL_INDEX_WAVELENGTH_MISMATCH")
 pols=list(state["polarizations"])
 if len(pols)!=2 or coefficients.shape!=(wavelengths.size,orders.shape[0],2,2):
  raise ValueError("CANONICAL_MODAL_BASIS_SHAPE")
 mode_power=np.zeros(coefficients.shape,dtype=float)
 for wi,wl in enumerate(wavelengths):
  for oi,(m,n) in enumerate(orders):
   for di,direction_sign in enumerate((1,-1)):
    for pi,polarization in enumerate(pols):
     mode=state_mod._mode(int(m),int(n),float(wl),local_index[wi],direction_sign,polarization)
     mode_power[wi,oi,di,pi]=float(mode["power_z_per_abs_e2"])
 q=mode_power*np.abs(coefficients)**2*normalization[:,None,None,None]
 propagating=np.asarray(state["propagating_mask"])[plane_index].astype(bool)
 return {
  "q":q,
  "all_modes_signed_W_m2":np.sum(q,axis=(1,2,3)),
  "propagating_signed_W_m2":np.sum(np.where(propagating[:,:,None,None],q,0.0),axis=(1,2,3)),
  "plus_z_W_m2":np.sum(q[:,:,0,:],axis=(1,2)),
  "minus_z_signed_W_m2":np.sum(q[:,:,1,:],axis=(1,2)),
  "propagating_plus_z_W_m2":np.sum(np.where(propagating[:,:,None],q[:,:,0,:],0.0),axis=(1,2)),
  "propagating_minus_z_signed_W_m2":np.sum(np.where(propagating[:,:,None],q[:,:,1,:],0.0),axis=(1,2)),
  "orders":orders,
 }
def relerr(a,b):
 return float(abs(a-b)/max(abs(a),abs(b),1e-300))
fsp=RUN/"run.fsp"; h5=RUN/"run"/"run_output.h5"
hash_index=json.loads((RUN/"hashes.json").read_text(encoding="utf-8"))
expected={"run.fsp":hash_index["run_fsp_sha256"],"run/run_output.h5":hash_index["run_output_h5_sha256"]}
before={k:sha(RUN/k) for k in expected}
if before!=expected: raise SystemExit("ARCHIVE_HASH_MISMATCH:"+json.dumps({"expected":expected,"actual":before}))
contract_path=CASE/"physical_contract.json"
contract=json.loads(contract_path.read_text(encoding="utf-8"))
if sha(contract_path)!="32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5":
 raise SystemExit("CONTRACT_HASH_MISMATCH")
ps=r'''$rows=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like "fdtd-engine*.exe" } | Select-Object Name,ProcessId,ParentProcessId,CreationDate,CommandLine); ConvertTo-Json -InputObject $rows -Compress'''
pr=subprocess.run(["powershell","-NoProfile","-Command",ps],capture_output=True,text=True,timeout=30)
if pr.returncode: raise SystemExit("PROCESS_CENSUS_FAILED:"+pr.stderr)
engines=json.loads(pr.stdout.strip() or "[]")
if engines: raise SystemExit("ACTIVE_FDTD_ENGINE_PRESENT:"+json.dumps(engines))
sys.path.insert(0,str(REPO/"scripts"/"shared_fdtd"/"gpu_runner_v1"))
import adapter
adapter._prepare_postprocess_import_paths()
launcher=adapter.load_pinned_launcher()
state_mod=importlib.import_module("shared_fdtd.tools.pw_complex_floquet_state_v1")
lumapi=importlib.import_module("lumapi")
fd=None
try:
 fd=lumapi.FDTD(hide=True)
 fd.load(str(fsp))
 raw_in=state_mod.read_fdtd_plane(fd,contract["monitors"]["input"])
 raw_out=state_mod.read_fdtd_plane(fd,contract["monitors"]["output"])
 pin=integrate_plane(raw_in); pout=integrate_plane(raw_out)
 if not np.allclose(pin["wavelength_nm"],pout["wavelength_nm"],rtol=0,atol=1e-7): raise ValueError("PLANE_WAVELENGTH_GRID_MISMATCH")
 if pin["wavelength_nm"].size!=21: raise ValueError("EXPECTED_21_WAVELENGTHS")
 if abs(pout["x_span_m"]-AREA_X_EXPECT)>1e-12 or abs(pout["y_span_m"]-AREA_Y_EXPECT)>1e-12: raise ValueError("POSTNP_NOT_FULL_PERIOD")
 area=pout["area_m2"]
 n_in=state_mod.read_fdtd_index(fd,contract["materials"]["substrate"],pin["f"])
 canonical=state_mod.canonical_state_from_fdtd(fd,contract)
 mon=contract["monitors"]["output"]
 t_native=np.real(vec(fd.transmission(mon)))
 t_result=np.real(vec(fd.getresult(mon,"T")["T"]))
 sp_native=np.real(vec(fd.sourcepower(pout["f"][np.argsort(pout["frequency_order"])]))) # native output-frequency order
 # Compare API arrays in native order, then store wavelength-sorted order.
 freq_native=vec(fd.getdata(mon,"f")).astype(float)
 if t_native.size!=21 or t_result.size!=21 or sp_native.size!=21 or freq_native.size!=21: raise ValueError("OUTPUT_NATIVE_LENGTH")
 api_order=np.argsort(C0/freq_native*1e9)
 t=t_native[api_order]; tr=t_result[api_order]; sourcepower=sp_native[api_order]
 if not np.allclose(t,tr,rtol=1e-10,atol=1e-12): raise ValueError("TRANSMISSION_API_PARITY")
 if not np.allclose(C0/freq_native[api_order]*1e9,pout["wavelength_nm"],rtol=0,atol=1e-7): raise ValueError("OUTPUT_FREQUENCY_ALIGNMENT")
 # Direct IN_REF zero-order TM amplitude from the spatially averaged E/H at MON_IN,
 # de-embedded 50 nm to the frozen reference plane. This is independent of Runner T_FDTD.
 _,_,_,fin=canonical_fields(raw_in)
 in_area=(pin["x_span_m"]*pin["y_span_m"])
 exbar=np.array([surface_mean(k,fin["Ex"],pin["x"],pin["y"],in_area) for k in range(21)])
 hybar=np.array([surface_mean(k,fin["Hy"],pin["x"],pin["y"],in_area) for k in range(21)])
 wl_in=pin["wavelength_nm"]
 n_sorted=n_in[np.argsort(C0/vec(raw_in["f"])*1e9)]
 eplus_sample=.5*(exbar+Z0*hybar/n_sorted)
 eminus_sample=.5*(exbar-Z0*hybar/n_sorted)
 kz=(2*np.pi/(wl_in*1e-9))*n_sorted
 dz=(float(contract["references_nm"][contract["monitors"]["input"]])-float(pin["wavelength_nm"][0])*0+float(np.asarray(raw_in["z"]).reshape(-1)[0])*1e9)*1e-9
 # reference minus sample is -50nm - (-100nm) = +50nm; avoid any nominal substitution.
 zref=float(contract["references_nm"][contract["monitors"]["input"]])*1e-9
 zsample=float(np.asarray(raw_in["z"]).reshape(-1)[0])
 dz=zref-zsample
 eplus_ref=eplus_sample*np.exp(1j*kz*dz)
 eminus_ref=eminus_sample*np.exp(-1j*kz*dz)
 pin_tm_density=.5*np.real(n_sorted/Z0)*np.abs(eplus_ref)**2
 pin_tm_reverse_density=-.5*np.real(n_sorted/Z0)*np.abs(eminus_ref)**2
 pin_te_density=np.zeros(21)
 # Reuse the independently constructed canonical H2 state. Its coefficients are
 # normalized to unit IN_REF incident power; restore physical modal flux with the
 # recorded incident-power density and local-medium modal power factors.
 state_pin=np.asarray(canonical["normalization"]["incident_power_per_area"],dtype=float)
 minfo=modal_flux_from_canonical(canonical,"IN",raw_in["f"],state_mod)
 moutfo=modal_flux_from_canonical(canonical,"POSTNP",raw_out["f"],state_mod)
 orders=np.asarray(minfo["orders"],dtype=int)
 oi={tuple(map(int,x)):i for i,x in enumerate(orders)}
 zero=oi[(0,0)]
 pin_proj_tm=minfo["q"][:,zero,0,1]
 pin_proj_te=minfo["q"][:,zero,0,0]
 # Align frequencies: _plane_projection returns sorted wavelengths; fd.sourcepower/T uses output native order.
 output_flux=pout["flux_W"]
 incident_cell=state_pin*area
 monitor_flux=t*sourcepower
 analysis=launcher.analyze(fd,{"pw_contract":{"contract":contract}},canonical)
 grating_groups=analysis["orders"]["post"]
 analyze_rows=analysis["rows"]
 out_q=moutfo["q"]
 proj_index={tuple(map(int,x)):i for i,x in enumerate(orders)}
 row_out=[]
 all_source_checks=[]
 order_eta_sums=[]
 for wi,wl in enumerate(pout["wavelength_nm"]):
  if len(grating_groups[wi])!=7: raise ValueError("EXPECTED_7_PROPAGATING_GRATING_ORDERS")
  row_orders=[]
  for order_row in grating_groups[wi]:
   mn=(int(order_row["order_x"]),int(order_row["order_y"]))
   if mn not in proj_index: raise ValueError("GRATING_ORDER_MISSING_FROM_H2_MODAL_GRID:"+str(mn))
   j=proj_index[mn]
   q=out_q[wi,j]
   forward_density=float(np.sum(q[0,:]))
   reverse_signed_density=float(np.sum(q[1,:]))
   net_modal_w=(forward_density+reverse_signed_density)*area
   physical_source_fraction=net_modal_w/incident_cell[wi]
   eta=float(order_row["power_fraction_of_monitor_total"])
   loader_expected_source_fraction=float(output_flux[wi]/incident_cell[wi]*eta)
   runner_source=float(order_row["power_fraction_of_source"])
   loader_match=bool(np.isclose(runner_source,loader_expected_source_fraction,rtol=1e-3,atol=1e-9))
   row_orders.append({
    "order_mn":list(mn),
    "grating_eta_monitor_total":eta,
    "grating_u_x":float(order_row["u_x"]),
    "grating_u_y":float(order_row["u_y"]),
    "modal_forward_flux_W":forward_density*area,
    "modal_reverse_signed_flux_W":reverse_signed_density*area,
    "modal_net_flux_W":net_modal_w,
    "modal_net_source_fraction":float(physical_source_fraction),
    "raw_EH_P_scale_IN_REF":float(output_flux[wi]/incident_cell[wi]),
    "loader_expected_source_fraction_from_raw_EH_and_eta":loader_expected_source_fraction,
    "runner_emitted_source_fraction":runner_source,
    "runner_vs_independent_modal_abs":float(abs(runner_source-physical_source_fraction)),
    "runner_vs_independent_modal_rel":relerr(runner_source,physical_source_fraction),
    "runner_vs_frozen_loader_reference_abs":float(abs(runner_source-loader_expected_source_fraction)),
    "runner_vs_frozen_loader_reference_rel":relerr(runner_source,loader_expected_source_fraction),
    "frozen_ingest_numeric_reference_match":loader_match,
   })
   all_source_checks.append(loader_match)
  order_eta_sums.append(sum(x["grating_eta_monitor_total"] for x in row_orders))
  q0=out_q[wi,proj_index[(0,0)]]
  zero_forward=float(np.sum(q0[0,:])*area)
  zero_reverse=float(np.sum(q0[1,:])*area)
  row_out.append({
   "wavelength_nm":float(wl),
   "frequency_hz":float(pout["frequency_hz"][wi]),
   "postnp_sample_z_m":float(np.asarray(raw_out["z"]).reshape(-1)[0]),
   "postnp_surface_flux_integral_W":float(output_flux[wi]),
   "postnp_monitor_transmission":float(t[wi]),
   "runner_output_P_scale_IN_REF":float(analyze_rows[wi]["output_P_scale_IN_REF"]),
   "independent_raw_EH_P_scale_IN_REF":float(output_flux[wi]/incident_cell[wi]),
   "postnp_getresult_T":float(tr[wi]),
   "sourcepower_W":float(sourcepower[wi]),
   "transmission_times_sourcepower_W":float(monitor_flux[wi]),
   "monitor_flux_vs_EH_integral_relative_difference":relerr(monitor_flux[wi],output_flux[wi]),
   "IN_REF_incident_power_per_area_W_m2":float(state_pin[wi]),
   "IN_REF_incident_cell_power_W":float(incident_cell[wi]),
   "IN_REF_manual_TM_forward_power_per_area_W_m2":float(pin_tm_density[wi]),
   "IN_REF_frozen_modal_TM_forward_power_per_area_W_m2":float(pin_proj_tm[wi]),
   "IN_REF_manual_TM_reverse_signed_W_m2":float(pin_tm_reverse_density[wi]),
   "IN_REF_frozen_modal_TE_forward_W_m2":float(pin_proj_te[wi]),
   "IN_plane_total_signed_EH_flux_W":float(pin["flux_W"][wi]),
   "IN_plane_frozen_modal_total_signed_flux_W_m2":float(minfo["all_modes_signed_W_m2"][wi]),
   "POSTNP_frozen_modal_total_signed_flux_W_m2":float(moutfo["all_modes_signed_W_m2"][wi]),
   "POSTNP_frozen_modal_propagating_signed_flux_W_m2":float(moutfo["propagating_signed_W_m2"][wi]),
   "POSTNP_surface_flux_vs_all_modal_relative_difference":relerr(output_flux[wi]/area,moutfo["all_modes_signed_W_m2"][wi]),
   "POSTNP_zero_order_forward_modal_flux_W":zero_forward,
   "POSTNP_zero_order_reverse_signed_modal_flux_W":zero_reverse,
   "runner_zero_order_T_FDTD_mode_proxy":float(analyze_rows[wi]["T_FDTD"]),
   "runner_total_T_monitor":float(t[wi]),
   "grating_eta_sum":float(order_eta_sums[-1]),
   "orders":row_orders,
  })
finally:
 if fd is not None:
  try: fd.close()
  except Exception: pass
after={k:sha(RUN/k) for k in expected}
if before!=after: raise SystemExit("ARCHIVE_MUTATED_DURING_AUDIT")
# Coupling v2 frozen checks found in k6_v2_pipeline/ingest.py.
eta_sum_pass=bool(np.allclose(order_eta_sums,1.0,rtol=0,atol=1e-6))
direct_order_comparator_allclose=bool(all(all_source_checks))
max_mon=max(r["monitor_flux_vs_EH_integral_relative_difference"] for r in row_out)
max_modal=max(r["POSTNP_surface_flux_vs_all_modal_relative_difference"] for r in row_out)
report={
 "schema":"APCD_GPU_RUNNER_V1_INDEPENDENT_PHYSICAL_POWER_AUDIT_V1",
 "result":"MEASURED",
 "scientific_entry_performed":False,"solver_run_called":False,"fsp_save_called":False,
 "case_id":"K6LDA1_DEV_D1_M05","attempt_id":"attempt_001","run_id":"K6V2_D1M05_20261004T175055Z_449c4f94",
 "physical_contract_sha256":sha(contract_path),
 "frozen_definitions":{
  "P_scale":"POSTNP full-period E/H surface flux divided by unit-cell area times IN_REF +z (0,0) TM incident power per area",
  "incident_reference":"IN_REF, +z zero-order TM; propagated to frozen reference plane",
  "grating_eta":"Lumerical grating order fraction of monitor-total transmitted flux",
  "legacy_T_FDTD":"Runner's zero-order modal amplitude proxy; not total multi-order transmission",
  "applicable_ingest_checks":{
   "eta_sum":"np.allclose(sum(eta),1,rtol=0,atol=1e-6)",
   "runner_source_fraction_vs_Coupling_raw_flux_scale_times_same_eta":"np.allclose(...,rtol=1e-3,atol=1e-9)",
   "raw_full_period_span":"x/y span within 1e-12 m of 1740/290 nm",
   "raw_wavelength_alignment":"absolute tolerance 1e-7 nm",
   "scope":"These are frozen ingestion/shape checks. No frozen direct threshold was found for transmission*sourcepower vs independently integrated E/H flux, or grating eta vs H2 modal per-order flux."
  },
 },
 "archive_hashes_before_after":{
  "run_fsp":{"sha256":before["run.fsp"],"after":after["run.fsp"]},
  "run_output_h5":{"sha256":before["run/run_output.h5"],"after":after["run/run_output.h5"]},
 },
 "backend":{
  "backend_id":adapter.PINNED_BACKEND_ID,"launcher_sha256":adapter.LAUNCHER_SHA256,
  "backend_manifest_sha256":sha(adapter.LAUNCHER_PATH.parents[3]/"manifest.json"),
  "inventory_sha256":json.loads((adapter.LAUNCHER_PATH.parents[3]/"manifest.json").read_text(encoding="utf-8"))["inventory_sha256"],
 },
 "grid":{
  "wavelength_count":len(row_out),"x_samples":int(len(pout["x"])),"y_samples":int(len(pout["y"])),
  "x_span_m":float(pout["x_span_m"]),"y_span_m":float(pout["y_span_m"]),
  "unit_cell_area_m2":float(area),"monitor_actual_z_nm":float(np.asarray(raw_out["z"]).reshape(-1)[0]*1e9),
 },
 "aggregate":{
  "transmission_getresult_api_parity_max_abs":float(np.max(np.abs(t-tr))),
  "max_rel_transmission_sourcepower_vs_postnp_EH_flux":float(max_mon),
  "max_rel_postnp_EH_flux_vs_frozen_H2_all_modal_sum":float(max_modal),
  "grating_eta_sum_pass_frozen_atol_1e-6":eta_sum_pass,
  "runner_source_fraction_matches_frozen_loader_reference":direct_order_comparator_allclose,
  "nonzero_diffraction_present":bool(max(max(x["grating_eta_monitor_total"] for x in r["orders"] if x["order_mn"]!=(0,0)) for r in row_out)>0),
  "max_runner_vs_modal_source_fraction_rel":max(x["runner_vs_independent_modal_rel"] for r in row_out for x in r["orders"]),
  "max_runner_vs_modal_source_fraction_abs":max(x["runner_vs_independent_modal_abs"] for r in row_out for x in r["orders"]),
 },
 "wavelength_rows":row_out,
 "interpretation":"Independent physical checks are reported without invented pass thresholds where none are frozen. The Coupling ingest rtol=1e-3/atol=1e-9 check is applied only to Runner source fractions versus independently integrated raw POSTNP E/H P_scale times the same measured grating eta; it is a downstream consistency check, not a physical closure test. Runner-versus-H2 modal residual is reported separately without applying that ingest tolerance.",
 "active_fdtd_engine_processes_before_load":engines,
}
REPORT.parent.mkdir(parents=True,exist_ok=True)
REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":report["result"],"report":str(REPORT),"backend":report["backend"],
 "grid":report["grid"],"aggregate":report["aggregate"],
 "first_row":row_out[0],"peak_transmission_flux_residual":max(row_out,key=lambda r:r["monitor_flux_vs_EH_integral_relative_difference"]),
 "peak_physical_source_fraction_residual":max((x for r in row_out for x in r["orders"]),key=lambda x:x["runner_vs_independent_modal_rel"])},indent=2))
