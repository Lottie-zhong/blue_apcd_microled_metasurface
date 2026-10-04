"""Frozen EXT02 two-air-plane evaluator; no phase or fitted-scale alignment."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple
import hashlib
from pathlib import Path
import numpy as np
from scripts.shared_fdtd.tools import pw_complex_floquet_state_v1 as _official
from .contracts import DIRECTIONS, ORDER_MN, POLARIZATIONS, REFERENCE_PLANE_NM, STATE_SCHEMA, TWO_PLANE_ATTEMPT_ID, TWO_PLANE_CASE_ID, TWO_PLANE_PROTOCOL_SHA256, WAVELENGTHS_NM

OFFICIAL_EXTRACTOR_SHA256 = "b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15"
SOURCE_NORMALIZATION = "incident_+z_(0,0)_TM_power_at_IN_REF"
PROJECTION_NAME = "actual_coordinate_trapezoidal_NUDFT"
ENDPOINT_RULE = "trapezoidal_weights_on_inclusive_monitor_coordinates"
PERIOD_X_M, PERIOD_Y_M = 1740e-9, 290e-9
STATE_REL_L2_MAX, ROUTING_MAX_ABS = 0.02, 0.005
ABSOLUTE_ORDER_MAX_ABS, TOTAL_POWER_REL_MAX = 0.005, 0.01
SIGNIFICANT_PHASE_RMSE_MAX_RAD, SIGNIFICANT_COORDINATE_SHARE = 0.05, 1e-4

@dataclass(frozen=True)
class PlaneProjection:
    """Official extractor projection at the actual sample z (z_reference=None)."""
    name: str
    z_sample_m: float
    z_reference_m: float
    wavelengths_nm: np.ndarray
    orders_mn: np.ndarray
    directions: Tuple[str, ...]
    polarizations: Tuple[str, ...]
    coefficients: np.ndarray                 # wavelength,order,direction,polarization
    mode_kz_rad_m: np.ndarray                # wavelength,order
    mode_power_z_per_abs_e2: np.ndarray      # wavelength,order,direction,polarization
    propagating_mask: np.ndarray             # wavelength,order
    basis_condition: np.ndarray              # wavelength,order
    local_index: np.ndarray
    axis_contract: Mapping[str, str]
    x_m: Optional[np.ndarray] = None
    y_m: Optional[np.ndarray] = None
    raw_fields: Optional[Mapping[str, np.ndarray]] = None  # canonical x,y,wavelength fields
    least_squares_residual: Optional[np.ndarray] = None
    least_squares_rank: Optional[np.ndarray] = None

@dataclass(frozen=True)
class TwoPlaneInput:
    case_id: str
    attempt_id: str
    state_schema: str
    extractor_sha256: str
    protocol_sha256: str
    normalization: str
    reference_plane_nm: float
    period_x_m: float
    period_y_m: float
    incident_power_per_area: np.ndarray
    near: PlaneProjection
    far: PlaneProjection
    provenance_sha256: Mapping[str, str]
    # phase(angle) of the frozen extractor's global source gauge at IN_REF.
    # This is needed to compare raw recovered coefficients to normalized state.
    source_gauge_phase_rad: Optional[np.ndarray] = None

def _finite_complex(a: np.ndarray) -> bool:
    a = np.asarray(a)
    return bool(np.isfinite(a.real).all() and np.isfinite(a.imag).all())

def _trap_weights(coordinates: np.ndarray, label: str) -> np.ndarray:
    x = np.asarray(coordinates, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.isfinite(x).all():
        raise ValueError(f"{label}_coordinates_invalid")
    dx = np.diff(x)
    if np.any(dx <= 0):
        raise ValueError(f"{label}_coordinates_not_strictly_increasing")
    w = np.empty_like(x)
    w[0], w[-1] = dx[0] / 2, dx[-1] / 2
    if x.size > 2:
        w[1:-1] = (x[2:] - x[:-2]) / 2
    return w

def _validate_plane(p: PlaneProjection) -> None:
    norders = np.asarray(p.orders_mn).shape[0] if np.asarray(p.orders_mn).ndim == 2 else -1
    if norders < 1 or np.asarray(p.orders_mn).shape[1:] != (2,):
        raise ValueError(f"{p.name}_orders_mn_invalid")
    orders = [tuple(map(int, x)) for x in np.asarray(p.orders_mn)]
    if len(set(orders)) != len(orders) or not set(ORDER_MN).issubset(orders):
        raise ValueError(f"{p.name}_orders_duplicate_or_required_m_minus3_to_plus3_n0_missing")
    if tuple(p.directions) != DIRECTIONS or tuple(p.polarizations) != POLARIZATIONS:
        raise ValueError(f"{p.name}_channel_order_mismatch")
    if np.asarray(p.wavelengths_nm).shape != (21,) or not np.allclose(p.wavelengths_nm, WAVELENGTHS_NM, rtol=0, atol=1e-9):
        raise ValueError(f"{p.name}_wavelength_grid_must_be_440_460nm_1nm")
    if not np.isfinite(p.z_sample_m) or not np.isfinite(p.z_reference_m):
        raise ValueError(f"{p.name}_actual_z_invalid")
    if not np.isclose(p.z_sample_m, p.z_reference_m, rtol=0, atol=1e-12):
        raise ValueError(f"{p.name}_must_contain_sample_plane_coefficients_before_deembedding")
    if p.axis_contract.get("projection") != PROJECTION_NAME or p.axis_contract.get("endpoint_rule") != ENDPOINT_RULE:
        raise ValueError(f"{p.name}_official_projection_or_trapezoid_metadata_mismatch")
    index = np.asarray(p.local_index, dtype=complex)
    if index.shape != (21,) or not _finite_complex(index) or not np.allclose(index, 1+0j, rtol=0, atol=1e-12):
        raise ValueError(f"{p.name}_must_be_uniform_air")
    shapes = {
        "coefficients": (21,norders,2,2), "mode_kz_rad_m": (21,norders),
        "mode_power_z_per_abs_e2": (21,norders,2,2),
        "propagating_mask": (21,norders), "basis_condition": (21,norders),
    }
    for name, shape in shapes.items():
        a=np.asarray(getattr(p,name))
        if a.shape != shape or (not _finite_complex(a) if name in ("coefficients","mode_kz_rad_m") else not np.isfinite(a).all()):
            raise ValueError(f"{p.name}_{name}_shape_or_finiteness_invalid")
    if np.any(np.asarray(p.basis_condition) <= 0):
        raise ValueError(f"{p.name}_basis_condition_not_positive")
    if np.any(np.asarray(p.mode_kz_rad_m).imag < -1e-9):
        raise ValueError(f"{p.name}_kz_not_on_official_passive_branch")
    for name in ("least_squares_residual","least_squares_rank"):
        a=getattr(p,name)
        if a is not None and (np.asarray(a).shape != (21,norders) or not np.isfinite(a).all()):
            raise ValueError(f"{p.name}_{name}_shape_or_finiteness_invalid")

def _deembed(p: PlaneProjection, reference_nm: float) -> np.ndarray:
    c=np.asarray(p.coefficients,dtype=complex)
    kz=np.asarray(p.mode_kz_rad_m,dtype=complex)
    dz=(reference_nm*1e-9)-p.z_sample_m
    out=np.empty_like(c)
    for di,direction in enumerate(DIRECTIONS):
        sign=1.0 if direction=="+z" else -1.0
        out[:,:,di,:]=c[:,:,di,:]*np.exp(sign*1j*kz*dz)[:,:,None]
    if not _finite_complex(out):
        raise ValueError(f"{p.name}_deembedding_nonfinite")
    return out

def _official_raw_fit_diagnostics(
    p: PlaneProjection,
    inp: TwoPlaneInput,
    fields: Mapping[str, np.ndarray],
    x: np.ndarray,
    y: np.ndarray,
) -> dict[str, Any]:
    """Re-run the frozen extractor's per-order 6x4 least-squares fit on saved raw E/H.

    This is a diagnostic parity check only. The official extractor and truth are
    never modified; its source hash is checked before invoking its exact _mode
    and trapezoid implementations.
    """
    source_path = Path(_official.__file__).resolve()
    source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_sha != OFFICIAL_EXTRACTOR_SHA256:
        raise ValueError("official_extractor_source_hash_mismatch")

    # Call the pinned extractor's exact coordinate-weight implementation.
    official_wx = _official._trap_weights(x)
    official_wy = _official._trap_weights(y)
    x_grid, y_grid = np.meshgrid(x, y, indexing="ij")
    orders = [tuple(map(int, row)) for row in np.asarray(p.orders_mn)]
    fit_coefficients = np.zeros_like(np.asarray(p.coefficients, dtype=np.complex128))
    residual_abs = np.zeros((21, len(orders)), dtype=float)
    sampled_norm = np.zeros_like(residual_abs)
    residual_rel = np.zeros_like(residual_abs)
    fit_rank = np.zeros((21, len(orders)), dtype=int)
    fit_condition = np.zeros((21, len(orders)), dtype=float)
    mode_kz_difference = 0.0
    field_names = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")

    # The official source uses absolute coordinates with phase origin (0, 0)
    # and its frozen default periods in _mode. The caller already validates
    # those periods against the exact official constants.
    for wi, wavelength in enumerate(np.asarray(p.wavelengths_nm, dtype=float)):
        refractive_index = complex(np.asarray(p.local_index, dtype=complex)[wi])
        for oi, (m, n) in enumerate(orders):
            basis_modes = [
                _official._mode(
                    m, n, float(wavelength), refractive_index, direction, polarization
                )
                for direction in (1, -1)
                for polarization in POLARIZATIONS
            ]
            matrix = np.stack(
                [np.concatenate((mode["e_hat"], mode["h_hat"])) for mode in basis_modes],
                axis=1,
            )
            fit_condition[wi, oi] = float(np.linalg.cond(matrix))
            mode_kz_difference = max(
                mode_kz_difference,
                abs(complex(p.mode_kz_rad_m[wi, oi]) - complex(basis_modes[0]["kz_rad_m"])),
            )
            phase = np.exp(
                -1j
                * (
                    2.0 * np.pi * m * x_grid / inp.period_x_m
                    + 2.0 * np.pi * n * y_grid / inp.period_y_m
                )
            )
            sampled = np.empty(6, dtype=np.complex128)
            for ci, name in enumerate(field_names):
                sampled[ci] = np.sum(
                    official_wx[:, None] * official_wy[None, :] * fields[name][:, :, wi] * phase
                ) / (inp.period_x_m * inp.period_y_m)
            modal, _, rank, _ = np.linalg.lstsq(matrix, sampled, rcond=None)
            fit_rank[wi, oi] = int(rank)
            residual_abs[wi, oi] = float(np.linalg.norm(matrix @ modal - sampled))
            sampled_norm[wi, oi] = float(np.linalg.norm(sampled))
            residual_rel[wi, oi] = residual_abs[wi, oi] / max(sampled_norm[wi, oi], 1e-30)
            for ci, value in enumerate(modal):
                fit_coefficients[wi, oi, ci // 2, ci % 2] = value

    gauge = inp.source_gauge_phase_rad
    parity: dict[str, Any]
    missing: list[str] = []
    if gauge is None:
        parity = {
            "available": False,
            "missing": ["official_source_gauge_phase_rad"],
            "max_abs_difference": None,
            "relative_l2_by_wavelength_order": None,
            "matches_within_floating_point_tolerance": None,
        }
        missing.append(p.name + ".official_source_gauge_phase_rad")
    else:
        gauge_array = np.asarray(gauge, dtype=float)
        if gauge_array.shape != (21,) or not np.isfinite(gauge_array).all():
            raise ValueError("source_gauge_phase_rad_shape_or_finiteness_invalid")
        normalized = fit_coefficients * (
            np.exp(1j * gauge_array) / np.sqrt(np.asarray(inp.incident_power_per_area, dtype=float))
        )[:, None, None, None]
        difference = normalized - np.asarray(p.coefficients, dtype=np.complex128)
        rel_by_wave_order = np.zeros((21, len(orders)), dtype=float)
        for wi in range(21):
            for oi in range(len(orders)):
                denominator = float(np.linalg.norm(p.coefficients[wi, oi]))
                numerator = float(np.linalg.norm(difference[wi, oi]))
                rel_by_wave_order[wi, oi] = numerator / max(denominator, 1e-30)
        abs_max = float(np.max(np.abs(difference)))
        parity_pass = bool(np.allclose(normalized, p.coefficients, rtol=1e-10, atol=1e-12))
        parity = {
            "available": True,
            "max_abs_difference": abs_max,
            "max_relative_l2": float(np.max(rel_by_wave_order)),
            "relative_l2_by_wavelength_order": rel_by_wave_order.tolist(),
            "matches_within_floating_point_tolerance": parity_pass,
            "floating_point_tolerance": {"rtol": 1e-10, "atol": 1e-12},
            "normalization": "exp(1j*official_gauge_phase_rad)/sqrt(official_incident_power_per_area)",
        }
        if not parity_pass:
            missing.append(p.name + ".raw_to_official_coefficient_parity")

    full_rank = bool(np.all(fit_rank == 4))
    if not full_rank:
        missing.append(p.name + ".full_rank_4_recomputed_from_raw")
    condition_json = [
        [float(v) if np.isfinite(v) else None for v in row]
        for row in fit_condition
    ]
    basis_condition_difference = np.abs(fit_condition - np.asarray(p.basis_condition, dtype=float))
    return {
        "available": True,
        "official_source_sha256_verified": source_sha,
        "method": "diagnostic reimplementation of frozen _plane_projection 6x4 complex least-squares; no truth alteration",
        "actual_coordinate_trapezoid": True,
        "trapezoid_weights_source": "pinned pw_complex_floquet_state_v1._trap_weights",
        "phase_origin_m": [0.0, 0.0],
        "period_xy_m": [float(inp.period_x_m), float(inp.period_y_m)],
        "residual_absolute_by_wavelength_order": residual_abs.tolist(),
        "sampled_vector_norm_by_wavelength_order": sampled_norm.tolist(),
        "residual_relative_to_sampled_vector_by_wavelength_order": residual_rel.tolist(),
        "residual_relative_to_max_sampled_vector_by_wavelength_order": (
            residual_abs / np.maximum(np.max(sampled_norm, axis=1, keepdims=True), 1e-30)
        ).tolist(),
        "rank_by_wavelength_order": fit_rank.tolist(),
        "full_rank_4": full_rank,
        "condition_number_by_wavelength_order": condition_json,
        "official_basis_condition_max_abs_difference": (
            float(np.max(basis_condition_difference))
            if np.isfinite(basis_condition_difference).all() else None
        ),
        "official_mode_kz_max_abs_difference_rad_m": float(mode_kz_difference),
        "official_coefficients_parity": parity,
        "missing": missing,
        "supplied_legacy_residual_max_abs_difference": (
            None if p.least_squares_residual is None
            else float(np.max(np.abs(np.asarray(p.least_squares_residual, dtype=float) - residual_abs)))
        ),
        "supplied_legacy_rank_matches": (
            None if p.least_squares_rank is None
            else bool(np.array_equal(np.asarray(p.least_squares_rank, dtype=int), fit_rank))
        ),
    }


def _raw_diagnostics(p: PlaneProjection, inp: TwoPlaneInput) -> dict[str,Any]:
    if p.raw_fields is None or p.x_m is None or p.y_m is None:
        return {"available":False,"missing":["actual_x_y_coordinates_and_six_raw_EH_fields"],
                "endpoint_closure":None,"mesh_spacing_nm":None,"poynting_normalized":None,
                "least_squares":{"available":False,"missing":["actual_x_y_coordinates_and_six_raw_EH_fields"]}}
    x,y=np.asarray(p.x_m,float),np.asarray(p.y_m,float)
    wx,wy=_trap_weights(x,p.name+"_x"),_trap_weights(y,p.name+"_y")
    if not np.isclose(x[-1]-x[0],inp.period_x_m,rtol=0,atol=inp.period_x_m*1e-8):
        raise ValueError(f"{p.name}_x_grid_not_full_period")
    if not np.isclose(y[-1]-y[0],inp.period_y_m,rtol=0,atol=inp.period_y_m*1e-8):
        raise ValueError(f"{p.name}_y_grid_not_full_period")
    names=("Ex","Ey","Ez","Hx","Hy","Hz")
    f={}
    for name in names:
        if name not in p.raw_fields: raise ValueError(f"{p.name}_raw_field_missing:{name}")
        a=np.asarray(p.raw_fields[name],complex)
        if a.shape!=(x.size,y.size,21) or not _finite_complex(a):
            raise ValueError(f"{p.name}_raw_field_shape_or_finiteness_invalid:{name}")
        f[name]=a
    endpoint,all_rel={},[]
    for name,a in f.items():
        endpoint[name]={}
        for axis,diff in (("x",np.max(np.abs(a[0]-a[-1]),axis=0)),("y",np.max(np.abs(a[:,0]-a[:,-1]),axis=0))):
            scale=np.max(np.abs(a),axis=(0,1))
            rel=np.divide(diff,scale,out=np.zeros_like(diff,dtype=float),where=scale>1e-30)
            rel[(scale<=1e-30)&(diff>1e-30)]=np.inf
            endpoint[name][axis]=rel.tolist()
            all_rel.extend(rel.tolist())
    least_squares = _official_raw_fit_diagnostics(p, inp, f, x, y)
    sz=.5*np.real(f["Ex"]*np.conj(f["Hy"])-f["Ey"]*np.conj(f["Hx"]))
    flux=np.einsum("i,j,ijw->w",wx,wy,sz,optimize=True)
    denom=np.asarray(inp.incident_power_per_area,float)*inp.period_x_m*inp.period_y_m
    if np.any(~np.isfinite(denom)) or np.any(denom<=0): raise ValueError("incident_power_per_area_invalid")
    dx,dy=np.diff(x)*1e9,np.diff(y)*1e9
    return {
        "available":True,"missing":[],
        "least_squares":least_squares,
        "endpoint_closure":{"per_component_relative_mismatch_by_wavelength":endpoint,
                            "max_relative_mismatch":float(max(all_rel,default=0.0)),
                            "boundary_condition":"normal_incidence_periodic"},
        "mesh_spacing_nm":{
            "x":{"min":float(dx.min()),"median":float(np.median(dx)),"max":float(dx.max()),"interval_count":int(dx.size)},
            "y":{"min":float(dy.min()),"median":float(np.median(dy)),"max":float(dy.max()),"interval_count":int(dy.size)},
            "trapezoid_endpoint_weights_m":{"x_first":float(wx[0]),"x_last":float(wx[-1]),"y_first":float(wy[0]),"y_last":float(wy[-1]),
                                            "sum_x":float(wx.sum()),"sum_y":float(wy.sum())}},
        "poynting_normalized":(flux/denom).tolist()
    }

def _relative(a: np.ndarray,b: np.ndarray)->np.ndarray:
    aa=np.asarray(a,float); bb=np.asarray(b,float)
    out=np.full(np.broadcast_shapes(aa.shape,bb.shape),np.inf)
    np.divide(np.abs(bb-aa),np.abs(aa),out=out,where=np.abs(aa)>1e-30)
    out[(np.abs(aa)<=1e-30)&(np.abs(bb)<=1e-30)]=0
    return out

def evaluate_two_plane_consistency(inp: TwoPlaneInput)->dict[str,Any]:
    """Run frozen actual-z de-embedding and one-case engineering thresholds."""
    if inp.case_id!=TWO_PLANE_CASE_ID or inp.attempt_id!=TWO_PLANE_ATTEMPT_ID:
        raise ValueError("two_plane_case_or_attempt_mismatch")
    if inp.state_schema!=STATE_SCHEMA: raise ValueError("two_plane_state_schema_mismatch")
    if inp.extractor_sha256.lower()!=OFFICIAL_EXTRACTOR_SHA256: raise ValueError("two_plane_extractor_sha256_mismatch")
    if inp.protocol_sha256.lower()!=TWO_PLANE_PROTOCOL_SHA256: raise ValueError("two_plane_protocol_sha256_mismatch")
    if inp.normalization!=SOURCE_NORMALIZATION: raise ValueError("two_plane_source_normalization_mismatch")
    if not np.isclose(inp.reference_plane_nm,REFERENCE_PLANE_NM,rtol=0,atol=1e-9): raise ValueError("reference_must_be_1722nm")
    if not np.isclose(inp.period_x_m,PERIOD_X_M,rtol=0,atol=1e-15) or not np.isclose(inp.period_y_m,PERIOD_Y_M,rtol=0,atol=1e-15):
        raise ValueError("period_mismatch_with_official_extractor")
    if not inp.provenance_sha256 or any(len(v)!=64 or any(c not in "0123456789abcdefABCDEF" for c in v) for v in inp.provenance_sha256.values()):
        raise ValueError("input_provenance_sha256_missing_or_invalid")
    incident=np.asarray(inp.incident_power_per_area,float)
    if incident.shape!=(21,) or not np.isfinite(incident).all() or np.any(incident<=0): raise ValueError("incident_power_per_area_invalid")
    if inp.near.name!="POSTNP" or inp.far.name!="EXT02_POSTNP_DIAG_Z2000": raise ValueError("plane_names_mismatch")
    if not (np.isfinite(inp.near.z_sample_m) and np.isfinite(inp.far.z_sample_m) and inp.far.z_sample_m>inp.near.z_sample_m):
        raise ValueError("actual_sample_z_order_invalid")
    _validate_plane(inp.near); _validate_plane(inp.far)
    if not np.array_equal(np.asarray(inp.near.orders_mn),np.asarray(inp.far.orders_mn)):
        raise ValueError("near_far_order_axis_mismatch")
    near_s,far_s=np.asarray(inp.near.coefficients,complex),np.asarray(inp.far.coefficients,complex)
    near_r,far_r=_deembed(inp.near,inp.reference_plane_nm),_deembed(inp.far,inp.reference_plane_nm)
    oi={tuple(map(int,row)):i for i,row in enumerate(np.asarray(inp.near.orders_mn))}
    idx=np.asarray([oi[o] for o in ORDER_MN],int)
    prop=np.asarray(inp.near.propagating_mask,bool)[:,idx]
    if not prop.all() or not np.asarray(inp.far.propagating_mask,bool)[:,idx].all():
        raise ValueError("required_m_minus3_to_plus3_orders_not_propagating")
    if not np.allclose(np.asarray(inp.near.mode_kz_rad_m)[:,idx],np.asarray(inp.far.mode_kz_rad_m)[:,idx],rtol=1e-10,atol=1e-8):
        raise ValueError("air_kz_differs_between_planes")

    # H1-compatible C_hat is the transmitted +z state. No truth-phase or scale alignment.
    n,f=near_r[:,idx,0,:],far_r[:,idx,0,:]
    state=np.linalg.norm((f-n).reshape(21,-1),axis=1)/np.maximum(np.linalg.norm(n.reshape(21,-1),axis=1),1e-30)
    down_n,down_f=near_r[:,idx,1,:],far_r[:,idx,1,:]
    down_state=np.linalg.norm((down_f-down_n).reshape(21,-1),axis=1)/np.maximum(np.linalg.norm(down_n.reshape(21,-1),axis=1),1e-30)
    npow=np.sum(np.asarray(inp.near.mode_power_z_per_abs_e2)[:,idx,0,:]*np.abs(near_s[:,idx,0,:])**2,axis=-1)
    fpow=np.sum(np.asarray(inp.far.mode_power_z_per_abs_e2)[:,idx,0,:]*np.abs(far_s[:,idx,0,:])**2,axis=-1)
    nt,ft=npow.sum(axis=1),fpow.sum(axis=1)
    if np.any(nt<=1e-30) or np.any(ft<=1e-30): raise ValueError("transmitted_propagating_power_nonpositive")
    nr,fr=npow/nt[:,None],fpow/ft[:,None]
    route_diff=np.abs(fr-nr); abs_diff=np.abs(fpow-npow); total_rel=np.abs(ft-nt)/np.abs(nt)
    amp_n,amp_f=np.abs(n),np.abs(f)
    phase=np.angle(f*np.conj(n))
    cpower=amp_n**2
    share=np.divide(cpower,cpower.sum(axis=(1,2),keepdims=True),out=np.zeros_like(cpower),where=cpower.sum(axis=(1,2),keepdims=True)>0)
    mask=share>=SIGNIFICANT_COORDINATE_SHARE
    weights=np.where(mask,amp_n,0)
    wsum=float(weights.sum())
    phase_rmse=float(np.sqrt(np.sum(weights*phase**2)/wsum)) if wsum>0 else float("nan")
    per_wave=[]
    for wi in range(21):
        sw=float(weights[wi].sum())
        per_wave.append(float(np.sqrt(np.sum(weights[wi]*phase[wi]**2)/sw)) if sw>0 else None)
    valid=(amp_n>1e-30)&(amp_f>1e-30)
    uw=np.where(valid,amp_n,0)
    unmasked=float(np.sqrt(np.sum(uw*phase**2)/max(float(uw.sum()),1e-30)))
    amp_abs=np.abs(amp_f-amp_n)
    amp_rel=_relative(amp_n,amp_f)

    dirs={}
    for p,c,ii in ((inp.near,near_s,idx),(inp.far,far_s,idx)):
        d={}
        for di,name in enumerate(DIRECTIONS):
            pw=np.sum(np.asarray(p.mode_power_z_per_abs_e2)[:,ii,di,:]*np.abs(c[:,ii,di,:])**2,axis=-1)
            d[name]={"signed_per_order":pw.tolist(),"signed_total_by_wavelength":pw.sum(axis=1).tolist()}
        dirs[p.name]=d
    set_main=set(ORDER_MN)
    extra_mask=np.asarray(inp.near.propagating_mask,bool)[:,[j for j,o in enumerate(np.asarray(inp.near.orders_mn,int)) if tuple(o) not in set_main]]
    if extra_mask.size and np.any(extra_mask):
        raise ValueError("unexpected_additional_propagating_orders_outside_frozen_seven_order_state")
    evan=[]
    orders=np.asarray(inp.near.orders_mn,int)
    for j,row in enumerate(orders.tolist()):
        order=tuple(row)
        if order in set_main or np.asarray(inp.near.propagating_mask,bool)[:,j].all(): continue
        kz=np.asarray(inp.near.mode_kz_rad_m)[:,j]
        fj=oi[order]
        for di,direction in enumerate(DIRECTIONS):
            sign=1 if direction=="+z" else -1
            pred=near_s[:,j,di,:]*np.exp(sign*1j*kz*(inp.far.z_sample_m-inp.near.z_sample_m))[:,None]
            obs=far_s[:,fj,di,:]
            near_amp=np.linalg.norm(near_s[:,j,di,:],axis=-1)
            far_amp=np.linalg.norm(obs,axis=-1)
            observed_ratio=[None if a<=1e-30 else float(b/a) for a,b in zip(near_amp,far_amp)]
            predicted_ratio=np.abs(np.exp(sign*1j*kz*(inp.far.z_sample_m-inp.near.z_sample_m)))
            evan.append({"order_mn":list(order),"direction":direction,
                         "continuous_kz_near_to_far_relative_l2":float(np.linalg.norm(obs-pred)/max(float(np.linalg.norm(pred)),1e-30)),
                         "observed_amplitude_ratio_by_wavelength":observed_ratio,
                         "continuous_kz_predicted_amplitude_ratio_by_wavelength":predicted_ratio.tolist(),
                         "threshold_applied":False,"far_field_power_assigned":False})
    raw_n,raw_f=_raw_diagnostics(inp.near,inp),_raw_diagnostics(inp.far,inp)
    missing=[]
    for p, raw in ((inp.near, raw_n), (inp.far, raw_f)):
        if not raw["available"]:
            missing.extend(p.name + "." + item for item in raw["missing"])
        else:
            missing.extend(raw["least_squares"]["missing"])
    if not evan: missing.append("evanescent_order_coefficients_and_fit_diagnostic")
    ls={inp.near.name:raw_n["least_squares"],inp.far.name:raw_f["least_squares"]}
    per_coord=[]
    for wi,wav in enumerate(WAVELENGTHS_NM):
        for oi2,order in enumerate(ORDER_MN):
            for pi,pol in enumerate(POLARIZATIONS):
                cn,cf=n[wi,oi2,pi],f[wi,oi2,pi]
                cs,fs=near_s[wi,idx[oi2],0,pi],far_s[wi,idx[oi2],0,pi]
                per_coord.append({"wavelength_nm":wav,"order_mn":list(order),"direction":"+z","polarization":pol,
                    "near_sample":[float(cs.real),float(cs.imag)],"far_sample":[float(fs.real),float(fs.imag)],
                    "sample_complex_difference":[float((fs-cs).real),float((fs-cs).imag)],
                    "sample_amplitude_near":float(abs(cs)),"sample_amplitude_far":float(abs(fs)),
                    "sample_phase_difference_rad":None if abs(cs)<=1e-30 or abs(fs)<=1e-30 else float(np.angle(fs*np.conj(cs))),
                    "near_reference":[float(cn.real),float(cn.imag)],"far_reference":[float(cf.real),float(cf.imag)],
                    "reference_complex_difference":[float((cf-cn).real),float((cf-cn).imag)],
                    "amplitude_near":float(abs(cn)),"amplitude_far":float(abs(cf)),
                    "amplitude_absolute_difference":float(amp_abs[wi,oi2,pi]),
                    "amplitude_relative_difference":float(amp_rel[wi,oi2,pi]) if np.isfinite(amp_rel[wi,oi2,pi]) else None,
                    "phase_difference_rad":None if abs(cn)<=1e-30 or abs(cf)<=1e-30 else float(phase[wi,oi2,pi]),
                    "near_power_share":float(share[wi,oi2,pi]),"significant_mask":bool(mask[wi,oi2,pi])})
    state_max=float(np.max(state)); route_max=float(np.max(route_diff)); abs_max=float(np.max(abs_diff)); total_max=float(np.max(total_rel))
    metrics={
        "propagating_state_relative_l2_by_wavelength":state.tolist(),"propagating_state_relative_l2_max":state_max,
        "routing_max_abs_difference":route_max,"routing_max_abs_difference_by_wavelength":np.max(route_diff,axis=1).tolist(),
        "source_normalized_absolute_order_max_abs_difference":abs_max,"source_normalized_absolute_order_max_abs_difference_by_wavelength":np.max(abs_diff,axis=1).tolist(),
        "propagating_total_power_relative_difference_by_wavelength":total_rel.tolist(),"propagating_total_power_relative_difference_max":total_max,
        "significant_coordinate_amplitude_weighted_phase_rmse_rad":phase_rmse,
        "significant_coordinate_amplitude_weighted_phase_rmse_by_wavelength_rad":per_wave,
        "significant_coordinate_count_by_wavelength":mask.sum(axis=(1,2)).astype(int).tolist(),
        "unmasked_amplitude_weighted_phase_rmse_rad":unmasked,
        "amplitude_absolute_difference_max":float(np.max(amp_abs)),
        "amplitude_relative_difference_max":float(np.max(amp_rel[np.isfinite(amp_rel)])) if np.isfinite(amp_rel).any() else None,
        "amplitude_relative_difference_undefined_count":int(np.count_nonzero(~np.isfinite(amp_rel))),
        "near_source_normalized_power_by_order":npow.tolist(),"far_source_normalized_power_by_order":fpow.tolist(),
        "near_routing_by_order":nr.tolist(),"far_routing_by_order":fr.tolist(),
        "near_transmitted_total_power_by_wavelength":nt.tolist(),"far_transmitted_total_power_by_wavelength":ft.tolist()}
    thresholds={
        "propagating_state_relative_l2":{"value":state_max,"max":STATE_REL_L2_MAX,"pass":state_max<=STATE_REL_L2_MAX},
        "routing_max_abs_difference":{"value":route_max,"max":ROUTING_MAX_ABS,"pass":route_max<=ROUTING_MAX_ABS},
        "source_normalized_absolute_order_max_abs_difference":{"value":abs_max,"max":ABSOLUTE_ORDER_MAX_ABS,"pass":abs_max<=ABSOLUTE_ORDER_MAX_ABS},
        "propagating_total_power_relative_difference":{"value":total_max,"max":TOTAL_POWER_REL_MAX,"pass":total_max<=TOTAL_POWER_REL_MAX},
        "significant_coordinate_amplitude_weighted_phase_rmse_rad":{"value":phase_rmse,"max":SIGNIFICANT_PHASE_RMSE_MAX_RAD,"pass":bool(np.isfinite(phase_rmse) and phase_rmse<=SIGNIFICANT_PHASE_RMSE_MAX_RAD)}}
    ready=not missing
    if not ready:
        for item in thresholds.values():
            item["numerical_value_available_from_coefficients"]=item["value"]
            item["pass"]=None
    allpass=ready and all(x["pass"] for x in thresholds.values())
    poynting={}
    for p,raw in ((inp.near,raw_n),(inp.far,raw_f)):
        if raw["available"]:
            modal=np.asarray(dirs[p.name]["+z"]["signed_total_by_wavelength"])+np.asarray(dirs[p.name]["-z"]["signed_total_by_wavelength"])
            py=np.asarray(raw["poynting_normalized"])
            poynting[p.name]={"modal_net_normalized":modal.tolist(),"poynting_normalized":py.tolist(),"absolute_difference":(py-modal).tolist()}
        else: poynting[p.name]=None
    return {
        "schema":"COUPLING_ML_EXT02_TWO_AIR_PLANES_EVALUATION_V1","scope":"single_case_cross_height_consistency_only",
        "case_id":inp.case_id,"attempt_id":inp.attempt_id,"extractor_sha256":inp.extractor_sha256,"protocol_sha256":inp.protocol_sha256,
        "reference_plane_nm":float(inp.reference_plane_nm),"phase_alignment":"none","fitted_power_scale":False,"normalization":inp.normalization,
        "sample_planes":{"near":{"name":inp.near.name,"actual_z_nm":inp.near.z_sample_m*1e9,"nominal_z_nm":1800.0},
                         "far":{"name":inp.far.name,"actual_z_nm":inp.far.z_sample_m*1e9,"nominal_z_nm":2000.0},
                         "separation_nm":(inp.far.z_sample_m-inp.near.z_sample_m)*1e9,
                         "deembedding":{"+z":"c_ref=c_sample*exp(+1j*kz*(1722nm-z_actual))","-z":"c_ref=c_sample*exp(-1j*kz*(1722nm-z_actual))"}},
        "metrics":metrics,"thresholds":thresholds,
        "threshold_attainment":"NOT_AVAILABLE_REQUIRED_DIAGNOSTICS_MISSING" if not ready else "NUMERICAL_THRESHOLDS_MET" if allpass else "NUMERICAL_THRESHOLDS_NOT_MET",
        "evaluation_readiness":"READY" if ready else "INCOMPLETE_REQUIRED_DIAGNOSTICS",
        "missing_required_diagnostics":missing,"least_squares_and_conditioning":ls,
        "periodic_endpoint_and_independent_poynting":{"near":raw_n,"far":raw_f,"poynting_vs_modal_net_by_wavelength":poynting,
            "quadrature":"actual-coordinate trapezoid; inclusive endpoints receive half-interval weights"},
         "directionality":{"modal_power_by_plane":dirs,"minus_z_deembedded_complex_state_relative_l2_by_wavelength":down_state.tolist(),"phase_alignment":"none"},"evanescent":evan,"per_coordinate":per_coord,
        "overall_result":"INCOMPLETE_REQUIRED_DIAGNOSTICS" if not ready else "CONSISTENCY_THRESHOLDS_MET" if allpass else "CONSISTENCY_THRESHOLDS_NOT_MET",
        "limitations":["one-case inter-plane consistency only; not absolute convergence, repeatability, full-dataset label validity, H1, or production admission",
            "continuous-medium kz de-embedding approximates FDTD numerical dispersion; report local mesh spacing",
            "evanescent channels are diagnostic only; no far-field power or propagating-state threshold"]}
