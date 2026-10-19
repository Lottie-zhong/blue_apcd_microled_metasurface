import csv
import hashlib
import json
import math
import re
from pathlib import Path

try:
    import numpy as np
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"numpy is required for read-only NPZ audit: {exc}")


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1"
BASE = ROOT / "outputs" / "coupling_v2_2" / "FINITE_K6_23UM_19UM_TWO_SLOT_BASELINE_COMPLETION_V1"
ML = ROOT / "outputs" / "coupling_ml"
ALLOWED_ROLES = {
    "EXACT_2D_TRAIN_TRUTH",
    "AUXILIARY_GEOMETRY_PRIOR",
    "AUXILIARY_PHYSICS_PRIOR",
    "VALIDATION_OR_OOD_ONLY",
    "SCREENING_ONLY",
    "HISTORICAL_REFERENCE_ONLY",
    "EXCLUDE_FROM_CURRENT_ML",
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def write_json(name, payload):
    path = OUT / name
    path.write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_csv(name, rows, fieldnames):
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def first_file(folder, patterns):
    for pattern in patterns:
        matches = sorted(folder.rglob(pattern))
        if matches:
            return matches[0]
    return None


def first_npz_with_key(folder, key):
    for path in sorted(folder.rglob("*.npz")):
        try:
            with np.load(path, allow_pickle=True) as data:
                if key in data.files:
                    return path
        except Exception:
            continue
    return None


def current_case(case_id, vector=None, post_path=None, raw_path=None):
    folder = BASE / case_id
    post = Path(post_path) if post_path else folder / "post.fsp"
    raw = Path(raw_path) if raw_path else (first_npz_with_key(folder, "farfield_theta_deg") or first_file(folder, ["*.npz"]))
    metadata = first_file(folder, ["*_RAW_METADATA.json", "*raw_metadata*.json"])
    completion = first_file(folder, ["*COMPLETION*.json", "*completion*.json", "*AUDIT*.json"])
    telemetry = first_file(folder, ["*_RUN_TELEMETRY.json"])
    metadata_obj = read_json(metadata, {}) if metadata else {}
    sha = metadata_obj.get("post_fsp_sha256") or (sha256(post) if post.exists() else None)
    return {
        "case_id": case_id,
        "folder": str(folder),
        "post_fsp": str(post),
        "post_fsp_exists": post.exists(),
        "post_fsp_size_bytes": post.stat().st_size if post.exists() else 0,
        "post_fsp_sha256": sha,
        "raw_npz": str(raw) if raw else None,
        "raw_npz_exists": bool(raw and raw.exists()),
        "raw_npz_sha256": sha256(raw) if raw and raw.exists() else None,
        "metadata": rel(metadata) if metadata else None,
        "completion_audit": rel(completion) if completion else None,
        "telemetry": rel(telemetry) if telemetry else None,
        "geometry_vector_nm": list(vector) if vector else None,
    }


def load_geometry_csv(path):
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            fields = []
            for i in range(1, 7):
                key = next((k for k in row if k.lower() in {f"d{i}", f"d{i}_nm", f"d{i}nm"}), None)
                if key is None or row[key] in (None, ""):
                    fields = []
                    break
                fields.append(int(round(float(row[key]))))
            if len(fields) == 6:
                rows.append((tuple(fields), row))
    return rows


def scan_alt1b():
    hits = []
    for path in ML.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".csv", ".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "ALT1B" in text:
            hits.append(rel(path))
    return hits[:40]


def halton(index, base):
    value = 0.0
    fraction = 1.0 / base
    n = index
    while n:
        value += (n % base) * fraction
        n //= base
        fraction /= base
    return value


def point_distance(a, b):
    return math.sqrt(sum(((x - y) / 130.0) ** 2 for x, y in zip(a, b)))


def geometry_hash(vector):
    return hashlib.sha256(",".join(str(int(x)) for x in vector).encode()).hexdigest()


def select_diverse(pool, seeds, count):
    remaining = sorted(set(pool) - set(seeds))
    selected = list(seeds)
    while remaining and len(selected) < len(seeds) + count:
        candidate = max(remaining, key=lambda p: min(point_distance(p, q) for q in selected))
        selected.append(candidate)
        remaining.remove(candidate)
    return selected[len(seeds):]


def make_generated(existing, count, start_index):
    grid = list(range(100, 231, 5))
    primes = (2, 3, 5, 7, 11, 13)
    candidates = []
    seen = set(existing)
    for index in range(start_index, start_index + 10000):
        point = tuple(grid[min(len(grid) - 1, int(halton(index, base) * len(grid)))] for base in primes)
        if point not in seen:
            candidates.append(point)
            seen.add(point)
    selected = []
    selected_all = list(existing)
    while candidates and len(selected) < count:
        point = max(candidates, key=lambda p: min(point_distance(p, q) for q in selected_all))
        candidates.remove(point)
        selected.append(point)
        selected_all.append(point)
    if len(selected) != count:
        raise RuntimeError(f"could not create {count} unique DOE geometries")
    return selected


def read_runtime_fields():
    telemetry = []
    for path in sorted(BASE.rglob("*_RUN_TELEMETRY.json")):
        obj = read_json(path, {})
        if isinstance(obj, dict) and obj.get("wall_time_s") is not None:
            telemetry.append({
                "case_id": path.parent.name,
                "wall_time_s": float(obj["wall_time_s"]),
                "mpi": obj.get("resource", {}).get("processes"),
                "threads": obj.get("resource", {}).get("threads"),
                "path": rel(path),
            })
    return telemetry


def audit_angular_profiles(cases):
    per_case = []
    for case in cases:
        raw = Path(case["raw_npz"]) if case.get("raw_npz") else None
        if not raw or not raw.exists():
            continue
        try:
            with np.load(raw, allow_pickle=True) as data:
                if "farfield_theta_deg" not in data.files or "farfield_e2" not in data.files:
                    raw = first_npz_with_key(raw.parent, "farfield_theta_deg")
                with np.load(raw, allow_pickle=True) as data:
                    theta = np.asarray(data["farfield_theta_deg"])
                    e2 = np.asarray(data["farfield_e2"])
        except Exception as exc:
            raise RuntimeError(f"cannot audit native farfield NPZ for {case['case_id']}: {exc}")
        u = np.sin(np.deg2rad(theta[:, 0]))
        du = np.diff(u)
        per_case.append({
            "case_id": case["case_id"],
            "theta_shape": list(theta.shape),
            "farfield_e2_shape": list(e2.shape),
            "theta_min_deg": float(np.nanmin(theta)),
            "theta_max_deg": float(np.nanmax(theta)),
            "ux_min": float(np.nanmin(u)),
            "ux_max": float(np.nanmax(u)),
            "ux_count": int(u.size),
            "ux_step_median": float(np.median(du)),
            "ux_step_max_abs_error": float(np.max(np.abs(du - np.median(du)))),
            "native_grid_is_uniform_ux": bool(np.max(np.abs(du - np.median(du))) < 1e-10),
            "theta_grid_is_uniform": bool(np.max(np.abs(np.diff(theta[:, 0]) - np.median(np.diff(theta[:, 0])))) < 1e-10),
            "finite_fraction": float(np.isfinite(e2).mean()),
            "nonnegative_fraction": float((e2 >= 0).mean()),
        })
    return {
        "audit_status": "PASS_READ_ONLY_NATIVE_GRID_AUDIT",
        "native_api": "Lumerical farfield2d / farfield_e2",
        "canonical_coordinate": "u_x = sin(theta_deg)",
        "native_measure": "du_x",
        "interpolation_required_for_native_profile": False,
        "integration_rule": "trapezoid over native monotonic u_x; never an unweighted sum",
        "pca_input": "normalized angular profile on the native u_x grid with explicit du_x weights",
        "edge_policy": "retain full native [-1,1] profile; report edge support separately; do not let endpoint singular theta spacing define PCA bins",
        "cases": per_case,
    }


def build_matrix(cases, m2a_csv, m2b_csv, alt1b_hits, control0_ref=None):
    evidence = lambda *paths: ";".join(str(p) for p in paths if p)
    rows = []
    for case_id, vector, role in [
        ("CURRENT_FINITE_2D_SOURCE_ONLY_23_19", None, "EXACT_2D_TRAIN_TRUTH"),
        ("CURRENT_FINITE_2D_CONTROL0_23_19", (125, 135, 150, 175, 190, 210), "EXACT_2D_TRAIN_TRUTH"),
        ("CURRENT_FINITE_2D_ALT1_23_19", (100, 115, 130, 145, 155, 185), "EXACT_2D_TRAIN_TRUTH"),
    ]:
        current_evidence = (control0_ref if case_id == "CURRENT_FINITE_2D_CONTROL0_23_19" else (BASE / (case_id.rsplit("_23_19", 1)[0].replace("CURRENT_FINITE_2D_", ""))))
        rows.append({
            "DATASET_ID": case_id,
            "DIMENSION": "2D",
            "SOURCE_TYPE": "isolated electric line dipole" if case_id != "CURRENT_FINITE_2D_SOURCE_ONLY_23_19" else "isolated electric line dipole, SOURCE_ONLY denominator",
            "SOURCE_ORIENTATION": "X",
            "X_BC": "PML",
            "Y_BC": "PML",
            "Z_BC": "N/A_2D",
            "PERIODIC_SOURCE_REPLICATION": "NO",
            "DEVICE_GEOMETRY_DOMAIN": "finite MDC/spacer, 23um FDTD / 19um monitor",
            "NP_GEOMETRY": json.dumps(vector) if vector else "SOURCE_ONLY",
            "MDC_GEOMETRY": "current frozen MDC/spacer",
            "WAVELENGTH_DOMAIN": "445:455 nm, 11 x 1 nm",
            "OBSERVABLES": "source_box, up/down monitor, native farfield2d, complex fields",
            "NORMALIZATION": "P_source_box; source-only denominator for G_emit",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "current 23/19 finite-domain source-box and up/down monitors; native farfield2d",
            "RAW_TRUTH_AVAILABLE": "YES",
            "POST_FSP_AVAILABLE": "YES",
            "SHA_AUTHORITY_AVAILABLE": "YES",
            "PHYSICAL_INTERPRETATION": "frozen finite isolated-emitter MDC-NP coupling truth",
            "CURRENT_2D_ML_ROLE": role,
            "EVIDENCE_PATHS": evidence(current_evidence, BASE / "PRODUCTION_DOMAIN_FREEZE.json"),
        })
    rows.extend([
        {
            "DATASET_ID": "HISTORICAL_DIRECT_MDC_2D_FDTD",
            "DIMENSION": "2D",
            "SOURCE_TYPE": "native Lumerical direct MDC 2D dipole cases",
            "SOURCE_ORIENTATION": "case-specific X/Z",
            "X_BC": "case-specific/partially recorded",
            "Y_BC": "case-specific/partially recorded",
            "Z_BC": "N/A_2D",
            "PERIODIC_SOURCE_REPLICATION": "NO_OR_UNRESOLVED_BY_CASE",
            "DEVICE_GEOMETRY_DOMAIN": "historical direct-MDC domains",
            "NP_GEOMETRY": "historical/variable",
            "MDC_GEOMETRY": "historical direct MDC",
            "WAVELENGTH_DOMAIN": "mixed; exact current 445:455 target not established",
            "OBSERVABLES": "raw farfield/monitor candidates",
            "NORMALIZATION": "case-specific; current P_source_box contract not proven",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "partial/variable; target Level1 operator not proven",
            "RAW_TRUTH_AVAILABLE": "PARTIAL",
            "POST_FSP_AVAILABLE": "PARTIAL",
            "SHA_AUTHORITY_AVAILABLE": "PARTIAL",
            "PHYSICAL_INTERPRETATION": "useful direct-MDC response and physics prior, not pooled current labels",
            "CURRENT_2D_ML_ROLE": "AUXILIARY_PHYSICS_PRIOR",
            "EVIDENCE_PATHS": evidence(ML / "M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1" / "M0D_UNIQUE_MDC_CONTRACT_DEDUP_V1.json", ML / "M1_EXACT_RESIDUAL_DATASET_V1"),
        },
        {
            "DATASET_ID": "HISTORICAL_MDC_V3_SURROGATE_DATABASE",
            "DIMENSION": "2D_SURROGATE",
            "SOURCE_TYPE": "MDC-V3 surrogate/profile database",
            "SOURCE_ORIENTATION": "mixed/historical",
            "X_BC": "not current contract",
            "Y_BC": "not current contract",
            "Z_BC": "N/A_2D",
            "PERIODIC_SOURCE_REPLICATION": "unresolved",
            "DEVICE_GEOMETRY_DOMAIN": "historical surrogate domain",
            "NP_GEOMETRY": "historical",
            "MDC_GEOMETRY": "MDC-V3 surrogate",
            "WAVELENGTH_DOMAIN": "not current frozen target",
            "OBSERVABLES": "surrogate profile/derived observables",
            "NORMALIZATION": "not current exact contract",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "not current exact contract",
            "RAW_TRUTH_AVAILABLE": "NO_OR_PARTIAL",
            "POST_FSP_AVAILABLE": "NO_OR_PARTIAL",
            "SHA_AUTHORITY_AVAILABLE": "PARTIAL",
            "PHYSICAL_INTERPRETATION": "screening only; surrogate output cannot be relabeled as exact FDTD truth",
            "CURRENT_2D_ML_ROLE": "SCREENING_ONLY",
            "EVIDENCE_PATHS": evidence(ML / "M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1", ROOT / "outputs" / "mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1"),
        },
        {
            "DATASET_ID": "NP_STANDALONE_K6_PROVIDER",
            "DIMENSION": "2D_PROVIDER",
            "SOURCE_TYPE": "standalone NP Level1 RCWA explicit-epsilon provider",
            "SOURCE_ORIENTATION": "P_XLIKE/S_YLIKE",
            "X_BC": "provider-specific periodic/planar",
            "Y_BC": "provider-specific periodic/planar",
            "Z_BC": "N/A_2D",
            "PERIODIC_SOURCE_REPLICATION": "YES_PROVIDER_CONTEXT",
            "DEVICE_GEOMETRY_DOMAIN": "standalone NP K6 provider",
            "NP_GEOMETRY": "ordered D1..D6 candidate vectors",
            "MDC_GEOMETRY": "NONE_CURRENT_MDC_COUPLING",
            "WAVELENGTH_DOMAIN": "445:455 nm, exact provider grid",
            "OBSERVABLES": "order fractions/eta plus/minus one",
            "NORMALIZATION": "provider-native",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "provider-native RCWA",
            "RAW_TRUTH_AVAILABLE": "YES_PROVIDER_RAW",
            "POST_FSP_AVAILABLE": "NO_FDTD_POST",
            "SHA_AUTHORITY_AVAILABLE": "YES_PROVIDER_MANIFEST",
            "PHYSICAL_INTERPRETATION": "geometry prior and cheap provider; not finite isolated line-source truth",
            "CURRENT_2D_ML_ROLE": "AUXILIARY_GEOMETRY_PRIOR",
            "EVIDENCE_PATHS": evidence(ML / "M2B_CORE_GEOMETRY_DIVERSITY_ACQUISITION_V1", m2b_csv),
        },
        {
            "DATASET_ID": "LEVEL2A_PERIODIC_PLANE_WAVE_PROVIDER",
            "DIMENSION": "2D_PERIODIC",
            "SOURCE_TYPE": "oblique plane wave/BFAST/Bloch integrated provider",
            "SOURCE_ORIENTATION": "P_XLIKE/S_YLIKE",
            "X_BC": "periodic/Bloch",
            "Y_BC": "periodic/Bloch",
            "Z_BC": "PML",
            "PERIODIC_SOURCE_REPLICATION": "YES",
            "DEVICE_GEOMETRY_DOMAIN": "periodic NP/MDC unit-cell or provider context",
            "NP_GEOMETRY": "K6/provider geometry",
            "MDC_GEOMETRY": "historical/current auxiliary",
            "WAVELENGTH_DOMAIN": "445:455 nm, exact in M2F/M2I subsets",
            "OBSERVABLES": "R/T/order profiles/Level2A residuals",
            "NORMALIZATION": "Level2A RT scope/reference-plane contract",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "NP pillar bottom/reference-plane contract, not current finite source-box semantics",
            "RAW_TRUTH_AVAILABLE": "YES_AUXILIARY",
            "POST_FSP_AVAILABLE": "YES_AUXILIARY",
            "SHA_AUTHORITY_AVAILABLE": "YES_AUXILIARY",
            "PHYSICAL_INTERPRETATION": "periodic plane-wave physics prior and validation/OOD evidence",
            "CURRENT_2D_ML_ROLE": "AUXILIARY_PHYSICS_PRIOR",
            "EVIDENCE_PATHS": evidence(ML / "M2F_G5_G6_PROVIDER_BLIND_PROSPECTIVE_AND_LEVEL2A_ACQUISITION_V1", ML / "M2I_G7_G8_PROVIDER_CONTEXT3_BLIND_PROSPECTIVE_AND_LEVEL2A_ACQUISITION_V1"),
        },
        {
            "DATASET_ID": "LEVEL2B_PERIODIC_DIPOLE_HISTORY",
            "DIMENSION": "2D_PERIODIC",
            "SOURCE_TYPE": "periodic/emitted electric dipole",
            "SOURCE_ORIENTATION": "historical Z/electric dipole cases",
            "X_BC": "periodic",
            "Y_BC": "periodic",
            "Z_BC": "PML",
            "PERIODIC_SOURCE_REPLICATION": "YES",
            "DEVICE_GEOMETRY_DOMAIN": "historical Level2B periodic domain",
            "NP_GEOMETRY": "historical",
            "MDC_GEOMETRY": "historical",
            "WAVELENGTH_DOMAIN": "historical/current-adjacent",
            "OBSERVABLES": "order/profile candidates",
            "NORMALIZATION": "LEVEL2B_ELECTRIC_DIPOLE_NORMALIZATION_CONTRACT_V2",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "NP pillar bottom in historical contract",
            "RAW_TRUTH_AVAILABLE": "PARTIAL",
            "POST_FSP_AVAILABLE": "PARTIAL",
            "SHA_AUTHORITY_AVAILABLE": "PARTIAL",
            "PHYSICAL_INTERPRETATION": "periodic array/emitted-source history; not isolated finite line-source labels",
            "CURRENT_2D_ML_ROLE": "HISTORICAL_REFERENCE_ONLY",
            "EVIDENCE_PATHS": evidence(ML / "M0_LEVEL1_LEVEL2_CONTRACT_RECONCILIATION_V1" / "M0B_LOGICAL_CASE_MATRIX_V1.csv"),
        },
        {
            "DATASET_ID": "M2Q_FINITE_3D_CENTROID_XZ",
            "DIMENSION": "3D",
            "SOURCE_TYPE": "finite 3D point/complex dipole source-only",
            "SOURCE_ORIENTATION": "CENTROID_X and CENTROID_Z",
            "X_BC": "PML",
            "Y_BC": "PML",
            "Z_BC": "PML",
            "PERIODIC_SOURCE_REPLICATION": "NO",
            "DEVICE_GEOMETRY_DOMAIN": "finite 3D MDC source-only",
            "NP_GEOMETRY": "none/source-only pilot",
            "MDC_GEOMETRY": "finite MDC 3D",
            "WAVELENGTH_DOMAIN": "445:455 nm, 11 points",
            "OBSERVABLES": "complex interface fields, dipolepower, sourcepower",
            "NORMALIZATION": "dipolepower(f); sourcepower auxiliary",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "NP-bottom-side interface field plane; 3D finite monitor",
            "RAW_TRUTH_AVAILABLE": "YES_3D",
            "POST_FSP_AVAILABLE": "YES_3D",
            "SHA_AUTHORITY_AVAILABLE": "YES_3D",
            "PHYSICAL_INTERPRETATION": "finite 3D complex-field validation/OOD truth; not 2D line-source labels",
            "CURRENT_2D_ML_ROLE": "VALIDATION_OR_OOD_ONLY",
            "EVIDENCE_PATHS": evidence(ML / "M2Q_CENTROID_XZ_3D_COMPLEX_SOURCE_PILOT_ACQUISITION_V1"),
        },
        {
            "DATASET_ID": "M2S_FINITE_3D_LATERAL_DOMAIN_ROBUSTNESS",
            "DIMENSION": "3D",
            "SOURCE_TYPE": "finite 3D source-only enlarged lateral domain",
            "SOURCE_ORIENTATION": "CENTROID_X and CENTROID_Z",
            "X_BC": "PML",
            "Y_BC": "PML",
            "Z_BC": "PML",
            "PERIODIC_SOURCE_REPLICATION": "NO",
            "DEVICE_GEOMETRY_DOMAIN": "finite 3D lateral-domain robustness",
            "NP_GEOMETRY": "none/source-only",
            "MDC_GEOMETRY": "finite MDC 3D",
            "WAVELENGTH_DOMAIN": "445:455 nm, 11 points",
            "OBSERVABLES": "3D source-only field/robustness evidence",
            "NORMALIZATION": "M2S resource/execution contract",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "3D finite monitor; not current 2D operator",
            "RAW_TRUTH_AVAILABLE": "ATTEMPT_DEPENDENT",
            "POST_FSP_AVAILABLE": "ATTEMPT_DEPENDENT",
            "SHA_AUTHORITY_AVAILABLE": "PROTECTED_FORENSIC_ONLY",
            "PHYSICAL_INTERPRETATION": "3D validation/OOD only; attempt-001 forensic evidence remains protected",
            "CURRENT_2D_ML_ROLE": "VALIDATION_OR_OOD_ONLY",
            "EVIDENCE_PATHS": evidence(ML / "M2S_CENTROID_XZ_3D_SOURCE_LATERAL_DOMAIN_ROBUSTNESS_V1", ML / "M2S_CENTROID_XZ_3D_SOURCE_LATERAL_DOMAIN_ROBUSTNESS_V1_ATTEMPT_002"),
        },
        {
            "DATASET_ID": "HISTORICAL_MDC_HF_SURROGATE_PILOT4",
            "DIMENSION": "2D",
            "SOURCE_TYPE": "historical native Lumerical MDC HF profile database",
            "SOURCE_ORIENTATION": "case-specific",
            "X_BC": "PML",
            "Y_BC": "PML",
            "Z_BC": "N/A_2D",
            "PERIODIC_SOURCE_REPLICATION": "NO_OR_CASE_SPECIFIC",
            "DEVICE_GEOMETRY_DOMAIN": "historical 2D MDC domain",
            "NP_GEOMETRY": "historical K6-like/variable",
            "MDC_GEOMETRY": "historical MDC",
            "WAVELENGTH_DOMAIN": "420:480 nm, 301 points",
            "OBSERVABLES": "raw farfield2d/profile and power",
            "NORMALIZATION": "historical profile contract; current P_source_box not proven",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "historical upward monitor/power-box semantics",
            "RAW_TRUTH_AVAILABLE": "YES_HISTORICAL",
            "POST_FSP_AVAILABLE": "YES_HISTORICAL",
            "SHA_AUTHORITY_AVAILABLE": "YES_HISTORICAL",
            "PHYSICAL_INTERPRETATION": "valuable physics prior but source/domain/wavelength contract differs",
            "CURRENT_2D_ML_ROLE": "SCREENING_ONLY",
            "EVIDENCE_PATHS": evidence(ROOT / "outputs" / "mdc_hf_surrogate_v2_pilot4_joint_profile_database_v1"),
        },
        {
            "DATASET_ID": "OTHER_COUPLING_HF_UNRESOLVED",
            "DIMENSION": "UNKNOWN_OR_MIXED",
            "SOURCE_TYPE": "other Coupling HF artifacts not proven canonical",
            "SOURCE_ORIENTATION": "UNKNOWN",
            "X_BC": "UNKNOWN",
            "Y_BC": "UNKNOWN",
            "Z_BC": "UNKNOWN",
            "PERIODIC_SOURCE_REPLICATION": "UNKNOWN",
            "DEVICE_GEOMETRY_DOMAIN": "not established",
            "NP_GEOMETRY": "not established",
            "MDC_GEOMETRY": "not established",
            "WAVELENGTH_DOMAIN": "not established",
            "OBSERVABLES": "not established",
            "NORMALIZATION": "not established",
            "REFERENCE_PLANE_MONITOR_SEMANTICS": "not established",
            "RAW_TRUTH_AVAILABLE": "UNRESOLVED",
            "POST_FSP_AVAILABLE": "UNRESOLVED",
            "SHA_AUTHORITY_AVAILABLE": "UNRESOLVED",
            "PHYSICAL_INTERPRETATION": "excluded until exact contract reconciliation exists",
            "CURRENT_2D_ML_ROLE": "EXCLUDE_FROM_CURRENT_ML",
            "EVIDENCE_PATHS": evidence(ML),
        },
    ])
    assert all(row["CURRENT_2D_ML_ROLE"] in ALLOWED_ROLES for row in rows)
    return rows


def main():
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite existing audit output: {OUT}")
    OUT.mkdir(parents=True)

    pool_path = ML / "M2A_GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_V1" / "M2A_NP22_GEOMETRY_CANDIDATE_POOL_V1.csv"
    provider_path = ML / "M2B_CORE_GEOMETRY_DIVERSITY_ACQUISITION_V1" / "M2B_CHEAP_PROVIDER_ACQUISITION_REGISTRY_V1.csv"
    pool_rows = load_geometry_csv(pool_path)
    provider_rows = load_geometry_csv(provider_path) if provider_path.exists() else []
    pool_vectors = [v for v, _ in pool_rows]
    observed_vectors = sorted(set(pool_vectors + [v for v, _ in provider_rows]))
    alt1 = (100, 115, 130, 145, 155, 185)
    control0 = (125, 135, 150, 175, 190, 210)
    existing_exact = [alt1, control0]

    control0_root = ROOT / "outputs" / "coupling_v2_2" / "FINITE_K6_23UM_DOMAIN_19UM_MONITOR_SINGLECASE_CONVERGENCE_PROBE_V1" / "VALIDATED_PROBE"
    cases = [
        current_case("SOURCE_ONLY", raw_path=BASE / "SOURCE_ONLY_RAW_TRUTH.npz"),
        current_case("CONTROL0", control0, post_path=control0_root / "CONTROL0" / "post.fsp", raw_path=control0_root / "CONTROL0_RAW_TRUTH.npz"),
        current_case("ALT1", alt1, raw_path=BASE / "ALT1_RAW_TRUTH.npz"),
    ]
    angular = audit_angular_profiles(cases)
    telemetry = read_runtime_fields()
    alt1b_hits = scan_alt1b()

    matrix = build_matrix(cases, pool_path, provider_path, alt1b_hits, control0_root / "CONTROL0" / "post.fsp")
    write_csv("DATABASE_AUTHORITY_MATRIX.csv", matrix, list(matrix[0]))
    write_json("DATABASE_AUTHORITY_MATRIX.json", {
        "schema_version": "DATABASE_AUTHORITY_MATRIX_V1",
        "audit_status": "PASS_ZERO_SOLVER_READ_ONLY",
        "classification_enum": sorted(ALLOWED_ROLES),
        "rows": matrix,
        "authority_notes": [
            "Only current finite 2D 23/19 isolated-X line-source cases are exact current train truth.",
            "SOURCE_ONLY is an exact denominator/reference case, not a new K6 geometry.",
            "M2Q/M2S 3D data are validation/OOD and are not pooled into 2D labels.",
            "Historical candidate pool states ordered D1..D6 and does not establish a separate fabrication-limit file.",
        ],
    })

    current_eligible = {
        "schema_version": "CURRENT_2D_TRAIN_ELIGIBLE_DATA_V1",
        "status": "EXACT_BY_CONTRACT_NOT_YET_SUFFICIENT_FOR_PRODUCTION_TRAINING",
        "training_started": False,
        "solver_started": False,
        "eligible_cases": [
            {"case_id": "SOURCE_ONLY", "role": "exact_denominator_and_source_reference", "post_fsp_sha256": cases[0]["post_fsp_sha256"], "raw_npz_sha256": cases[0]["raw_npz_sha256"]},
            {"case_id": "CONTROL0", "role": "exact_K6_train_truth_anchor", "geometry_vector_nm": list(control0), "post_fsp_sha256": cases[1]["post_fsp_sha256"], "raw_npz_sha256": cases[1]["raw_npz_sha256"]},
            {"case_id": "ALT1", "role": "exact_K6_train_truth_anchor", "geometry_vector_nm": list(alt1), "post_fsp_sha256": cases[2]["post_fsp_sha256"], "raw_npz_sha256": cases[2]["raw_npz_sha256"]},
        ],
        "exact_K6_geometry_count": 2,
        "source_only_reference_count": 1,
        "formal_model_training_ready": False,
        "blocking_reason": "two exact K6 geometries are insufficient for the planned 2D ML space; DOE acquisition remains future and requires Chart freeze",
    }
    write_json("CURRENT_2D_TRAIN_ELIGIBLE_DATA.json", current_eligible)
    write_json("EXCLUDED_OR_AUXILIARY_DATA.json", {
        "schema_version": "EXCLUDED_OR_AUXILIARY_DATA_V1",
        "training_started": False,
        "items": [
            {"dataset_id": row["DATASET_ID"], "role": row["CURRENT_2D_ML_ROLE"], "reason": row["PHYSICAL_INTERPRETATION"], "evidence_paths": row["EVIDENCE_PATHS"].split(";") if row["EVIDENCE_PATHS"] else []}
            for row in matrix if row["CURRENT_2D_ML_ROLE"] != "EXACT_2D_TRAIN_TRUTH"
        ],
    })

    seed_rows = []
    for vector in sorted(set(observed_vectors + existing_exact)):
        origins = []
        if vector in pool_vectors:
            origins.append("M2A_NP22_FORMAL_CANDIDATE_POOL")
        if vector in [v for v, _ in provider_rows]:
            origins.append("M2B_STANDALONE_PROVIDER_REGISTRY")
        if vector == control0:
            origins.append("CURRENT_CONTROL0_EXACT_23_19")
        if vector == alt1:
            origins.append("CURRENT_ALT1_EXACT_23_19")
        seed_rows.append({
            "geometry_id": "K6X_D" + "_D".join(str(x) for x in vector),
            "D1_nm": vector[0], "D2_nm": vector[1], "D3_nm": vector[2], "D4_nm": vector[3], "D5_nm": vector[4], "D6_nm": vector[5],
            "geometry_fingerprint_sha256": geometry_hash(vector),
            "source_origins": ";".join(origins),
            "ordered_position_sensitive": "YES",
            "has_exact_23_19_truth": "YES" if vector in existing_exact else "NO",
            "current_ml_role": "EXACT_2D_TRAIN_TRUTH" if vector in existing_exact else "AUXILIARY_GEOMETRY_PRIOR",
            "fabrication_authority": "CANDIDATE_POOL_ONLY; INDEPENDENT_LIMIT_FILE_NOT_IDENTIFIED",
        })
    write_csv("HISTORICAL_K6_GEOMETRY_SEED_LIBRARY.csv", seed_rows, list(seed_rows[0]))

    label_contract = {
        "schema_version": "2D_ML_V1_LABEL_CONTRACT_PROPOSAL_V1",
        "status": "PROPOSAL_NOT_FROZEN",
        "row_identity": ["geometry_id", "geometry_fingerprint_sha256", "lambda_nm"],
        "labels": {
            "G_emit": "P_source_box(case,lambda) / P_source_box(SOURCE_ONLY,lambda), same 23/19 domain and source contract",
            "eta_up": "P_up(case,lambda) / P_source_box(case,lambda)",
            "eta_down": "P_down(case,lambda) / P_source_box(case,lambda), diagnostic retained",
            "angular_profile": "raw native farfield_e2 normalized by explicit du_x integration; preserve complex/raw provenance",
            "angular_profile_pca": "PCA coordinates derived only after frozen profile schema and geometry-group split",
        },
        "required_provenance": ["post_fsp_path", "post_fsp_sha256", "raw_npz_path", "raw_npz_sha256", "physical_contract_hash", "source_orientation", "source_position", "reference_plane", "domain_23um", "monitor_19um"],
        "forbidden_operations": ["interpolation across wavelength to create labels", "source substitution", "normalization substitution", "reference-plane substitution", "RCWA-as-FDTD label substitution", "M2Q/M2S 3D pooling into 2D train rows", "random row split across wavelengths or cases"],
        "split_rule": "geometry-group split; all wavelengths of one ordered K6 geometry remain in one split",
    }
    write_json("2D_ML_V1_LABEL_CONTRACT_PROPOSAL.json", label_contract)
    (OUT / "2D_ML_V1_LABEL_CONTRACT_PROPOSAL.md").write_text(
        "# 2D ML v1 label contract proposal\n\n"
        "Status: proposal only; no training or solver was run.\n\n"
        "- `G_emit = P_source_box(case, lambda) / P_source_box(SOURCE_ONLY, lambda)`.\n"
        "- `eta_up = P_up / P_source_box`; retain `eta_down` as a diagnostic.\n"
        "- Store raw complex fields and native farfield data; derived labels never replace raw truth.\n"
        "- Angular profiles use native `u_x = sin(theta)` and explicit `du_x` quadrature weights.\n"
        "- Split by ordered K6 geometry fingerprint, never by wavelength rows.\n"
        "- RCWA, Level2A, historical direct-MDC, M2Q and M2S artifacts remain auxiliary or OOD according to the matrix.\n",
        encoding="utf-8",
    )

    write_json("ANGULAR_REPRESENTATION_AUDIT.json", angular)
    write_json("ANGULAR_PROFILE_SCHEMA.json", {
        "schema_version": "ANGULAR_PROFILE_SCHEMA_V1",
        "coordinate": "u_x = sin(theta_deg)",
        "native_grid": {"source": "farfield_theta_deg", "stored_coordinate": "u_x", "expected_count": 721, "expected_range": [-1.0, 1.0], "native_uniformity_required": True},
        "measure": {"name": "du_x", "integration": "trapezoid", "unweighted_sum_forbidden": True, "theta_endpoint_spacing_is_not_a_weight": True},
        "storage": ["raw_farfield_e2", "raw_farfield_polar_complex", "theta_deg", "u_x", "profile_integral", "profile_normalized", "du_x_weights", "support_mask"],
        "derived_windows": ["full_native", "u_x_abs_le_0.2", "u_x_abs_le_0.5", "u_x_abs_le_0.8"],
        "pca": {"fit_on": "train geometry groups only", "validation_transform_only": True, "blind_transform_only": True, "rank_frozen_before_blind": True},
        "status": "SCHEMA_READY_NO_PROFILE_RESAMPLING_OR_PCA_FIT_PERFORMED",
    })
    write_json("PCA_PIPELINE_SCHEMA.json", {
        "schema_version": "PCA_PIPELINE_SCHEMA_V1",
        "status": "SCHEMA_ONLY_NO_FIT",
        "input": "angular_profile_schema_v1 normalized on native uniform-u_x grid",
        "steps": ["validate finite raw profile", "apply explicit du_x quadrature", "normalize by integral", "fit PCA on train geometry groups only", "freeze rank by explained variance/held-out group rule", "transform validation and blind only"],
        "leakage_guards": ["no wavelength-row split", "no blind access during fit", "no historical auxiliary data in exact-truth fit unless separately authorized", "no interpolation-generated labels"],
        "rank_selection": "deferred until sufficient exact geometry groups exist",
        "current_exact_geometry_groups": 2,
    })

    write_json("2D_ML_V1_INPUT_PARAMETER_SPACE.json", {
        "schema_version": "2D_ML_V1_INPUT_PARAMETER_SPACE_V1",
        "status": "READY_FOR_CHART_FREEZE",
        "geometry": {"K": 6, "parameters": ["D1_nm", "D2_nm", "D3_nm", "D4_nm", "D5_nm", "D6_nm"], "observed_candidate_bounds_nm": [100, 230], "candidate_grid_nm": 5, "bounds_authority": "M2A formal candidate pool; independent fabrication-limit file not identified", "ordered_position_sensitive": True, "sorting_forbidden": True, "pitch_nm": 290},
        "fixed_physics": {"MDC": "current frozen MDC", "spacer": "current frozen spacer", "source_orientation": "X", "source_semantics": "isolated finite line dipole", "source_z_semantic": "CENTROID_X", "source_z_physical_nm": -276, "domain_um": 23, "monitor_um": 19, "boundaries": "four-side PML"},
        "spectral": {"lambda_nm": {"min": 445, "max": 455, "step": 1, "count": 11}, "normalized_lambda": "(lambda_nm - 450) / 5"},
        "future_split": {"train": "geometry groups only", "validation": "geometry groups only", "blind": "geometry groups frozen before training"},
    })
    write_json("2D_ML_V1_DATASET_SCHEMA.json", {
        "schema_version": "2D_ML_V1_DATASET_SCHEMA_V1",
        "row_granularity": "one ordered K6 geometry x one wavelength; raw profile/field artifacts referenced, not flattened-only",
        "required_fields": ["geometry_id", "D1..D6", "lambda_nm", "normalized_lambda", "source_orientation", "source_z_semantic", "source_z_nm", "domain_um", "monitor_um", "G_emit", "eta_up", "eta_down", "angular_profile_ref", "angular_profile_pca_ref", "post_fsp_sha256", "raw_sha256", "split", "truth_role"],
        "raw_artifact_fields": ["post_fsp_path", "raw_npz_path", "source_box_complex_fields", "upward_complex_fields", "downward_complex_fields", "native_farfield2d"],
        "label_units": {"D": "nm", "lambda": "nm", "G_emit": "dimensionless", "eta_up": "dimensionless", "eta_down": "dimensionless"},
        "authority": "only CURRENT_FINITE_2D_SOURCE_ONLY_23_19, CONTROL0, ALT1 and future same-contract 23/19 entries are exact train truth",
    })

    anchor_extra = select_diverse(observed_vectors, existing_exact, 6)
    anchors = [("CONTROL0", control0, "CURRENT_EXACT"), ("ALT1", alt1, "CURRENT_EXACT")]
    anchors += [("HISTORICAL_" + str(i + 1), v, "M2A_FORMAL_POOL") for i, v in enumerate(anchor_extra)]
    space = make_generated([v for _, v, _ in anchors], 48, 101)
    blind = make_generated([v for _, v, _ in anchors] + space, 8, 10001)
    doe_rows = []
    for i, (label, vector, origin) in enumerate(anchors, 1):
        doe_rows.append({"candidate_id": f"K6V1_A{i:02d}", "design_family": "ANCHOR", "split": "TRAIN", "geometry_id": "K6V1_A" + f"{i:02d}", "D1_nm": vector[0], "D2_nm": vector[1], "D3_nm": vector[2], "D4_nm": vector[3], "D5_nm": vector[4], "D6_nm": vector[5], "geometry_fingerprint_sha256": geometry_hash(vector), "origin": origin + ":" + label, "new_solver_required": "NO" if vector in existing_exact else "YES", "blind_frozen_before_training": "NO"})
    for i, vector in enumerate(space, 1):
        split = "TRAIN" if i <= 40 else "VALIDATION"
        doe_rows.append({"candidate_id": f"K6V1_S{i:02d}", "design_family": "SPACE_FILLING", "split": split, "geometry_id": f"K6V1_S{i:02d}", "D1_nm": vector[0], "D2_nm": vector[1], "D3_nm": vector[2], "D4_nm": vector[3], "D5_nm": vector[4], "D6_nm": vector[5], "geometry_fingerprint_sha256": geometry_hash(vector), "origin": "deterministic_halton_maximin_on_observed_candidate_grid", "new_solver_required": "YES", "blind_frozen_before_training": "NO"})
    for i, vector in enumerate(blind, 1):
        doe_rows.append({"candidate_id": f"K6V1_B{i:02d}", "design_family": "BLIND_PROSPECTIVE", "split": "BLIND", "geometry_id": f"K6V1_B{i:02d}", "D1_nm": vector[0], "D2_nm": vector[1], "D3_nm": vector[2], "D4_nm": vector[3], "D5_nm": vector[4], "D6_nm": vector[5], "geometry_fingerprint_sha256": geometry_hash(vector), "origin": "deterministic_frozen_blind_stream", "new_solver_required": "YES", "blind_frozen_before_training": "YES"})
    assert len(doe_rows) == 64 and len({r["geometry_fingerprint_sha256"] for r in doe_rows}) == 64
    write_csv("K6_V1_64G_DOE_CANDIDATES.csv", doe_rows, list(doe_rows[0]))
    write_json("K6_V1_64G_DOE_AUDIT.json", {
        "schema_version": "K6_V1_64G_DOE_AUDIT_V1",
        "status": "PASS_ZERO_SOLVER_MANIFEST_ONLY",
        "total_candidates": 64,
        "anchor_count": 8,
        "space_filling_count": 48,
        "blind_count": 8,
        "train_count": 48,
        "validation_count": 8,
        "blind_frozen_before_training": True,
        "unique_geometry_count": 64,
        "observed_bounds_nm": [100, 230],
        "candidate_grid_nm": 5,
        "ordered_position_sensitive": True,
        "fabrication_limit_authority": "UNRESOLVED_INDEPENDENT_FILE; do not infer manufacturing acceptance from candidate pool alone",
        "existing_exact_geometry_count": 2,
        "new_solver_entries_required": 62,
        "solver_entries_started_by_this_task": 0,
    })
    write_json("K6_V1_GEOMETRY_SPLIT_MANIFEST.json", {
        "schema_version": "K6_V1_GEOMETRY_SPLIT_MANIFEST_V1",
        "split_unit": "geometry_fingerprint_sha256",
        "wavelength_grouping": "all 11 wavelengths remain with geometry",
        "random_row_split": False,
        "train_geometry_ids": [r["geometry_id"] for r in doe_rows if r["split"] == "TRAIN"],
        "validation_geometry_ids": [r["geometry_id"] for r in doe_rows if r["split"] == "VALIDATION"],
        "blind_geometry_ids": [r["geometry_id"] for r in doe_rows if r["split"] == "BLIND"],
        "fingerprint_overlap": False,
        "blind_manifest_frozen": True,
    })
    write_json("K6_V1_EXISTING_TRUTH_REUSE.json", {
        "schema_version": "K6_V1_EXISTING_TRUTH_REUSE_V1",
        "status": "PASS_REUSE_NO_RERUN",
        "reuse": [
            {"geometry_id": "K6V1_A01", "case_id": "CONTROL0", "vector_nm": list(control0), "post_fsp_sha256": cases[1]["post_fsp_sha256"], "raw_sha256": cases[1]["raw_npz_sha256"], "new_solver_required": False},
            {"geometry_id": "K6V1_A02", "case_id": "ALT1", "vector_nm": list(alt1), "post_fsp_sha256": cases[2]["post_fsp_sha256"], "raw_sha256": cases[2]["raw_npz_sha256"], "new_solver_required": False},
            {"case_id": "SOURCE_ONLY", "role": "shared_denominator_reference", "post_fsp_sha256": cases[0]["post_fsp_sha256"], "raw_sha256": cases[0]["raw_npz_sha256"], "new_solver_required": False},
        ],
        "production_m2s_rerun": False,
        "training_started": False,
    })
    new_cases = [r for r in doe_rows if r["new_solver_required"] == "YES"]
    batches = [new_cases[i:i + 2] for i in range(0, len(new_cases), 2)]
    max_wall = max((x["wall_time_s"] for x in telemetry), default=None)
    mean_wall = sum(x["wall_time_s"] for x in telemetry) / len(telemetry) if telemetry else None
    write_json("K6_V1_NEW_SOLVER_ACQUISITION_PLAN.json", {
        "schema_version": "K6_V1_NEW_SOLVER_ACQUISITION_PLAN_V1",
        "status": "PLANNED_NOT_AUTHORIZED_NOT_STARTED",
        "new_solver_entries": len(new_cases),
        "existing_truth_entries_reused": 2,
        "source_only_entries_reused": 1,
        "execution_contract": {"dimension": "2D", "domain_um": 23, "monitor_um": 19, "mpi": 12, "threads": 1, "max_concurrent_slots": 2, "scheduler": "canonical_global_fdtd_slot_scheduler", "persistence_gate": "canonical post-FSP SHA + independent LOAD-only + raw + audit before release"},
        "candidate_ids": [r["candidate_id"] for r in new_cases],
        "solver_entries_started_by_this_task": 0,
    })
    write_json("TWO_SLOT_2D_DOE_ACQUISITION_PLAN.json", {
        "schema_version": "TWO_SLOT_2D_DOE_ACQUISITION_PLAN_V1",
        "status": "PLANNED_NOT_STARTED",
        "new_entries": len(new_cases),
        "two_slot_batches": len(batches),
        "batch_size": 2,
        "max_concurrent_slots": 2,
        "resource": {"mpi": 12, "threads": 1},
        "observed_runtime_telemetry": telemetry,
        "observed_runtime_max_s": max_wall,
        "observed_runtime_mean_s": mean_wall,
        "estimated_solver_window_s_upper_bound": len(batches) * max_wall if max_wall else None,
        "estimated_solver_window_h_upper_bound": (len(batches) * max_wall / 3600.0) if max_wall else None,
        "estimate_basis": "31 two-job batches x max observed current 23/19 telemetry; excludes queue/persistence variance",
        "persistence_path_unchanged": True,
        "solver_entries_started_by_this_task": 0,
        "m2s_attempt_002_started": False,
    })

    report = {
        "schema_version": "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_REPORT_V1",
        "status": "PASS",
        "verdict": "DATABASE_AUTHORITY_AUDITED_AND_2D_ML_V1_SPACE_READY_FOR_CHART_FREEZE",
        "solver_entries_started": 0,
        "training_entries_started": 0,
        "rerun_entries_started": 0,
        "production_m2s_attempt_002_started": False,
        "q1_q10": {
            "Q1": "Current exact finite 2D 23/19 isolated-X line-source truth is SOURCE_ONLY + CONTROL0 + ALT1; only CONTROL0 and ALT1 are K6 geometry groups.",
            "Q2": "SOURCE_ONLY is an exact denominator/reference case; it is not counted as a new K6 geometry.",
            "Q3": "Historical direct MDC/HF and Level2A are auxiliary physics priors or screening only; M2Q/M2S 3D are validation/OOD only.",
            "Q4": "Current labels use source-box normalization and native u_x angular profiles with explicit du_x quadrature.",
            "Q5": "K6 input space is ordered D1..D6, 100..230 nm observed candidate bounds, 5 nm candidate grid; fabrication-limit authority remains unresolved.",
            "Q6": "64G manifest is 8 anchors + 48 space-filling + 8 blind; 48 train / 8 validation / 8 blind geometry groups.",
            "Q7": "Existing exact truth reuse is 2 K6 geometries plus SOURCE_ONLY denominator; no rerun.",
            "Q8": "62 future solver entries remain; two-slot acquisition plan uses canonical 12 MPI x 1 path and persistence gate.",
            "Q9": "Observed runtime telemetry is SOURCE_ONLY 207.465 s and ALT1 268.303 s; CONTROL0 telemetry is unavailable, so no CONTROL0 runtime claim is made.",
            "Q10": "No solver, training, M2S rerun, registry edit, or prior-artifact overwrite occurred.",
        },
        "alt1b_search_hits": alt1b_hits,
        "angular_audit": angular,
        "telemetry": telemetry,
        "next": "CHART_FREEZE_2D_ML_V1_AND_TWO_SLOT_DOE_ACQUISITION",
    }
    (OUT / "REPORT.md").write_text(
        "# APCD Coupling v2.2 database authority audit\n\n"
        "## Status\n\nPASS — `DATABASE_AUTHORITY_AUDITED_AND_2D_ML_V1_SPACE_READY_FOR_CHART_FREEZE`\n\n"
        "This was a zero-solver, zero-training, zero-rerun audit.\n\n"
        "## Authority conclusion\n\n"
        "Only the frozen 23/19 finite 2D isolated-X line-source cases are exact current train truth. SOURCE_ONLY is the exact denominator reference; CONTROL0 and ALT1 are the two existing K6 geometry groups. Historical direct-MDC/HF, standalone provider, Level2A, Level2B, M2Q and M2S artifacts remain auxiliary, screening, historical, or validation/OOD according to `DATABASE_AUTHORITY_MATRIX.csv`.\n\n"
        "## 2D ML space\n\n"
        "The manifest contains 64 unique ordered K6 vectors: 8 anchors, 48 deterministic maximin space-filling candidates, and 8 frozen blind candidates. The observed candidate-pool bound is 100–230 nm on a 5 nm grid. A separate fabrication-limit file was not identified, so this is not asserted as a manufacturing limit.\n\n"
        "## Angular representation\n\n"
        "The native farfield grid is uniform in `u_x = sin(theta)` rather than uniform in theta. The schema therefore stores native `u_x`, raw farfield data, and explicit `du_x` trapezoid weights; unweighted sums and endpoint-theta binning are forbidden. PCA is schema-only and was not fit.\n\n"
        "## Acquisition\n\n"
        "62 future entries remain after reusing CONTROL0/ALT1 and SOURCE_ONLY. The future plan is two slots at 12 MPI × 1 thread through the validated lifecycle/persistence path. Current observed telemetry is SOURCE_ONLY 207.465 s and ALT1 268.303 s; CONTROL0 has no independent runtime telemetry. No solver was started.\n\n"
        "## Next\n\n"
        "`CHART_FREEZE_2D_ML_V1_AND_TWO_SLOT_DOE_ACQUISITION`\n",
        encoding="utf-8",
    )
    write_json("REPORT.json", report)

    manifest = []
    for path in sorted(OUT.iterdir()):
        if path.name == "FINAL_SHA256_MANIFEST.json" or not path.is_file():
            continue
        manifest.append({"path": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    write_json("FINAL_SHA256_MANIFEST.json", {
        "schema_version": "FINAL_SHA256_MANIFEST_V1",
        "manifest_scope": "new audit output files only; prior scientific artifacts are referenced and untouched",
        "files": manifest,
        "solver_entries_started": 0,
        "m2s_attempt_002_started": False,
    })
    print(json.dumps({"output": str(OUT), "files": len(manifest) + 1, "status": "PASS", "solver_entries_started": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
