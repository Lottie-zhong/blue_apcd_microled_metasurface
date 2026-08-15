from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1f1_k6_coupling_level0"
GRID = [450.0 + 0.5 * i for i in range(9)]
H_GLOBAL_NM = 550.0
P_NM = 431.907786
P_SUPERCELL_NM = 2591.446716
P_Y_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
PROCESSES = 4
THREADS = 1
MAX_NEW_CASES = 6
OLD_STRICT = [
    ("GLOBAL_006", "58cb7c6aebab655f9f14af16d5a2ec1d0182037e8543fca5a31e7a08ebfcd176"),
    ("GLOBAL_015", "008a917f209f17a46f5bfd48dde796d5e473af44a93209b4432f5b6d9908a446"),
    ("H1C1B_V2_005", "7ba530060e07eb8b651007da12053d43b506b488dc27a8b1ba186f7b9dd2ce82"),
    ("H1C1B_V2_009", "955c293def3063f64969c25743e14ce122e7ed0364b12be0b9f75cdb350cb800"),
    ("H1C1B_V2_010", "3f1dc26c576ffc1bc4c074f90d1c58ade24eb09b6926603aa8208ee52da19611"),
    ("H1C1B_V2_012", "9191ce264313547454e8730bd323ea9ae49244af138113c2fa5b75e1a627857b"),
    ("H1C1B_V2_015", "6af50bfc327c190ec461a424241496195795522cfecaefde81b65228f40dbbc7"),
]
NEW_STRICT = [
    "H1E3C_A_DECOUPLED_PLUS_H1C1B_V2_010",
    "H1E3C_A_DECOUPLED_MINUS_H1C1B_V2_010",
    "H1E3C_A_TIED_PLUS_H1C1B_V2_010",
    "H1E3C_A_TIED_MINUS_H1C1B_V2_010",
    "H1E3C_B_DECOUPLED_MINUS_GLOBAL_006",
]
H1C1B_MANIFEST = ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_candidate_manifest.json"
H1C1B_JONES = ROOT / "reports/stage_h1c1b_broadband_adaptive/h1c1b_broadband_full_jones.csv"
H1C1A_MANIFEST = ROOT / "reports/stage_h1c1a_broadband_global/h1c1a_candidate_manifest.json"
H1C1A_JONES = ROOT / "reports/stage_h1c1a_broadband_global/h1c1a_broadband_full_jones.csv"
H1E3C_MANIFEST = ROOT / "reports/stage_h1e3c_j2_decoupling_probe/h1e3c_candidate_manifest.json"
H1E3C_JONES = ROOT / "reports/stage_h1e3c_j2_decoupling_probe/h1e3c_broadband_full_jones.csv"
H1E3C_BANK = ROOT / "reports/stage_h1e3c_j2_decoupling_probe/h1e3c_strict_bank_updated.json"
H1D1_FINAL = ROOT / "reports/stage_h1d1_detour_feasibility/h1d1_final.json"
H1F0_ML_AUDIT = ROOT / "reports/stage_h1f0_lp_route_closure/h1f0_ml_role_audit.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def complex_dict(z: complex) -> dict[str, float]:
    return {"re": float(z.real), "im": float(z.imag)}


def complex_from(row: dict[str, str], name: str) -> complex:
    return complex(float(row["Re_" + name]), float(row["Im_" + name]))


def identity_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    identity = dict(candidate["legality"]["geometry_identity"])
    if "J2_rotation_deg" not in identity:
        identity["J2_rotation_deg"] = float(candidate.get("theta_J2_deg", 0.0))
    identity["Psi_position_deg"] = float(candidate.get("Psi_position_deg", identity.get("Psi_position_deg", 0.0)))
    return identity


def load_csv(path: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            out.setdefault(row["geometry_uid"], []).append(row)
    for uid in out:
        out[uid].sort(key=lambda row: float(row["wavelength_nm"]))
    return out


def seed_record(uid: str, exact_hash: str, identity: dict[str, Any], rows: list[dict[str, Any]], provenance: dict[str, Any]) -> dict[str, Any]:
    assert len(rows) == 9, (uid, len(rows))
    assert [float(row["wavelength_nm"]) for row in rows] == GRID
    jones = []
    for row in rows:
        jones.append({
            "wavelength_nm": float(row["wavelength_nm"]),
            "txx": complex_from(row, "txx"), "txy": complex_from(row, "txy"),
            "tyx": complex_from(row, "tyx"), "tyy": complex_from(row, "tyy"),
            "phi_deg": float(row["phi_txx"]), "projector_error": float(row["projector_error"]),
            "Txx": float(row["Txx"]), "throughput": float(row.get("throughput", row.get("throughput_x", "nan"))),
        })
    return {
        "geometry_uid": uid, "exact_hash": exact_hash, "identity": identity,
        "coordinates_5d": {
            "J1_side_nm": float(identity["J1_side_nm"]),
            "J2_length_nm": float(identity["J2_length_nm"]),
            "J2_width_nm": float(identity["J2_width_nm"]),
            "D_nm": float(identity["J2_center_x_nm"] - identity["J1_center_x_nm"]),
            "Psi_position_deg": float(identity.get("Psi_position_deg", 0.0)),
            "theta_J2_deg": float(identity.get("J2_rotation_deg", 0.0)),
            "delta_theta_J2_deg": float(identity.get("delta_theta_J2_deg", 0.0)),
        },
        "H_global_nm": float(identity["H_global_nm"]), "wavelength_grid_nm": GRID,
        "jones": jones, "provenance": provenance,
    }


def load_seeds() -> list[dict[str, Any]]:
    old_manifest = read_json(H1C1B_MANIFEST)
    old_candidates = {candidate["geometry_uid"]: candidate for candidate in old_manifest["candidates"]}
    old_rows = load_csv(H1C1B_JONES)
    global_manifest = read_json(H1C1A_MANIFEST)
    global_candidates = {candidate["geometry_uid"]: candidate for candidate in global_manifest["candidates"]}
    global_rows = load_csv(H1C1A_JONES)
    new_manifest = read_json(H1E3C_MANIFEST)
    new_candidates = {candidate["geometry_uid"]: candidate for candidate in new_manifest["candidates"]}
    new_rows = load_csv(H1E3C_JONES)
    seeds = []
    for uid, exact_hash in OLD_STRICT:
        if uid.startswith("GLOBAL_"):
            candidates, rows, manifest_path, csv_path, stage = global_candidates, global_rows, H1C1A_MANIFEST, H1C1A_JONES, "H1C1A_BROADBAND_STRICT_BANK"
        else:
            candidates, rows, manifest_path, csv_path, stage = old_candidates, old_rows, H1C1B_MANIFEST, H1C1B_JONES, "H1C1B_BROADBAND_STRICT_BANK"
        seeds.append(seed_record(uid, exact_hash, identity_from_candidate(candidates[uid]), rows[uid], {
            "artifact": str(csv_path), "manifest": str(manifest_path), "source_stage": stage,
        }))
    for uid in NEW_STRICT:
        candidate = new_candidates[uid]
        seeds.append(seed_record(uid, candidate["exact_hash"], identity_from_candidate(candidate), new_rows[uid], {
            "artifact": str(H1E3C_JONES), "manifest": str(H1E3C_MANIFEST), "strict_bank": str(H1E3C_BANK), "source_stage": "H1E3C_NEW_STRICT_CHILD",
        }))
    assert len(seeds) == 12
    assert len({seed["exact_hash"] for seed in seeds}) == 12
    return seeds


def rotate(sequence: tuple[int, ...], shift: int) -> tuple[int, ...]:
    return sequence[shift:] + sequence[:shift]


def canonical_cycle(sequence: tuple[int, ...]) -> tuple[int, ...]:
    return min(rotate(sequence, shift) for shift in range(6))


def fundamental_period_6p(sequence: tuple[int, ...]) -> dict[str, Any]:
    translations = {str(q): all(sequence[n] == sequence[(n + q) % 6] for n in range(6)) for q in (1, 2, 3)}
    return {"translations_tested_p_2p_3p": translations, "FUNDAMENTAL_PERIOD_6P": not any(translations.values())}


def rotate_corners(cx: float, cy: float, length: float, width: float, angle_deg: float) -> list[tuple[float, float]]:
    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    return [(cx + sx * length / 2 * ux + sy * width / 2 * vx, cy + sx * length / 2 * uy + sy * width / 2 * vy) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def segment_distance(a, b, c, d) -> float:
    def cross(u, v): return u[0] * v[1] - u[1] * v[0]
    def sub(u, v): return u[0] - v[0], u[1] - v[1]
    def dot(u, v): return u[0] * v[0] + u[1] * v[1]
    def point_segment(p, a0, b0):
        vec = sub(b0, a0)
        den = dot(vec, vec)
        if den == 0: return math.hypot(p[0] - a0[0], p[1] - a0[1])
        q = max(0.0, min(1.0, dot(sub(p, a0), vec) / den))
        x = a0[0] + q * vec[0], a0[1] + q * vec[1]
        return math.hypot(p[0] - x[0], p[1] - x[1])
    r, s = sub(b, a), sub(d, c)
    den = cross(r, s)
    if abs(den) > 1e-14:
        t, u = cross(sub(c, a), s) / den, cross(sub(c, a), r) / den
        if 0 <= t <= 1 and 0 <= u <= 1: return 0.0
    return min(point_segment(a, c, d), point_segment(b, c, d), point_segment(c, a, b), point_segment(d, a, b))


def polygon_distance(first, second) -> float:
    return min(segment_distance(first[i], first[(i + 1) % 4], second[j], second[(j + 1) % 4]) for i in range(4) for j in range(4))


def site_shapes(seed: dict[str, Any], site_x: float) -> list[list[tuple[float, float]]]:
    identity = seed["identity"]
    return [
        rotate_corners(site_x + identity["J1_center_x_nm"], identity["J1_center_y_nm"], identity["J1_side_nm"], identity["J1_side_nm"], identity.get("J1_rotation_deg", 0.0)),
        rotate_corners(site_x + identity["J2_center_x_nm"], identity["J2_center_y_nm"], identity["J2_length_nm"], identity["J2_width_nm"], identity.get("J2_rotation_deg", 0.0)),
    ]


def sequence_legality(sequence: tuple[int, ...], seeds: list[dict[str, Any]]) -> dict[str, Any]:
    cache = build_legality_cache(seeds)
    positions = [(n + 0.5) * P_NM for n in range(6)]
    direct = [cache["direct"][index] for index in sequence]
    y_bounds = [cache["y_bounds"][index] for index in sequence]
    cross = [cache["cross"][m - n][sequence[n], sequence[m]] for n in range(6) for m in range(n + 1, 6)]
    minimum = min(direct + cross + y_bounds)
    return {
        "pass": minimum > 0.0, "no_overlap": minimum > 0.0, "minimum_clearance_nm": float(minimum),
        "minimum_direct_pillar_gap_nm": float(min(direct)), "minimum_cross_site_gap_nm": float(min(cross)),
        "periodic_boundary_gap_y_nm": float(min(y_bounds)), "materials": [MATERIAL] * 12,
        "H_global_nm": H_GLOBAL_NM, "P_supercell_nm": P_SUPERCELL_NM, "p_nm": P_NM,
        "positions_nm": [{"site": n, "x_nm": positions[n], "y_nm": 0.0} for n in range(6)],
        "orientation_source": "exact authoritative local geometry identity",
    }


def build_legality_cache(seeds: list[dict[str, Any]]) -> dict[str, Any]:
    direct = np.zeros(12, dtype=float)
    y_bounds = np.zeros(12, dtype=float)
    cross = {distance: np.zeros((12, 12), dtype=float) for distance in range(1, 6)}
    origin_shapes = [site_shapes(seed, 0.0) for seed in seeds]
    for i in range(12):
        direct[i] = polygon_distance(origin_shapes[i][0], origin_shapes[i][1])
        bounds = []
        for poly in origin_shapes[i]:
            bounds.extend([216.0 - max(y for _, y in poly), min(y for _, y in poly) + 216.0])
        y_bounds[i] = min(bounds)
    for distance in range(1, 6):
        for i in range(12):
            for j in range(12):
                gaps = []
                left = origin_shapes[i]
                right = site_shapes(seeds[j], distance * P_NM)
                for shift in (-P_SUPERCELL_NM, 0.0, P_SUPERCELL_NM):
                    for first in left:
                        for second in right:
                            gaps.append(polygon_distance(first, [(x + shift, y) for x, y in second]))
                cross[distance][i, j] = min(gaps)
    return {"direct": direct, "y_bounds": y_bounds, "cross": cross}


def proxy_for_sequence(sequence: tuple[int, ...], seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for wavelength_index, wavelength in enumerate(GRID):
        row = {"wavelength_nm": wavelength}
        for order in (-1, 0, 1):
            jones = {}
            for name in ("txx", "txy", "tyx", "tyy"):
                jones[name] = sum(seeds[index]["jones"][wavelength_index][name] * complex(math.cos(-2 * math.pi * order * n / 6), math.sin(-2 * math.pi * order * n / 6)) for n, index in enumerate(sequence)) / 6.0
            row[f"m{order}_jones"] = jones
        target = row["m1_jones"]
        row["m_plus1_target_xx_power"] = abs(target["txx"]) ** 2
        row["m_plus1_x_input_cross_leakage"] = abs(target["tyx"]) ** 2
        row["m_plus1_y_input_target_leakage"] = abs(target["txy"]) ** 2 + abs(target["tyy"]) ** 2
        row["m_plus1_projector_error"] = math.sqrt(abs(target["txy"]) ** 2 + abs(target["tyx"]) ** 2 + abs(target["tyy"]) ** 2) / max(abs(target["txx"]), 1e-30)
        row["m_plus1_phase_deg"] = math.degrees(math.atan2(target["txx"].imag, target["txx"].real))
        row["m0_xx_power"] = abs(row["m0_jones"]["txx"]) ** 2
        row["mminus1_xx_power"] = abs(row["m-1_jones"]["txx"]) ** 2
        output.append(row)
    return output


def proxy_metrics(proxy: list[dict[str, Any]]) -> dict[str, float]:
    target = [row["m_plus1_target_xx_power"] for row in proxy]
    y_leakage = [row["m_plus1_y_input_target_leakage"] for row in proxy]
    mean_target, mean_y = statistics.fmean(target), statistics.fmean(y_leakage)
    return {
        "mean_target_order_strength": float(mean_target), "worst_wavelength_target_order_strength": float(min(target)),
        "mean_y_target_leakage": float(mean_y), "x_y_contrast_ratio": float(mean_target / max(mean_y, 1e-30)),
        "x_y_contrast_safe_difference": float(mean_target - mean_y), "mean_m0_xx_leakage": float(statistics.fmean(row["m0_xx_power"] for row in proxy)),
        "mean_mminus1_xx_leakage": float(statistics.fmean(row["mminus1_xx_power"] for row in proxy)),
        "worst_projector_error": float(max(row["m_plus1_projector_error"] for row in proxy)),
    }


def run_search(seeds: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cache = build_legality_cache(seeds)
    canonical_sequences = []
    seen = set()
    for sequence in itertools.product(range(12), repeat=6):
        canonical_sequence = canonical_cycle(sequence)
        if canonical_sequence != sequence or canonical_sequence in seen:
            continue
        seen.add(canonical_sequence)
        if fundamental_period_6p(canonical_sequence)["FUNDAMENTAL_PERIOD_6P"]:
            canonical_sequences.append(canonical_sequence)
    sequence_array = np.asarray(canonical_sequences, dtype=np.int8)
    jones = np.asarray([[[row[name] for name in ("txx", "txy", "tyx", "tyy")] for row in seed["jones"]] for seed in seeds], dtype=np.complex128)
    metric_records = []
    for start in range(0, len(sequence_array), 50000):
        batch = sequence_array[start:start + 50000]
        legal_mask = np.min(cache["y_bounds"][batch], axis=1) > 0.0
        for distance in range(1, 6):
            legal_mask &= cache["cross"][distance][batch[:, :-distance], batch[:, distance:]].min(axis=1) > 0.0
        legal_mask &= np.min(cache["direct"][batch], axis=1) > 0.0
        if not np.any(legal_mask):
            continue
        valid = batch[legal_mask]
        selected = jones[valid]
        metrics = []
        for order in (-1, 0, 1):
            weights = np.exp(-2j * np.pi * order * np.arange(6) / 6.0)
            metrics.append(np.sum(selected * weights[None, :, None, None], axis=1))
        minus, zero, plus = metrics
        target = np.abs(plus[:, :, 0]) ** 2
        y_leak = np.abs(plus[:, :, 1]) ** 2 + np.abs(plus[:, :, 3]) ** 2
        proj = np.sqrt(np.abs(plus[:, :, 1]) ** 2 + np.abs(plus[:, :, 2]) ** 2 + np.abs(plus[:, :, 3]) ** 2) / np.maximum(np.abs(plus[:, :, 0]), 1e-30)
        for index, sequence in enumerate(valid):
            mean_target = float(np.mean(target[index]))
            mean_y = float(np.mean(y_leak[index]))
            metric_records.append({
                "canonical_sequence": [int(x) for x in sequence],
                "sequence_indices": [int(x) for x in sequence],
                "metrics": {
                    "mean_target_order_strength": mean_target,
                    "worst_wavelength_target_order_strength": float(np.min(target[index])),
                    "mean_y_target_leakage": mean_y,
                    "x_y_contrast_ratio": float(mean_target / max(mean_y, 1e-30)),
                    "x_y_contrast_safe_difference": float(mean_target - mean_y),
                    "mean_m0_xx_leakage": float(np.mean(np.abs(zero[index, :, 0]) ** 2)),
                    "mean_mminus1_xx_leakage": float(np.mean(np.abs(minus[index, :, 0]) ** 2)),
                    "worst_projector_error": float(np.max(proj[index])),
                },
            })
    return metric_records, {"raw_sequence_count": 12 ** 6, "cyclic_canonical_count": len(seen), "period_6p_count": len(canonical_sequences), "legal_fundamental_sequence_count": len(metric_records), "mirror_reversal_not_collapsed": True}


def materialize(record: dict[str, Any], seeds: list[dict[str, Any]]) -> dict[str, Any]:
    sequence = tuple(record["sequence_indices"])
    proxy = proxy_for_sequence(sequence, seeds)
    return {**record, "sequence_uids": [seeds[i]["geometry_uid"] for i in sequence], "sequence_hashes": [seeds[i]["exact_hash"] for i in sequence], "mirror_sequence": list(reversed(sequence)), "period_audit": fundamental_period_6p(sequence), "legality": sequence_legality(sequence, seeds), "proxy": proxy, "metrics": proxy_metrics(proxy)}


def choose_roles(records: list[dict[str, Any]]) -> list[tuple[str, str, dict[str, Any]]]:
    assert records
    used: set[tuple[int, ...]] = set()
    def pick(key):
        for record in sorted(records, key=key):
            sequence = tuple(record["canonical_sequence"])
            if sequence not in used:
                used.add(sequence)
                return record
        raise RuntimeError("not enough distinct legal candidates")
    a = pick(lambda r: (-r["metrics"]["mean_target_order_strength"], -r["metrics"]["worst_wavelength_target_order_strength"], -r["metrics"]["x_y_contrast_ratio"], r["metrics"]["mean_m0_xx_leakage"], r["canonical_sequence"]))
    b = pick(lambda r: (-r["metrics"]["worst_wavelength_target_order_strength"], -r["metrics"]["mean_target_order_strength"], -r["metrics"]["x_y_contrast_ratio"], r["metrics"]["mean_m0_xx_leakage"], r["canonical_sequence"]))
    c = pick(lambda r: (-r["metrics"]["x_y_contrast_ratio"], -r["metrics"]["mean_target_order_strength"], -r["metrics"]["worst_wavelength_target_order_strength"], r["metrics"]["mean_m0_xx_leakage"], r["canonical_sequence"]))
    return [("K6_L0_A", "K6_L0_MEAN_TARGET_ORDER_CHAMPION", a), ("K6_L0_B", "K6_L0_WORST_WAVELENGTH_ROBUST_CHAMPION", b), ("K6_L0_C", "K6_L0_POLARIZATION_CONTRAST_CHAMPION", c)]


def slim_seed(seed: dict[str, Any]) -> dict[str, Any]:
    return {key: seed[key] for key in ("geometry_uid", "exact_hash", "coordinates_5d", "H_global_nm", "wavelength_grid_nm", "provenance")}


def create_outputs() -> dict[str, Any]:
    print("H1F1_OFFLINE_START", flush=True)
    seeds = load_seeds()
    print(f"H1F1_SEEDS={len(seeds)}", flush=True)
    write_json(REPORT / "h1f1_strict_bank_source.json", {"schema": "H1F1_STRICT_BANK_SOURCE_V1", "count": len(seeds), "wavelength_grid_nm": GRID, "seeds": [slim_seed(seed) for seed in seeds], "source_artifacts": [str(H1C1A_MANIFEST), str(H1C1A_JONES), str(H1C1B_MANIFEST), str(H1C1B_JONES), str(H1E3C_MANIFEST), str(H1E3C_JONES), str(H1E3C_BANK)], "ml_admitted": False})
    records, search_summary = run_search(seeds)
    print(f"H1F1_SEARCH_DONE={len(records)}", flush=True)
    roles = choose_roles(records)
    roles = [(candidate_uid, role, materialize(record, seeds)) for candidate_uid, role, record in roles]
    candidates = {}
    for candidate_uid, role, record in roles:
        payload = {
            "candidate_uid": candidate_uid, "role": role, "sequence_uids": record["sequence_uids"], "sequence_hashes": record["sequence_hashes"], "sequence_indices": record["sequence_indices"],
            "site_positions_nm": record["legality"]["positions_nm"], "p_nm": P_NM, "P_supercell_nm": P_SUPERCELL_NM, "P_y_nm": P_Y_NM, "H_global_nm": H_GLOBAL_NM,
            "material": MATERIAL, "fundamental_period_audit": record["period_audit"], "geometry_legality": record["legality"], "proxy": record["proxy"], "proxy_metrics": record["metrics"],
            "local_geometries": [seeds[index]["identity"] for index in record["sequence_indices"]], "no_position_shift": True, "no_local_geometry_mutation": True, "ml_admitted": False,
        }
        payload["candidate_hash"] = sha256_obj(payload)
        candidates[candidate_uid] = payload
    write_json(REPORT / "h1f1_sequence_search_summary.json", {"schema": "H1F1_SEQUENCE_SEARCH_SUMMARY_V1", **search_summary, "role_selection": [{"candidate_uid": uid, "role": role, "canonical_sequence": record["canonical_sequence"], "metrics": record["metrics"]} for uid, role, record in roles], "selection_method": "deterministic lexicographic roles over legal fundamental-period candidates; no weighted composite", "raw_space": "12^6"})
    top = sorted(records, key=lambda r: (-r["metrics"]["mean_target_order_strength"], -r["metrics"]["worst_wavelength_target_order_strength"], r["canonical_sequence"]))[:100]
    rows = [{"sequence_uids": "|".join(seeds[i]["geometry_uid"] for i in record["sequence_indices"]), "sequence_hashes": "|".join(seeds[i]["exact_hash"] for i in record["sequence_indices"]), **record["metrics"]} for record in top]
    with (REPORT / "h1f1_proxy_pareto.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0]); writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    write_json(REPORT / "h1f1_candidate_manifest.json", {"schema": "H1F1_K6_CANDIDATE_MANIFEST_V1", "status": "FROZEN_READY_FOR_SETUP", "stage": "H1F-1", "candidate_count": 3, "candidates": list(candidates.values()), "p_nm": P_NM, "P_supercell_nm": P_SUPERCELL_NM, "P_y_nm": P_Y_NM, "H_global_nm": H_GLOBAL_NM, "wavelength_grid_nm": GRID, "processes": PROCESSES, "threads": THREADS, "max_new_formal_cases": MAX_NEW_CASES, "position_convention": "x_n=(n+0.5)*p, y_n=0; no additional shifts", "freeze_sha256": sha256_obj(candidates), "ml_admitted": False})
    write_json(REPORT / "h1f1_fundamental_period_audit.json", {uid: candidate["fundamental_period_audit"] for uid, candidate in candidates.items()})
    write_json(REPORT / "h1f1_geometry_legality.json", {uid: candidate["geometry_legality"] for uid, candidate in candidates.items()})
    write_json(REPORT / "h1f1_solver_accounting.json", {"schema": "H1F1_SOLVER_ACCOUNTING_V1", "planned_formal_cases": 6, "entered_formal_cases": 0, "accepted_formal_cases": 0, "quarantine_cases": 0, "replay_cases": 0, "cases": [], "processes_per_job": PROCESSES, "threads_per_job": THREADS, "wavelength_grid_nm": GRID, "max_active_lp_fdtd": 1, "ml_admitted": False})
    local_audit = read_json(H1F0_ML_AUDIT)
    local_count = int(local_audit["versioned_local_dimer_rows"])
    assert local_count == 578
    summary = {"schema": "H1F1_PRE_SOLVER_SUMMARY_V1", "status": "FROZEN_READY_FOR_SETUP", "strict_seed_count": len(seeds), "search_summary": search_summary, "candidate_uids": list(candidates), "local_registry_rows_observed": local_count, "h1d1_reused_read_only": True, "new_solver_runs": 0, "entered_true_new": 0, "ml_admitted": False}
    write_json(REPORT / "h1f1_final.json", summary)
    (REPORT / "h1f1_summary.md").write_text("# H1F-1 K6 coupling-aware Level-0\n\n" + f"- Status: FROZEN_READY_FOR_SETUP\n- Strict seeds: {len(seeds)}; raw search: {search_summary['raw_sequence_count']}; legal fundamental sequences: {search_summary['legal_fundamental_sequence_count']}.\n- New solver runs: 0; entered: 0; ML admitted: false.\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    print(json.dumps(create_outputs(), indent=2, ensure_ascii=False))
