"""Train-only local affine diagnostic for frozen S31 +/-5nm axial DOE."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence, Tuple
import numpy as np
from .contracts import CaseTruth, DEVELOPMENT_ROLES, ROLE_LOCAL_AXIS, pack_model_target, unpack_model_target
S31_ANCHOR_NM=(220,195,210,150,140,210)
AXIS_STEP_NM=5.0
AXIAL_CASE_COUNT=12
OUTPUT_WIDTH=609

@dataclass(frozen=True)
class LocalAffinePrediction:
    c_hat: np.ndarray
    p_scale: np.ndarray

@dataclass(frozen=True)
class LocalAffineFit:
    feature_mean_nm: np.ndarray
    feature_scale_nm: np.ndarray
    target_mean: np.ndarray
    target_scale: np.ndarray
    coefficients_standardized: np.ndarray
    fit_case_ids: Tuple[str,...]
    design_rank: int
    sensitivity_per_nm: np.ndarray
    def predict(self, ordered_D_nm: Sequence[float])->LocalAffinePrediction:
        x=np.asarray(ordered_D_nm,dtype=float)
        if x.shape!=(6,) or not np.isfinite(x).all(): raise ValueError("ordered_D_nm_must_be_finite_length_6")
        xs=(x-self.feature_mean_nm)/self.feature_scale_nm
        design=np.concatenate(([1.0],xs))[None,:]
        target=(design@self.coefficients_standardized)*self.target_scale+self.target_mean
        c,p=unpack_model_target(target)
        return LocalAffinePrediction(c[0],p[0])

@dataclass(frozen=True)
class LocalAffineLOOFold:
    held_out_case_id: str
    train_case_ids: Tuple[str,...]
    fit: LocalAffineFit
    prediction: LocalAffinePrediction
    state_relative_l2: float
    p_scale_relative_l2: float

@dataclass(frozen=True)
class LocalAffineLOOReport:
    anchor_case_id: str
    folds: Tuple[LocalAffineLOOFold,...]
    final_fit: LocalAffineFit

def _validate_anchor(anchor:CaseTruth)->None:
    if anchor.role not in DEVELOPMENT_ROLES: raise ValueError("local_affine_anchor_must_be_development_case")
    if tuple(int(x) for x in anchor.ordered_D_nm)!=S31_ANCHOR_NM: raise ValueError("local_affine_anchor_must_be_frozen_S31_geometry")
    if not anchor.case_id: raise ValueError("local_affine_anchor_case_id_missing")

def _validate_axial_cases(anchor:CaseTruth,axial_cases:Sequence[CaseTruth])->Tuple[CaseTruth,...]:
    _validate_anchor(anchor)
    cases=tuple(axial_cases)
    if len(cases)!=AXIAL_CASE_COUNT: raise ValueError("local_affine_requires_exactly_12_axial_cases")
    ids=[anchor.case_id,*(c.case_id for c in cases)]
    geoms=[S31_ANCHOR_NM,*(tuple(c.ordered_D_nm) for c in cases)]
    if len(set(ids))!=13: raise ValueError("local_affine_case_ids_must_be_unique")
    if len(set(geoms))!=13: raise ValueError("local_affine_geometries_must_be_unique")
    expected={(a,s) for a in range(6) for s in (-1,1)}
    observed=set()
    for c in cases:
        if c.role!=ROLE_LOCAL_AXIS: raise ValueError(f"local_affine_axis_role_mismatch:{c.case_id}:{c.role}")
        if len(c.ordered_D_nm)!=6: raise ValueError(f"local_affine_geometry_length_invalid:{c.case_id}")
        delta=np.asarray(c.ordered_D_nm,float)-np.asarray(S31_ANCHOR_NM,float)
        changed=np.flatnonzero(np.abs(delta)>1e-9)
        if changed.size!=1: raise ValueError(f"local_affine_case_not_single_axis:{c.case_id}")
        axis=int(changed[0])
        if not np.isclose(abs(delta[axis]),AXIS_STEP_NM,rtol=0,atol=1e-9):
            raise ValueError(f"local_affine_axis_step_must_be_5nm:{c.case_id}")
        key=(axis,1 if delta[axis]>0 else -1)
        if key in observed: raise ValueError(f"local_affine_duplicate_axis_side:{axis}:{key[1]}")
        observed.add(key)
    if observed!=expected: raise ValueError("local_affine_requires_both_5nm_sides_for_each_ordered_coordinate")
    return cases

def _fit_train_cases(train_cases:Sequence[CaseTruth])->LocalAffineFit:
    cases=tuple(train_cases)
    if len(cases)<8: raise ValueError("local_affine_requires_anchor_and_at_least_7_axis_cases")
    ids=tuple(c.case_id for c in cases)
    if len(set(ids))!=len(ids): raise ValueError("local_affine_train_case_ids_must_be_unique")
    if any(c.role not in DEVELOPMENT_ROLES for c in cases): raise ValueError("local_affine_training_accepts_development_roles_only")
    x=np.asarray([c.ordered_D_nm for c in cases],float)
    if x.shape!=(len(cases),6) or not np.isfinite(x).all(): raise ValueError("local_affine_train_geometry_invalid")
    y=np.asarray([pack_model_target(c.c_hat,c.p_scale)[0] for c in cases],float)
    if y.shape!=(len(cases),OUTPUT_WIDTH) or not np.isfinite(y).all(): raise ValueError("local_affine_train_target_invalid")
    # Input and output transforms are refit from this fold's training cases only.
    xm=x.mean(axis=0); xs=x.std(axis=0,ddof=0)
    if np.any(~np.isfinite(xs)) or np.any(xs<=0): raise ValueError("local_affine_train_feature_scale_zero_or_nonfinite")
    ym=y.mean(axis=0); ys=y.std(axis=0,ddof=0)
    if np.any(~np.isfinite(ys)): raise ValueError("local_affine_train_target_scale_nonfinite")
    ys=np.where(ys>0,ys,1.0)
    design=np.column_stack((np.ones(len(cases)),(x-xm)/xs))
    coefs,_,rank,_=np.linalg.lstsq(design,(y-ym)/ys,rcond=None)
    if int(rank)!=7: raise ValueError(f"local_affine_design_rank_must_be_7:{rank}")
    sensitivity=coefs[1:]*ys[None,:]/xs[:,None]
    return LocalAffineFit(xm,xs,ym,ys,coefs,ids,int(rank),sensitivity)

def fit_local_affine(anchor:CaseTruth,axial_cases:Sequence[CaseTruth])->LocalAffineFit:
    """Fit S31 plus all twelve frozen axial development responses."""
    return _fit_train_cases((anchor,*_validate_axial_cases(anchor,axial_cases)))

def evaluate_local_affine_loo(anchor:CaseTruth,axial_cases:Sequence[CaseTruth])->LocalAffineLOOReport:
    """Run 12 LOO folds; held-out response is accessed only after prediction."""
    cases=_validate_axial_cases(anchor,axial_cases)
    folds=[]
    for held in cases:
        train=(anchor,)+tuple(c for c in cases if c.case_id!=held.case_id)
        if len(train)!=12 or held.case_id in {c.case_id for c in train}:
            raise AssertionError("local_affine_loo_train_holdout_separation_failed")
        fit=_fit_train_cases(train)
        pred=fit.predict(held.ordered_D_nm)
        # Held-out labels are used only after prediction for diagnostic metrics.
        tc=np.asarray(held.c_hat,dtype=complex); tp=np.asarray(held.p_scale,dtype=float)
        if tc.shape!=(21,7,2) or tp.shape!=(21,): raise ValueError(f"local_affine_held_out_truth_shape_invalid:{held.case_id}")
        se=float(np.linalg.norm(pred.c_hat-tc)/max(float(np.linalg.norm(tc)),1e-30))
        pe=float(np.linalg.norm(pred.p_scale-tp)/max(float(np.linalg.norm(tp)),1e-30))
        if not np.isfinite(se) or not np.isfinite(pe): raise ValueError(f"local_affine_nonfinite_diagnostic:{held.case_id}")
        folds.append(LocalAffineLOOFold(held.case_id,fit.fit_case_ids,fit,pred,se,pe))
    if len(folds)!=12 or {f.held_out_case_id for f in folds}!={c.case_id for c in cases}:
        raise AssertionError("local_affine_loo_fold_coverage_failed")
    final=fit_local_affine(anchor,cases)
    return LocalAffineLOOReport(anchor.case_id,tuple(folds),final)
