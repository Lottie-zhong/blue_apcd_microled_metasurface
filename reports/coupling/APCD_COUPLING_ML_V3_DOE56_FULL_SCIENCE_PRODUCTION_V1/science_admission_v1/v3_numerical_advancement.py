"""V3 preregistered comparison; no solver, fitting, or sealed-response loader."""
from pathlib import Path
import hashlib
import numpy as np

LIMITS = {'state_relative_l2': .02, 'routing_max_abs': .005,
          'absolute_order_max_abs': .005, 'total_power_relative': .01,
          'significant_phase_rmse_rad': .05}
EXPECTED = {'K6V3_NUM_REPEAT_A1': ('K6GDP2_DEV_G001', 5),
            'K6V3_NUM_REPEAT_A2': ('K6GDP2_DEV_G004', 5),
            'K6V3_NUM_MESH4_A1': ('K6GDP2_DEV_G001', 4),
            'K6V3_NUM_MESH4_A2': ('K6GDP2_DEV_G004', 4)}
ANCHORS = {'K6GDP2_DEV_G001': [120,160,165,175,160,195],
           'K6GDP2_DEV_G004': [210,115,175,115,180,125]}

def _state(c, p):
    c, p = np.asarray(c, complex), np.asarray(p, float)
    if c.shape != (21,7,2) or p.shape != (21,):
        raise ValueError('state_shape')
    if not (np.isfinite(c).all() and np.isfinite(p).all() and (p>0).all()):
        raise ValueError('nonfinite_or_nonpositive')
    if (np.sum(abs(c)**2,axis=(1,2))<=0).any():
        raise ValueError('zero_state_energy')
    return c,p

def compare_arrays(base_c, base_p, candidate_c, candidate_p, *, decode):
    """Caller must verify provenance before any advancement receipt is accepted."""
    a,p = _state(base_c,base_p); b,q = _state(candidate_c,candidate_p)
    sq=abs(a)**2; energy=sq.sum((1,2)); mask=sq/energy[:,None,None]>=1e-4
    # Undefined candidate phase in a significant base channel is a hard HOLD.
    if ((abs(b)==0)&mask).any():
        raise ValueError('undefined_significant_candidate_phase')
    delta=np.angle(b*np.conj(a))
    phase=np.sqrt((sq*mask*delta**2).sum((1,2))/(sq*mask).sum((1,2)))
    h0,h1=decode(a,p),decode(b,q)
    def view(h,k):
        v=np.asarray(h[k]);return v[0] if v.shape[0]==1 else v
    values={'state_relative_l2':np.sqrt((abs(b-a)**2).sum((1,2))/energy),
            'routing_max_abs':abs(view(h1,'eta')-view(h0,'eta')).max(1),
            'absolute_order_max_abs':abs(view(h1,'absolute_order')-view(h0,'absolute_order')).max(1),
            'total_power_relative':abs(view(h1,'total_power')-view(h0,'total_power'))/view(h0,'total_power'),
            'significant_phase_rmse_rad':phase}
    if any(v.shape!=(21,) or not np.isfinite(v).all() for v in values.values()):
        raise ValueError('decoded_metric_invalid')
    gates={k:bool((v<=LIMITS[k]).all()) for k,v in values.items()}
    return {'comparison_pass':all(gates.values()),'gates':gates,
            'per_wavelength':{k:v.tolist() for k,v in values.items()},
            'maxima':{k:float(v.max()) for k,v in values.items()},
            'amplitude_relative_l2_per_wavelength':(np.sqrt(((abs(b)-abs(a))**2).sum((1,2))/energy)).tolist(),
            'all_coordinate_phase_rmse_per_wavelength':np.sqrt((sq*delta**2).sum((1,2))/energy).tolist(),
            'order_complex_squared_error':(abs(b-a)**2).sum((0,2)).tolist(),
            'polarization_complex_squared_error':(abs(b-a)**2).sum((0,1)).tolist(),
            'significant_mask_count_per_wavelength':mask.sum((1,2)).tolist(),
            'oracle_alignment':False,'h1_admission':False}

def verify_pair_identity(base, candidate):
    cid=candidate['case_id']
    if cid not in EXPECTED:raise ValueError('non_diagnostic_identity')
    bid,mesh=EXPECTED[cid]
    if base['case_id']!=bid or candidate['attempt_id']!='attempt_001':
        raise ValueError('case_attempt_mismatch')
    for x in [base,candidate]:
        if list(x['ordered_D_nm'])!=ANCHORS[bid]:raise ValueError('geometry_mismatch')
        if x['wavelengths_nm']!=list(range(440,461)) or x['orders_m']!=list(range(-3,4)) or x['polarizations']!=['TE','TM']:
            raise ValueError('coordinate_order_mismatch')
        if x['reference_plane_nm']!=1722 or x['normalization']!='incident_+z_(0,0)_TM_power_at_IN_REF':
            raise ValueError('reference_normalization_mismatch')
        for k in ['label_sha256','truth_sha256','contract_sha256','fresh_load_receipt_sha256']:
            v=x[k]
            if not isinstance(v,str) or len(v)!=64 or any(z not in '0123456789abcdef' for z in v):raise ValueError('invalid_sha:'+k)
        if not x['truth_valid'] or not x['six_component_eh_valid']:raise ValueError('incomplete_truth')
    if base['mesh_nm']!=5 or candidate['mesh_nm']!=mesh:raise ValueError('mesh_identity')
    if candidate['solver_entry_count']!=1 or candidate['replay_count']!=0:raise ValueError('entry_replay')
    if mesh==4 and base['contract_sha256']==candidate['contract_sha256']:raise ValueError('mesh_contract_not_distinct')
    if mesh==5 and base['contract_sha256']!=candidate['contract_sha256']:raise ValueError('repeat_contract_changed')
    if not candidate['setup_contract_verified'] or not candidate['original_source_pins_verified']:
        raise ValueError('setup_or_source_unverified')
    return True

def advancement(results, protocol_sha256):
    """Four independent comparisons, never pool or bypass a failed diagnostic."""
    if set(results)!=set(EXPECTED):raise ValueError('four_diagnostics_required')
    for cid,r in results.items():
        if r.get('case_id')!=cid or not r.get('pair_identity_verified') or not r.get('durable_receipts_verified'):
            raise ValueError('unverified_diagnostic_receipt')
        if r.get('protocol_sha256')!=protocol_sha256:raise ValueError('protocol_binding')
    passed=all(r['comparison']['comparison_pass'] for r in results.values())
    return {'status':'DIAGNOSTIC_ADVANCE_PASS' if passed else 'DIAGNOSTIC_HOLD',
            'advance_to_development':passed,'protocol_sha256':protocol_sha256,
            'independent_h1_admission':False,'replay_allowed':False}
