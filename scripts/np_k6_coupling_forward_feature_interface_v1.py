#!/usr/bin/env python3
"""Read-only NP-K6 to Coupling-ML feature adapter; zero solver and fail-closed."""
from __future__ import annotations
import csv, gzip, hashlib, json, math
from pathlib import Path
from typing import Mapping

INTERFACE_NAME = "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1"
ROUTE_DECISION = "NP_COMPLEX_COEFFICIENT_NOT_COMPOSABLE_AS_SCATTERING_STATE"
WAVELENGTHS_NM = tuple(range(445, 456))
ORDER_VECTOR = (-3, -2, -1, 0, 1, 2, 3)
PROPAGATING_ORDERS = (-1, 0, 1)
NORMALIZER_NM = 130.0
SRC = {
    "provider_manifest": "outputs/np_k6_final_freeze_closeout_v1/provider_manifest.json",
    "prior_features": "outputs/np_k6_final_freeze_closeout_v1/NP_PRIOR_FEATURES_V1.json",
    "coupling_handoff": "outputs/np_k6_final_freeze_closeout_v1/coupling_handoff.json",
    "hf22_csv": "outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv",
    "lf22_csv": "outputs/np_k6_m9_22g_forward_retraining_v1/lf22_full_vector_authority.csv",
    "lf_array_manifest": "outputs/np_k6_ml_d0_database_foundation_v1/k6_lf_arrays_manifest.json",
    "lf_master": "outputs/np_k6_ml_d0_database_foundation_v1/k6_design_space_master.csv.gz",
}
COMPLEX = {
    "COMPLEX_SCATTERING_STATE_AVAILABLE": False,
    "COMPOSABLE_COMPLEX_PHASE_AVAILABLE": False,
    "FULL_2x2_JONES_MATRIX": False,
    "MULTI_INPUT_FLOQUET_SCATTERING_MATRIX": False,
    "ARBITRARY_RETURNING_ORDER_RESCATTERING": False,
}

def _root():
    return Path(__file__).resolve().parents[1]

def _path(root, rel):
    return root / Path(rel)

def _load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def geometry_id(g):
    return "K6X_" + "_".join(f"D{int(x) if float(x).is_integer() else float(x):g}" for x in g)

def geometry_hash(g):
    return hashlib.sha256(geometry_id(g).encode()).hexdigest()

def validate_geometry(g):
    if isinstance(g, (str, bytes)) or len(g) != 6:
        raise ValueError("geometry must be ordered [D1,D2,D3,D4,D5,D6]")
    g = tuple(float(x) for x in g)
    if not all(math.isfinite(x) for x in g):
        raise ValueError("geometry values must be finite")
    return g

def canonical_polarization(p):
    try:
        return {
            "P": "P_XLIKE", "TM": "P_XLIKE", "XLIKE": "P_XLIKE",
            "P_XLIKE": "P_XLIKE", "S": "S_YLIKE", "TE": "S_YLIKE",
            "YLIKE": "S_YLIKE", "S_YLIKE": "S_YLIKE",
        }[str(p).upper()]
    except KeyError as exc:
        raise ValueError("polarization must be P/P_XLIKE or S/S_YLIKE") from exc

def validate_wavelength(x):
    x = float(x)
    if not math.isfinite(x) or not x.is_integer() or int(x) not in WAVELENGTHS_NM:
        raise ValueError("wavelength_nm must be integer 445..455")
    return int(x)

def validate_ux(x):
    x = 0.0 if x is None else float(x)
    if not math.isfinite(x):
        raise ValueError("ux must be finite")
    return x

def parse_geometry_id(s):
    p = s.split("_")
    if len(p) != 7 or p[0] != "K6X":
        raise ValueError("invalid geometry_id")
    return tuple(float(x[1:]) for x in p[1:])

def eta(row, prefix="eta_m"):
    return {m: float(row[f"{prefix}{m:+d}"]) for m in ORDER_VECTOR}

class FrozenAuthority:
    def __init__(self, root=None):
        self.root = root or _root()
        self.hf = None
        self.hf_geometries = None
        self.bounds = None
        self.lf = None
        self.lf_manifest = None
        self.master_index = {}
        self.master_scan_complete = False
        self.array_cache = {}

    def _load_hf(self):
        if self.hf is not None:
            return
        rows, geoms = {}, {}
        with open(_path(self.root, SRC["hf22_csv"]), newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                g = row["geometry_id"]
                key = (g, int(row["wavelength_nm"]), canonical_polarization(row["polarization"]))
                if key in rows:
                    raise ValueError(f"duplicate HF row {key}")
                rows[key] = row
                geoms[g] = parse_geometry_id(g)
        if len(geoms) != 22 or len(rows) != 484:
            raise ValueError("HF22 cardinality mismatch")
        self.hf, self.hf_geometries = rows, geoms
        self.bounds = [
            (min(g[i] for g in geoms.values()), max(g[i] for g in geoms.values()))
            for i in range(6)
        ]

    def _load_lf(self):
        if self.lf is not None:
            return
        rows = {}
        with open(_path(self.root, SRC["lf22_csv"]), newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                rows[(row["geometry_id"], int(row["wavelength_nm"]),
                      canonical_polarization(row["polarization"]))] = row
        if len(rows) != 484:
            raise ValueError("LF22 cardinality mismatch")
        self.lf = rows

    def support_audit(self, geometry):
        g = validate_geometry(geometry)
        self._load_hf()
        gid = geometry_id(g)
        exact = gid in self.hf_geometries and self.hf_geometries[gid] == g
        per = [
            {
                "field": f"D{i + 1}",
                "value_nm": g[i],
                "hf22_min_nm": low,
                "hf22_max_nm": high,
                "within_positionwise_support": low <= g[i] <= high,
            }
            for i, (low, high) in enumerate(self.bounds)
        ]
        nearest_gid, nearest = min(
            self.hf_geometries.items(),
            key=lambda pair: (
                math.sqrt(sum(((g[i] - pair[1][i]) / NORMALIZER_NM) ** 2 for i in range(6))),
                pair[0],
            ),
        )
        distance = math.sqrt(sum(((g[i] - nearest[i]) / NORMALIZER_NM) ** 2 for i in range(6)))
        classification = (
            "exact_HF22_match"
            if exact
            else "interpolation_support_only"
            if all(item["within_positionwise_support"] for item in per)
            else "extrapolation"
        )
        return {
            "ordered_geometry": list(g),
            "geometry_id": gid,
            "geometry_hash_sha256": geometry_hash(g),
            "exact_HF22_match": exact,
            "per_dimension_support": per,
            "all_dimensions_within_positionwise_support": all(
                item["within_positionwise_support"] for item in per
            ),
            "normalized_nearest_HF22_distance": distance,
            "distance_normalizer_nm": NORMALIZER_NM,
            "nearest_HF22_geometry_id": nearest_gid,
            "nearest_HF22_geometry": list(nearest),
            "classification": classification,
            "interpolation_performed": False,
            "training_domain_warning": (
                "NONE_EXACT_HF22"
                if exact
                else "OOD_EXTRAPOLATIVE"
                if classification == "extrapolation"
                else "OOD_NOT_EXACT_HF22"
            ),
        }

    def _scan_master(self, gid):
        if gid in self.master_index:
            return self.master_index[gid]
        if self.master_scan_complete:
            return None
        with gzip.open(_path(self.root, SRC["lf_master"]), "rt", newline="", encoding="utf-8") as f:
            for index, row in enumerate(csv.DictReader(f)):
                row_gid = row.get("geometry_id") or geometry_id(tuple(float(row[f"D{i}"]) for i in range(6)))
                self.master_index.setdefault(row_gid, index)
                if row_gid == gid:
                    return index
        self.master_scan_complete = True
        return None

    def _array_value(self, index, wavelength):
        if self.lf_manifest is None:
            self.lf_manifest = _load_json(_path(self.root, SRC["lf_array_manifest"]))
        chunk = next(
            item for item in self.lf_manifest["chunk_manifest"]
            if item["geometry_index_start"] <= index <= item["geometry_index_end"]
        )
        start = int(chunk["geometry_index_start"])
        if start not in self.array_cache:
            import numpy as np
            array_path = _path(
                self.root,
                "outputs/np_k6_ml_d0_database_foundation_v1/" + chunk["path"],
            )
            with np.load(array_path) as data:
                self.array_cache[start] = data["eta_m_proxy"].copy()
        arr = self.array_cache[start]
        return {
            int(m): float(arr[index - start, wavelength - 445, j])
            for j, m in enumerate(self.lf_manifest["m_values"])
        }

    def lf_features(self, geometry, wavelength, polarization):
        g = validate_geometry(geometry)
        wavelength = validate_wavelength(wavelength)
        polarization = canonical_polarization(polarization)
        gid = geometry_id(g)
        self._load_lf()
        row = self.lf.get((gid, wavelength, polarization))
        if row is not None:
            order_values = eta(row, "lf_eta_m")
            source = "LF22_FULL_VECTOR_AUTHORITY"
            artifact = SRC["lf22_csv"]
        else:
            index = self._scan_master(gid)
            if index is None:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "geometry_not_present_in_frozen_LF_design_space",
                    "provenance": "LF_ONLY",
                    "requested_polarization": polarization,
                    "polarization_scope": "POLARIZATION_BLIND_UX0",
                }
            order_values = self._array_value(index, wavelength)
            source = "FROZEN_D0_FULL_VECTOR_ARRAY_AUTHORITY"
            artifact = SRC["lf_array_manifest"]
        return {
            "status": "AVAILABLE",
            "provenance": "LF_ONLY",
            "source": source,
            "source_artifact": artifact,
            "requested_polarization": polarization,
            "polarization_scope": "POLARIZATION_BLIND_UX0",
            "order_vector": {str(m): order_values[m] for m in ORDER_VECTOR},
            "propagating_order_powers": {
                str(m): order_values[m] for m in PROPAGATING_ORDERS
            },
            "T_proxy": sum(order_values[m] for m in PROPAGATING_ORDERS),
            "R": {"status": "UNAVAILABLE", "reason": "LF_authority_does_not_provide_R"},
            "normalization": "frozen LF eta_m_proxy; T_proxy=sum(m=-1,0,+1)",
        }

    def hf_truth(self, geometry, wavelength, polarization):
        g = validate_geometry(geometry)
        wavelength = validate_wavelength(wavelength)
        polarization = canonical_polarization(polarization)
        self._load_hf()
        row = self.hf.get((geometry_id(g), wavelength, polarization))
        if row is None:
            return None
        order_values = eta(row)
        return {
            "provenance": "FROZEN_HF_TRUTH",
            "source_artifact": SRC["hf22_csv"],
            "requested_polarization": polarization,
            "R": float(row["R_total"]),
            "T": float(row["T_total"]),
            "order_vector": order_values,
            "propagating_order_powers": {
                str(m): order_values[m] for m in PROPAGATING_ORDERS
            },
            "transmitted_order_sum": float(row["transmitted_order_sum"]),
            "closure": float(row["closure"]),
            "quality_gate_pass": row["quality_gate_pass"].lower() == "true",
        }

    def angular_capability(self, ux, polarization):
        polarization = canonical_polarization(polarization)
        cases = [
            (0.22413793103448276, "S_YLIKE", "AVAILABLE_SPARSE_HF_CROSS_REFERENCE"),
            (0.37868939998860307, "P_XLIKE", "AVAILABLE_SPARSE_HF_CROSS_REFERENCE"),
            (0.37868939998860307, "S_YLIKE", "AVAILABLE_SPARSE_HF_CROSS_REFERENCE"),
            (-0.3786893999886029, "P_XLIKE", "AVAILABLE_QUANTITATIVE_HF_ANCHOR"),
            (-0.3786893999886029, "S_YLIKE", "AVAILABLE_QUANTITATIVE_HF_ANCHOR"),
            (0.22413793103448276, "P_XLIKE", "UNRESOLVED_NOT_TRUTH_NO_ATTEMPT_003"),
            (-0.48275862069, "P_XLIKE", "RAYLEIGH_STRESS_TEST_ONLY_NOT_QUANTITATIVE_ANCHOR"),
        ]
        for known_ux, known_pol, status in cases:
            if math.isclose(ux, known_ux, abs_tol=1e-12) and polarization == known_pol:
                return {
                    "ux": ux,
                    "polarization": polarization,
                    "status": status,
                    "values_available": False,
                    "provider_type": "sparse_angular_handoff_metadata_only",
                    "interpolation_performed": False,
                    "symmetry_substitution": False,
                }
        return {
            "ux": ux,
            "polarization": polarization,
            "status": "UNSUPPORTED_NO_FROZEN_CASE",
            "values_available": False,
            "provider_type": "sparse_angular_handoff_metadata_only",
            "interpolation_performed": False,
            "symmetry_substitution": False,
        }

    def request(self, request):
        if not isinstance(request, Mapping):
            raise TypeError("request must be a mapping")
        geometry = validate_geometry(request.get("geometry"))
        wavelength = validate_wavelength(request.get("wavelength_nm"))
        polarization = canonical_polarization(request.get("polarization"))
        ux = validate_ux(request.get("ux", 0.0))
        support = self.support_audit(geometry)
        if (
            request.get("complex_scattering_state")
            or request.get("composable_complex_coefficient")
            or request.get("jones_matrix")
        ):
            return {
                "status": "UNSUPPORTED",
                "error_code": "COMPLEX_SCATTERING_STATE_UNAVAILABLE",
                "route_decision": ROUTE_DECISION,
                "capability": COMPLEX,
                "support": support,
                "features": {},
            }
        if not math.isclose(ux, 0.0, abs_tol=0.0):
            return {
                "status": "UNSUPPORTED",
                "error_code": "ANGULAR_RESPONSE_NOT_EXPOSED_BY_NORMAL_INCIDENCE_INTERFACE",
                "angular": self.angular_capability(ux, polarization),
                "support": support,
                "features": {},
            }
        return {
            "status": "OK",
            "interface": INTERFACE_NAME,
            "input": {
                "geometry": list(geometry),
                "geometry_order": ["D1", "D2", "D3", "D4", "D5", "D6"],
                "wavelength_nm": wavelength,
                "polarization": polarization,
                "ux": ux,
                "k_y": 0.0,
            },
            "support": support,
            "features": {
                "lf": self.lf_features(geometry, wavelength, polarization),
                "hf_truth": self.hf_truth(geometry, wavelength, polarization),
                "ranking_score": {
                    "status": "UNAVAILABLE",
                    "reason": "NP_PROVIDER_RECOVERY_FAIL",
                    "provider_id": "NP_K6_NORMAL_INCIDENCE_SCREENING_PROVIDER_V1",
                },
                "spectral_surrogate": {
                    "status": "UNAVAILABLE",
                    "reason": "NOT_ENABLED_UNTIL_PROVIDER_PARITY_PASS",
                    "provider_id": "NP_K6_NORMAL_INCIDENCE_SCREENING_PROVIDER_V1",
                },
            },
            "capability": {
                "complex_scattering_state_available": False,
                "composable_complex_phase_available": False,
                "full_2x2_jones_matrix": False,
                "multi_input_floquet_scattering_matrix": False,
                "arbitrary_returning_order_rescattering": False,
            },
            "no_solver_calls": True,
        }

def request_features(request, root=None):
    return FrozenAuthority(root).request(request)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    print(json.dumps(request_features(_load_json(args.request_json), args.root), indent=2))
