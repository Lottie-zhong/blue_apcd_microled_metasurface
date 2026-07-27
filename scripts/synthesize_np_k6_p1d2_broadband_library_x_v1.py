"""Offline-only synthesis of the P1-D2 x-polarized broadband candidate library.

This module intentionally imports neither lumapi nor the FDTD runner.  It reads
immutable lightweight result JSON files and writes derived library artifacts.
"""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs"/"np_k6_p1d2_broadband_library_26point_v1"
DIAMETERS=tuple(d for d in range(100,231,5) if d != 180)
AXIS=tuple(range(445,456))
def now(): return datetime.now(timezone.utc).isoformat()
def write(path:Path,x:Any): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def digest(x:Any): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def result_path(d:int)->Path:
    matches=list((ROOT/"outputs").glob(f"np_k6_p1d2b*_broadband_d{d}_x_v1/results.json"))
    if len(matches)!=1: raise RuntimeError(f"expected one immutable results.json for D{d}, got {len(matches)}")
    return matches[0]
def load() -> tuple[list[int],dict[int,list[dict[str,Any]]],dict[str,str]]:
    rows={}; hashes={}
    for d in DIAMETERS:
        p=result_path(d); raw=json.loads(p.read_text(encoding="utf-8")); rs=raw["rows"]
        if [round(x["wavelength_nm"]) for x in rs] != list(AXIS): raise RuntimeError(f"D{d} wavelength axis is not the frozen 11 points")
        values=[v for r in rs for v in (r["T"],r["R_total"],r["txx"]["real"],r["txx"]["imag"],r["tyx"]["amplitude"],r["energy_residual"],r["x_input_reconstruction_residual"])]
        if not np.isfinite(values).all(): raise RuntimeError(f"D{d} contains non-finite data")
        rows[d]=rs; hashes[str(d)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return list(DIAMETERS),rows,hashes
def matrices(ds:list[int], rows:dict[int,list[dict[str,Any]]]) -> dict[str,Any]:
    def a(fn): return [[float(fn(rows[d][j])) for j in range(11)] for d in ds]
    wrapped=a(lambda r:r["txx"]["phase_deg_wrapped"])
    unwrapped=np.degrees(np.unwrap(np.radians(np.asarray(wrapped)),axis=0)).tolist()
    return {"diameters_nm":ds,"wavelength_nm":list(AXIS),"T":a(lambda r:r["T"]),"R":a(lambda r:r["R_total"]),"txx_complex":[[{"real":float(r["txx"]["real"]),"imag":float(r["txx"]["imag"])} for r in rows[d]] for d in ds],"txx_amplitude":a(lambda r:r["txx"]["amplitude"]),"txx_wrapped_phase_deg":wrapped,"txx_unwrapped_phase_vs_diameter_deg":unwrapped,"tyx_amplitude":a(lambda r:r["tyx"]["amplitude"]),"cross_pol":a(lambda r:r["cross_pol_zero_order_power"]),"energy_residual":a(lambda r:r["energy_residual"]),"reconstruction_residual":a(lambda r:r["x_input_reconstruction_residual"]),"phase_unwrap_method":"adjacent_minimum_jump_per_wavelength_no_D180_interpolation"}
def phase_analysis(m:dict[str,Any])->dict[str,Any]:
    p=np.asarray(m["txx_unwrapped_phase_vs_diameter_deg"]); T=np.asarray(m["T"]); amp=np.asarray(m["txx_amplitude"]); cross=np.asarray(m["cross_pol"]); energy=np.asarray(m["energy_residual"]); recon=np.asarray(m["reconstruction_residual"])
    usable=(T>=.70)&(amp>=.80)&(energy<=.08)&(recon<=.08)
    per=[]
    for j,w in enumerate(AXIS):
        steps=np.diff(p[:,j]); spans=float(np.ptp(p[:,j])); usp=float(np.ptp(p[usable[:,j],j])) if usable[:,j].any() else 0.
        per.append({"wavelength_nm":w,"total_phase_span_deg":spans,"usable_phase_span_deg":usp,"full_2pi_coverage_at_lambda":spans>=360,"phase_direction":"increasing" if np.mean(steps)>=0 else "decreasing","phase_step_by_available_diameter_deg":steps.tolist(),"phase_step_mean_deg":float(steps.mean()),"phase_step_std_deg":float(steps.std()),"phase_step_min_deg":float(steps.min()),"phase_step_max_deg":float(steps.max()),"T_min":float(T[:,j].min()),"T_max":float(T[:,j].max()),"txx_amplitude_min":float(amp[:,j].min()),"txx_amplitude_max":float(amp[:,j].max()),"cross_pol_max":float(cross[:,j].max()),"energy_residual_max":float(energy[:,j].max()),"reconstruction_residual_max":float(recon[:,j].max())})
    spans=[x["total_phase_span_deg"] for x in per]; usable_spans=[x["usable_phase_span_deg"] for x in per]
    return {"engineering_usable_gate":{"T_min":.70,"txx_amplitude_min":.80,"energy_residual_max":.08,"reconstruction_residual_max":.08},"per_wavelength":per,"full_2pi_wavelength_count":sum(x>=360 for x in spans),"full_2pi_all_11_wavelengths":all(x>=360 for x in spans),"minimum_phase_span_over_band":min(spans),"maximum_phase_span_over_band":max(spans),"usable_phase_span_at_each_wavelength_deg":usable_spans,"usable_full_2pi_all_band":all(x>=360 for x in usable_spans),"missing_diameter_nm":180,"interpolation_used":False,"old_P1D1A_phase_used":False}
def adjacent(ds:list[int],m:dict[str,Any])->dict[str,Any]:
    p=np.asarray(m["txx_unwrapped_phase_vs_diameter_deg"]); out=[]
    for i,(a,b) in enumerate(zip(ds,ds[1:])):
        delta=p[i+1]-p[i]; out.append({"pair":f"D{a}_to_D{b}","diameter_gap_nm":b-a,"crosses_missing_D180":a==175 and b==185,"phase_delta_deg_by_wavelength":delta.tolist(),"phase_delta_mean_deg":float(delta.mean()),"phase_delta_peak_to_peak_deg":float(np.ptp(delta)),"interpolation_used":False})
    return {"pairs":out,"missing_diameter_nm":180,"not_a_complete_contiguous_27_point_claim":True}
def sextet(ds:list[int],m:dict[str,Any],kind:str)->dict[str,Any]:
    phase=np.asarray(m["txx_unwrapped_phase_vs_diameter_deg"])[:,5]; amp=np.asarray(m["txx_amplitude"])[:,5]
    if kind=="amplitude_uniformity_optimal": picks=np.argsort(amp)[-6:]
    else:
        picks=[]
        for target in np.arange(0,360,60):
            order=np.argsort(np.abs(((phase-phase.min()-target+180)%360)-180))
            picks.append(next(i for i in order if i not in picks))
    picks=sorted(picks); selected=[ds[i] for i in picks]; ps=phase[picks]; fit=ps-(ps[0]+np.arange(6)*60); fit-=fit.mean()
    return {"ranking_kind":kind,"diameters_nm":selected,"phase_fit_RMS_deg_at_450_nm":float(np.sqrt(np.mean(fit**2))),"maximum_phase_error_deg_at_450_nm":float(np.max(abs(fit))),"amplitude_CV_at_450_nm":float(amp[picks].std()/amp[picks].mean()),"common_phase_offset_allowed":True,"selection_is_provisional_lpa":True,"K6_SUPERCELL_VALIDATION_STATUS":"not_run","x_only":True}
def d180_audit()->dict[str,Any]:
    p=ROOT/"outputs"/"np_k6_p1d2_batch_d120_d230_v1"/"batch_progress.json"; row=json.loads(p.read_text(encoding="utf-8"))["cases"]["180"]
    return {"diameter_nm":180,"status":row["status"],"forensic_provenance":row.get("forensic_provenance"),"results_present":result_path_exists(180),"excluded_from_library":True,"interpolation_used":False,"retry_prohibited":row.get("forensic_provenance",{}).get("retry_prohibited")}
def result_path_exists(d:int)->bool: return bool(list((ROOT/"outputs").glob(f"np_k6_p1d2b*_broadband_d{d}_x_v1/results.json")))
def synthesize(out:Path=OUT)->dict[str,Any]:
    ds,rows,hashes=load(); m=matrices(ds,rows); out.mkdir(parents=True,exist_ok=True)
    long=[]
    for i,d in enumerate(ds):
        for j,w in enumerate(AXIS):
            r=rows[d][j]; long.append({"diameter_nm":d,"wavelength_nm":w,"T":r["T"],"R":r["R_total"],"txx_real":r["txx"]["real"],"txx_imag":r["txx"]["imag"],"txx_amplitude":r["txx"]["amplitude"],"txx_wrapped_phase_deg":r["txx"]["phase_deg_wrapped"],"txx_unwrapped_phase_vs_diameter_deg":m["txx_unwrapped_phase_vs_diameter_deg"][i][j],"tyx_amplitude":r["tyx"]["amplitude"],"cross_pol":r["cross_pol_zero_order_power"],"energy_residual":r["energy_residual"],"reconstruction_residual":r["x_input_reconstruction_residual"]})
    with (out/"library_long.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=list(long[0])); w.writeheader(); w.writerows(long)
    pa=phase_analysis(m); aa={"global_T_min":min(x["T"] for x in long),"global_T_max":max(x["T"] for x in long),"global_txx_amplitude_min":min(x["txx_amplitude"] for x in long),"global_txx_amplitude_max":max(x["txx_amplitude"] for x in long),"global_crosspol_max":max(x["cross_pol"] for x in long),"max_energy_residual":max(x["energy_residual"] for x in long),"max_reconstruction_residual":max(x["reconstruction_residual"] for x in long),"polarization_completeness":"x_only","polarization_insensitive_claim":"not_yet_authorized"}
    ranking={"phase_error_optimal":sextet(ds,m,"phase_error_optimal"),"amplitude_uniformity_optimal":sextet(ds,m,"amplitude_uniformity_optimal"),"broadband_dispersion_optimal":sextet(ds,m,"broadband_dispersion_optimal"),"all_engineering_gates_passing_sextet_exists":False,"K6_SUPERCELL_VALIDATION_STATUS":"not_run"}
    manifest={"created_utc":now(),"offline_only":True,"lumapi_imported":False,"fdtd_run_called":False,"source_result_hashes":hashes,"included_diameters_nm":ds,"missing_diameters_nm":[180],"row_count":len(long),"wavelength_grid_nm":list(AXIS),"x_only":True}
    surrogate={"status":"data_contract_only_not_trained","feature_columns":["diameter_nm","wavelength_nm"],"label_columns":["T","R","txx_real","txx_imag","txx_amplitude","txx_unwrapped_phase_vs_diameter_deg","tyx_amplitude"],"row_count":len(long),"missing_diameter_nm":180,"interpolation_or_imputation_used":False,"x_only":True,"K6_SUPERCELL_VALIDATION_STATUS":"not_run"}
    gap_pairs=adjacent(ds,m); gap=[x for x in gap_pairs["pairs"] if x["crosses_missing_D180"]][0]
    geometry=[{"diameter_nm":d,"radius_nm":d/2,"gap_nm":290-d,"height_nm":500,"aspect_ratio":500/d,"case_id":f"NP_P1D2_BROADBAND_PILLAR_H500_D{d}_X"} for d in ds]
    quality=[{"diameter_nm":d,"T_min":min(r["T"] for r in rows[d]),"T_max":max(r["T"] for r in rows[d]),"txx_amplitude_min":min(r["txx"]["amplitude"] for r in rows[d]),"cross_pol_max":max(r["cross_pol_zero_order_power"] for r in rows[d]),"energy_residual_max":max(r["energy_residual"] for r in rows[d]),"reconstruction_residual_max":max(r["x_input_reconstruction_residual"] for r in rows[d])} for d in ds]
    trend={"diameters_nm":ds,"T_at_450_nm":[rows[d][5]["T"] for d in ds],"txx_amplitude_at_450_nm":[rows[d][5]["txx"]["amplitude"] for d in ds],"phase_at_450_nm_unwrapped_deg":[m["txx_unwrapped_phase_vs_diameter_deg"][i][5] for i in range(len(ds))],"missing_diameter_nm":180,"D175_to_D185_gap_nm":10,"interpolation_used":False}
    dataset={"dataset_name":"NP_P1D2_BROADBAND_26POINT_X_ONLY","diameters_nm":ds,"missing_diameters_nm":[180],"wavelength_grid_nm":list(AXIS),"row_count":len(long),"source_result_hashes":hashes,"read_only_source_results":True,"interpolation_used":False,"polarization_completeness":"x_only"}
    forward={"contract_type":"forward_surrogate_data_contract_only","input_columns":["diameter_nm","wavelength_nm"],"output_columns":surrogate["label_columns"],"training_status":"not_trained","physical_solver_calls":0,"missing_diameter_nm":180,"x_only":True}
    inverse={"contract_type":"inverse_surrogate_not_authorized","status":"not_trained_not_run","requires_forward_validation_before_use":True,"K6_SUPERCELL_VALIDATION_STATUS":"not_run","x_only":True}
    verification={"finite_data_gate":True,"library_row_count":len(long),"expected_row_count":286,"D180_excluded_gate":True,"D180_results_absent_gate":not result_path_exists(180),"source_provenance_hashes_present":len(hashes)==26,"x_only":True,"complete_27_point_library_claim":False}
    for name,x in [("library_matrix.json",m),("matrix.json",m),("phase_library_analysis.json",pa),("amplitude_transmission_analysis.json",aa),("adjacent_pair_dispersion.json",gap_pairs),("phase_gap_analysis.json",gap),("phase_unwrap_gap_audit.json",{"missing_diameter_nm":180,"gap_pair":gap,"no_interpolation_or_imputation":True}),("diameter_trend_analysis.json",trend),("trend_analysis.json",trend),("candidate_sextet_ranking.json",ranking),("sixbin_provisional.json",ranking),("d180_failure_audit.json",d180_audit()),("missing_diameter_audit.json",d180_audit()),("dataset_contract.json",dataset),("provenance_verification.json",{"source_result_hashes":hashes,"source_count":26,"D180_excluded":True,"read_only":True}),("surrogate_dataset_contract.json",surrogate),("surrogate_forward_contract.json",forward),("surrogate_inverse_contract.json",inverse),("library_manifest.json",manifest),("verification_summary.json",verification)]: write(out/name,x)
    for name,table in [("geometry_table.csv",geometry),("quality_table.csv",quality)]:
        with (out/name).open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=list(table[0])); w.writeheader(); w.writerows(table)
    report=ROOT/"docs"/"np_k6_p1d2_broadband_library_26point_x_report_v1.md"; report.write_text(f"# NP-K6 P1-D2 26-point broadband x-only library\n\n- Rows: {len(long)} (26 diameters x 11 wavelengths)\n- Missing D180: sealed_failed_case_local; excluded without interpolation.\n- Phase gap: D175 to D185 is retained as a 10 nm nonadjacent gap.\n- Six-bin selection: provisional LPA only; K6 supercell validation not run.\n- Surrogate artifacts are data contracts only; no model was trained.\n",encoding="utf-8")
    return manifest
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=OUT); a=p.parse_args(); print(json.dumps(synthesize(a.output),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
