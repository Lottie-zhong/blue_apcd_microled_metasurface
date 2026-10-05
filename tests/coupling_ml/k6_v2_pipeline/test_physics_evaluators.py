from dataclasses import replace
import numpy as np
import pytest

from scripts.coupling_ml.k6_v2_pipeline import contracts as C
from scripts.coupling_ml.k6_v2_pipeline.contracts import (
    CaseTruth, ROLE_OLD32, ROLE_LOCAL_AXIS, WAVELENGTHS_NM,
    STATE_SCHEMA, TWO_PLANE_CASE_ID, TWO_PLANE_ATTEMPT_ID,
    TWO_PLANE_PROTOCOL_SHA256, pack_model_target,
)
from scripts.coupling_ml.k6_v2_pipeline.local_affine import (
    S31_ANCHOR_NM, evaluate_local_affine_loo,
)
from scripts.coupling_ml.k6_v2_pipeline.evaluators import (
    ENDPOINT_RULE, OFFICIAL_EXTRACTOR_SHA256, PERIOD_X_M, PERIOD_Y_M,
    PROJECTION_NAME, SOURCE_NORMALIZATION, PlaneProjection, TwoPlaneInput,
    evaluate_two_plane_consistency,
)
from scripts.shared_fdtd.tools import pw_complex_floquet_state_v1 as official


def _synthetic_truth_provenance(role):
    if role == ROLE_OLD32:
        return {"dataset_npz_sha256":"fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28",
                "dataset_authority_sha256":C.DATASET_AUTHORITY_SHA256,
                "state_sha256":"a"*64,"synthetic_test_only":True}
    return {"source_manifest_sha256":"a"*64,"state_npz_sha256":"b"*64,
            "state_metadata_sha256":"c"*64,"raw_npz_sha256":"d"*64,
            "raw_metadata_sha256":"e"*64,"orders_sha256":"f"*64,
            "physical_contract_sha256":C.PHYSICAL_CONTRACT_SHA256,
            "truth_extractor_sha256":C.H1_EVALUATOR_SOURCE_SHA256,
            "reference_plane_nm":C.REFERENCE_PLANE_NM,
            "normalization":C.PSCALE_DEFINITION,"truth_schema":C.STATE_SCHEMA,
            "synthetic_test_only":True}


def _synthetic_local_cases():
    rng = np.random.default_rng(3411)
    waves = np.asarray(WAVELENGTHS_NM, dtype=float)
    base = (0.6 + np.arange(21*7*2).reshape(21,7,2)/900) + 1j*(0.3 + np.arange(21*7*2).reshape(21,7,2)/1100)
    slopes = rng.normal(0, 0.0005, size=(6,21,7,2)) + 1j*rng.normal(0, 0.0004, size=(6,21,7,2))
    logp0 = np.linspace(-0.25,0.15,21)
    logp_slope = rng.normal(0,0.0003,size=(6,21))
    def make(case_id, role, geom):
        delta=np.asarray(geom,dtype=float)-np.asarray(S31_ANCHOR_NM,dtype=float)
        c=base+np.tensordot(delta,slopes,axes=(0,0))
        p=np.exp(logp0+np.tensordot(delta,logp_slope,axes=(0,0)))
        return CaseTruth(case_id, "attempt_001", role, tuple(int(x) for x in geom), c, p,
                         np.ones((21,7)), np.ones((21,7)), _synthetic_truth_provenance(role))
    anchor=make("S31",ROLE_OLD32,S31_ANCHOR_NM)
    axial=[]
    for axis in range(6):
        for sign in (-1,1):
            geom=list(S31_ANCHOR_NM); geom[axis]+=5*sign
            axial.append(make(f"AXIS_D{axis+1}_{'P' if sign>0 else 'M'}05",ROLE_LOCAL_AXIS,geom))
    return anchor,axial


def test_local_affine_twelve_loo_and_final_fit_are_train_only():
    anchor,axial=_synthetic_local_cases()
    result=evaluate_local_affine_loo(anchor,axial)
    assert len(result.folds)==12
    assert len(result.final_fit.fit_case_ids)==13
    assert result.final_fit.design_rank==7
    for fold in result.folds:
        assert len(fold.train_case_ids)==12
        assert fold.held_out_case_id not in fold.train_case_ids
        train=[anchor]+[c for c in axial if c.case_id in fold.train_case_ids]
        x=np.asarray([c.ordered_D_nm for c in train],float)
        assert np.allclose(fold.fit.feature_mean_nm,x.mean(axis=0))
        packed=np.concatenate([pack_model_target(c.c_hat,c.p_scale) for c in train],axis=0)
        assert np.allclose(fold.fit.target_mean,packed.mean(axis=0))
        assert fold.state_relative_l2<1e-9
        assert fold.p_scale_relative_l2<1e-9


def test_local_affine_rejects_confirmation_role():
    anchor,axial=_synthetic_local_cases()
    axial[0]=replace(axial[0],role="SEALED_LOCAL_COMBINATION")
    with pytest.raises(ValueError):
        evaluate_local_affine_loo(anchor,axial)


_SOURCE_INCIDENT_AMPLITUDE = 0.55 - 0.07j


def _synthetic_amplitudes():
    return {
        (0,0,1,"TE"):0.43+0.11j,
        (0,0,1,"TM"):_SOURCE_INCIDENT_AMPLITUDE,
        (1,0,1,"TE"):0.16+0.035j,
        (-1,0,1,"TM"):0.10-0.04j,
        (4,0,1,"TE"):0.20+0.03j,
        (-1,0,-1,"TE"):0.06+0.01j,
    }


def _plane(name,z_nm,amplitudes,nonmodal_ez=0.0):
    wavelengths=np.asarray(WAVELENGTHS_NM,dtype=float)
    orders=tuple((m,0) for m in range(-4,5))
    raw=official._synthetic_raw(65,17,z_nm*1e-9,1+0j,amplitudes,wavelengths)
    if nonmodal_ez:
        raw["Ez"][:,:,0,10] += complex(nonmodal_ez)
    proj=official._plane_projection(raw,np.ones(21,dtype=complex),orders=orders,z_reference_nm=None)
    fields,axes=official.canonicalize_plane_raw(raw)
    fields={name:value[:,:,np.asarray(proj["frequency_order"],dtype=int)] for name,value in fields.items()}
    incident_power_per_mode=np.asarray([
        official._mode(0,0,float(w),1+0j,1,"TM")["power_z_per_abs_e2"]
        for w in wavelengths
    ],float)
    pin=incident_power_per_mode*abs(_SOURCE_INCIDENT_AMPLITUDE)**2
    gauge=np.full(21,-np.angle(_SOURCE_INCIDENT_AMPLITUDE),dtype=float)
    norm_coeff=np.asarray(proj["coefficients"],complex)*(np.exp(1j*gauge)/np.sqrt(pin))[:,None,None,None]
    return PlaneProjection(
        name=name,z_sample_m=float(axes["z_sample_m"]),z_reference_m=float(axes["z_sample_m"]),
        wavelengths_nm=np.asarray(proj["wavelengths_nm"]),orders_mn=np.asarray(proj["orders"]),
        directions=("+z","-z"),polarizations=("TE","TM"),coefficients=norm_coeff,
        mode_kz_rad_m=np.asarray(proj["mode_kz_rad_m"]),mode_power_z_per_abs_e2=np.asarray(proj["mode_power_z_per_abs_e2"]),
        propagating_mask=np.asarray(proj["propagating_mask"]),basis_condition=np.asarray(proj["basis_condition"]),
        local_index=np.ones(21,dtype=complex),axis_contract=proj["axis_contract"],
        x_m=axes["x_m"],y_m=axes["y_m"],raw_fields=fields,
    ),pin


def _two_plane_input():
    amps=_synthetic_amplitudes()
    near,pin=_plane("POSTNP",1801.9999999999932,amps)
    far,_=_plane("EXT02_POSTNP_DIAG_Z2000",2000.0,amps)
    return TwoPlaneInput(
        case_id=TWO_PLANE_CASE_ID,attempt_id=TWO_PLANE_ATTEMPT_ID,state_schema=STATE_SCHEMA,
        extractor_sha256=OFFICIAL_EXTRACTOR_SHA256,protocol_sha256=TWO_PLANE_PROTOCOL_SHA256,
        normalization=SOURCE_NORMALIZATION,reference_plane_nm=1722.0,
        period_x_m=PERIOD_X_M,period_y_m=PERIOD_Y_M,incident_power_per_area=pin,
        near=near,far=far,provenance_sha256={"near_raw":"a"*64,"far_raw":"b"*64,"manifest":"c"*64},
        source_gauge_phase_rad=np.full(21,-np.angle(_SOURCE_INCIDENT_AMPLITUDE),dtype=float),
    )


def test_exact_complex_propagation_deembeds_and_reports_independent_checks():
    result=evaluate_two_plane_consistency(_two_plane_input())
    assert result["overall_result"]=="CONSISTENCY_THRESHOLDS_MET"
    assert result["evaluation_readiness"]=="READY"
    assert result["phase_alignment"]=="none"
    assert result["fitted_power_scale"] is False
    assert result["sample_planes"]["near"]["actual_z_nm"]==pytest.approx(1802.0)
    assert result["sample_planes"]["far"]["actual_z_nm"]==pytest.approx(2000.0)
    assert result["metrics"]["propagating_state_relative_l2_max"]<1e-9
    assert max(result["directionality"]["minus_z_deembedded_complex_state_relative_l2_by_wavelength"])<1e-9
    assert result["periodic_endpoint_and_independent_poynting"]["quadrature"].startswith("actual-coordinate trapezoid")
    assert result["periodic_endpoint_and_independent_poynting"]["near"]["endpoint_closure"]["max_relative_mismatch"]<1e-10
    assert result["evanescent"] and all(not row["far_field_power_assigned"] for row in result["evanescent"])
    assert len(result["per_coordinate"])==21*7*2


def test_oracle_phase_alignment_is_not_applied_and_threshold_fails():
    inp=_two_plane_input()
    amps=_synthetic_amplitudes()
    amps[(0,0,1,"TE")]*=np.exp(1j*0.11)
    far,_=_plane("EXT02_POSTNP_DIAG_Z2000",2000.0,amps)
    result=evaluate_two_plane_consistency(replace(inp,far=far))
    assert result["phase_alignment"]=="none"
    assert 0.05 < result["metrics"]["significant_coordinate_amplitude_weighted_phase_rmse_rad"] < 0.08
    assert not result["thresholds"]["significant_coordinate_amplitude_weighted_phase_rmse_rad"]["pass"]
    assert not result["thresholds"]["propagating_state_relative_l2"]["pass"]


def test_power_and_routing_deviations_trigger_their_own_thresholds():
    inp=_two_plane_input()
    amps=_synthetic_amplitudes()
    for key in list(amps):
        m,n,direction,pol=key
        if direction==1 and -3 <= m <= 3:
            amps[key]*=np.sqrt(1.02)
    scaled_far,_=_plane("EXT02_POSTNP_DIAG_Z2000",2000.0,amps)
    power_result=evaluate_two_plane_consistency(replace(inp,far=scaled_far))
    assert power_result["metrics"]["propagating_total_power_relative_difference_max"]==pytest.approx(0.02,abs=1e-10)
    assert not power_result["thresholds"]["propagating_total_power_relative_difference"]["pass"]
    assert power_result["metrics"]["routing_max_abs_difference"]<1e-12

    routed_amps=_synthetic_amplitudes()
    routed_amps[(1,0,1,"TE")]*=2.0
    routed_far,_=_plane("EXT02_POSTNP_DIAG_Z2000",2000.0,routed_amps)
    routing_result=evaluate_two_plane_consistency(replace(inp,far=routed_far))
    assert routing_result["metrics"]["routing_max_abs_difference"]>0.005
    assert not routing_result["thresholds"]["routing_max_abs_difference"]["pass"]


def test_raw_field_fit_rank_residual_and_official_coefficient_parity_are_recomputed():
    result=evaluate_two_plane_consistency(_two_plane_input())
    fit=result["least_squares_and_conditioning"]["POSTNP"]
    assert fit["available"]
    assert fit["official_source_sha256_verified"]==OFFICIAL_EXTRACTOR_SHA256
    assert fit["full_rank_4"]
    assert fit["trapezoid_weights_source"]=="pinned pw_complex_floquet_state_v1._trap_weights"
    assert np.all(np.asarray(fit["rank_by_wavelength_order"])==4)
    assert np.max(fit["residual_absolute_by_wavelength_order"])<1e-12
    assert np.max(fit["residual_relative_to_max_sampled_vector_by_wavelength_order"])<1e-12
    parity=fit["official_coefficients_parity"]
    assert parity["matches_within_floating_point_tolerance"]
    assert parity["max_abs_difference"]<1e-12


def test_missing_raw_fields_remain_incomplete_instead_of_claiming_fit_pass():
    inp=_two_plane_input()
    incomplete=replace(inp,near=replace(inp.near,raw_fields=None,x_m=None,y_m=None))
    result=evaluate_two_plane_consistency(incomplete)
    assert result["threshold_attainment"]=="NOT_AVAILABLE_REQUIRED_DIAGNOSTICS_MISSING"
    assert result["evaluation_readiness"]=="INCOMPLETE_REQUIRED_DIAGNOSTICS"
    assert result["overall_result"]=="INCOMPLETE_REQUIRED_DIAGNOSTICS"
    assert any("actual_x_y_coordinates_and_six_raw_EH_fields" in x for x in result["missing_required_diagnostics"])


def test_nonmodal_raw_field_component_produces_nonzero_fit_residual():
    inp=_two_plane_input()
    far,_=_plane("EXT02_POSTNP_DIAG_Z2000",2000.0,_synthetic_amplitudes(),nonmodal_ez=0.2)
    result=evaluate_two_plane_consistency(replace(inp,far=far))
    fit=result["least_squares_and_conditioning"]["EXT02_POSTNP_DIAG_Z2000"]
    assert max(map(max,fit["residual_absolute_by_wavelength_order"]))>1e-4
    assert fit["official_coefficients_parity"]["matches_within_floating_point_tolerance"]


def test_rank_deficient_basis_is_reported_incomplete(monkeypatch):
    inp=_two_plane_input()
    original=official._mode
    def degenerate_mode(*args,**kwargs):
        mode=original(*args,**kwargs)
        mode["e_hat"]=np.asarray([1,0,0],dtype=complex)
        mode["h_hat"]=np.asarray([0,1,0],dtype=complex)
        return mode
    monkeypatch.setattr(official,"_mode",degenerate_mode)
    result=evaluate_two_plane_consistency(inp)
    fit=result["least_squares_and_conditioning"]["POSTNP"]
    assert not fit["full_rank_4"]
    assert np.any(np.asarray(fit["rank_by_wavelength_order"])<4)
    assert result["evaluation_readiness"]=="INCOMPLETE_REQUIRED_DIAGNOSTICS"
    assert any("full_rank_4_recomputed_from_raw" in x for x in result["missing_required_diagnostics"])


def test_rejects_wrong_reference_and_extractor_provenance():
    inp=_two_plane_input()
    bad_plane=replace(inp.near,z_reference_m=1722e-9)
    with pytest.raises(ValueError,match="sample_plane_coefficients"):
        evaluate_two_plane_consistency(replace(inp,near=bad_plane))
    with pytest.raises(ValueError,match="extractor_sha256"):
        evaluate_two_plane_consistency(replace(inp,extractor_sha256="0"*64))
