from __future__ import annotations
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("lp_global_h_h1b0",ROOT/"scripts/lp_global_h_h1b0_ranking_v1.py")
MODULE=importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)

def test_circular_span_and_pairwise_wrap():
    assert MODULE.span([355.0,5.0,15.0])["circular_coverage_deg"]==20.0
    rows=[{"authoritative_id":"a","phase_deg":355.0},{"authoritative_id":"b","phase_deg":5.0}]
    assert MODULE.pairs(rows)[0]["separation_deg"]==10.0

def test_authoritative_inputs_and_zero_solver():
    c=MODULE.load_inputs()
    assert len(c["rows"])==30
    assert c["final_report"]["solver_subruns_entered"]==48
    assert c["final_report"]["solver_subruns_accepted"]==48
    assert c["final_report"]["H500_scheduled"] is False
    assert c["solver_delta"]=={"new_solver_entered":0,"new_rcwa_entered":0,"new_physics_solver_entered":0,"scheduler_invoked":False}

def test_ranking_and_sector_gate():
    c=MODULE.load_inputs()
    a={h:MODULE.analyze_height(c["rows"],h,c["interactions"][h]) for h in MODULE.H_GRID}
    r=MODULE.ranking(a)
    assert r["PRIMARY_H_CANDIDATE"]==550.0
    assert r["CONTROL_H"]==500.0
    assert r["SECONDARY_H_CANDIDATE"]==[400.0,450.0]
    assert all(60-a[h]["max_projector_compatible_pairwise_separation_deg"]>0 for h in MODULE.H_GRID)

def test_leave_one_anchor_out_is_stable():
    r=MODULE.leave_one_out(MODULE.load_inputs())
    assert r["primary_survives_all_single_anchor_removals"] is True
    assert r["ranking_stability"]=="H_RANKING_REASONABLY_STABLE_WITHIN_H1A_SAMPLE"
    assert len(r["cases"])==6

def test_stage_script_has_no_solver_or_scheduler_surface():
    text=(ROOT/"scripts/lp_global_h_h1b0_ranking_v1.py").read_text(encoding="utf-8").lower()
    for forbidden in ("lumapi","fdtd.run","mpiexec","apcd_global_fdtd_slot"):
        assert forbidden not in text
