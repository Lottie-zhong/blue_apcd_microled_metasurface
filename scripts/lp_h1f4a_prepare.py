from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1")
REPORT = ROOT / "reports/stage_h1f4a_grouped_d_first_harmonic_jacobian_probe"
SOURCE_MANIFEST = ROOT / "reports/stage_h1f3b_k6_position_mode_level2/h1f3b_candidate_manifest.json"
TRANSFER_MANIFEST = ROOT / "reports/stage_h1f2_k6_frontier_level1/h1f2_candidate_manifest.json"
PRIMARY_UID = "K6_L1_C_POS_PLUS10"
PRIMARY_HASH = "a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198"
TRANSFER_UID = "K6_L1_B"
P_NM = 431.907786
P_SUPER_NM = 2591.446716
P_Y_NM = 432.0
H_NM = 550.0
GRID = [450.0 + 0.5 * i for i in range(9)]
AD_NM = 4.0


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(name, value):
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(value):
    return hashlib.sha256(canon(value)).hexdigest()


def rect(cx, cy, sx, sy, rot):
    t = math.radians(float(rot)); ct, st = math.cos(t), math.sin(t)
    return [(cx + x * ct - y * st, cy + x * st + y * ct) for x, y in ((-sx/2, -sy/2), (sx/2, -sy/2), (sx/2, sy/2), (-sx/2, sy/2))]


def cross(a, b, c): return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
def on_segment(a, b, p): return abs(cross(a,b,p)) < 1e-8 and min(a[0],b[0])-1e-8 <= p[0] <= max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8 <= p[1] <= max(a[1],b[1])+1e-8
def intersects(a,b,c,d):
    ab1, ab2, cd1, cd2 = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
    if ((ab1 > 0 > ab2) or (ab1 < 0 < ab2)) and ((cd1 > 0 > cd2) or (cd1 < 0 < cd2)): return True
    return on_segment(a,b,c) or on_segment(a,b,d) or on_segment(c,d,a) or on_segment(c,d,b)
def point_segment_distance(p,a,b):
    dx, dy = b[0]-a[0], b[1]-a[1]; den = dx*dx + dy*dy
    t = 0.0 if den == 0 else max(0.0, min(1.0, ((p[0]-a[0])*dx + (p[1]-a[1])*dy)/den))
    q = (a[0]+t*dx, a[1]+t*dy); return math.hypot(p[0]-q[0], p[1]-q[1])
def polygon_gap(a,b):
    if any(intersects(a[i],a[(i+1)%len(a)],b[j],b[(j+1)%len(b)]) for i in range(len(a)) for j in range(len(b))): return 0.0
    return min(point_segment_distance(p,b[j],b[(j+1)%len(b)]) for p in a for j in range(len(b)))


def polygons(candidate):
    out=[]
    for site,(geo,pos) in enumerate(zip(candidate["local_geometries"],candidate["site_positions_nm"])):
        xbase=float(pos["x_nm"])-P_SUPER_NM/2.0
        for pillar,(cx,cy,sx,sy,rot) in enumerate(((geo["J1_center_x_nm"],geo["J1_center_y_nm"],geo["J1_side_nm"],geo["J1_side_nm"],geo.get("J1_rotation_deg",0.0)),(geo["J2_center_x_nm"],geo["J2_center_y_nm"],geo["J2_length_nm"],geo["J2_width_nm"],geo.get("J2_rotation_deg",0.0)))):
            out.append((site,pillar,rect(xbase+float(cx),float(pos["y_nm"])+float(cy),float(sx),float(sy),float(rot))))
    return out


def legality(candidate):
    ps=polygons(candidate); best=float("inf"); direct=float("inf"); cross_site=float("inf")
    for i,(si,pi,a) in enumerate(ps):
        for j,(sj,pj,b) in enumerate(ps):
            if j <= i: continue
            for kx in (-1,0,1):
                for ky in (-1,0,1):
                    if not (kx or ky) and si == sj and pi == pj: continue
                    bb=[(x+kx*P_SUPER_NM,y+ky*P_Y_NM) for x,y in b]
                    gap=min(polygon_gap(a,bb),polygon_gap(bb,a)); best=min(best,gap)
                    if si == sj: direct=min(direct,gap)
                    else: cross_site=min(cross_site,gap)
    return {"minimum_clearance_nm":best,"minimum_direct_pillar_gap_nm":direct,"minimum_cross_site_gap_nm":cross_site,"periodic_boundary_gap_y_nm":P_Y_NM-max(max(abs(y) for x,y in q) for _,_,q in ps),"no_overlap":best>0.25,"fundamental_period_6P":candidate["P_supercell_nm"] == P_SUPER_NM and candidate["P_y_nm"] == P_Y_NM,"minimum_feature_nm":min([g["J1_side_nm"] for g in candidate["local_geometries"]]+[g["J2_width_nm"] for g in candidate["local_geometries"]]),"pass":best>0.25 and candidate["P_supercell_nm"] == P_SUPER_NM and candidate["P_y_nm"] == P_Y_NM}


def main():
    source=load(SOURCE_MANIFEST); source_candidates={c["candidate_uid"]:c for c in (source["candidates"].values() if isinstance(source["candidates"],dict) else source["candidates"])}; transfer_raw=load(TRANSFER_MANIFEST)["candidates"]; transfer_candidates={c["candidate_uid"]:c for c in (transfer_raw.values() if isinstance(transfer_raw,dict) else transfer_raw)}
    if PRIMARY_UID not in source_candidates or source_candidates[PRIMARY_UID]["candidate_hash"] != PRIMARY_HASH: raise RuntimeError("HARD_GATE_PRIMARY_SEED_HASH_MISMATCH")
    primary=source_candidates[PRIMARY_UID]
    transfer=transfer_candidates.get(TRANSFER_UID)
    if transfer is None: raise RuntimeError("HARD_GATE_TRANSFER_SEED_MISSING")
    children=[]
    coeffs={"A_PLUS":(4.0,0.0),"A_MINUS":(-4.0,0.0),"B_PLUS":(0.0,4.0),"B_MINUS":(0.0,-4.0)}
    for label,(a_d,b_d) in coeffs.items():
        c=copy.deepcopy(primary); c["candidate_uid"]=f"H1F4A_{PRIMARY_UID}_{label}"; c["base_candidate_uid"]=PRIMARY_UID; c["base_candidate_hash"]=PRIMARY_HASH; c["grouped_d_mode"]="D_n=D_n_baseline+a_D*cos(2*pi*n/6)+b_D*sin(2*pi*n/6)"; c["harmonic_coefficients"]={"a_D_nm":a_d,"b_D_nm":b_d}; c["site_ordering"]="n=0..5 in authoritative primary site order"; c["no_position_modulation"]=True; c["helper_J3"]=None
        c["local_geometries"]=[]; dvals=[]
        for n,g0 in enumerate(primary["local_geometries"]):
            g=copy.deepcopy(g0); baseline=float(g0["J2_center_x_nm"])-float(g0["J1_center_x_nm"]); delta=a_d*math.cos(2*math.pi*n/6)+b_d*math.sin(2*math.pi*n/6); new_d=baseline+delta; mid=(float(g0["J2_center_x_nm"])+float(g0["J1_center_x_nm"])) / 2.0; g["J1_center_x_nm"]=mid-new_d/2.0; g["J2_center_x_nm"]=mid+new_d/2.0; g["D_n_baseline_nm"]=baseline; g["D_n_nm"]=new_d; c["local_geometries"].append(g); dvals.append(new_d)
        c["D_n_baseline_nm"]= [float(g["D_n_baseline_nm"]) for g in c["local_geometries"]]; c["D_n_nm"]=dvals
        payload={"H_global_nm":c["H_global_nm"],"P_supercell_nm":c["P_supercell_nm"],"P_y_nm":c["P_y_nm"],"material":c["material"],"local_geometries":c["local_geometries"],"site_positions_nm":c["site_positions_nm"],"grouped_d_mode":c["grouped_d_mode"],"harmonic_coefficients":c["harmonic_coefficients"]}; c["candidate_hash"]=sha(payload); c["physical_canonical_hash"]=c["candidate_hash"]; c["solver_case_uids"]=[f"{c['candidate_uid']}_{p}" for p in ("x","y")]; c["geometry_legality"]=legality(c); children.append(c)
    if not all(c["geometry_legality"]["pass"] for c in children): raise RuntimeError("HARD_GATE_GROUPED_D_GEOMETRY_ILLEGAL")
    readiness={"schema":"H1F4A_AUTHORITATIVE_READINESS_RECOVERY_V1","route":"GROUPED_D_FIRST_HARMONIC_READY","stage":"H1F-4A","source_manifest":str(SOURCE_MANIFEST),"primary_seed_uid":PRIMARY_UID,"primary_seed_frozen_hash":PRIMARY_HASH,"primary_seed_source_stage":"H1F3B","transfer_seed_uid":TRANSFER_UID,"transfer_seed_hash":transfer["candidate_hash"],"transfer_seed_solver_authorized":False,"p_nm":P_NM,"P_supercell_nm":P_SUPER_NM,"P_y_nm":P_Y_NM,"H_global_nm":H_NM,"A_D_nm":AD_NM,"wavelength_grid_nm":GRID,"formal_xy_cases":8,"ml_admitted":False,"helper_J3":None,"primary_seed_recovered_from_authoritative_artifact":True}
    manifest={"schema":"H1F4A_GROUPED_D_CANDIDATE_MANIFEST_V1","status":"FROZEN_READY_FOR_SOLVER","route":"GROUPED_D_FIRST_HARMONIC_JACOBIAN_PROBE","stage":"H1F-4A","branch":"work/lp-global-h-manifold-v1","worktree":str(ROOT),"primary_seed":readiness,"candidate_count":4,"max_new_formal_cases":8,"processes":4,"threads":1,"polarizations":["x","y"],"wavelength_grid_nm":GRID,"P_supercell_nm":P_SUPER_NM,"P_y_nm":P_Y_NM,"fundamental_period_6P":True,"grouped_d_definition":"D_n=D_n_baseline+a_D*cos(2*pi*n/6)+b_D*sin(2*pi*n/6)","site_ordering":"n=0..5 authoritative primary order","A_D_nm":AD_NM,"children":children,"ml_admitted":False,"solver_plan":{"layouts":4,"formal_xy_cases":8,"serial_within_lp":True,"max_active_lp_fdtd":1,"effective_global_fdtd_capacity":3,"permanent_global_fdtd_policy":2,"rcwa_consumes_fdtd_slot":False}}
    manifest["freeze_sha256"]=sha(manifest); dump("authoritative_readiness_recovery.json",readiness); dump("primary_seed_recovery.json",{"primary":primary,"transfer":{"candidate_uid":TRANSFER_UID,"candidate_hash":transfer["candidate_hash"],"solver_authorized":False}}); dump("geometry_legality.json",{"schema":"H1F4A_GEOMETRY_LEGALITY_V1","layouts":{c["candidate_uid"]:c["geometry_legality"] for c in children},"all_pass":True}); dump("grouped_d_candidate_manifest.json",manifest); case_rows=[{"case_uid":uid,"candidate_uid":uid.rsplit("_",1)[0],"polarization":pol,"candidate_hash":next(c["candidate_hash"] for c in children if uid.startswith(c["candidate_uid"])),"planned":True,"solver_entered":False,"accepted":False,"replay":False} for c in children for uid,pol in ((c["solver_case_uids"][0],"x"),(c["solver_case_uids"][1],"y"))]; dump("h1f4a_solver_accounting.json",{"schema":"H1F4A_SOLVER_ACCOUNTING_V1","stage":"H1F-4A","planned_formal_cases":8,"entered_formal_cases":0,"accepted_formal_cases":0,"solver_entered_delta":0,"solver_accepted_delta":0,"quarantine_cases":0,"replay_cases":0,"max_global_active_fdtd_jobs":3,"permanent_global_fdtd_policy":2,"max_lp_active_fdtd_jobs":1,"processes":4,"threads":1,"ml_admitted":False,"cases":case_rows}); dump("solver_ledger.json",{"schema":"H1F4A_SOLVER_LEDGER_V1","planned_cases":[c["solver_case_uids"][i] for c in children for i in (0,1)],"solver_entered":[],"solver_entered_count":0,"solver_accepted_count":0,"replay_cases":[],"status":"PREREGISTERED","no_auto_replay":True}); dump("scheduler_audit_preregistration.json",{"permanent_global_fdtd_policy":2,"temporary_stage_capacity":3,"max_active_lp_fdtd":1,"rcwa_consumes_fdtd_slot":False,"fresh_audit_required_before_each_entry":True,"no_fourth_fdtd":True}); print(json.dumps({"freeze_sha256":manifest["freeze_sha256"],"children":[(c["candidate_uid"],c["candidate_hash"],c["D_n_nm"],c["geometry_legality"]["minimum_clearance_nm"]) for c in children]},indent=2))

if __name__ == "__main__": main()
