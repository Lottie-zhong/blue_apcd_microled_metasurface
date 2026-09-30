"""Runtime-only, deterministic NP LF feature adapter.

This is a power-level, single-pillar-DFT proxy.  It is not an HF predictor,
scattering matrix, complex/Jones provider, or FDTD replacement.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

PROVIDER_ID = "NP_LF_FEATURE_PROVIDER_V2"
INTERFACE_ID = "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V2"
DIAMETERS_NM = tuple(range(100, 231, 5))
WAVELENGTHS_NM = tuple(range(445, 456))
ORDERS = tuple(range(-3, 4))
PROPAGATING_ORDERS = (-1, 0, 1)
PITCH_NM = 290
HEIGHT_NM = 500
PERIOD_X_NM = 1740
PERIOD_Y_NM = 290
POSITIONS_NM = (-725, -435, -145, 145, 435, 725)
MATERIALS = ("APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1")
EXP = np.exp(-2j * np.pi * np.outer(np.asarray(ORDERS), np.arange(6)) / 6).astype(np.complex64)


class UnsupportedRequest(ValueError):
    """Raised for capability requests outside the frozen V2 contract."""

    def __init__(self, payload: Mapping[str, Any]):
        self.payload = dict(payload)
        super().__init__(self.payload["reason"])


def _root(root: str | os.PathLike[str] | None = None) -> Path:
    if root is not None:
        return Path(root).resolve()
    configured = os.environ.get("NP_K6_REPO_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def geometry_id(geometry: Sequence[float]) -> str:
    d = tuple(int(x) for x in geometry)
    return "K6X_" + "_".join(f"D{x}" for x in d)


def _geometry_hash(geometry: Sequence[int]) -> str:
    # Exact payload/hash convention from stage_np_k6_ml_d0_build_database_foundation.py.
    d = tuple(int(x) for x in geometry)
    payload = {
        "schema_version": "canonical_k6_geometry_v1",
        "geometry_id": geometry_id(d),
        "diameters_nm": list(d),
        "phase_bin_mapping": {
            "phase_bin": [0, 1, 2, 3, 4, 5],
            "x_nm": list(POSITIONS_NM),
            "ideal_phase_deg": [0, 60, 120, 180, 240, 300],
        },
        "period_x_nm": PERIOD_X_NM,
        "period_y_nm": PERIOD_Y_NM,
        "pillar_height_nm": HEIGHT_NM,
        "material_contract_ids": list(MATERIALS),
        "target_order": 1,
        "target_direction": "+x",
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _parse_geometry_id(value: str) -> tuple[int, ...]:
    if not value.startswith("K6X_"):
        raise ValueError(f"invalid K6 geometry identity: {value!r}")
    fields = value[4:].split("_")
    if len(fields) != 6 or any(not x.startswith("D") for x in fields):
        raise ValueError(f"invalid K6 geometry identity: {value!r}")
    out = tuple(int(x[1:]) for x in fields)
    if geometry_id(out) != value:
        raise ValueError(f"non-canonical K6 geometry identity: {value!r}")
    return out


def validate_geometry(geometry: Sequence[float]) -> tuple[int, ...]:
    if isinstance(geometry, (str, bytes)) or len(geometry) != 6:
        raise ValueError("ordered geometry must contain exactly D1..D6")
    out: list[int] = []
    for i, value in enumerate(geometry, start=1):
        if isinstance(value, bool):
            raise ValueError(f"D{i} must be a numeric diameter in nm")
        number = float(value)
        if not math.isfinite(number) or not number.is_integer():
            raise ValueError(f"D{i} must be an integer nm grid value")
        d = int(number)
        if d not in DIAMETERS_NM:
            raise ValueError(f"D{i}={d} is outside the frozen 100..230 nm, 5 nm grid")
        out.append(d)
    result = tuple(out)
    # No sorting/canonicalization: tuple order is the physical +x pillar order.
    gaps = tuple(PITCH_NM - (result[i] + result[(i + 1) % 6]) / 2 for i in range(6))
    if min(gaps) <= 0:
        raise ValueError("geometry violates the fixed-pitch non-overlap contract")
    return result


def canonical_polarization(polarization: str) -> str:
    if not isinstance(polarization, str):
        raise ValueError("polarization must be explicit P/XLIKE")
    key = polarization.strip().upper().replace("-", "_")
    if key in {"P", "P_XLIKE", "XLIKE", "TM", "X"}:
        return "P_XLIKE"
    raise UnsupportedRequest({
        "status": "UNSUPPORTED_POLARIZATION",
        "requested_polarization": polarization,
        "supported_polarization": ["P_XLIKE"],
        "reason": "the frozen deterministic single-pillar source library is x-only; no S/P averaging or substitution is allowed",
    })


def validate_wavelength(wavelength_nm: float) -> int:
    if isinstance(wavelength_nm, bool):
        raise ValueError("wavelength must be an exact integer nm grid point")
    x = float(wavelength_nm)
    if not math.isfinite(x) or not x.is_integer() or int(x) not in WAVELENGTHS_NM:
        raise ValueError("wavelength support is exact integer points 445..455 nm; interpolation/extrapolation is forbidden")
    return int(x)


def unsupported_feature(name: str) -> dict[str, Any]:
    key = name.strip().lower()
    if key in {"complex", "complex_amplitude", "scattering_state", "jones", "jones_matrix", "phase"}:
        return {
            "status": "UNSUPPORTED_COMPLEX",
            "requested_feature": name,
            "provider": PROVIDER_ID,
            "reason": "A1 exposes normalized power proxies only; the frozen complex coefficients are not a composable scattering state",
        }
    if key in {"r", "reflection", "r_total"}:
        return {
            "status": "UNAVAILABLE",
            "requested_feature": name,
            "provider": PROVIDER_ID,
            "reason": "the authorized D0 full-K6 LF authority does not provide an R proxy",
        }
    return {"status": "UNSUPPORTED", "requested_feature": name, "provider": PROVIDER_ID}


class NP_LF_FEATURE_PROVIDER_V2_Runtime:
    """Callable single-pillar-DFT feature provider for ordered K6 coordinates."""

    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = _root(root)
        self.library_path = self.root / "outputs/np_k6_p1d2_broadband_library_27point_v1/library_long.csv"
        self.library_manifest_path = self.library_path.with_name("library_manifest.json")
        self.provenance_path = self.library_path.with_name("provenance_verification.json")
        self.generator_path = self.root / "scripts/stage_np_k6_ml_d0_build_database_foundation.py"
        self.lf_manifest_path = self.root / "outputs/np_k6_ml_d0_database_foundation_v1/k6_lf_arrays_manifest.json"
        self.lf22_manifest_path = self.root / "outputs/np_k6_m9_22g_forward_retraining_v1/lf22_full_vector_authority_manifest.json"
        self.d180_contract_path = self.root / "outputs/np_k6_p1d2_d180_explicit_rerun_v1/execution_contract.json"
        self.d180_heartbeat_path = self.root / "outputs/np_k6_p1d2_d180_explicit_rerun_v1/heartbeat.json"
        self.d180_run_manifest_path = self.root / "outputs/np_k6_p1d2b_broadband_d180_x_v1/run_manifest.json"
        self.d180_results_path = self.root / "outputs/np_k6_p1d2b_broadband_d180_x_v1/results.json"
        self.d180_verification_path = self.root / "outputs/np_k6_p1d2b_broadband_d180_x_v1/verification_summary.json"
        self.d180_post_fsp_path = self.root / "runtime_fsp/np_k6_p1d2_d180_explicit_rerun_v1/NP_P1D2_BROADBAND_PILLAR_H500_D180_X_EXPLICIT_RERUN_V1_post.fsp"
        self.library_manifest = json.loads(self.library_manifest_path.read_text(encoding="utf-8-sig"))
        self.legacy_provenance = json.loads(self.provenance_path.read_text(encoding="utf-8-sig"))
        self.array_manifest = json.loads(self.lf_manifest_path.read_text(encoding="utf-8-sig"))
        self.lf22_manifest = json.loads(self.lf22_manifest_path.read_text(encoding="utf-8-sig"))
        self._validate_source_authority()
        self._single: dict[tuple[int, int], np.complex64] = {}
        with self.library_path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != 297:
            raise RuntimeError(f"expected the frozen 27x11 source library, got {len(rows)} rows")
        for row in rows:
            d, w = int(row["diameter_nm"]), int(float(row["wavelength_nm"]))
            key = (d, w)
            if key in self._single:
                raise RuntimeError(f"duplicate single-pillar source row {key}")
            self._single[key] = np.complex64(complex(float(row["txx_real"]), float(row["txx_imag"])))
        expected = {(d, w) for d in DIAMETERS_NM for w in WAVELENGTHS_NM}
        if set(self._single) != expected or not all(np.isfinite(x) for x in self._single.values()):
            raise RuntimeError("single-pillar library grid is incomplete or non-finite")
        self._validate_d180_library_parity()
        self.hf22_geometries = tuple(sorted({_parse_geometry_id(gid) for gid in self.lf22_manifest["geometry_hashes"]}))
        if len(self.hf22_geometries) != 22:
            raise RuntimeError("HF22 geometry-only support manifest is not exactly 22 geometries")
        self.position_min = tuple(min(g[i] for g in self.hf22_geometries) for i in range(6))
        self.position_max = tuple(max(g[i] for g in self.hf22_geometries) for i in range(6))
        self.provenance_hashes = {
            "d0_generator_sha256": _sha(self.generator_path),
            "single_pillar_library_sha256": _sha(self.library_path),
            "single_pillar_library_manifest_sha256": _sha(self.library_manifest_path),
            "legacy_provenance_snapshot_sha256": _sha(self.provenance_path),
            "d0_array_manifest_sha256": _sha(self.lf_manifest_path),
            "hf22_geometry_support_manifest_sha256": _sha(self.lf22_manifest_path),
            "d180_explicit_execution_contract_sha256": _sha(self.d180_contract_path),
            "d180_attempt2_heartbeat_sha256": _sha(self.d180_heartbeat_path),
            "d180_attempt2_run_manifest_sha256": _sha(self.d180_run_manifest_path),
            "d180_attempt2_results_sha256": _sha(self.d180_results_path),
            "d180_attempt2_verification_sha256": _sha(self.d180_verification_path),
            "d180_attempt2_post_fsp_sha256": _sha(self.d180_post_fsp_path),
        }
        self.provenance_hash = hashlib.sha256(_canonical_json(self.provenance_hashes)).hexdigest()
        self.provenance_warnings = getattr(self, "provenance_warnings", [])

    def _validate_d180_library_parity(self) -> None:
        result = json.loads(self.d180_results_path.read_text(encoding="utf-8-sig"))
        for row in result["rows"]:
            w = int(round(float(row["wavelength_nm"])))
            source = self._single[(180, w)]
            if source.real != float(row["txx"]["real"]) or source.imag != float(row["txx"]["imag"]):
                raise RuntimeError(f"D180 library row differs from explicit attempt-2 extracted txx at {w} nm")

    def _validate_source_authority(self) -> None:
        if self.library_manifest.get("row_count") != 297 or self.library_manifest.get("x_only") is not True:
            raise RuntimeError("single-pillar library manifest does not authorize the expected x-only 27x11 grid")
        if self.library_manifest.get("interpolation_used") is not False:
            raise RuntimeError("source library interpolation is not permitted")
        if self.array_manifest.get("label") != "LOW_FIDELITY_SINGLE_PILLAR_DFT_PROXY" or self.array_manifest.get("solver_calls") != 0:
            raise RuntimeError("D0 authority identity/solver provenance mismatch")
        if self.array_manifest.get("m_values") != list(ORDERS) or self.array_manifest.get("propagating_orders") != list(PROPAGATING_ORDERS):
            raise RuntimeError("tracked diffraction-order contract mismatch")
        if not self.legacy_provenance.get("D180_excluded"):
            raise RuntimeError("legacy provenance snapshot unexpectedly changed; require explicit re-audit")
        # D180's older sealed failure stays immutable.  This later one-run attempt is
        # admitted only through its explicit authorization, saved post-FSP, formal
        # read-only extraction, and exact source-result hash link.
        contract = json.loads(self.d180_contract_path.read_text(encoding="utf-8-sig"))
        heartbeat = json.loads(self.d180_heartbeat_path.read_text(encoding="utf-8-sig"))
        run = json.loads(self.d180_run_manifest_path.read_text(encoding="utf-8-sig"))
        verify = json.loads(self.d180_verification_path.read_text(encoding="utf-8-sig"))
        self.provenance_warnings = []
        result_sha = _sha(self.d180_results_path)
        post_sha = _sha(self.d180_post_fsp_path)
        if contract.get("retry_authorization") != "explicit_user_authorized_independent_rerun_v1" or contract.get("maximum_new_solver_runs") != 1:
            raise RuntimeError("D180 later attempt lacks one-run explicit authorization")
        if heartbeat.get("stage") != "setup_pass" or not heartbeat.get("pre_fsp", {}).get("sha256"):
            raise RuntimeError("D180 attempt-2 setup heartbeat lacks a pre-FSP fingerprint")
        pre_ref = heartbeat["pre_fsp"]
        pre_path = self.root / Path(str(pre_ref["path"]).replace("\\", "/"))
        current_pre_sha = _sha(pre_path) if pre_path.is_file() else None
        self.d180_pre_fsp_audit = {
            "heartbeat_path": pre_ref.get("path"),
            "heartbeat_recorded_sha256": pre_ref.get("sha256"),
            "current_path_exists": pre_path.is_file(),
            "current_path_sha256": current_pre_sha,
            "current_bytes_match_heartbeat": current_pre_sha == pre_ref.get("sha256"),
        }
        if not pre_path.is_file():
            self.provenance_warnings.append("D180 setup heartbeat pre-FSP path is absent at audit time; recorded setup hash retained as historical evidence")
        elif _sha(pre_path) != pre_ref["sha256"]:
            self.provenance_warnings.append("D180 setup heartbeat pre-FSP path now contains different bytes; do not treat the current file as the setup artifact")
        if run.get("case_id") != "NP_P1D2_BROADBAND_PILLAR_H500_D180_X_EXPLICIT_RERUN_V1":
            raise RuntimeError("D180 run manifest does not identify the explicit attempt-2 case")
        if run.get("new_solver_run_entered") != 1 or run.get("new_solver_run_completed") != 1:
            raise RuntimeError("D180 explicit attempt-2 run counts are incomplete")
        if run.get("post_fsp", {}).get("sha256") != post_sha:
            raise RuntimeError("D180 post-FSP checksum does not match the run manifest")
        if run.get("pre_fsp", {}).get("sha256") != pre_ref["sha256"]:
            self.provenance_warnings.append(
                "D180 run_manifest pre_fsp pointer does not match setup heartbeat; setup hash is retained from the heartbeat, but the referenced pre-FSP bytes are not currently recoverable"
            )
        if verify.get("P1D2_BATCH_FORMAL_STATUS") != "pass" or verify.get("post_fsp_readonly_gate") is not True:
            raise RuntimeError("D180 attempt-2 post-FSP extraction did not pass the formal read-only gate")
        if self.library_manifest.get("source_result_hashes", {}).get("180") != result_sha:
            raise RuntimeError("D180 result hash is not linked to the source library manifest")
        result = json.loads(self.d180_results_path.read_text(encoding="utf-8-sig"))
        if result.get("case_id") != run.get("case_id") or len(result.get("rows", [])) != len(WAVELENGTHS_NM):
            raise RuntimeError("D180 result rows are not tied to the explicit attempt-2 identity")

    def support_audit(self, geometry: Sequence[float]) -> dict[str, Any]:
        g = validate_geometry(geometry)
        gid = geometry_id(g)
        exact = g in self.hf22_geometries
        distances = [math.sqrt(sum(((g[i] - h[i]) / 130.0) ** 2 for i in range(6))) for h in self.hf22_geometries]
        nearest_i = min(range(len(distances)), key=distances.__getitem__)
        inside_positionwise = all(self.position_min[i] <= g[i] <= self.position_max[i] for i in range(6))
        gaps = [PITCH_NM - (g[i] + g[(i + 1) % 6]) / 2 for i in range(6)]
        return {
            "geometry_id": gid,
            "ordered_D_nm": list(g),
            "physical_domain_valid": True,
            "physical_domain_reason": "six fixed +x physical pillar bins; each D on the source grid; positive periodic edge gaps at 290 nm pitch",
            "min_periodic_gap_nm": min(gaps),
            "provider_fit_support": {"status": "NOT_APPLICABLE_DETERMINISTIC_PROVIDER", "fitted_geometry_count": 0},
            "source_calibration_support": {"single_pillar_diameters_nm": [100, 230, 5], "wavelength_nm": [445, 455], "polarization": "x-only"},
            "hf22_empirical_support": {
                "full_k6_hf22_geometry_count": 22,
                "exact_hf22_match": exact,
                "status": "IN_HF22_EXACT_GEOMETRY_SUPPORT" if exact else "OOD_OUTSIDE_HF22_EXACT_GEOMETRY_SUPPORT",
                "inside_all_positionwise_minmax": inside_positionwise,
            },
            "runtime_domain": {
                "provider_id": PROVIDER_ID,
                "status": "SUPPORTED_DISCRETE_ORDERED_LF_DOMAIN",
                "diameter_domain_nm": [100, 230],
                "diameter_step_nm": 5,
                "ordered_geometry_input": True,
                "sorting_or_permutation": False,
                "polarization": "P_XLIKE_ONLY",
                "wavelength_nm": [445, 455],
            },
            "nearest_hf22_geometry_id": geometry_id(self.hf22_geometries[nearest_i]),
            "nearest_hf22_distance_normalized_by_130nm": distances[nearest_i],
            "extrapolative_vs_hf22_positionwise_bounds": not inside_positionwise,
            "ood": not exact,
        }

    def infer(
        self,
        geometry: Sequence[float],
        wavelength_nm: float,
        polarization: str,
        *,
        u_x: float = 0.0,
        k_y: float = 0.0,
    ) -> dict[str, Any]:
        g = validate_geometry(geometry)
        wavelength = validate_wavelength(wavelength_nm)
        pol = canonical_polarization(polarization)
        if not math.isclose(float(u_x), 0.0, abs_tol=1e-12) or not math.isclose(float(k_y), 0.0, abs_tol=1e-12):
            raise UnsupportedRequest({"status": "UNSUPPORTED_ANGLE", "u_x": u_x, "k_y": k_y, "reason": "normal-incidence-only frozen scope"})
        t = np.asarray([self._single[(d, wavelength)] for d in g], dtype=np.complex64).reshape(1, 1, 6)
        amplitudes = np.einsum("nwj,mj->nwm", t, EXP, optimize=True)[0, 0]
        power = np.abs(amplitudes) ** 2
        denominator = power.sum()
        if not np.isfinite(power).all() or not math.isfinite(float(denominator)) or denominator <= 0:
            raise RuntimeError("non-finite or zero tracked-order LF proxy denominator")
        eta = power / denominator
        support = self.support_audit(g)
        eta_by_order = {f"m{m:+d}": float(eta[i]) for i, m in enumerate(ORDERS)}
        t_proxy = float(sum(eta[ORDERS.index(m)] for m in PROPAGATING_ORDERS))
        return {
            "interface_id": INTERFACE_ID,
            "provider_id": PROVIDER_ID,
            "provenance": "LF_ONLY_SINGLE_PILLAR_DFT_PROXY",
            "provenance_hash": self.provenance_hash,
            "geometry_hash": _geometry_hash(g),
            "geometry_id": geometry_id(g),
            "ordered_D_nm": list(g),
            "wavelength_nm": wavelength,
            "polarization": pol,
            "u_x": 0.0,
            "k_y": 0.0,
            "features": {
                "eta_m_proxy": eta_by_order,
                "T_proxy": t_proxy,
                "normalization_contract": "eta_m_proxy = |A_m|^2 / sum(|A_m|^2 for tracked m=-3..+3); T_proxy is eta_-1+eta_0+eta_+1 and is not absolute HF transmission",
                "R": {"status": "UNAVAILABLE", "reason": "not produced by the authorized D0 full-K6 LF contract"},
            },
            "support_status": support["hf22_empirical_support"]["status"],
            "ood": support["ood"],
            "domain_warning": "LF proxy only; OOD relative to HF22 exact geometry support; not coupled-device truth or FDTD replacement",
            "provenance_warnings": list(self.provenance_warnings),
            "runtime": {"python": platform.python_version(), "numpy": np.__version__},
            "support_audit": support,
        }


def NP_LF_FEATURE_PROVIDER_V2(
    D1: float,
    D2: float,
    D3: float,
    D4: float,
    D5: float,
    D6: float,
    wavelength: float,
    polarization: str,
    *,
    root: str | os.PathLike[str] | None = None,
    u_x: float = 0.0,
    k_y: float = 0.0,
) -> dict[str, Any]:
    """Functional facade: ordered D1..D6, exact lambda, explicit P/XLIKE."""
    resolved_root = str(_root(root))
    provider = _PROVIDER_CACHE.get(resolved_root)
    if provider is None:
        provider = NP_LF_FEATURE_PROVIDER_V2_Runtime(root=resolved_root)
        _PROVIDER_CACHE[resolved_root] = provider
    return provider.infer((D1, D2, D3, D4, D5, D6), wavelength, polarization, u_x=u_x, k_y=k_y)


_PROVIDER_CACHE: dict[str, NP_LF_FEATURE_PROVIDER_V2_Runtime] = {}
