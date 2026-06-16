from __future__ import annotations

import json, math, traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.apcd_diffraction import extract_fdtd_grating_orders
from metasurface.stage12_k6_fdtd import flt, read_csv_rows, write_csv_rows

K=6
FORWARD_BINS=[0,60,120,180,240,300]
TARGET_N=0
TARGET_M=1
GROUP_PREFIX="K6_LP_APCD_H500_forward_ygrad_plus10"
FSP_FILENAME="stage12_4_h500_lp_k6_forward_ygrad_gui_inspection.fsp"
EPS=1e-12
LAYOUT_FIELDS="supercell_index phase_bin_deg candidate_id gradient_axis selected_input_polarization steering_plane height_nm lambda_nm orthogonal_period_x_nm pitch_y_nm supercell_period_lambda_y_nm supercell_center_x_nm supercell_center_y_nm source_xgrad_center_x_nm source_xgrad_center_y_nm dimer_label placement_type swap_order gap_nm local_offset_nm j1_shape_family j1_geometry_params j1_center_x_nm j1_center_y_nm j1_abs_center_x_nm j1_abs_center_y_nm j1_footprint_x_nm j1_footprint_y_nm j2_length_nm j2_width_nm j2_rotation_deg j2_center_x_nm j2_center_y_nm j2_abs_center_x_nm j2_abs_center_y_nm j2_footprint_x_nm j2_footprint_y_nm".split()
GEOMETRY_FIELDS="supercell_index phase_bin_deg candidate_id gradient_axis selected_input_polarization steering_plane dimer_center_x_nm dimer_center_y_nm supercell_period_lambda_y_nm orthogonal_period_x_nm expected_plus1_theta_deg internal_clearance_nm neighbor_clearance_prev_nm neighbor_clearance_next_nm min_neighbor_clearance_nm footprint_min_x_nm footprint_max_x_nm footprint_min_y_nm footprint_max_y_nm crosses_unit_boundary crosses_supercell_boundary geometry_legal is_240_risk_bin is_20nm_min_clearance_dimer audit_notes".split()
PHASE_FIELDS="supercell_index phase_bin_deg candidate_id actual_common_phase_deg phase_err_deg Tx blocked_y_leakage conversion_to_leakage_ratio matrix_error".split()
RUN_PLAN_FIELDS="run_id polarization polarization_angle_deg gradient_axis target_order_n target_order_m layout_plan_csv geometry_audit_csv phase_amplitude_audit_csv wavelength_nm height_nm supercell_period_lambda_y_nm orthogonal_period_x_nm expected_theta_yz_deg mode status notes".split()
RESULT_FIELDS="run_id polarization fdtd_status total_transmission dominant_order_n dominant_order_m dominant_order_power dominant_theta_yz_deg target_y_plus1_power zero_y_order_power minus_y_order_power order_contrast_y_plus1_vs_next plus1_y_direction_consistent fsp_path fsp_retained diagnostics notes".split()
ORDER_FIELDS="run_id polarization order_n order_m ux uy theta_xz_deg theta_yz_deg order_power_fraction_of_transmitted total_transmission order_power_source_norm Ex_order_complex_real Ex_order_complex_imag Ey_order_complex_real Ey_order_complex_imag Ez_order_complex_real Ez_order_complex_imag".split()
SELECTIVITY_FIELDS="metric value notes".split()
MARKER_FIELDS="supercell_index phase_bin_deg candidate_id dimer_label dimer_center_x_nm dimer_center_y_nm geometry_family actual_common_phase_deg Tx ratio matrix_error is_240_risk_bin is_20nm_min_clearance_dimer adjacent_to_20nm_min_clearance_region".split()

@dataclass(frozen=True)
class Stage12YGradPaths:
    source_layout_csv: Path
    source_geometry_csv: Path
    source_phase_csv: Path
    xgrad_results_csv: Path
    xgrad_selectivity_csv: Path
    output_dir: Path
    fdtd_work_dir: Path
    gui_fsp_path: Path

@dataclass(frozen=True)
class FP:
    cx: float; cy: float; wx: float; wy: float
    @property
    def min_x(self): return self.cx-self.wx/2
    @property
    def max_x(self): return self.cx+self.wx/2
    @property
    def min_y(self): return self.cy-self.wy/2
    @property
    def max_y(self): return self.cy+self.wy/2

def bool_from(v): return str(v).strip().lower() in {"true","1","yes"}
def dimer_label(i:int,b:int)->str: return f"DIMER_{i:02d}_BIN{b:03d}_phase{b:03d}"+("_RISK" if b==240 else "")
def expected_theta_deg(m:int,wavelength_nm:float,lambda_y_nm:float)->float:
    a=m*wavelength_nm/lambda_y_nm
    return math.nan if abs(a)>1 else math.degrees(math.asin(a))

def validate_source_layout(rows):
    bins=[int(float(r["phase_bin_deg"])) for r in rows]
    if len(rows)!=K or bins!=FORWARD_BINS: raise ValueError(f"Stage12-4 requires forward K=6 bins {FORWARD_BINS}; got {bins}")
    if any(abs(flt(r["height_nm"])-500)>1e-6 for r in rows): raise ValueError("Stage12-4 is H500 only")

def transform_xgrad_to_ygrad(source_rows:Sequence[dict[str,str]])->list[dict[str,object]]:
    validate_source_layout(source_rows)
    first=source_rows[0]; pitch=flt(first["dimer_pitch_x_nm"]); lam=pitch*K; px=flt(first["p_y_nm"])
    out=[]
    for r in source_rows:
        i=int(float(r["supercell_index"])); b=int(float(r["phase_bin_deg"])); cx0=flt(r["supercell_center_x_nm"]); cy0=flt(r.get("supercell_center_y_nm"),0)
        cx=0.0; cy=(i+0.5)*pitch
        j1x=flt(r["j1_abs_center_x_nm"])-cx0; j1y=flt(r["j1_abs_center_y_nm"])-cy0
        j2x=flt(r["j2_abs_center_x_nm"])-cx0; j2y=flt(r["j2_abs_center_y_nm"])-cy0
        out.append({"supercell_index":i,"phase_bin_deg":b,"candidate_id":r["candidate_id"],"gradient_axis":"y","selected_input_polarization":"x-LP","steering_plane":"y-z","height_nm":r["height_nm"],"lambda_nm":r["lambda_nm"],"orthogonal_period_x_nm":px,"pitch_y_nm":pitch,"supercell_period_lambda_y_nm":lam,"supercell_center_x_nm":cx,"supercell_center_y_nm":cy,"source_xgrad_center_x_nm":cx0,"source_xgrad_center_y_nm":cy0,"dimer_label":dimer_label(i,b),"placement_type":r.get("placement_type",""),"swap_order":r.get("swap_order",""),"gap_nm":r.get("gap_nm",""),"local_offset_nm":r.get("local_offset_nm",""),"j1_shape_family":r.get("j1_shape_family",""),"j1_geometry_params":r.get("j1_geometry_params",""),"j1_center_x_nm":j1x,"j1_center_y_nm":j1y,"j1_abs_center_x_nm":cx+j1x,"j1_abs_center_y_nm":cy+j1y,"j1_footprint_x_nm":r.get("j1_footprint_x_nm",""),"j1_footprint_y_nm":r.get("j1_footprint_y_nm",""),"j2_length_nm":r.get("j2_length_nm",""),"j2_width_nm":r.get("j2_width_nm",""),"j2_rotation_deg":r.get("j2_rotation_deg",""),"j2_center_x_nm":j2x,"j2_center_y_nm":j2y,"j2_abs_center_x_nm":cx+j2x,"j2_abs_center_y_nm":cy+j2y,"j2_footprint_x_nm":r.get("j2_footprint_x_nm",""),"j2_footprint_y_nm":r.get("j2_footprint_y_nm","")})
    return out

def fps(r): return [FP(flt(r["j1_abs_center_x_nm"]),flt(r["j1_abs_center_y_nm"]),flt(r["j1_footprint_x_nm"]),flt(r["j1_footprint_y_nm"])),FP(flt(r["j2_abs_center_x_nm"]),flt(r["j2_abs_center_y_nm"]),flt(r["j2_footprint_x_nm"]),flt(r["j2_footprint_y_nm"]))]
def clearance(a,b):
    dx=max(a.min_x-b.max_x,b.min_x-a.max_x,0); dy=max(a.min_y-b.max_y,b.min_y-a.max_y,0); return math.hypot(dx,dy)
def shifted(fs,dy): return [FP(f.cx,f.cy+dy,f.wx,f.wy) for f in fs]
def min_neighbor(a,b,sa=0,sb=0): return min(clearance(x,y) for x in shifted(a,sa) for y in shifted(b,sb))

def audit_ygrad_geometry(rows):
    fs=[fps(r) for r in rows]; first=rows[0]; px=flt(first["orthogonal_period_x_nm"]); pitch=flt(first["pitch_y_nm"]); lam=flt(first["supercell_period_lambda_y_nm"]); theta=expected_theta_deg(1,flt(first["lambda_nm"]),lam)
    internal=[clearance(f[0],f[1]) for f in fs]; minint=min(internal); out=[]
    for i,r in enumerate(rows):
        prev=min_neighbor(fs[i-1],fs[i],0,0) if i else min_neighbor(fs[-1],fs[i],-lam,0)
        nxt=min_neighbor(fs[i],fs[(i+1)%len(rows)],0,0) if i<len(rows)-1 else min_neighbor(fs[i],fs[0],0,lam)
        mn=min(prev,nxt); xs=[p.min_x for p in fs[i]]+[p.max_x for p in fs[i]]; ys=[p.min_y for p in fs[i]]+[p.max_y for p in fs[i]]
        minx,maxx,miny,maxy=min(xs),max(xs),min(ys),max(ys); bottom=i*pitch; top=(i+1)*pitch
        cross_unit=miny<bottom or maxy>top or minx<-px/2 or maxx>px/2; cross_super=miny<0 or maxy>lam or minx<-px/2 or maxx>px/2
        notes=[]
        if internal[i]<20: notes.append("internal_clearance_below_20nm")
        if mn<20: notes.append("neighbor_clearance_below_20nm")
        if cross_unit: notes.append("crosses_assigned_y_cell_or_x_period")
        if cross_super: notes.append("crosses_supercell_boundary")
        b=int(float(r["phase_bin_deg"])); legal=internal[i]>=20 and mn>=20 and not cross_unit and not cross_super
        out.append({"supercell_index":i,"phase_bin_deg":b,"candidate_id":r["candidate_id"],"gradient_axis":"y","selected_input_polarization":"x-LP","steering_plane":"y-z","dimer_center_x_nm":r["supercell_center_x_nm"],"dimer_center_y_nm":r["supercell_center_y_nm"],"supercell_period_lambda_y_nm":lam,"orthogonal_period_x_nm":px,"expected_plus1_theta_deg":theta,"internal_clearance_nm":internal[i],"neighbor_clearance_prev_nm":prev,"neighbor_clearance_next_nm":nxt,"min_neighbor_clearance_nm":mn,"footprint_min_x_nm":minx,"footprint_max_x_nm":maxx,"footprint_min_y_nm":miny,"footprint_max_y_nm":maxy,"crosses_unit_boundary":cross_unit,"crosses_supercell_boundary":cross_super,"geometry_legal":legal,"is_240_risk_bin":b==240,"is_20nm_min_clearance_dimer":abs(internal[i]-minint)<=1e-6,"audit_notes":";".join(notes) if notes else "ok"})
    return out

def phase_rows_for_ygrad(rows): return [{f:r.get(f,"") for f in PHASE_FIELDS} for r in rows]

def build_marker_table(layout, geom, phase):
    pb={int(float(r["supercell_index"])):r for r in phase}; gb={int(float(r["supercell_index"])):r for r in geom}; mins={int(float(r["supercell_index"])) for r in geom if bool_from(r.get("is_20nm_min_clearance_dimer"))}; adj=set(mins)
    for i in mins:
        if i>0: adj.add(i-1)
        if i<len(layout)-1: adj.add(i+1)
    out=[]
    for r in layout:
        i=int(float(r["supercell_index"])); b=int(float(r["phase_bin_deg"])); p=pb[i]; g=gb[i]
        out.append({"supercell_index":i,"phase_bin_deg":b,"candidate_id":r["candidate_id"],"dimer_label":r["dimer_label"],"dimer_center_x_nm":r["supercell_center_x_nm"],"dimer_center_y_nm":r["supercell_center_y_nm"],"geometry_family":f"{r.get('j1_shape_family','')}+rect_j2/{r.get('placement_type','')}","actual_common_phase_deg":p.get("actual_common_phase_deg",""),"Tx":p.get("Tx",""),"ratio":p.get("conversion_to_leakage_ratio",""),"matrix_error":p.get("matrix_error",""),"is_240_risk_bin":str(b==240),"is_20nm_min_clearance_dimer":str(bool_from(g.get("is_20nm_min_clearance_dimer"))),"adjacent_to_20nm_min_clearance_region":str(i in adj)})
    return out

def build_run_plan(paths, layout, geom):
    if any(not bool_from(r["geometry_legal"]) for r in geom): raise ValueError("Stage12-4 cannot run illegal y-gradient geometry")
    f=layout[0]; theta=expected_theta_deg(1,flt(f["lambda_nm"]),flt(f["supercell_period_lambda_y_nm"])); out=[]
    for pol,ang in (("x",0.0),("y",90.0)):
        out.append({"run_id":f"stage12_4_h500_k6_forward_ygrad_{pol}","polarization":pol,"polarization_angle_deg":ang,"gradient_axis":"y","target_order_n":0,"target_order_m":1,"layout_plan_csv":(paths.output_dir/"stage12_4_ygrad_layout_plan.csv").as_posix(),"geometry_audit_csv":(paths.output_dir/"stage12_4_ygrad_geometry_audit.csv").as_posix(),"phase_amplitude_audit_csv":(paths.output_dir/"stage12_4_ygrad_phase_amplitude_audit.csv").as_posix(),"wavelength_nm":flt(f["lambda_nm"]),"height_nm":flt(f["height_nm"]),"supercell_period_lambda_y_nm":flt(f["supercell_period_lambda_y_nm"]),"orthogonal_period_x_nm":flt(f["orthogonal_period_x_nm"]),"expected_theta_yz_deg":theta,"mode":"official_y_gradient_minimal_two_input_full_fdtd_validation","status":"planned","notes":"H500 y-gradient forward K=6 only; no sweep; no reverse; no H600/H700; no CP branch"})
    return out

def object_name(r,part): return f"{GROUP_PREFIX}_{r['dimer_label']}_{part}"
def build_ygrad_model(fdtd, layout, polarization):
    nm=1e-9; f=layout[0]; wl=flt(f["lambda_nm"]); h=flt(f["height_nm"]); px=flt(f["orthogonal_period_x_nm"]); py=flt(f["supercell_period_lambda_y_nm"]); sy=py/2
    fdtd.switchtolayout(); fdtd.deleteall(); fdtd.addfdtd(); fdtd.set("dimension","3D"); fdtd.set("x",0); fdtd.set("x span",px*nm); fdtd.set("y",0); fdtd.set("y span",py*nm); fdtd.set("z min",-500*nm); fdtd.set("z max",(h+700)*nm); fdtd.set("x min bc","Periodic"); fdtd.set("x max bc","Periodic"); fdtd.set("y min bc","Periodic"); fdtd.set("y max bc","Periodic"); fdtd.set("z min bc","PML"); fdtd.set("z max bc","PML"); fdtd.set("mesh accuracy",2); fdtd.set("simulation time",1000e-15)
    for r in layout: add_j1(fdtd,r,sy); add_j2(fdtd,r,sy)
    fdtd.addplane(); fdtd.set("name",f"{GROUP_PREFIX}_source_{polarization}_LP"); fdtd.set("injection axis","z"); fdtd.set("direction","Forward"); fdtd.set("x",0); fdtd.set("x span",px*nm); fdtd.set("y",0); fdtd.set("y span",py*nm); fdtd.set("z",-250*nm); fdtd.set("wavelength start",wl*nm); fdtd.set("wavelength stop",wl*nm); fdtd.set("polarization angle",0 if polarization=="x" else 90)
    fdtd.addpower(); fdtd.set("name","T"); fdtd.set("monitor type","2D Z-normal"); fdtd.set("x",0); fdtd.set("x span",px*nm); fdtd.set("y",0); fdtd.set("y span",py*nm); fdtd.set("z",(h+350)*nm)

def add_j1(fdtd,r,sy):
    nm=1e-9; shape=str(r["j1_shape_family"]); params=json.loads(str(r["j1_geometry_params"]));
    if shape=="circle": fdtd.addcircle(); fdtd.set("name",object_name(r,"j1")); fdtd.set("radius",0.5*flt(params.get("diameter_nm"))*nm)
    else:
        fdtd.addrect(); fdtd.set("name",object_name(r,"j1"))
        if shape=="square": side=flt(params.get("side_nm")); fdtd.set("x span",side*nm); fdtd.set("y span",side*nm)
        else: fdtd.set("x span",flt(params.get("length_nm"))*nm); fdtd.set("y span",flt(params.get("width_nm"))*nm)
        rot=flt(params.get("rotation_deg"),0)
        if abs(rot)>1e-9: fdtd.set("first axis","z"); fdtd.set("rotation 1",rot)
    fdtd.set("x",flt(r["j1_abs_center_x_nm"])*nm); fdtd.set("y",(flt(r["j1_abs_center_y_nm"])-sy)*nm); fdtd.set("z min",0); fdtd.set("z max",flt(r["height_nm"])*nm); fdtd.set("material","<Object defined dielectric>"); fdtd.set("index",2.6)

def add_j2(fdtd,r,sy):
    nm=1e-9; fdtd.addrect(); fdtd.set("name",object_name(r,"j2")); fdtd.set("x",flt(r["j2_abs_center_x_nm"])*nm); fdtd.set("y",(flt(r["j2_abs_center_y_nm"])-sy)*nm); fdtd.set("x span",flt(r["j2_length_nm"])*nm); fdtd.set("y span",flt(r["j2_width_nm"])*nm); fdtd.set("z min",0); fdtd.set("z max",flt(r["height_nm"])*nm); rot=flt(r.get("j2_rotation_deg"),0)
    if abs(rot)>1e-9: fdtd.set("first axis","z"); fdtd.set("rotation 1",rot)
    fdtd.set("material","<Object defined dielectric>"); fdtd.set("index",2.6)

def export_gui_fsp(lumapi,runtime,layout,fsp):
    fsp.parent.mkdir(parents=True,exist_ok=True); fdtd=None
    try:
        fdtd=lumapi.FDTD(hide=getattr(runtime,"hide_gui",True)); build_ygrad_model(fdtd,layout,"x"); fdtd.save(str(fsp))
    finally:
        if fdtd:
            try: fdtd.close()
            except Exception: pass

def normalize_ygrad_orders(raw,run_id,pol):
    out=[]
    for r in raw:
        ux=flt(r.get("expected_ux")); uy=flt(r.get("expected_uy")); tx=math.degrees(math.asin(max(-1,min(1,ux)))) if not math.isnan(ux) else math.nan; ty=math.degrees(math.asin(max(-1,min(1,uy)))) if not math.isnan(uy) else math.nan
        out.append({"run_id":run_id,"polarization":pol,"order_n":int(round(flt(r.get("order_n"),0))),"order_m":int(round(flt(r.get("order_m"),0))),"ux":ux,"uy":uy,"theta_xz_deg":tx,"theta_yz_deg":ty,"order_power_fraction_of_transmitted":flt(r.get("order_power_fraction_of_transmitted"),0),"total_transmission":flt(r.get("total_transmission"),0),"order_power_source_norm":flt(r.get("order_efficiency_source_norm"),0),"Ex_order_complex_real":r.get("Ex_order_complex_real",""),"Ex_order_complex_imag":r.get("Ex_order_complex_imag",""),"Ey_order_complex_real":r.get("Ey_order_complex_real",""),"Ey_order_complex_imag":r.get("Ey_order_complex_imag",""),"Ez_order_complex_real":r.get("Ez_order_complex_real",""),"Ez_order_complex_imag":r.get("Ez_order_complex_imag","")})
    return out

def y_order_power(rows,m,n=0):
    vals=[flt(r.get("order_power_source_norm"),0) for r in rows if int(r["order_n"])==n and int(r["order_m"])==m]
    return max(vals) if vals else 0.0
def dominant_order(rows): return max(rows,key=lambda r:flt(r.get("order_power_source_norm"),0))
def y_order_contrast(rows,m=1):
    t=y_order_power(rows,m); others=[flt(r.get("order_power_source_norm"),0) for r in rows if not (int(r["order_n"])==0 and int(r["order_m"])==m)]; return t/max(max(others) if others else 0,EPS)

def summarize_run(run_id,pol,status,orders,fsp,retained,diag,note):
    if status!="ok" or not orders: return {"run_id":run_id,"polarization":pol,"fdtd_status":status,"fsp_path":fsp,"fsp_retained":retained,"diagnostics":" | ".join(diag),"notes":note[:2000]}
    d=dominant_order(orders); theta=flt(d.get("theta_yz_deg")); return {"run_id":run_id,"polarization":pol,"fdtd_status":status,"total_transmission":flt(d.get("total_transmission"),0),"dominant_order_n":d["order_n"],"dominant_order_m":d["order_m"],"dominant_order_power":d["order_power_source_norm"],"dominant_theta_yz_deg":theta,"target_y_plus1_power":y_order_power(orders,1),"zero_y_order_power":y_order_power(orders,0),"minus_y_order_power":y_order_power(orders,-1),"order_contrast_y_plus1_vs_next":y_order_contrast(orders,1),"plus1_y_direction_consistent":int(d["order_n"])==0 and int(d["order_m"])==1 and abs(theta-10)<=2,"fsp_path":fsp,"fsp_retained":retained,"diagnostics":" | ".join(diag),"notes":note}

def run_one_ygrad_fdtd(lumapi,runtime,layout,plan,paths):
    run_id=str(plan["run_id"]); pol=str(plan["polarization"]); paths.fdtd_work_dir.mkdir(parents=True,exist_ok=True); fsp=paths.fdtd_work_dir/f"{run_id}.fsp"; fdtd=None; diag=[]; orders=[]; status="failed"; note=""
    try:
        fdtd=lumapi.FDTD(hide=getattr(runtime,"hide_gui",True)); build_ygrad_model(fdtd,layout,pol); fdtd.save(str(fsp)); fdtd.close(); fdtd=None
        fdtd=lumapi.FDTD(hide=getattr(runtime,"hide_gui",True)); fdtd.load(str(fsp)); fdtd.run(); raw=extract_fdtd_grating_orders(fdtd,monitor_name="T",K=K,diagnostics=diag); orders=normalize_ygrad_orders(raw,run_id,pol); status="ok"
    except Exception as e:
        note=f"{type(e).__name__}: {e}\n{''.join(traceback.format_exception(type(e),e,e.__traceback__)).strip()}"
    finally:
        if fdtd:
            try: fdtd.close()
            except Exception: pass
        if fsp.exists():
            try: fsp.unlink()
            except Exception as e: diag.append(f"failed_to_delete_run_fsp: {type(e).__name__}: {e}")
    return summarize_run(run_id,pol,status,orders,str(fsp),fsp.exists(),diag,note),orders

def compute_selectivity(results, orders):
    xo=[r for r in orders if r["polarization"]=="x"]; yo=[r for r in orders if r["polarization"]=="y"]; xp=y_order_power(xo,1); yp=y_order_power(yo,1); xt=max([flt(r.get("total_transmission"),0) for r in xo] or [0]); yt=max([flt(r.get("total_transmission"),0) for r in yo] or [0]); yd=dominant_order(yo) if yo else {}
    ratio=xp/max(yp,EPS); total=xt/max(yt,EPS); frac=yp/max(yt,EPS); xok=any(r.get("polarization")=="x" and r.get("fdtd_status")=="ok" and int(r.get("dominant_order_n",999))==0 and int(r.get("dominant_order_m",999))==1 and bool_from(r.get("plus1_y_direction_consistent")) for r in results); rok=ratio>=6
    return [{"metric":"effective_target_power","value":xp,"notes":"x-LP y-order +1 source-normalized power"},{"metric":"effective_blocked_leakage","value":yp,"notes":"y-LP leakage into target y-order +1"},{"metric":"target_order_selectivity_ratio","value":ratio,"notes":"effective_target_power / effective_blocked_leakage"},{"metric":"x_total_transmitted_power","value":xt,"notes":"total x-LP transmission"},{"metric":"y_total_transmitted_power","value":yt,"notes":"total y-LP transmission"},{"metric":"total_transmission_selectivity_ratio","value":total,"notes":"global blocking proxy only"},{"metric":"y_leakage_fraction_in_target_order","value":frac,"notes":"y-LP target +1 leakage / y total"},{"metric":"dominant_y_leakage_order_n","value":yd.get("order_n",""),"notes":"dominant y-LP leakage order n"},{"metric":"dominant_y_leakage_order_m","value":yd.get("order_m",""),"notes":"dominant y-LP leakage order m"},{"metric":"dominant_y_leakage_power","value":yd.get("order_power_source_norm",0),"notes":"dominant y-LP leakage power"},{"metric":"x_yplus1_dominant_and_angle_pass","value":xok,"notes":"x-LP dominant order is (0,+1) and theta_yz close to +10 deg"},{"metric":"target_selectivity_pass","value":rok,"notes":"target_order_selectivity_ratio >= 6"},{"metric":"overall_stage12_4_pass","value":bool(xok and rok),"notes":"target-direction criteria only; not global blocking"}]

def write_farfield_audit(path,results,metrics,geom):
    m={r["metric"]:r["value"] for r in metrics}; x=next((r for r in results if r.get("polarization")=="x"),{}); y=next((r for r in results if r.get("polarization")=="y"),{}); mi=min(flt(r["internal_clearance_nm"]) for r in geom); mn=min(flt(r["min_neighbor_clearance_nm"]) for r in geom); glob="validated" if flt(m.get("total_transmission_selectivity_ratio"))>=6 else "not validated"; status="PASS" if bool_from(m.get("overall_stage12_4_pass")) else "FAIL"
    lines=["# Stage12-4 Official Y-Gradient Far-Field Audit","","- Boundary: exactly two FDTD runs were planned and executed for x-LP and y-LP.","- Boundary: no sweep, no reverse FDTD, no H600/H700, no CP branch, no geometry optimization.","- Coordinate convention: selected input polarization = x-LP; gradient axis = y; steering plane = y-z; top emission = +z.","- Target order: (order_n=0, order_m=+1).","- This is target-direction LP selectivity only, not a global APCD/Jones completion claim.","","## Geometry",f"- Geometry legal: {all(bool_from(r['geometry_legal']) for r in geom)}.",f"- Minimum intra-dimer clearance: {mi:.6f} nm.",f"- Minimum neighboring-dimer clearance: {mn:.6f} nm.",f"- Expected +1 angle in y-z plane: {geom[0]['expected_plus1_theta_deg']} deg.","","## X-LP Selected Channel",f"- Dominant order: (n={x.get('dominant_order_n')}, m={x.get('dominant_order_m')}).",f"- y-order +1 power: {x.get('target_y_plus1_power')}",f"- y-order 0 power: {x.get('zero_y_order_power')}",f"- y-order -1 power: {x.get('minus_y_order_power')}",f"- Steering angle in y-z plane: {x.get('dominant_theta_yz_deg')} deg.",f"- Order contrast: {x.get('order_contrast_y_plus1_vs_next')}",f"- Direction consistent with +10 deg: {x.get('plus1_y_direction_consistent')}","","## Y-LP Leakage Channel",f"- Total transmitted/leaked power: {y.get('total_transmission')}",f"- Target y-order +1 leakage: {y.get('target_y_plus1_power')}",f"- Dominant leakage order: (n={y.get('dominant_order_n')}, m={y.get('dominant_order_m')}).",f"- Dominant leakage power: {y.get('dominant_order_power')}",f"- Leakage redirected to non-target orders: {not (str(y.get('dominant_order_n'))=='0' and str(y.get('dominant_order_m'))=='1')}","","## Metrics",f"- target_order_selectivity_ratio: {m.get('target_order_selectivity_ratio')}",f"- total_transmission_selectivity_ratio: {m.get('total_transmission_selectivity_ratio')} ({glob})",f"- y_leakage_fraction_in_target_order: {m.get('y_leakage_fraction_in_target_order')}",f"- Stage12-4 target-direction result: {status}"]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def write_comparison(path,results,metrics,paths):
    m={r["metric"]:r["value"] for r in metrics}; xr=read_csv_rows(paths.xgrad_results_csv); xm={r["metric"]:r["value"] for r in read_csv_rows(paths.xgrad_selectivity_csv)}; xx=next(r for r in xr if r["polarization"]=="x"); xy=next(r for r in xr if r["polarization"]=="y"); yx=next(r for r in results if r["polarization"]=="x"); yy=next(r for r in results if r["polarization"]=="y")
    lines=["# Stage12-4 Y-Gradient vs Stage12-2 X-Gradient Comparison","","Stage12-2 x-gradient is retained as a positive-control validation. Stage12-4 y-gradient is the official project convention for x-LP selected input, y-z steering, and top +z emission.","","| Metric | Stage12-2 x-gradient positive control | Stage12-4 official y-gradient |","|---|---:|---:|",f"| Target order | n=+1,m=0 | n=0,m=+1 |",f"| Target power | {xx.get('target_plus1_power')} | {yx.get('target_y_plus1_power')} |",f"| Steering angle | {xx.get('dominant_theta_deg')} deg x-z | {yx.get('dominant_theta_yz_deg')} deg y-z |",f"| Target-order selectivity ratio | {xm.get('effective_selectivity_ratio')} | {m.get('target_order_selectivity_ratio')} |",f"| y-LP target leakage | {xy.get('target_plus1_power')} | {yy.get('target_y_plus1_power')} |",f"| y-LP dominant leakage order | n={xy.get('dominant_order_n')},m={xy.get('dominant_order_m')} | n={yy.get('dominant_order_n')},m={yy.get('dominant_order_m')} |",f"| Total transmission selectivity | {xm.get('total_transmission_selectivity_ratio','not available')} | {m.get('total_transmission_selectivity_ratio')} |","","Do not claim global y-LP blocking unless total-transmission selectivity is also high."]
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def write_all_outputs(paths,lumapi,runtime):
    paths.output_dir.mkdir(parents=True,exist_ok=True); layout=transform_xgrad_to_ygrad(read_csv_rows(paths.source_layout_csv)); geom=audit_ygrad_geometry(layout); phase=phase_rows_for_ygrad(read_csv_rows(paths.source_phase_csv)); markers=build_marker_table(layout,geom,phase); plan=build_run_plan(paths,layout,geom)
    write_csv_rows(layout,paths.output_dir/"stage12_4_ygrad_layout_plan.csv",LAYOUT_FIELDS); write_csv_rows(geom,paths.output_dir/"stage12_4_ygrad_geometry_audit.csv",GEOMETRY_FIELDS); write_csv_rows(phase,paths.output_dir/"stage12_4_ygrad_phase_amplitude_audit.csv",PHASE_FIELDS); write_csv_rows(markers,paths.output_dir/"stage12_4_ygrad_geometry_marker_table.csv",MARKER_FIELDS); write_csv_rows(plan,paths.output_dir/"stage12_4_ygrad_fdtd_run_plan.csv",RUN_PLAN_FIELDS); export_gui_fsp(lumapi,runtime,layout,paths.gui_fsp_path)
    results=[]; all_orders=[]
    for p in plan:
        res,orders=run_one_ygrad_fdtd(lumapi,runtime,layout,p,paths); results.append(res); all_orders.extend(orders); write_csv_rows(results,paths.output_dir/"stage12_4_ygrad_fdtd_results.csv",RESULT_FIELDS); write_csv_rows(orders,paths.output_dir/f"stage12_4_ygrad_order_power_{p['polarization']}_lp.csv",ORDER_FIELDS)
    sel=compute_selectivity(results,all_orders); write_csv_rows(sel,paths.output_dir/"stage12_4_ygrad_selectivity_summary.csv",SELECTIVITY_FIELDS); write_farfield_audit(paths.output_dir/"stage12_4_ygrad_farfield_audit.md",results,sel,geom); write_comparison(paths.output_dir/"stage12_4_ygrad_vs_xgrad_comparison.md",results,sel,paths); md={r["metric"]:r["value"] for r in sel}
    return {"fsp_path":str(paths.gui_fsp_path),"fsp_generated":paths.gui_fsp_path.exists(),"fdtd_runs":len(plan),"target_order_selectivity_ratio":md.get("target_order_selectivity_ratio"),"overall_stage12_4_pass":md.get("overall_stage12_4_pass"),"geometry_legal":all(bool_from(r["geometry_legal"]) for r in geom),"minimum_clearance_nm":min(flt(r["internal_clearance_nm"]) for r in geom),"minimum_neighbor_clearance_nm":min(flt(r["min_neighbor_clearance_nm"]) for r in geom)}
