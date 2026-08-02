"""Build helper for the NP K6-x 449 nm constant-epsilon setup-only control.
No solver call is made here.
"""
from math import sqrt
from metasurface.apcd_material_library import get_epsilon, get_nk

def canonical_constant_spec(material_reference_id: str, wavelength_nm: float = 449.0) -> dict:
    epsilon = complex(get_epsilon(material_reference_id, wavelength_nm))
    nk = complex(get_nk(material_reference_id, wavelength_nm))
    return {"material_reference_id": material_reference_id, "wavelength_nm": wavelength_nm, "epsilon": epsilon, "n": nk, "epsilon_from_n": nk * nk}

def set_constant_dielectric(fdtd, material_reference_id: str, name: str, wavelength_nm: float = 449.0) -> str:
    spec = canonical_constant_spec(material_reference_id, wavelength_nm)
    if abs(spec["epsilon"].imag) > 1e-14:
        raise ValueError("Lumerical Dielectric scalar path cannot represent nonzero imaginary epsilon")
    temporary = str(fdtd.addmaterial("Dielectric"))
    fdtd.setmaterial(temporary, "name", name)
    fdtd.setmaterial(name, "permittivity", float(spec["epsilon"].real))
    return name
