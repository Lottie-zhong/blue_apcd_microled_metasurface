import argparse,csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; CASES=('blank_x','pillar_x','blank_y','pillar_y'); EXPECT={'blank_x':'AC7AAEB588778CE0462DE4C6F6EFB19270D674FEB3374BEF3A3A845CADFFE6A7','blank_y':'7FF440782FF5DA57CE7A7094F0022B5BBACFCF624DF19D82E751E2A2D6F9AF05','pillar_x':'D18F69A97D92F470D538981C3D1DC0F2DDC2679D2667889F9EF70738EAFADA08','pillar_y':'081DAB14F676023A2241883CB6E1599FB2ADE0053570DE2F5AFA51D58644E578'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cdict(z):z=complex(z);return {'real':z.real,'imag':z.imag,'amplitude':abs(z),'phase_rad_wrapped':float(np.angle(z)),'phase_deg_wrapped':float(np.degrees(np.angle(z)))}
def read(case,rt):
 p=rt/f'post_run_{case}.fsp'
 if not p.exists() or sha(p).upper()!=EXPECT[case]:raise RuntimeError(f'FSP missing/hash mismatch: {case}')
 sys.path.insert(0,str(ROOT/'scripts'));import build_np_k6_unitcell_setup_v1 as b
 f=b._import_lumapi().FDTD(hide=True)
 try:
  f.load(str(p));e=np.squeeze(f.getresult('T_fields','E')['E'])
  if e.ndim<2 or e.shape[-1]!=3 or not np.isfinite(e).all():raise RuntimeError(f'bad monitor E: {case}')
  ax,ay=np.mean(e[...,0]),np.mean(e[...,1]);t=float(np.squeeze(f.transmission('T_fields')));rr=float(np.squeeze(f.transmission('R_fields')))
  if not np.isfinite([t,rr,ax.real,ax.imag,ay.real,ay.imag]).all():raise RuntimeError('nonfinite')
  return {'case':case,'T_total':t,'R_raw':rr,'reflection_sign_factor':-1,'R_total':-rr,'energy_residual':abs(1-t+rr),'ax':cdict(ax),'ay':cdict(ay),'fsp_path':str(p.relative_to(ROOT)),'fsp_sha256':sha(p),'fsp_size':p.stat().st_size,'fsp_mtime_ns':p.stat().st_mtime_ns,'extraction_only':True,'solver_run_this_thread':False,'reused_existing_postrun':True,'cumulative_completed_run_count':1}
 finally:f.close()

def main():
 a=argparse.ArgumentParser();a.add_argument('--mode',required=True);a.add_argument('--forbid-solver',action='store_true');a.add_argument('--runtime-dir',type=Path,default=ROOT/'runtime_fsp'/'np_k6_p1c_singlepoint_v1');a.add_argument('--output-dir',type=Path,default=ROOT/'outputs'/'np_k6_p1c_singlepoint_v1');x=a.parse_args();args=x
 if args.mode!='extract-only' or not args.forbid_solver:raise RuntimeError('extract-only and --forbid-solver required')
 r={k:read(k,args.runtime_dir) for k in CASES}; bx,px,by,py=(r[k] for k in CASES);z=lambda q,k:complex(q[k]['real'],q[k]['imag']);dx,dy=z(bx,'ax'),z(by,'ay')
 if abs(dx)<1e-12 or abs(dy)<1e-12:raise RuntimeError('unsafe blank denominator')
 j={'txx':z(px,'ax')/dx,'tyx':z(px,'ay')/dx,'txy':z(py,'ax')/dy,'tyy':z(py,'ay')/dy};jx={k:cdict(v) for k,v in j.items()};rx=bx['T_total']*(abs(j['txx'])**2+abs(j['tyx'])**2);ry=by['T_total']*(abs(j['txy'])**2+abs(j['tyy'])**2)
 m={'jones':jx,'reconstructed_T_x':rx,'reconstructed_T_y':ry,'jones_relative_residual_x':abs(rx-px['T_total'])/px['T_total'],'jones_relative_residual_y':abs(ry-py['T_total'])/py['T_total'],'copol_amplitude_mismatch':abs(abs(j['txx'])-abs(j['tyy']))/((abs(j['txx'])+abs(j['tyy']))/2),'copol_power_mismatch':abs(px['T_total']-py['T_total'])/((px['T_total']+py['T_total'])/2),'copol_phase_mismatch_deg':float(np.degrees(np.angle(j['txx']/j['tyy']))),'cross_pol_fraction_x':abs(j['tyx'])**2/(abs(j['txx'])**2+abs(j['tyx'])**2),'cross_pol_fraction_y':abs(j['txy'])**2/(abs(j['tyy'])**2+abs(j['txy'])**2)}
 data={'branch_id':'NP-K6-MDC-V1','stage_id':'P1-C','solver_run_count_this_thread':0,'weighted_G0_used':False,'subruns':r,'combined_candidate':m};args.output_dir.mkdir(parents=True,exist_ok=True);(args.output_dir/'results.json').write_text(json.dumps(data,indent=2));(args.output_dir/'run_manifest.json').write_text(json.dumps(data,indent=2));
 with (args.output_dir/'results.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['row','T_total','R_total','energy_residual']);[w.writerow([k,r[k]['T_total'],r[k]['R_total'],r[k]['energy_residual']]) for k in CASES];w.writerow(['combined','','',''])
 print(json.dumps(m));return 0
if __name__=='__main__':raise SystemExit(main())