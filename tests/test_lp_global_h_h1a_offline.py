import importlib.util,pytest
from pathlib import Path
S=importlib.util.spec_from_file_location("off",Path(__file__).resolve().parents[1]/"scripts/lp_global_h_h1a_offline_readiness_v1.py");M=importlib.util.module_from_spec(S);assert S and S.loader;S.loader.exec_module(M)
def p(a,h,v,status="ACCEPTED",pol="x",case_id=None,**k):
 r={"geometry_hash_sha256":a,"authoritative_id":a,"H_global_nm":h,"phi_arg_txx_deg":v,"status":status,"polarization":pol,"case_id":case_id or f"{a}_{h}_{pol}"};r.update(k);return r
def f(a,h,v):
 r=p(a,h,v,pol="xy");r.update(Jones_complete=True,projector_eligible=True,projector_error_apcd_v1=.01);return r
def test_common():
 b=[("a",0),("b",100),("c",200)];x=[p(a,h,v+(40 if h==550 else 0)) for a,v in b for h in(500,550)];y=[f(a,h,v+(40 if h==550 else 0)) for a,v in b for h in(500,550)];z=next(z for z in M.analyze(x,y)["interactions"] if z["H_global_nm"]==550);assert z["rms_residual_deg"]==pytest.approx(0)
def test_geometry():
 b=[("a",0,20),("b",100,40),("c",200,80)];x=[p(a,h,v+(s if h==550 else 0)) for a,v,s in b for h in(500,550)];y=[f(a,h,v+(s if h==550 else 0)) for a,v,s in b for h in(500,550)];assert next(z for z in M.analyze(x,y)["interactions"] if z["H_global_nm"]==550)["max_abs_residual_deg"]>10
def test_wrap():assert M.Z.circular_phase_span([355,5,15])["circular_coverage_deg"]==pytest.approx(20)
def test_flags():
 for v,k in((65,"FLAG_60_SECTOR"),(130,"FLAG_120_ML_RESTART")):
  x=[p(a,h,z) for h in(500,550) for a,z in(("a",0),("b",v),("c",10),("d",20))];y=[f(a,h,z) for h in(500,550) for a,z in(("a",0),("b",v),("c",10),("d",20))];assert M.analyze(x,y)["flags"][k]
def test_incompatible():
 r=M.analyze([p("a",500,0),p("b",500,180),p("a",550,0),p("b",550,180,x_only=True)],[f("a",500,0),f("a",550,0)]);z=next(z for z in r["fixed_height_spans"] if z["H_global_nm"]==550);assert z["anchor_phase_circular_coverage_deg"]==pytest.approx(180) and z["projector_compatible_phase_circular_coverage_deg"]==0
def test_x_only():assert M.pe({"x_only":True,"Jones_complete":True}) is False
def test_retry():
 r=M.analyze([p("a",500,10,"FAILED","x","a_1"),p("a",500,10,"ACCEPTED","x","a_2"),p("a",550,20)],[f("a",500,10),f("a",550,20)]);assert r["authoritative_phase_row_count"]==2 and len([z for z in r["per_anchor_phi_table"] if z["H_global_nm"]==500])==1 and all(z["status"]=="ACCEPTED" for z in r["per_anchor_phi_table"])
