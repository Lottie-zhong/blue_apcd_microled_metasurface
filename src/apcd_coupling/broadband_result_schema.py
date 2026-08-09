from __future__ import annotations
import math
from typing import Any

def validate_broadband_result(result: dict[str, Any]) -> dict[str, Any]:
    required={'schema_version','case_id','control_group','spacer_nm','total_sio2_separation_nm','wavelength_grid_nm','rows','source_contract_id','material_contract_id','coordinate_contract_id','mesh_contract_id','pre_fsp_sha256','post_fsp_sha256','solver_entered','solver_completed','source_commits','coupling_commit','provenance_status'}
    missing=sorted(required-set(result))
    if missing: raise ValueError(f'broadband result missing fields: {missing}')
    grid=[float(x) for x in result['wavelength_grid_nm']]
    expected=[float(x) for x in range(445,456)]
    if len(grid)!=11 or any(abs(a-b)>1e-9 for a,b in zip(grid,expected)): raise ValueError(f'exact 445-455 grid required: {grid}')
    rows=result['rows']
    if len(rows)!=11: raise ValueError('one row per exact wavelength required')
    for wavelength,row in zip(expected,rows):
        if abs(float(row['wavelength_nm'])-wavelength)>1e-9: raise ValueError('row wavelength does not match exact grid')
        for key in ('R_total','T_total','residual_1_minus_R_minus_T','eta_plus1','eta_zero','eta_minus1','theta_plus1_deg','directionality'):
            if not math.isfinite(float(row[key])): raise ValueError(f'non-finite broadband row field {key}')
        if not row['sign_audit']['pass'] or not row['order_closure']['pass'] or not row['power_closure']['pass']: raise ValueError('broadband row closure/sign failure')
    if result['solver_entered'] is not True or result['solver_completed'] is not True: raise ValueError('completed broadband result must record solver entered/completed')
    return result
