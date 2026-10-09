"""Read-only dimensional bridge; Coupling keeps all scientific acceptance authority."""

import importlib.util
from pathlib import Path

import numpy as np

from .artifacts import sha256
from .config import CONTRACT_SHA
from .ledger import Refused


def validate_labels(c_hat, p_scale, *, role, physical_contract_sha256):
    if role not in {"DEVELOPMENT_GLOBAL", "DEVELOPMENT_LOCAL_AXIS", "OFFLINE_FIXTURE"}:
        raise Refused("SEALED_OR_UNKNOWN_ROLE")
    if physical_contract_sha256 != CONTRACT_SHA:
        raise Refused("LABEL_CONTRACT_MISMATCH")
    c, p = np.asarray(c_hat), np.asarray(p_scale)
    if c.shape != (21, 7, 2) or not np.iscomplexobj(c) or p.shape != (21,):
        raise Refused("LABEL_SHAPE_OR_COMPLEX_TYPE_MISMATCH")
    if not np.isfinite(c).all() or not np.isfinite(p).all() or (p <= 0).any():
        raise Refused("LABEL_NONFINITE_OR_NONPOSITIVE")
    target = np.concatenate((np.stack((c.real, c.imag), axis=-1).ravel(), np.log(p)))
    if target.shape != (609,):
        raise Refused("LABEL_OUTPUT_COUNT_MISMATCH")
    return {
        "shape": [21, 7, 2],
        "outputs": 609,
        "independent_p_scale": True,
        "scientific_validated": False,
        "offline_fixture": role == "OFFLINE_FIXTURE",
    }


def compare_consumer(contracts_path, expected_sha256, c_hat, p_scale, *, role):
    if role not in {"DEVELOPMENT_GLOBAL", "DEVELOPMENT_LOCAL_AXIS"}:
        raise Refused("CONSUMER_ROLE_FORBIDDEN")
    path = Path(contracts_path)
    if sha256(path) != expected_sha256:
        raise Refused("CONSUMER_SOURCE_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location(
        "apcd_v2_readonly_consumer_contract", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.PHYSICAL_CONTRACT_SHA256 != CONTRACT_SHA:
        raise Refused("CONSUMER_CONTRACT_MISMATCH")
    validate_labels(c_hat, p_scale, role=role, physical_contract_sha256=CONTRACT_SHA)
    packed = module.pack_model_target(c_hat, p_scale)
    recovered_c, recovered_p = module.unpack_model_target(packed)
    if not np.array_equal(recovered_c[0], c_hat) or not np.allclose(
        recovered_p[0], p_scale, rtol=1e-14
    ):
        raise Refused("CONSUMER_ROUNDTRIP_MISMATCH")
    return {
        "consumer_source_sha256": expected_sha256,
        "outputs": int(packed.shape[1]),
        "read_only": True,
        "full_importer_acceptance": False,
        "role": role,
    }
