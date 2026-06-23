from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT=Path(__file__).resolve().parents[1]; SRC=REPO_ROOT/"src"
if str(SRC) not in sys.path: sys.path.insert(0,str(SRC))

from metasurface.stage13_7b_finite_patch_plane_wave_sanity import HEARTBEAT_SECONDS, PLANE_SOURCE, SOURCE_Z_NM, add_plane_wave, sanity_decision, source_preflight
from metasurface.stage13_4_center_dipole import X_SOURCE, Y_SOURCE


class FakeFDTD:
    def __init__(self): self.selected=""; self.objects={X_SOURCE:{},Y_SOURCE:{}}; self.current={}
    def select(self,name): self.selected=name; self.current=self.objects[name]
    def delete(self): del self.objects[self.selected]; self.current={}
    def addplane(self): self.current={}; self.objects["pending"]=self.current
    def set(self,key,value):
        if key=="name": self.objects[value]=self.current; self.objects.pop("pending",None); self.selected=value
        self.current[key]=value
    def getnamed(self,name,key):
        if name=="FDTD": return "PML"
        value=self.objects[name][key]
        return "Z-AXIS" if key=="injection axis" else value
    def getnamednumber(self,name): return 1 if name in self.objects else 0


def test_plane_wave_is_explicit_xlp_forward_plusz() -> None:
    fdtd=FakeFDTD(); setup={"fdtd_x_span_nm":9000.0,"fdtd_y_span_nm":9400.0,"wavelength_nm":450.0}
    add_plane_wave(fdtd,setup); source=fdtd.objects[PLANE_SOURCE]
    assert source["injection axis"]=="z" and source["direction"]=="Forward"
    assert source["polarization angle"]==0.0 and source["z"]==SOURCE_Z_NM*1e-9
    assert X_SOURCE not in fdtd.objects and Y_SOURCE not in fdtd.objects
    assert HEARTBEAT_SECONDS <= 60.0
    assert source_preflight(fdtd,setup) == []


def test_sanity_decision_pass_and_no_steering() -> None:
    orders=[]
    for order,power in (("zero_order",1.0),("plus_target_order",2.0),("minus_target_order",0.5)):
        orders.append({"order_id":order,"cone_deg":5.0,"target_LP_power":power})
    peak={"component":"Ex_target","peak_ux":0.174,"peak_uy":0.0,"distance_to_plus_target_deg":0.1,"distance_to_minus_target_deg":20.0}
    assert sanity_decision([peak],orders)["finite_patch_plane_wave_steering_pass"] is True
    peak2={**peak,"peak_ux":0.4,"distance_to_plus_target_deg":15.0,"distance_to_minus_target_deg":35.0}
    result=sanity_decision([peak2],orders)
    assert result["finite_patch_plane_wave_no_steering"] is True
