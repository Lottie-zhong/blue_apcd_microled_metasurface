"""Shared frozen interfaces for the K6 V2 pipeline."""
from dataclasses import dataclass
from typing import Any, Mapping, Tuple
import numpy as np

PIPELINE_ID = "COUPLING_ML_K6_V2_TRAINING_AND_VALIDATION_PIPELINE_IMPLEMENTATION_V1"
STATE_SCHEMA = "PW_COMPLEX_FLOQUET_STATE_V1 POSTNP +z, seven y=0 orders, TE/TM"
WAVELENGTHS_NM = tuple(range(440, 461))
ORDER_MN = tuple((m, 0) for m in range(-3, 4))
ORDER_M = tuple(range(-3, 4))
POLARIZATIONS = ("TE", "TM")
DIRECTIONS = ("+z", "-z")
REFERENCE_PLANE_NM = 1722.0
PHYSICAL_CONTRACT_SHA256 = "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"
DATASET_AUTHORITY_SHA256 = "0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e"
GEOMETRY_AUTHORITY_SHA256 = "93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f"
H1_AUTHORITY_SHA256 = "8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd"
H2_DECODER_SHA256 = "b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15"
H1_EVALUATOR_SOURCE_SHA256 = "2bb4988e2324f09e4ee6710a0eb60fb38ac6e7e628c6c90a23d9a62766297416"
MODEL_SOURCE_SHA256 = "919471fce7d9d324947c9dfa4fc63e1ae7384061195f174d943879a745d6712f"
V2_BASE_PROTOCOL_SHA256 = "4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a"
V2_AMENDMENT_01_SHA256 = "124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a"
V2_CANDIDATE_CSV_SHA256 = "596bcc8fd7011cb5ec0c2fc93b9dfe26653ef74720d1bcd4872d3b22e18727c4"
V2_FOLD_MANIFEST_SHA256 = "309556978921717151716f20bbb80faf38e9d94bbbf52e27e6ff0a61d44a15ee"
V2_INNER_FOLD_MANIFEST_SHA256 = "ab8d7d1cf1dc1909b03d15cc43fda7d9a036c50fd66039eed66c6e1495936441"
V2_LEARNING_CURVE_MANIFEST_SHA256 = "2ad2282e6551520e32644e3335d167f2706dd6a3e250ac75d7358c47fb5706de"
TWO_PLANE_PROTOCOL_SHA256 = "fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8"
TWO_PLANE_CASE_ID = "K6V1_EXT02_TWO_AIR_PLANES_DIAG"
TWO_PLANE_ATTEMPT_ID = "attempt_001"

C_HAT_SHAPE = (21, 7, 2)
C_HAT_REAL_OUTPUTS = 588
P_SCALE_OUTPUTS = 21
MODEL_OUTPUTS = 609
ROLE_OLD32 = "DEVELOPMENT_OLD32"
ROLE_LOCAL_AXIS = "DEVELOPMENT_LOCAL_AXIS"
ROLE_GLOBAL_DEV = "DEVELOPMENT_GLOBAL"
ROLE_LOCAL_CONFIRM = "SEALED_LOCAL_COMBINATION"
ROLE_GLOBAL_CORE_CONFIRM = "SEALED_CONFIRMATION_GLOBAL"
ROLE_GLOBAL_STRESS_CONFIRM = "SEALED_CONFIRMATION_STRESS"
ROLE_DIAGNOSTIC = "DIAGNOSTIC_TWO_PLANE"
DEVELOPMENT_ROLES = frozenset((ROLE_OLD32, ROLE_LOCAL_AXIS, ROLE_GLOBAL_DEV))
CONFIRMATION_ROLES = frozenset((ROLE_LOCAL_CONFIRM, ROLE_GLOBAL_CORE_CONFIRM, ROLE_GLOBAL_STRESS_CONFIRM))
FORBIDDEN_TRAIN_ROLES = frozenset((ROLE_DIAGNOSTIC,)) | CONFIRMATION_ROLES
PSCALE_DEFINITION = "positive dimensionless POSTNP transmitted power: E/H trapezoidal Poynting integral / unit-cell area / incident power per area"
MODEL_TARGET_LAYOUT = "wavelength, m=-3..3, TE/TM, real then imaginary; 588 C_hat reals then 21 log(P_scale)"

@dataclass(frozen=True)
class CaseTruth:
    case_id: str
    attempt_id: str
    role: str
    ordered_D_nm: Tuple[int, int, int, int, int, int]
    c_hat: np.ndarray
    p_scale: np.ndarray
    eta: np.ndarray
    absolute_order: np.ndarray
    provenance: Mapping[str, Any]

@dataclass(frozen=True)
class CaseCollection:
    purpose: str
    cases: Tuple[CaseTruth, ...]
    manifest_sha256: str
    provenance: Mapping[str, Any]

    def training_cases(self) -> Tuple[CaseTruth, ...]:
        if self.purpose != "development":
            raise ValueError("training_entry_requires_development_collection")
        bad = [c.case_id for c in self.cases if c.role not in DEVELOPMENT_ROLES]
        if bad:
            raise ValueError("non_development_role_in_training_collection:" + ",".join(bad))
        return self.cases

def pack_model_target(c_hat: np.ndarray, p_scale: np.ndarray) -> np.ndarray:
    c = np.asarray(c_hat, dtype=np.complex128)
    p = np.asarray(p_scale, dtype=np.float64)
    if c.ndim == 3: c = c[None, ...]
    if p.ndim == 1: p = p[None, ...]
    if c.ndim != 4 or c.shape[1:] != C_HAT_SHAPE:
        raise ValueError("c_hat_shape_must_be_Nx21x7x2")
    if p.shape != (c.shape[0], 21):
        raise ValueError("p_scale_shape_must_be_Nx21")
    if not (np.isfinite(c.real).all() and np.isfinite(c.imag).all()):
        raise ValueError("c_hat_nonfinite")
    if not (np.isfinite(p).all() and (p > 0).all()):
        raise ValueError("p_scale_truth_must_be_finite_positive")
    cart = np.stack((c.real, c.imag), axis=-1).reshape(c.shape[0], C_HAT_REAL_OUTPUTS)
    with np.errstate(divide="raise", invalid="raise"):
        logp = np.log(p)
    y = np.concatenate((cart, logp), axis=1)
    if y.shape != (c.shape[0], MODEL_OUTPUTS) or not np.isfinite(y).all():
        raise ValueError("packed_target_invalid")
    return y

def unpack_model_target(target: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    y = np.asarray(target, dtype=np.float64)
    if y.ndim == 1: y = y[None, :]
    if y.ndim != 2 or y.shape[1] != MODEL_OUTPUTS or not np.isfinite(y).all():
        raise ValueError("model_output_must_be_finite_Nx609")
    v = y[:, :C_HAT_REAL_OUTPUTS].reshape((-1,) + C_HAT_SHAPE + (2,))
    c = v[..., 0] + 1j * v[..., 1]
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        p = np.exp(y[:, C_HAT_REAL_OUTPUTS:])
    if not (np.isfinite(p).all() and (p > 0).all()):
        raise ValueError("predicted_p_scale_exp_nonfinite_overflow_or_underflow")
    return c, p
