from __future__ import annotations
import argparse, cmath, json
from typing import Any

EPSILON = 1e-15

def _divide(value: complex, blank_copol: complex) -> complex:
    if abs(blank_copol) <= EPSILON: raise ValueError("blank co-polar zero-order amplitude is too small for normalization")
    return complex(value) / complex(blank_copol)

def complex_metrics(value: complex) -> dict[str, float]:
    z=complex(value); return {"real":z.real,"imag":z.imag,"abs":abs(z),"phase_rad":cmath.phase(z)}

def normalize_input(candidate_copol: complex, candidate_crosspol: complex, blank_copol: complex) -> dict[str, Any]:
    copol=_divide(candidate_copol,blank_copol); crosspol=_divide(candidate_crosspol,blank_copol)
    return {"copol":complex_metrics(copol),"crosspol":complex_metrics(crosspol),"phase_rel_rad":cmath.phase(copol)}

def build_jones(x_input: dict[str, Any], y_input: dict[str, Any]) -> dict[str, Any]:
    return {"txx":x_input["copol"],"tyx":x_input["crosspol"],"txy":y_input["crosspol"],"tyy":y_input["copol"],"x_y_amplitude_mismatch":abs(x_input["copol"]["abs"]-y_input["copol"]["abs"]),"x_y_phase_mismatch_rad":x_input["phase_rel_rad"]-y_input["phase_rel_rad"]}

def postrun_result_schema() -> dict[str, Any]:
    return {"raw_zero_order_complex_amplitude":None,"raw_zero_order_power":None,"blank_relative_complex_transmission":None,"phase_rel_rad":None,"T0":None,"R":None,"total_T":None,"energy_residual":None,"txx":None,"tyx":None,"txy":None,"tyy":None,"x_y_amplitude_mismatch":None,"x_y_phase_mismatch_rad":None,"result_status":"not_run"}
def main() -> int:
    p=argparse.ArgumentParser(description="Fail-closed post-run extractor skeleton; no FDTD execution.")
    p.add_argument("--results-json", required=True, help="post-run monitor export; setup-only FSP has none")
    args=p.parse_args()
    raise RuntimeError("no solved monitor data is available; setup-only FSP extraction is forbidden")
if __name__ == "__main__":
    main()