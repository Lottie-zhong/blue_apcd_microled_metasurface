"""Zero-solver validator for the conservative NP K6 source scope freeze."""
import hashlib, json
from pathlib import Path

EXPECTED_PACKAGE = "0b7b45e838a0d73b92d63f8a45459bc46206677a91821fa474dacf4bd9028eaa"
EXPECTED_CANDIDATE = "NP_K6X_125_135_150_175_190_210"
EXPECTED_WAVELENGTHS = list(range(445, 456))

def _sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def validate(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    out = root / "outputs" / "np_k6_formal_source_scope_v1"
    errors=[]
    scope_path=out/"formal_source_scope_v1.json"
    handoff_path=out/"coupling_handoff_manifest_v1.json"
    if not scope_path.exists() or not handoff_path.exists(): return ["scope or handoff artifact missing"]
    scope=json.loads(scope_path.read_text(encoding='utf-8'))
    handoff=json.loads(handoff_path.read_text(encoding='utf-8'))
    if scope.get('state') != 'NP_SOURCE_SCOPE_FROZEN_CONSERVATIVE': errors.append('state')
    if scope.get('package_sha256') != EXPECTED_PACKAGE: errors.append('package sha')
    if scope.get('candidate_id') != EXPECTED_CANDIDATE: errors.append('candidate')
    if scope.get('wavelength_scope',{}).get('values_nm') != EXPECTED_WAVELENGTHS: errors.append('wavelength axis')
    ws=scope.get('wavelength_scope',{})
    if not ws.get('exact_points_only') or ws.get('interpolation') or ws.get('extrapolation'): errors.append('no extrapolation')
    kx=scope.get('kx_over_k0_scope',{})
    if kx.get('allowed_values') != [0.0] or not kx.get('normal_incidence_only'): errors.append('kx')
    pol=scope.get('polarization_scope',{})
    if pol.get('formally_validated') != ['x'] or pol.get('y_polarization') == 'VALIDATED': errors.append('polarization')
    if pol.get('xy_averaging') != 'NOT_JUSTIFIED': errors.append('averaging')
    if scope.get('interface_stack_scope',{}).get('final_mdc_joint_stack') != 'NOT_VALIDATED': errors.append('stack')
    if scope.get('use_scope',{}).get('normalized_scope_enum') != 'EXPLORATORY_ONLY': errors.append('use scope')
    ex=' '.join(scope.get('known_exclusions',[])).lower()
    for token in ['y-polarization','oblique','finite sio2','mdc-np','micro-led','no extrapolation']:
        if token not in ex: errors.append('missing exclusion '+token)
    for rel,h in scope.get('evidence_paths',{}).items():
        p=root/rel
        if not p.exists(): errors.append('missing evidence '+rel)
        elif _sha(p) != h: errors.append('evidence sha '+rel)
    if handoff.get('formal_scope_artifact_sha256') != _sha(scope_path): errors.append('handoff scope sha')
    if handoff.get('coupling_read_matrix',{}).get('quantitative_joint_power_prediction') != 'NOT_ALLOWED': errors.append('quantitative gate')
    zero=json.loads((out/'solver_zero_audit.json').read_text(encoding='utf-8'))
    if any(zero.get(k)!=0 for k in ['FDTD','RCWA','TMM','FEM','training','run_invocation','sealed_test_reads']): errors.append('solver zero')
    return errors

if __name__ == '__main__':
    e=validate()
    print(json.dumps({'status':'PASS' if not e else 'FAIL','errors':e}, indent=2))
    raise SystemExit(0 if not e else 1)
