from __future__ import annotations

import argparse, csv, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_np_k6_unitcell_setup_v1 as base
import run_np_k6_p1d2a_broadband_blank_x_v1 as shared

CASE = "NP_P1D2_BROADBAND_PILLAR_H500_D100_X"
DIAMETER_NM, HEIGHT_NM = 100, 500
RUNTIME = ROOT / "runtime_fsp" / "np_k6_p1d2_broadband_v1"
OUT = ROOT / "outputs" / "np_k6_p1d2b0_broadband_d100_x_v1"
PRE, POST = RUNTIME / f"{CASE}_pre.fsp", RUNTIME / f"{CASE}_post.fsp"
BLANK_OUT = ROOT / "outputs" / "np_k6_p1d2a_broadband_blank_x_v1"

def _json(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, value: Any) -> None: path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n", encoding="utf-8")
def _hash(value: Any) -> str: return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def spec(case_id: str = CASE, diameter_nm: int = DIAMETER_NM) -> dict[str, Any]:
    if case_id != CASE or diameter_nm != DIAMETER_NM: raise ValueError("only H500/D100/x is authorized")
    base.validate_geometry(HEIGHT_NM, DIAMETER_NM)
    return {"case_id": CASE, "geometry_type": "circular_tio2_pillar", "height_nm": HEIGHT_NM,
            "diameter_nm": DIAMETER_NM, "radius_nm": 50, "gap_nm": 190, "aspect_ratio": 5.0,
            "polarization": "x", "normal_incidence": True, "target_wavelength_grid_nm": shared.target_axis(),
            "sampling_backend": shared.BACKEND, "monitor_mapping": shared.build_spec()["monitor_mapping"],
            "inherited_builder_spec": base.build_spec("pillar", 450, "x", HEIGHT_NM, DIAMETER_NM)}

def _delete(fdtd: Any, name: str) -> None:
    if int(fdtd.getnamednumber(name)): fdtd.select(name); fdtd.delete()
def _fp(path: Path) -> dict[str, Any]: return shared.fingerprint(path)

def blank_evidence() -> dict[str, Any]:
    library = _json(ROOT/"outputs"/"np_k6_p1d2_broadband_contract_v1"/"broadband_library_contract.json")
    spectrum = _json(BLANK_OUT/"blank_spectrum.json"); audit = _json(BLANK_OUT/"wavelength_axis_audit.json")
    if library["broadband_blank_status"] != "trusted_completed" or library["broadband_blank_id"] != "NP_P1D2_BROADBAND_FIXED_REFERENCE_BLANK_X": raise RuntimeError("blank release not trusted")
    if library["broadband_blank_result_hash"] != shared.sha256(BLANK_OUT/"blank_spectrum.json"): raise RuntimeError("blank result hash mismatch")
    if not (library["broadband_blank_fsp_path"] and (ROOT/library["broadband_blank_fsp_path"]).exists()): raise RuntimeError("blank post-FSP missing")
    if len(spectrum["rows"]) != 11 or audit["sampling_backend"] != shared.BACKEND: raise RuntimeError("blank spectral evidence invalid")
    return {"library": library, "spectrum": spectrum, "audit": audit}

def build_pre(s: dict[str, Any]) -> dict[str, Any]:
    PRE.parent.mkdir(parents=True, exist_ok=True); base.create_setup(s["inherited_builder_spec"], PRE)
    fdtd = base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(PRE)); _delete(fdtd,"R_fields"); _delete(fdtd,"T_fields"); fdtd.select("source")
        shared._set(fdtd,"wavelength start",shared.SOURCE_START_NM*base.NM); shared._set(fdtd,"wavelength stop",shared.SOURCE_STOP_NM*base.NM); shared._set(fdtd,"polarization angle",0)
        for w in shared.TARGET_NM:
            t,r,e=shared.monitor_names(w)
            shared._configure_monitor(fdtd,t,w,base.LAYOUT_NM["transmission_monitor_z_nm"],False)
            shared._configure_monitor(fdtd,r,w,base.LAYOUT_NM["reflection_monitor_z_nm"],False)
            shared._configure_monitor(fdtd,e,w,base.LAYOUT_NM["transmission_monitor_z_nm"],True)
        fdtd.save(str(PRE))
    finally: fdtd.close()
    return audit(PRE,s)

def _read(fdtd: Any,name: str,prop: str) -> float: return float(np.squeeze(fdtd.getnamed(name,prop)))

def compare_contract(s: dict[str, Any], a: dict[str, Any]) -> dict[str, Any]:
    blank = blank_evidence()["library"]
    common = {"pitch_nm":290,"source_nm":[440,460,-500],"axis_nm":shared.target_axis(),"backend":shared.BACKEND,"mapping":s["monitor_mapping"],"fdt_nm":[-1000,1200],"reference_nm":[-750,900],"boundaries":["Periodic","Periodic","PML"],"simulation_time_s":a["simulation_time_s"],"auto_shutoff_min":a["auto_shutoff_min"],"native_material_chain":"Native-M1"}
    b = dict(common, pillar_present=False, pillar_geometry=None, geometry_hash=_hash({"blank":True}))
    pgeo={"height_nm":500,"diameter_nm":100,"radius_nm":50,"base_nm":0,"top_nm":500,"material":"APCD_TIO2_NATIVE_M1","mesh_override_nm":[-20,720,5]}
    p = dict(common, pillar_present=True, pillar_geometry=pgeo, geometry_hash=_hash(pgeo))
    diff={k:{"blank":b.get(k),"pillar":p.get(k)} for k in sorted(set(b)|set(p)) if b.get(k)!=p.get(k)}
    allowed=sorted(["pillar_present","pillar_geometry","geometry_hash"])
    if sorted(diff) != allowed: raise RuntimeError(f"unexpected contract differences: {sorted(diff)}")
    return {"allowed_contract_differences":allowed,"actual_differences":diff,"equivalence_gate":True,"blank_contract_hash":blank["broadband_blank_physical_contract_hash"],"comparison_hash":_hash(diff)}

def audit(path: Path, s: dict[str, Any]) -> dict[str, Any]:
    before=_fp(path); fdtd=base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(path))
        if int(fdtd.getnamednumber("TiO2 pillar")) != 1: raise RuntimeError("exactly one pillar required")
        g={"radius_nm":_read(fdtd,"TiO2 pillar","radius")/base.NM,"z_min_nm":_read(fdtd,"TiO2 pillar","z min")/base.NM,"z_max_nm":_read(fdtd,"TiO2 pillar","z max")/base.NM,"material":str(fdtd.getnamed("TiO2 pillar","material")),"source_start_nm":_read(fdtd,"source","wavelength start")/base.NM,"source_stop_nm":_read(fdtd,"source","wavelength stop")/base.NM,"source_angle_deg":_read(fdtd,"source","polarization angle"),"source_z_nm":_read(fdtd,"source","z")/base.NM,"simulation_time_s":_read(fdtd,"FDTD","simulation time"),"auto_shutoff_min":_read(fdtd,"FDTD","auto shutoff min")}
        axis=[]; inventory=[]
        for w in shared.TARGET_NM:
            for n in shared.monitor_names(w):
                c=_read(fdtd,n,"wavelength center")/base.NM; span=_read(fdtd,n,"wavelength span")/base.NM; pts=int(_read(fdtd,n,"frequency points")); wl=bool(fdtd.getnamed(n,"use wavelength spacing")); lim=bool(fdtd.getnamed(n,"use source limits")); z=_read(fdtd,n,"z")/base.NM
                if not (pts==1 and wl and not lim and abs(span)<1e-9 and math.isclose(c,w,abs_tol=1e-6)): raise RuntimeError(f"monitor contract failed: {n}")
                if n.startswith("T_FIELDS"): axis.append(c)
                inventory.append({"name":n,"wavelength_nm":c,"z_nm":z,"priming_span_configuration":"verified_zero_span_after_priming"})
        if not np.allclose(axis,shared.target_axis(),atol=1e-6,rtol=0) or len(inventory)!=33: raise RuntimeError("axis/inventory failure")
        if not (math.isclose(g["radius_nm"],50,abs_tol=1e-6) and math.isclose(g["z_min_nm"],0,abs_tol=1e-6) and math.isclose(g["z_max_nm"],500,abs_tol=1e-6) and g["material"]=="APCD_TIO2_NATIVE_M1" and math.isclose(g["source_angle_deg"],0,abs_tol=1e-12)): raise RuntimeError("D100 geometry/material failure")
        result={"case_id":CASE,"geometry":g,"monitor_count":len(inventory),"configured_axis_nm":axis,"monitor_inventory":inventory,"sampling_backend":shared.BACKEND}
    finally: fdtd.close()
    after=_fp(path)
    if before != after: raise RuntimeError("read-only FSP audit changed file")
    result["fingerprint"]=after; result["contract_diff"]=compare_contract(s,g); return result

def _phase(z: complex) -> dict[str,float]: return {"real":z.real,"imag":z.imag,"amplitude":abs(z),"phase_rad_wrapped":float(np.angle(z)),"phase_deg_wrapped":float(np.degrees(np.angle(z)))}

def extract(path: Path) -> dict[str, Any]:
    bmap={round(r["wavelength_nm"]):r for r in blank_evidence()["spectrum"]["rows"]}; before=_fp(path); fdtd=base._import_lumapi().FDTD(hide=True); rows=[]
    try:
        fdtd.load(str(path))
        for w in shared.TARGET_NM:
            tname,rname,ename=shared.monitor_names(w); fields=fdtd.getresult(ename,"E"); e=np.squeeze(np.asarray(fields["E"])); lam=float(np.squeeze(fields["lambda"]))/base.NM
            if e.ndim!=3 or e.shape[-1]!=3 or not math.isclose(lam,w,abs_tol=1e-6): raise RuntimeError(f"bad field data {w}")
            ax=shared._area_average(e[...,0],fields["x"],fields["y"]); ay=shared._area_average(e[...,1],fields["x"],fields["y"]); T=float(np.squeeze(fdtd.transmission(tname))); Rraw=float(np.squeeze(fdtd.transmission(rname))); bx=complex(bmap[w]["ax"]["real"],bmap[w]["ax"]["imag"])
            if abs(bx)<1e-12: raise RuntimeError(f"unsafe blank denominator {w}")
            txx,tyx=ax/bx,ay/bx; Rt=-Rraw; co=bmap[w]["T"]*abs(txx)**2; cross=bmap[w]["T"]*abs(tyx)**2; recon=co+cross
            if not np.isfinite([T,Rraw,ax.real,ax.imag,ay.real,ay.imag,txx.real,txx.imag,tyx.real,tyx.imag]).all(): raise RuntimeError(f"nonfinite {w}")
            rows.append({"wavelength_nm":lam,"frequency_hz":299792458/(lam*base.NM),"T":T,"R_raw":Rraw,"R_total":Rt,"energy_residual":abs(1-T-Rt),"ax_pillar":_phase(ax),"ay_pillar":_phase(ay),"txx":_phase(txx),"tyx":_phase(tyx),"co_pol_zero_order_power":co,"cross_pol_zero_order_power":cross,"cross_pol_fraction":cross/recon if recon else 0.0,"x_input_reconstruction_residual":abs(recon-T)})
    finally: fdtd.close()
    after=_fp(path)
    if before!=after: raise RuntimeError("post FSP changed during extraction")
    return {"rows":rows,"fingerprint":after}

def write_outputs(s:dict[str,Any], pre:dict[str,Any], post:dict[str,Any]) -> dict[str,Any]:
    OUT.mkdir(parents=True,exist_ok=True); rows=post["rows"]; axis=[r["wavelength_nm"] for r in rows]
    if not np.allclose(axis,shared.target_axis(),atol=1e-6,rtol=0): raise RuntimeError("pillar axis mismatch")
    phase=np.unwrap([r["txx"]["phase_rad_wrapped"] for r in rows]); i=5; phase_deg=np.degrees(phase-phase[i]+rows[i]["txx"]["phase_rad_wrapped"]); coef=np.polyfit(shared.target_axis(),phase_deg,1); fit=np.polyval(coef,shared.target_axis()); amps=np.array([r["txx"]["amplitude"] for r in rows]); energy=np.array([r["energy_residual"] for r in rows]); recon=np.array([r["x_input_reconstruction_residual"] for r in rows])
    metrics={"phase_at_445_nm":float(phase_deg[0]),"phase_at_450_nm":float(phase_deg[i]),"phase_at_455_nm":float(phase_deg[-1]),"phase_shift_445_to_455_deg":float(phase_deg[-1]-phase_deg[0]),"phase_peak_to_peak_over_band":float(np.ptp(phase_deg)),"phase_linear_fit_slope_deg_per_nm":float(coef[0]),"phase_linear_fit_rms_residual_deg":float(np.sqrt(np.mean((phase_deg-fit)**2))),"txx_amplitude_min_over_band":float(amps.min()),"txx_amplitude_max_over_band":float(amps.max()),"txx_amplitude_peak_to_peak":float(np.ptp(amps)),"txx_amplitude_CV_over_band":float(amps.std()/amps.mean()),"T_min_over_band":min(r["T"] for r in rows),"T_max_over_band":max(r["T"] for r in rows),"T_peak_to_peak":max(r["T"] for r in rows)-min(r["T"] for r in rows),"R_total_min_over_band":min(r["R_total"] for r in rows),"R_total_max_over_band":max(r["R_total"] for r in rows),"cross_pol_max_over_band":max(r["tyx"]["amplitude"] for r in rows),"energy_residual_mean_over_band":float(energy.mean()),"energy_residual_max_over_band":float(energy.max()),"reconstruction_residual_mean_over_band":float(recon.mean()),"reconstruction_residual_max_over_band":float(recon.max())}
    quality="pass" if max(metrics["energy_residual_max_over_band"],metrics["reconstruction_residual_max_over_band"])<=.03 else "warning_valid" if max(metrics["energy_residual_max_over_band"],metrics["reconstruction_residual_max_over_band"])<=.08 else "fail_data_quality"
    contract={"case_id":CASE,"geometry_type":s["geometry_type"],"pillar_present":True,"pillar_geometry":{"height_nm":500,"diameter_nm":100,"radius_nm":50,"base_nm":0,"top_nm":500,"material":"APCD_TIO2_NATIVE_M1"},"sampling_backend":shared.BACKEND,"target_axis_nm":shared.target_axis(),"monitor_mapping":s["monitor_mapping"],"pre_audit":pre,"blank_pillar_contract_diff_hash":pre["contract_diff"]["comparison_hash"],"interpolation_used":False,"nearest_neighbor_used":False}
    summary={"P1D2B0_FORMAL_STATUS":"pass" if quality!="fail_data_quality" else "fail","finite_data_gate":True,"denominator_safety_gate":True,"blank_pillar_axis_match_gate":True,"post_fsp_readonly_gate":True,"individual_pillar_spectral_quality":quality,"metrics":metrics}
    manifest={"case_id":CASE,"created_utc":datetime.now(timezone.utc).isoformat(),"pre_fsp":pre["fingerprint"],"post_fsp":post["fingerprint"],"physical_contract_hash":_hash(contract),"new_solver_run_entered":1,"new_solver_run_completed":1}
    _write(OUT/"results.json",{"case_id":CASE,"rows":rows}); _write(OUT/"spectral_metrics.json",metrics); _write(OUT/"wavelength_axis_audit.json",{"target_axis":shared.target_axis(),"configured_axis":pre["configured_axis_nm"],"extracted_axis":axis,"exact_axis_gate":True,"interpolation_used":False,"nearest_neighbor_used":False,"sampling_backend":shared.BACKEND}); _write(OUT/"blank_pillar_contract_diff.json",pre["contract_diff"]); _write(OUT/"physical_contract.json",contract); _write(OUT/"run_manifest.json",manifest); _write(OUT/"verification_summary.json",summary)
    fields=["wavelength_nm","frequency_hz","T","R_raw","R_total","energy_residual","ax_pillar_real","ax_pillar_imag","ax_pillar_amplitude","ax_pillar_phase_deg","ay_pillar_real","ay_pillar_imag","ay_pillar_amplitude","ay_pillar_phase_deg","txx_real","txx_imag","txx_amplitude","txx_phase_deg_wrapped","tyx_real","tyx_imag","tyx_amplitude","tyx_phase_deg_wrapped","cross_pol_fraction","x_input_reconstruction_residual"]
    with (OUT/"results.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:
            d={"wavelength_nm":r["wavelength_nm"],"frequency_hz":r["frequency_hz"],"T":r["T"],"R_raw":r["R_raw"],"R_total":r["R_total"],"energy_residual":r["energy_residual"],"cross_pol_fraction":r["cross_pol_fraction"],"x_input_reconstruction_residual":r["x_input_reconstruction_residual"]}
            for q,prefix in (("ax_pillar","ax_pillar"),("ay_pillar","ay_pillar"),("txx","txx"),("tyx","tyx")):
                d.update({prefix+"_real":r[q]["real"],prefix+"_imag":r[q]["imag"],prefix+"_amplitude":r[q]["amplitude"],prefix+("_phase_deg_wrapped" if prefix in ("txx","tyx") else "_phase_deg"):r[q]["phase_deg_wrapped"]})
            w.writerow(d)
    progress={"P1D2B0_FORMAL_STATUS":summary["P1D2B0_FORMAL_STATUS"],"completed_broadband_pillars":[CASE],"completed_diameter_count":1,"remaining_diameter_count":26,"P1D2_BROADBAND_LIBRARY_STATUS":"in_progress","P1D2_NEXT_AUTHORIZED_ACTION":"BROADBAND_PILLAR_D105_X_ONLY" if quality!="fail_data_quality" else None,"P1D2_D105_READY":quality!="fail_data_quality"}
    _write(ROOT/"outputs"/"np_k6_p1d2_broadband_contract_v1"/"library_progress.json",progress)
    (ROOT/"docs"/"np_k6_p1d2b0_broadband_d100_x_report_v1.md").write_text(f"# NP-K6 P1-D2B0 H500 D100 x broadband pillar\n\n- Case: {CASE}\n- Axis: {shared.target_axis()} nm\n- Quality: {quality}\n- T range: {metrics['T_min_over_band']:.8g}–{metrics['T_max_over_band']:.8g}\n- Max energy/reconstruction residual: {metrics['energy_residual_max_over_band']:.8g} / {metrics['reconstruction_residual_max_over_band']:.8g}\n- This is the first of 27 pillars; it does not establish six-pillar or full-library performance.\n",encoding="utf-8")
    return summary

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=("build","audit","run"),required=True);p.add_argument("--diameter-nm",type=int,default=100);p.add_argument("--case-id",default=CASE);a=p.parse_args();s=spec(a.case_id,a.diameter_nm)
    if a.mode=="build": print(json.dumps(build_pre(s),indent=2));return 0
    if a.mode=="audit": print(json.dumps(audit(PRE,s),indent=2));return 0
    if not PRE.exists(): raise RuntimeError("pre-FSP required before the one solver call")
    pre=audit(PRE,s);fdtd=base._import_lumapi().FDTD(hide=True)
    try: fdtd.load(str(PRE));print("SOLVER_RUN_CALL_ENTERING",flush=True);fdtd.run();print("SOLVER_RUN_CALL_RETURNED",flush=True);fdtd.save(str(POST))
    finally: fdtd.close()
    post=extract(POST);print(json.dumps(write_outputs(s,pre,post),indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
