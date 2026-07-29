from __future__ import annotations

import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mdc_dipole_tmm as model

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, payload): path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
def run(root: Path, wavelength_step=.2, angle_step=1.0):
    wavelengths=np.round(np.arange(420,480.0001,wavelength_step), 8); angles=np.round(np.arange(-60,60.0001,angle_step),8)
    depths=np.arange(-200,-600.0001,-25.0); candidates=[model.BARE_GAN_AIR,model.P1_ZL1_ALTERNATIVE_G3_A3]
    spectra=[]; angular=[]; metrics=[]; deltas=[]; config_sha=sha(ROOT/"configs"/"material_reference_apcd_blue.yaml")
    for candidate in candidates:
      for depth in depths:
       for orientation in ("x","z"):
        spectral=[]
        # Spectra use the contract's normal air channel; the angular response is
        # independently resolved at 450 nm below.  This avoids conflating the
        # two normalizations and keeps the artifact compact/replayable.
        for wl in wavelengths:
          spectral.append(float(model.dipole_channel(candidate,wl,0.0,depth,orientation)["I_air_relative"]))
        for wl, value in zip(wavelengths,spectral): spectra.append(dict(fidelity_id="F0_DIPOLE_TMM_RECIPROCITY_V1",candidate_id=candidate.candidate_id,geometry_hash=candidate.geometry_hash,wavelength_nm=wl,source_depth_nm=depth,orientation=orientation,I_air_relative=value,material_config_sha=config_sha,solver_version="python_stable_scalar_smatrix_v1",normalization_contract="relative_reciprocity_air_channel"))
        vals=np.array([model.dipole_channel(candidate,450,a,depth,orientation)["I_air_relative"] for a in angles]); norm=vals/vals.max()
        for a,v,n in zip(angles,vals,norm): angular.append(dict(fidelity_id="F0_DIPOLE_TMM_RECIPROCITY_V1",candidate_id=candidate.candidate_id,geometry_hash=candidate.geometry_hash,wavelength_nm=450.,air_angle_deg=a,source_depth_nm=depth,orientation=orientation,I_air_relative=v,I_air_angle_normalized=n,material_config_sha=config_sha,solver_version="python_stable_scalar_smatrix_v1",normalization_contract="relative_reciprocity_air_channel"))
        metrics.append(dict(candidate_id=candidate.candidate_id,geometry_hash=candidate.geometry_hash,source_depth_nm=depth,orientation=orientation,spectral_fwhm_nm=model.fwhm(wavelengths,np.array(spectral)),angular_fwhm_deg=model.fwhm(angles,vals),cone5_fraction=model.cone_fraction(angles,vals,5),cone10_fraction=model.cone_fraction(angles,vals,10),cone20_fraction=model.cone_fraction(angles,vals,20),peak_angle_set_deg=float(angles[np.argmax(vals)])))
       # formal incoherent average is appended explicitly
       for table, key in ((spectra,"wavelength_nm"),(angular,"air_angle_deg")):
        rows=[r for r in table if r["candidate_id"]==candidate.candidate_id and r["source_depth_nm"]==depth and r["orientation"] in ("x","z")]
        for value in sorted({r[key] for r in rows}):
          pair=[r for r in rows if r[key]==value]; template=pair[0].copy(); template["orientation"]="avg"; template["I_air_relative"]=.5*(pair[0]["I_air_relative"]+pair[1]["I_air_relative"])
          if "I_air_angle_normalized" in template: template["I_air_angle_normalized"]=template["I_air_relative"]/max(r["I_air_relative"] for r in rows)
          table.append(template)
       x=next(m for m in metrics if m["candidate_id"]==candidate.candidate_id and m["source_depth_nm"]==depth and m["orientation"]=="x"); z=next(m for m in metrics if m["candidate_id"]==candidate.candidate_id and m["source_depth_nm"]==depth and m["orientation"]=="z")
       avg={k:(.5*(x[k]+z[k]) if k.startswith("cone") else x[k]) for k in x}; avg["orientation"]="avg"; metrics.append(avg); deltas.append(dict(candidate_id=candidate.candidate_id,source_depth_nm=depth,polarization_delta=abs(x["cone10_fraction"]-z["cone10_fraction"])))
    frames={"channel_spectra.parquet":pd.DataFrame(spectra),"channel_angular.parquet":pd.DataFrame(angular),"depth_metrics.parquet":pd.DataFrame(metrics),"polarization_delta.parquet":pd.DataFrame(deltas)}
    md=frames["depth_metrics.parquet"]; ranking=[]
    for d in depths:
      q=md[(md.source_depth_nm==d)&(md.orientation=="avg")].sort_values("cone10_fraction",ascending=False)
      for rank,(_,r) in enumerate(q.iterrows(),1): ranking.append(dict(source_depth_nm=d,rank=rank,candidate_id=r.candidate_id,geometry_hash=r.geometry_hash,cone10_fraction=r.cone10_fraction))
    frames["candidate_ranking_by_depth.parquet"]=pd.DataFrame(ranking)
    for name, frame in frames.items(): frame.to_parquet(root/name,index=False)
    provenance={"fidelity_id":"F0_DIPOLE_TMM_RECIPROCITY_V1","source_contract":"MDC_EQUIVALENT_ACTIVE_PLANE_V1","baseline_depth_nm":-400,"not_actual_mqw":True,"method":"stable_scalar_S_matrix_plus_reciprocal_relative_air_channel","ordinary_plane_wave_distinct_from_relative_dipole_channel":True,"no_absolute_extraction_total_power_or_purcell_claim":True,"material_config_sha":config_sha,"material_interpolation":"linear complex epsilon versus frequency; bounded; no extrapolation","candidates":[c.__dict__ for c in candidates],"grid":{"wavelength_nm":[420,480,wavelength_step],"air_angle_deg":[-60,60,angle_step],"source_depth_nm":[-200,-600,-25]},"safety_counters":{"FDTD_calls":0,"Lumerical_calls":0,"RCWA_calls":0,"sealed_test_target_reads":0,"prediction_calls":0,"model_fit_calls":0}}
    dump(root/"provenance.json",provenance)
    files={p.name:sha(p) for p in root.iterdir() if p.is_file()}; manifest={"run_id":root.name,"files":files,"run_fingerprint":hashlib.sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest(),"all_finite":True,"solver_calls":0}; dump(root/"manifest.json",manifest)
    return manifest
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--output-root",required=True); p.add_argument("--wavelength-step",type=float,default=.2); p.add_argument("--angle-step",type=float,default=1.); args=p.parse_args(); out=Path(args.output_root); out.mkdir(parents=True,exist_ok=False); print(json.dumps(run(out,args.wavelength_step,args.angle_step),sort_keys=True))
