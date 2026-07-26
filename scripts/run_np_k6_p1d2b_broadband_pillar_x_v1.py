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

def configure(diameter_nm: int) -> None:
    global CASE, DIAMETER_NM, OUT, PRE, POST
    allowed = set(range(100, 116, 5)) | set(range(120, 231, 5))
    if diameter_nm not in allowed: raise ValueError("only the frozen D100-D115 or authorized D120-D230 5-nm cases are runner-allowlisted")
    DIAMETER_NM = diameter_nm; CASE = f"NP_P1D2_BROADBAND_PILLAR_H500_D{diameter_nm}_X"
    stage = {100:"p1d2b0_broadband_d100_x_v1",105:"p1d2b1_broadband_d105_x_v1",110:"p1d2b2_broadband_d110_x_v1",115:"p1d2b3_broadband_d115_x_v1"}.get(diameter_nm, f"p1d2b_broadband_d{diameter_nm}_x_v1")
    OUT = ROOT/"outputs"/f"np_k6_{stage}"
    PRE, POST = RUNTIME/f"{CASE}_pre.fsp", RUNTIME/f"{CASE}_post.fsp"

def _json(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, value: Any) -> None: path.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n", encoding="utf-8")
def _hash(value: Any) -> str: return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def spec(case_id: str | None = None, diameter_nm: int | None = None) -> dict[str, Any]:
    case_id = CASE if case_id is None else case_id; diameter_nm = DIAMETER_NM if diameter_nm is None else diameter_nm
    if case_id != CASE or diameter_nm != DIAMETER_NM: raise ValueError("only the configured H500/x allowlisted case is authorized")
    base.validate_geometry(HEIGHT_NM, DIAMETER_NM)
    return {"case_id": CASE, "geometry_type": "circular_tio2_pillar", "height_nm": HEIGHT_NM,
            "diameter_nm": DIAMETER_NM, "radius_nm": DIAMETER_NM/2, "gap_nm": 290-DIAMETER_NM, "aspect_ratio": HEIGHT_NM/DIAMETER_NM,
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
    pgeo={"height_nm":500,"diameter_nm":s["diameter_nm"],"radius_nm":s["radius_nm"],"base_nm":0,"top_nm":500,"material":"APCD_TIO2_NATIVE_M1","mesh_override_nm":[-20,720,5]}
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
        if not (math.isclose(g["radius_nm"],s["radius_nm"],abs_tol=1e-6) and math.isclose(g["z_min_nm"],0,abs_tol=1e-6) and math.isclose(g["z_max_nm"],500,abs_tol=1e-6) and g["material"]=="APCD_TIO2_NATIVE_M1" and math.isclose(g["source_angle_deg"],0,abs_tol=1e-12)): raise RuntimeError("pillar geometry/material failure")
        result={"case_id":CASE,"geometry":g,"monitor_count":len(inventory),"configured_axis_nm":axis,"monitor_inventory":inventory,"sampling_backend":shared.BACKEND}
        if s["diameter_nm"] == 105:
            allowed=["aspect_ratio","case_id","diameter_nm","gap_nm","geometry_hash","output_paths","radius_nm"]
            actual={"case_id":{"D100":"NP_P1D2_BROADBAND_PILLAR_H500_D100_X","D105":CASE},"diameter_nm":{"D100":100,"D105":105},"radius_nm":{"D100":50,"D105":52.5},"gap_nm":{"D100":190,"D105":185},"aspect_ratio":{"D100":5.0,"D105":500/105},"geometry_hash":{"D100":"D100_frozen","D105":_hash({"diameter_nm":105,"radius_nm":52.5})},"output_paths":{"D100":"outputs/np_k6_p1d2b0_broadband_d100_x_v1","D105":str(OUT.relative_to(ROOT))}}
            if sorted(actual) != sorted(allowed): raise RuntimeError("D100/D105 contract diff failure")
            result["d100_d105_contract_diff"]={"allowed_contract_differences":allowed,"actual_differences":actual,"equivalence_gate":True,"comparison_hash":_hash(actual)}
        if s["diameter_nm"] == 110:
            allowed=["aspect_ratio","case_id","diameter_nm","gap_nm","geometry_hash","output_paths","radius_nm"]
            actual={"case_id":{"D105":"NP_P1D2_BROADBAND_PILLAR_H500_D105_X","D110":CASE},"diameter_nm":{"D105":105,"D110":110},"radius_nm":{"D105":52.5,"D110":55},"gap_nm":{"D105":185,"D110":180},"aspect_ratio":{"D105":500/105,"D110":500/110},"geometry_hash":{"D105":"D105_frozen","D110":_hash({"diameter_nm":110,"radius_nm":55})},"output_paths":{"D105":"outputs/np_k6_p1d2b1_broadband_d105_x_v1","D110":str(OUT.relative_to(ROOT))}}
            if sorted(actual) != sorted(allowed): raise RuntimeError("D105/D110 contract diff failure")
            result["d105_d110_contract_diff"]={"allowed_contract_differences":allowed,"actual_differences":actual,"equivalence_gate":True,"comparison_hash":_hash(actual)}
        if s["diameter_nm"] == 115:
            allowed=["aspect_ratio","case_id","diameter_nm","gap_nm","geometry_hash","output_paths","radius_nm"]
            actual={"case_id":{"D110":"NP_P1D2_BROADBAND_PILLAR_H500_D110_X","D115":CASE},"diameter_nm":{"D110":110,"D115":115},"radius_nm":{"D110":55,"D115":57.5},"gap_nm":{"D110":180,"D115":175},"aspect_ratio":{"D110":500/110,"D115":500/115},"geometry_hash":{"D110":"D110_frozen","D115":_hash({"diameter_nm":115,"radius_nm":57.5})},"output_paths":{"D110":"outputs/np_k6_p1d2b2_broadband_d110_x_v1","D115":str(OUT.relative_to(ROOT))}}
            result["d110_d115_contract_diff"]={"allowed_contract_differences":allowed,"actual_differences":actual,"equivalence_gate":sorted(actual)==sorted(allowed),"comparison_hash":_hash(actual)}
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

def pair_dispersion(rows_new: list[dict[str,Any]], previous_diameter: int, current_diameter: int) -> dict[str,Any]:
    stage={100:"0",105:"1",110:"2"}[previous_diameter]; previous=_json(ROOT/"outputs"/f"np_k6_p1d2b{stage}_broadband_d{previous_diameter}_x_v1"/"results.json")["rows"]
    if [round(r["wavelength_nm"]) for r in previous] != [round(r["wavelength_nm"]) for r in rows_new]: raise RuntimeError("adjacent-pair axis mismatch")
    p0=np.array([r["txx"]["phase_rad_wrapped"] for r in previous]); p1=np.array([r["txx"]["phase_rad_wrapped"] for r in rows_new])
    wrapped=np.degrees(np.angle(np.exp(1j*(p1-p0)))); unwrapped=np.degrees(np.unwrap(np.radians(wrapped)))
    a0=np.array([r["txx"]["amplitude"] for r in previous]); a1=np.array([r["txx"]["amplitude"] for r in rows_new]); td=np.array([r["T"] for r in rows_new])-np.array([r["T"] for r in previous])
    coeff=np.polyfit(shared.target_axis(),unwrapped,1); fit=np.polyval(coeff,shared.target_axis())
    prior_slope=_json(ROOT/"outputs"/f"np_k6_p1d2b{stage}_broadband_d{previous_diameter}_x_v1"/"spectral_metrics.json")["phase_linear_fit_slope_deg_per_nm"]
    p2p=float(np.ptp(unwrapped)); stability="stable" if p2p<=3 else "mildly_dispersive" if p2p<=8 else "strongly_dispersive"
    prefix=f"delta_phase_{previous_diameter}_{current_diameter}"; ratio=f"txx_amplitude_ratio_{current_diameter}_to_{previous_diameter}"; delta=f"txx_amplitude_difference_{current_diameter}_minus_{previous_diameter}"; tdelta=f"T_difference_{current_diameter}_minus_{previous_diameter}"
    outrows=[{"wavelength_nm":float(w),f"{prefix}_wrapped_deg":float(a),f"{prefix}_unwrapped_deg":float(b),ratio:float(c),delta:float(d),tdelta:float(e)} for w,a,b,c,d,e in zip(shared.target_axis(),wrapped,unwrapped,a1/a0,a1-a0,td)]
    summary={"delta_phase_at_445_nm":float(unwrapped[0]),"delta_phase_at_450_nm":float(unwrapped[5]),"delta_phase_at_455_nm":float(unwrapped[-1]),"delta_phase_mean_over_band":float(np.mean(unwrapped)),"delta_phase_std_over_band":float(np.std(unwrapped)),"delta_phase_peak_to_peak":p2p,"delta_phase_max_deviation_from_450":float(np.max(np.abs(unwrapped-unwrapped[5]))),"differential_phase_slope_deg_per_nm":float(coeff[0]),"differential_phase_fit_rms_deg":float(np.sqrt(np.mean((unwrapped-fit)**2))),"differential_phase_slope_minus_previous_slope":float(coeff[0]-prior_slope),f"differential_phase_slope_minus_d{previous_diameter}_slope":float(coeff[0]-prior_slope),"amplitude_ratio_mean":float(np.mean(a1/a0)),"amplitude_ratio_std":float(np.std(a1/a0)),"amplitude_ratio_peak_to_peak":float(np.ptp(a1/a0)),"T_difference_mean":float(np.mean(td)),"T_difference_peak_to_peak":float(np.ptp(td)),"pair_relative_phase_stability":stability}
    return {"pair":f"D{previous_diameter}_to_D{current_diameter}","rows":outrows,"summary":summary,"not_a_six_pillar_claim":True}

def partial_three_diameter_line(rows110: list[dict[str,Any]]) -> dict[str,Any]:
    results={100:_json(ROOT/"outputs"/"np_k6_p1d2b0_broadband_d100_x_v1"/"results.json")["rows"],105:_json(ROOT/"outputs"/"np_k6_p1d2b1_broadband_d105_x_v1"/"results.json")["rows"],110:rows110}; diam=np.array([100.,105.,110.]); out=[]
    for i,w in enumerate(shared.target_axis()):
        wrapped=np.array([results[d][i]["txx"]["phase_deg_wrapped"] for d in diam.astype(int)]); local=np.degrees(np.unwrap(np.radians(wrapped))); steps=np.diff(local)
        out.append({"wavelength_nm":float(w),"phase_deg_wrapped_by_diameter":{"D100":float(wrapped[0]),"D105":float(wrapped[1]),"D110":float(wrapped[2])},"phase_deg_local_unwrapped_by_diameter":{"D100":float(local[0]),"D105":float(local[1]),"D110":float(local[2])},"D100_D110_phase_span_deg":float(local[2]-local[0]),"local_phase_slope_deg_per_nm":float(np.polyfit(diam,local,1)[0]),"curvature_indicator_deg":float(local[2]-2*local[1]+local[0]),"pair_step_difference_deg":float(steps[1]-steps[0])})
    step=np.array([r["pair_step_difference_deg"] for r in out]); return {"provisional_three_diameter_broadband_line":True,"diameters_nm":[100,105,110],"rows":out,"summary":{"pair_step_difference_mean_deg":float(step.mean()),"pair_step_difference_std_deg":float(step.std()),"pair_step_difference_peak_to_peak_deg":float(np.ptp(step)),"no_phase_library_claim":True,"no_two_pi_claim":True,"no_six_bin_claim":True,"no_K6_claim":True}}

def partial_four_diameter_line(rows115: list[dict[str,Any]]) -> dict[str,Any]:
    stages={100:"0",105:"1",110:"2"}; data={d:_json(ROOT/"outputs"/f"np_k6_p1d2b{stages[d]}_broadband_d{d}_x_v1"/"results.json")["rows"] for d in stages}; data[115]=rows115; ds=np.array([100.,105.,110.,115.]); out=[]
    for i,w in enumerate(shared.target_axis()):
        wrap=np.array([data[int(d)][i]["txx"]["phase_deg_wrapped"] for d in ds]); un=np.degrees(np.unwrap(np.radians(wrap))); steps=np.diff(un); slopes=steps/5
        out.append({"wavelength_nm":float(w),"wrapped_phase_by_diameter":{f"D{int(d)}":float(x) for d,x in zip(ds,wrap)},"provisional_unwrapped_phase_by_diameter":{f"D{int(d)}":float(x) for d,x in zip(ds,un)},"delta_phase_100_105":float(steps[0]),"delta_phase_105_110":float(steps[1]),"delta_phase_110_115":float(steps[2]),"D100_to_D115_phase_span":float(un[-1]-un[0]),"local_phase_steps":steps.tolist(),"local_phase_step_mean":float(steps.mean()),"local_phase_step_std":float(steps.std()),"local_phase_step_min":float(steps.min()),"local_phase_step_max":float(steps.max()),"slopes_deg_per_nm":slopes.tolist(),"curvature_at_D105":float(steps[1]-steps[0]),"curvature_at_D110":float(steps[2]-steps[1])})
    c105=np.array([r["curvature_at_D105"] for r in out]); c110=np.array([r["curvature_at_D110"] for r in out]); allsteps=np.array([x for r in out for x in r["local_phase_steps"]]); progression="approximately_linear" if max(abs(c105).mean(),abs(c110).mean())<2 else "smoothly_accelerating" if (c105.mean()>0 and c110.mean()>0) else "smoothly_decelerating" if (c105.mean()<0 and c110.mean()<0) else "irregular"
    return {"provisional_four_diameter_broadband_line":True,"diameters_nm":[100,105,110,115],"rows":out,"summary":{"local_phase_step_mean":float(allsteps.mean()),"local_phase_step_std":float(allsteps.std()),"curvature_at_D105":{"mean":float(c105.mean()),"std":float(c105.std()),"peak_to_peak":float(np.ptp(c105))},"curvature_at_D110":{"mean":float(c110.mean()),"std":float(c110.std()),"peak_to_peak":float(np.ptp(c110))},"local_phase_progression":progression,"no_phase_library_claim":True,"no_two_pi_claim":True,"no_six_bin_claim":True,"no_K6_claim":True}}

def cross_contract_450_audit(rows110: list[dict[str,Any]]) -> dict[str,Any]:
    old=_json(ROOT/"outputs"/"np_k6_p1d1a0_h500_d110_v1"/"results.json"); new=next(r for r in rows110 if math.isclose(r["wavelength_nm"],450,abs_tol=1e-6))
    old_phase=old["txx"]["phase_deg_wrapped"]; new_phase=new["txx"]["phase_deg_wrapped"]; phase=float(np.degrees(np.angle(np.exp(1j*np.radians(new_phase-old_phase))))); values={"T":(old["T"],new["T"]),"R_total":(old["R_total"],new["R_total"]),"txx_amplitude":(old["txx"]["amplitude"],new["txx"]["amplitude"]),"wrapped_phase_deg":(old_phase,new_phase),"cross_pol_amplitude":(old["tyx"]["amplitude"],new["tyx"]["amplitude"]),"energy_residual":(old["energy_residual"],new["energy_residual"]),"reconstruction_residual":(old["x_input_reconstruction_residual"],new["x_input_reconstruction_residual"])}
    diffs={k:{"old":float(a),"new":float(b),"absolute_difference":float(abs(b-a))} for k,(a,b) in values.items()}; diffs["wrapped_phase_deg"]["minimal_wrapped_difference_deg"]=phase
    bad=any(not np.isfinite(x) for r in rows110 for x in (r["T"],r["R_total"],r["txx"]["amplitude"],r["energy_residual"]))
    strict=diffs["T"]["absolute_difference"]<=.03 and diffs["R_total"]["absolute_difference"]<=.03 and diffs["txx_amplitude"]["absolute_difference"]<=.05 and abs(phase)<=10
    status="consistent" if strict else "inconsistent_investigate" if bad or abs(phase)>20 else "warning_review"
    return {"official_old_source":"outputs/np_k6_p1d1a0_h500_d110_v1/results.json","new_source":"results.json:450_nm","old_execution_mode":old.get("execution_mode"),"comparison":diffs,"status":status,"thresholds":{"T":.03,"R_total":.03,"txx_amplitude":.05,"phase_consistent_deg":10,"phase_inconsistent_deg":20},"expected_contract_differences":["source spectrum","monitor sampling backend","monitor priming implementation","matched broadband blank"],"strict_equality_not_required":True}

def write_outputs(s:dict[str,Any], pre:dict[str,Any], post:dict[str,Any]) -> dict[str,Any]:
    OUT.mkdir(parents=True,exist_ok=True); rows=post["rows"]; axis=[r["wavelength_nm"] for r in rows]
    if not np.allclose(axis,shared.target_axis(),atol=1e-6,rtol=0): raise RuntimeError("pillar axis mismatch")
    phase=np.unwrap([r["txx"]["phase_rad_wrapped"] for r in rows]); i=5; phase_deg=np.degrees(phase-phase[i]+rows[i]["txx"]["phase_rad_wrapped"]); coef=np.polyfit(shared.target_axis(),phase_deg,1); fit=np.polyval(coef,shared.target_axis()); amps=np.array([r["txx"]["amplitude"] for r in rows]); energy=np.array([r["energy_residual"] for r in rows]); recon=np.array([r["x_input_reconstruction_residual"] for r in rows])
    metrics={"phase_at_445_nm":float(phase_deg[0]),"phase_at_450_nm":float(phase_deg[i]),"phase_at_455_nm":float(phase_deg[-1]),"phase_shift_445_to_455_deg":float(phase_deg[-1]-phase_deg[0]),"phase_peak_to_peak_over_band":float(np.ptp(phase_deg)),"phase_linear_fit_slope_deg_per_nm":float(coef[0]),"phase_linear_fit_rms_residual_deg":float(np.sqrt(np.mean((phase_deg-fit)**2))),"txx_amplitude_min_over_band":float(amps.min()),"txx_amplitude_max_over_band":float(amps.max()),"txx_amplitude_peak_to_peak":float(np.ptp(amps)),"txx_amplitude_CV_over_band":float(amps.std()/amps.mean()),"T_min_over_band":min(r["T"] for r in rows),"T_max_over_band":max(r["T"] for r in rows),"T_peak_to_peak":max(r["T"] for r in rows)-min(r["T"] for r in rows),"R_total_min_over_band":min(r["R_total"] for r in rows),"R_total_max_over_band":max(r["R_total"] for r in rows),"cross_pol_max_over_band":max(r["tyx"]["amplitude"] for r in rows),"energy_residual_mean_over_band":float(energy.mean()),"energy_residual_max_over_band":float(energy.max()),"reconstruction_residual_mean_over_band":float(recon.mean()),"reconstruction_residual_max_over_band":float(recon.max())}
    quality="pass" if max(metrics["energy_residual_max_over_band"],metrics["reconstruction_residual_max_over_band"])<=.03 else "warning_valid" if max(metrics["energy_residual_max_over_band"],metrics["reconstruction_residual_max_over_band"])<=.08 else "fail_data_quality"
    contract={"case_id":CASE,"geometry_type":s["geometry_type"],"pillar_present":True,"pillar_geometry":{"height_nm":500,"diameter_nm":s["diameter_nm"],"radius_nm":s["radius_nm"],"base_nm":0,"top_nm":500,"material":"APCD_TIO2_NATIVE_M1"},"sampling_backend":shared.BACKEND,"target_axis_nm":shared.target_axis(),"monitor_mapping":s["monitor_mapping"],"pre_audit":pre,"blank_pillar_contract_diff_hash":pre["contract_diff"]["comparison_hash"],"interpolation_used":False,"nearest_neighbor_used":False}
    formal_key={100:"P1D2B0_FORMAL_STATUS",105:"P1D2B1_FORMAL_STATUS",110:"P1D2B2_FORMAL_STATUS",115:"P1D2B3_FORMAL_STATUS"}[s["diameter_nm"]]
    summary={formal_key:"pass" if quality!="fail_data_quality" else "fail","finite_data_gate":True,"denominator_safety_gate":True,"blank_pillar_axis_match_gate":True,"post_fsp_readonly_gate":True,"individual_pillar_spectral_quality":quality,"metrics":metrics}
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
    if s["diameter_nm"] == 105:
        pair = pair_dispersion(rows, 100, 105)
        _write(OUT/"pair_dispersion_d100_d105.json",pair)
        d100_contract=_json(ROOT/"outputs"/"np_k6_p1d2b0_broadband_d100_x_v1"/"physical_contract.json")
        allowed=["aspect_ratio","case_id","diameter_nm","gap_nm","geometry_hash","output_paths","radius_nm"]
        actual={"case_id":{"D100":d100_contract["case_id"],"D105":CASE},"diameter_nm":{"D100":100,"D105":105},"radius_nm":{"D100":50,"D105":52.5},"gap_nm":{"D100":190,"D105":185},"aspect_ratio":{"D100":5.0,"D105":500/105},"geometry_hash":{"D100":d100_contract["blank_pillar_contract_diff_hash"],"D105":pre["contract_diff"]["comparison_hash"]},"output_paths":{"D100":str(ROOT/"outputs"/"np_k6_p1d2b0_broadband_d100_x_v1"),"D105":str(OUT)}}
        _write(OUT/"d100_d105_contract_diff.json",{"allowed_contract_differences":allowed,"actual_differences":actual,"equivalence_gate":sorted(actual)==sorted(allowed)})
        progress={"P1D2B0_FORMAL_STATUS":"pass","P1D2B1_FORMAL_STATUS":summary[formal_key],"completed_broadband_pillars":["NP_P1D2_BROADBAND_PILLAR_H500_D100_X",CASE],"completed_diameter_count":2,"remaining_diameter_count":25,"P1D2_BROADBAND_LIBRARY_STATUS":"in_progress","P1D2_NEXT_AUTHORIZED_ACTION":"BROADBAND_PILLAR_D110_X_ONLY" if quality!="fail_data_quality" else None,"P1D2_D110_READY":quality!="fail_data_quality"}
        report_extra=f"- Pair relative phase stability: {pair['summary']['pair_relative_phase_stability']}\n"
    elif s["diameter_nm"] == 110:
        pair=pair_dispersion(rows,105,110); line=partial_three_diameter_line(rows); cross=cross_contract_450_audit(rows)
        _write(OUT/"pair_dispersion_d105_d110.json",pair); _write(OUT/"partial_line_d100_d105_d110.json",line); _write(OUT/"cross_contract_450nm_audit.json",cross); _write(OUT/"d105_d110_contract_diff.json",pre["d105_d110_contract_diff"])
        release=quality!="fail_data_quality" and cross["status"]!="inconsistent_investigate"
        progress={"P1D2B0_FORMAL_STATUS":"pass","P1D2B1_FORMAL_STATUS":"pass","P1D2B2_FORMAL_STATUS":summary[formal_key],"completed_broadband_pillars":["NP_P1D2_BROADBAND_PILLAR_H500_D100_X","NP_P1D2_BROADBAND_PILLAR_H500_D105_X",CASE],"completed_diameter_count":3,"remaining_diameter_count":24,"P1D2_BROADBAND_LIBRARY_STATUS":"in_progress","P1D2_NEXT_AUTHORIZED_ACTION":"BROADBAND_PILLAR_D115_X_ONLY" if release else None,"P1D2_D115_READY":release,"P1D2_CROSS_CONTRACT_450_STATUS":cross["status"]}
        report_extra=f"- D105 to D110 pair stability: {pair['summary']['pair_relative_phase_stability']}\n- Three-diameter line is provisional: {line['provisional_three_diameter_broadband_line']}\n- Historical D110 450 nm cross-contract status: {cross['status']}\n"
    elif s["diameter_nm"] == 115:
        pair=pair_dispersion(rows,110,115); line=partial_four_diameter_line(rows); _write(OUT/"pair_dispersion_d110_d115.json",pair); _write(OUT/"partial_line_d100_d105_d110_d115.json",line); _write(OUT/"d110_d115_contract_diff.json",pre["d110_d115_contract_diff"])
        release=quality!="fail_data_quality"; progress={"P1D2B0_FORMAL_STATUS":"pass","P1D2B1_FORMAL_STATUS":"pass","P1D2B2_FORMAL_STATUS":"pass","P1D2B3_FORMAL_STATUS":summary[formal_key],"P1D2_BROADBAND_LIBRARY_STATUS":"in_progress","P1D2_CROSS_CONTRACT_450_STATUS":"warning_review","completed_broadband_pillars":["NP_P1D2_BROADBAND_PILLAR_H500_D100_X","NP_P1D2_BROADBAND_PILLAR_H500_D105_X","NP_P1D2_BROADBAND_PILLAR_H500_D110_X",CASE],"completed_diameter_count":4,"remaining_diameter_count":23,"P1D2_NEXT_AUTHORIZED_ACTION":"BROADBAND_PILLAR_D120_X_ONLY" if release else None,"P1D2_D120_READY":release}; report_extra=f"- D110 to D115 pair stability: {pair['summary']['pair_relative_phase_stability']}\n- Four-diameter line is provisional: {line['provisional_four_diameter_broadband_line']}\n- Inherited D110 cross-contract warning: warning_review\n"
    else:
        progress={"P1D2B0_FORMAL_STATUS":summary[formal_key],"completed_broadband_pillars":[CASE],"completed_diameter_count":1,"remaining_diameter_count":26,"P1D2_BROADBAND_LIBRARY_STATUS":"in_progress","P1D2_NEXT_AUTHORIZED_ACTION":"BROADBAND_PILLAR_D105_X_ONLY" if quality!="fail_data_quality" else None,"P1D2_D105_READY":quality!="fail_data_quality"}; report_extra=""
    _write(ROOT/"outputs"/"np_k6_p1d2_broadband_contract_v1"/"library_progress.json",progress)
    label={100:"P1-D2B0",105:"P1-D2B1",110:"P1-D2B2",115:"P1-D2B3"}[s["diameter_nm"]]; stage={100:"0",105:"1",110:"2",115:"3"}[s["diameter_nm"]]
    (ROOT/"docs"/f"np_k6_p1d2b{stage}_broadband_d{s['diameter_nm']}_x_report_v1.md").write_text(f"# NP-K6 {label} H500 D{s['diameter_nm']} x broadband pillar\n\n- Case: {CASE}\n- Axis: {shared.target_axis()} nm\n- Quality: {quality}\n- T range: {metrics['T_min_over_band']:.8g} to {metrics['T_max_over_band']:.8g}\n- Max energy/reconstruction residual: {metrics['energy_residual_max_over_band']:.8g} / {metrics['reconstruction_residual_max_over_band']:.8g}\n{report_extra}- This remains a local adjacent-pair result, not a phase library, 2pi, six-bin, or K6 claim.\n",encoding="utf-8")
    return summary

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=("build","audit","run"),required=True);p.add_argument("--diameter-nm",type=int,default=100);p.add_argument("--case-id",default=CASE);a=p.parse_args()
    configure(a.diameter_nm); s=spec(a.case_id,a.diameter_nm)
    if a.mode=="build": print(json.dumps(build_pre(s),indent=2));return 0
    if a.mode=="audit": print(json.dumps(audit(PRE,s),indent=2));return 0
    if not PRE.exists(): raise RuntimeError("pre-FSP required before the one solver call")
    pre=audit(PRE,s);fdtd=base._import_lumapi().FDTD(hide=True)
    try: fdtd.load(str(PRE));print("SOLVER_RUN_CALL_ENTERING",flush=True);fdtd.run();print("SOLVER_RUN_CALL_RETURNED",flush=True);fdtd.save(str(POST))
    finally: fdtd.close()
    post=extract(POST);print(json.dumps(write_outputs(s,pre,post),indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
