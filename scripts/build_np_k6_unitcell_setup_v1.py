from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
NM = 1e-9
PITCH_NM = 290
LAYOUT_NM = {"fdtd_z_min_nm": -1000, "fdtd_z_max_nm": 1200, "source_z_nm": -500, "reflection_monitor_z_nm": -750, "transmission_monitor_z_nm": 900, "mesh_override_z_min_nm": -20, "mesh_override_z_max_nm": 720, "mesh_nm": 5}

def parse_integer_nm(value: str) -> int:
    if not re.fullmatch(r"[+-]?\d+", str(value)):
        raise argparse.ArgumentTypeError("nanometre inputs must be integer literals")
    return int(value)

def validate_geometry(height_nm: int, diameter_nm: int) -> None:
    if not isinstance(height_nm, int) or not isinstance(diameter_nm, int): raise ValueError("geometry must be integer nm")
    if not 100 <= diameter_nm <= 230: raise ValueError("diameter must satisfy 100 <= D <= 230 nm")
    if not 300 <= height_nm <= 700: raise ValueError("height must satisfy 300 <= H <= 700 nm")
    if PITCH_NM - diameter_nm < 60: raise ValueError("edge-to-edge gap must be >= 60 nm")
    if height_nm / diameter_nm > 5.5: raise ValueError("aspect ratio H/D must be <= 5.5")

def build_spec(case: str, wavelength_nm: int, polarization: str, height_nm: int, diameter_nm: int) -> dict[str, Any]:
    if case not in {"blank", "pillar"}: raise ValueError("case must be blank or pillar")
    if wavelength_nm not in {448, 450, 453}: raise ValueError("unsupported wavelength")
    if polarization not in {"x", "y"}: raise ValueError("polarization must be x or y")
    validate_geometry(height_nm, diameter_nm)
    return {"case":case,"wavelength_nm":wavelength_nm,"polarization":polarization,"height_nm":height_nm,"diameter_nm":diameter_nm,"pitch_x_nm":PITCH_NM,"period_y_nm":PITCH_NM,"layout_nm":dict(LAYOUT_NM),"source_monitor_reference_shared":True,"objects":["FDTD","source","R_fields","T_fields","SiO2 substrate"]+(["TiO2 pillar","pillar mesh override"] if case=="pillar" else [])}
def _import_lumapi():
    api = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
    if str(api) not in sys.path: sys.path.insert(0, str(api))
    import lumapi
    return lumapi

def _register_native_materials(fdtd: Any) -> dict[str, Any]:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from apcd_native_materials import register_lumerical_sampled_material
    return {k: register_lumerical_sampled_material(fdtd, k) for k in ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")}

def _set(fdtd: Any, key: str, value: Any) -> None: fdtd.set(key, value)

def create_setup(spec: dict[str, Any], output_fsp: Path) -> dict[str, Any]:
    fdtd = _import_lumapi().FDTD(hide=True)
    try:
        materials = _register_native_materials(fdtd)
        zmin, zmax = spec["layout_nm"]["fdtd_z_min_nm"]*NM, spec["layout_nm"]["fdtd_z_max_nm"]*NM
        fdtd.addfdtd(); _set(fdtd,"dimension","3D")
        _set(fdtd,"x span",PITCH_NM*NM); _set(fdtd,"y span",PITCH_NM*NM); _set(fdtd,"z min",zmin); _set(fdtd,"z max",zmax)
        for key,val in (("x min bc","Periodic"),("x max bc","Periodic"),("y min bc","Periodic"),("y max bc","Periodic"),("z min bc","PML"),("z max bc","PML")): _set(fdtd,key,val)
        fdtd.addrect(); _set(fdtd,"name","SiO2 substrate"); _set(fdtd,"material","APCD_SIO2_NATIVE_M1")
        _set(fdtd,"x span",PITCH_NM*NM); _set(fdtd,"y span",PITCH_NM*NM); _set(fdtd,"z min",zmin); _set(fdtd,"z max",0)
        if spec["case"] == "pillar":
            fdtd.addcircle(); _set(fdtd,"name","TiO2 pillar"); _set(fdtd,"material","APCD_TIO2_NATIVE_M1")
            _set(fdtd,"radius",spec["diameter_nm"]*NM/2); _set(fdtd,"z min",0); _set(fdtd,"z max",spec["height_nm"]*NM)
            fdtd.addmesh(); _set(fdtd,"name","pillar mesh override"); _set(fdtd,"x span",(spec["diameter_nm"]+20)*NM); _set(fdtd,"y span",(spec["diameter_nm"]+20)*NM)
            _set(fdtd,"z min",spec["layout_nm"]["mesh_override_z_min_nm"]*NM); _set(fdtd,"z max",spec["layout_nm"]["mesh_override_z_max_nm"]*NM)
            for k in ("dx","dy","dz"): _set(fdtd,k,spec["layout_nm"]["mesh_nm"]*NM)
        fdtd.addplane(); _set(fdtd,"name","source"); _set(fdtd,"injection axis","z"); _set(fdtd,"direction","Forward")
        _set(fdtd,"x span",PITCH_NM*NM); _set(fdtd,"y span",PITCH_NM*NM); _set(fdtd,"z",spec["layout_nm"]["source_z_nm"]*NM)
        _set(fdtd,"wavelength start",spec["wavelength_nm"]*NM); _set(fdtd,"wavelength stop",spec["wavelength_nm"]*NM); _set(fdtd,"polarization angle",0 if spec["polarization"]=="x" else 90)
        for name,z in (("R_fields",spec["layout_nm"]["reflection_monitor_z_nm"]),("T_fields",spec["layout_nm"]["transmission_monitor_z_nm"])):
            fdtd.addprofile(); _set(fdtd,"name",name); _set(fdtd,"monitor type","2D Z-normal"); _set(fdtd,"x span",PITCH_NM*NM); _set(fdtd,"y span",PITCH_NM*NM); _set(fdtd,"z",z*NM)
        output_fsp.parent.mkdir(parents=True, exist_ok=True); fdtd.save(str(output_fsp))
        return {"materials":materials,"run_count":0,"output_fsp":str(output_fsp)}
    finally:
        fdtd.close()

def audit_saved_fsp(path: Path) -> dict[str, Any]:
    fdtd = _import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(path))
        names=["FDTD","source","R_fields","T_fields","SiO2 substrate"]
        pillar_count=int(fdtd.getnamednumber("TiO2 pillar"))
        if pillar_count: names += ["TiO2 pillar","pillar mesh override"]
        return {"path":str(path),"objects":names,"pillar_count":pillar_count,"fdtd":{"x_span_m":float(fdtd.getnamed("FDTD","x span")),"y_span_m":float(fdtd.getnamed("FDTD","y span")),"x_min_bc":str(fdtd.getnamed("FDTD","x min bc")),"y_min_bc":str(fdtd.getnamed("FDTD","y min bc")),"z_min_bc":str(fdtd.getnamed("FDTD","z min bc"))},"source":{"wavelength_start_m":float(fdtd.getnamed("source","wavelength start")),"polarization_angle_deg":float(fdtd.getnamed("source","polarization angle")),"direction":str(fdtd.getnamed("source","direction")),"z_m":float(fdtd.getnamed("source","z"))},"monitors":{"R_z_m":float(fdtd.getnamed("R_fields","z")),"T_z_m":float(fdtd.getnamed("T_fields","z"))},"materials":{"substrate":str(fdtd.getnamed("SiO2 substrate","material")),"pillar":str(fdtd.getnamed("TiO2 pillar","material")) if pillar_count else None},"pillar_geometry":{"height_m":float(fdtd.getnamed("TiO2 pillar","z max"))-float(fdtd.getnamed("TiO2 pillar","z min")) if pillar_count else None,"diameter_m":2*float(fdtd.getnamed("TiO2 pillar","radius")) if pillar_count else None},"run_count":0}
    finally:
        fdtd.close()

def main() -> int:
    parser=argparse.ArgumentParser(description="Create or audit a setup-only NP unit cell; never runs a solver.")
    parser.add_argument("--case", choices=("blank","pillar")); parser.add_argument("--wavelength-nm", type=parse_integer_nm, default=450)
    parser.add_argument("--polarization", choices=("x","y"), default="x"); parser.add_argument("--height-nm", type=parse_integer_nm, default=500)
    parser.add_argument("--diameter-nm", type=parse_integer_nm, default=160); parser.add_argument("--output-fsp", type=Path)
    parser.add_argument("--audit-fsp", type=Path); args=parser.parse_args()
    if args.audit_fsp:
        print(json.dumps(audit_saved_fsp(args.audit_fsp), indent=2, sort_keys=True)); return 0
    if args.output_fsp is None: parser.error("--output-fsp is required when creating a setup")
    spec=build_spec(args.case,args.wavelength_nm,args.polarization,args.height_nm,args.diameter_nm)
    print(json.dumps({"spec":spec,"setup":create_setup(spec,args.output_fsp)}, indent=2, sort_keys=True)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
