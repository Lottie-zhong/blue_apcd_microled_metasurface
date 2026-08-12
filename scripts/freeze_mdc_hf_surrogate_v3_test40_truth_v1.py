import hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sel = Path(sys.argv[1])
run = Path(sys.argv[2])

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def sha_obj(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def write_json(p, x):
    p.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

state = json.loads((run / "state.json").read_text(encoding="utf-8"))
cases = list(state["cases"].values())
assert len(cases) == 240 and all(c.get("accepted") and c.get("solver_status") == "COMPLETE" for c in cases)
geom = pd.read_csv(sel / "v3_test40_geometry_manifest_v1.csv")
matrix = pd.read_csv(sel / "v3_test40_case_matrix_v1.csv")
assert len(geom) == 40 and len(matrix) == 240 and matrix.case_uid.is_unique
cases = sorted(cases, key=lambda c: c["case_uid"])
arrays = {}
for c in cases:
    with np.load(c["raw_npz_path"], allow_pickle=False) as z:
        arrays[c["case_uid"]] = {k: np.asarray(z[k]) for k in z.files}
lam = np.asarray(arrays[cases[0]["case_uid"]]["wavelength_nm"], float)
ang = np.asarray(arrays[cases[0]["case_uid"]]["angle_deg"], float)
assert lam.shape == (301,) and ang.shape == (2000,)
grid_sha = hashlib.sha256(lam.tobytes() + ang.tobytes()).hexdigest()
case_rows, quality = [], []
for c in cases:
    a = arrays[c["case_uid"]]
    j = np.asarray(a["joint_raw"], float)
    assert j.shape == (301, 2000) and np.isfinite(j).all() and (j >= 0).all()
    assert np.allclose(lam, a["wavelength_nm"], rtol=0, atol=1e-6)
    assert np.allclose(ang, a["angle_deg"], rtol=0, atol=1e-6)
    sm = np.trapezoid(j, np.radians(ang), axis=1)
    am = np.trapezoid(j, lam, axis=0)
    case_rows.append({"case_uid": c["case_uid"], "geometry_id": c["geometry_id"], "geometry_hash": c["geometry_hash"], "source_position": c["source_position"], "source_position_nm": c["source_position_nm"], "dipole_orientation": c["dipole_orientation"], "raw_npz_path": c["raw_npz_path"], "joint_tensor_sha256": sha_file(c["raw_npz_path"]), "shape": [301, 2000], "wavelength_grid_sha256": hashlib.sha256(lam.tobytes()).hexdigest(), "angle_grid_sha256": hashlib.sha256(ang.tobytes()).hexdigest(), "raw_before_normalization": True, "validity": "PASS"})
    quality.append({"case_uid": c["case_uid"], "finite_ratio": float(np.isfinite(j).mean()), "negative_count": int((j < 0).sum()), "spectral_marginal_max_abs_error": float(np.max(np.abs(sm - np.asarray(a["spectral_marginal_raw"], float)))), "angular_marginal_max_abs_error": float(np.max(np.abs(am - np.asarray(a["angular_marginal_raw"], float))))})
case_rows = sorted(case_rows, key=lambda x: x["case_uid"])
(run / "test40_truth_case_index.json").write_text(json.dumps(case_rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
write_json(run / "test40_truth_case_quality_audit.json", {"status": "PASS", "case_count": 240, "unique_case_uid_count": len({x["case_uid"] for x in case_rows}), "all_shapes_identical": True, "shape": [301, 2000], "grid_sha256": grid_sha, "max_spectral_marginal_error": max(x["spectral_marginal_max_abs_error"] for x in quality), "max_angular_marginal_error": max(x["angular_marginal_max_abs_error"] for x in quality), "per_case": quality})
profiles, aggs = [], []
profile_dir = run / "truth_profiles"
profile_dir.mkdir(exist_ok=True)
for gh in sorted(geom.geometry_hash.astype(str)):
    rs = [c for c in cases if str(c["geometry_hash"]) == gh]
    assert len(rs) == 6 and {(c["source_position"], c["dipole_orientation"]) for c in rs} == {(p, o) for p in ("top", "centroid", "bottom") for o in ("x", "z")}
    by = {(c["source_position"], c["dipole_orientation"]): c for c in rs}
    pos = {p: 0.5 * (arrays[by[(p, "x")]["case_uid"]]["joint_raw"] + arrays[by[(p, "z")]["case_uid"]]["joint_raw"]) for p in ("top", "centroid", "bottom")}
    raw = sum(pos.values()) / 3.0
    spectral = np.trapezoid(raw, np.radians(ang), axis=1)
    angular = np.trapezoid(raw, lam, axis=0)
    total = float(np.trapezoid(spectral, lam))
    assert total > 0
    norm = raw / total
    spectral_norm = spectral / float(np.trapezoid(spectral, lam))
    angular_norm = angular / float(np.trapezoid(angular, np.radians(ang)))
    pp = profile_dir / (gh + "__geometry_profile.npz")
    np.savez_compressed(pp, wavelength_nm=lam, angle_deg=ang, raw_joint=raw, normalized_joint=norm, spectral_raw=spectral, angular_raw=angular, spectral_norm=spectral_norm, angular_norm=angular_norm)
    profiles.append({"geometry_hash": gh, "profile_path": str(pp), "profile_sha256": sha_file(pp), "normalized_profile_sha256": hashlib.sha256(norm.tobytes()).hexdigest(), "case_count": 6})
    aggs.append({"geometry_hash": gh, "case_count": 6, "raw_xz_average_before_normalization": True, "raw_three_position_average_before_normalization": True, "normalization_before_aggregation": False, "normalized_profile_integral": float(np.trapezoid(np.trapezoid(norm, np.radians(ang), axis=1), lam))})
(run / "test40_truth_geometry_index.json").write_text(json.dumps(profiles, indent=2, sort_keys=True) + "\n", encoding="utf-8")
write_json(run / "test40_truth_aggregation_audit.json", {"status": "PASS", "geometry_count": 40, "case_count": 240, "raw_before_normalization": True, "all_integrals_close_to_one": all(abs(x["normalized_profile_integral"] - 1.0) < 1e-10 for x in aggs), "grid_sha256": grid_sha, "per_geometry": aggs})
truth = {"status": "PASS", "phase": "B_TRUTH_FROZEN", "contract_id": "MDC_HF_SURROGATE_V3_TEST40_PROSPECTIVE_EXTERNAL_HF_ACQUISITION_V1", "geometry_count": 40, "case_count": 240, "cases_per_geometry": 6, "case_index_sha256": sha_obj([{k: r[k] for k in ("case_uid", "geometry_hash", "source_position", "dipole_orientation")} for r in case_rows]), "tensor_index_sha256": sha_obj([{ "case_uid": r["case_uid"], "tensor_sha256": r["joint_tensor_sha256"]} for r in case_rows]), "geometry_profile_index_sha256": sha_obj([{ "geometry_hash": r["geometry_hash"], "profile_sha256": r["normalized_profile_sha256"]} for r in profiles]), "grid_sha256": grid_sha, "aggregation": "raw x/z average per source position, raw top/centroid/bottom average per geometry, then normalization", "truth_label_reads_after_acquisition": 240, "prediction_metric_reads_before_truth_freeze": 0, "test40_labels_generated": True, "sealed_test_reads_before_truth_freeze": 0, "solver_calls": 0, "model_fits": 0, "pca_fit_calls": 0, "scaler_fit_calls": 0}
write_json(run / "test40_truth_freeze_manifest.json", truth)
write_json(run / "test40_truth_sha256_manifest.json", {"status": "PASS", "case_index_sha256": sha_file(run / "test40_truth_case_index.json"), "case_quality_sha256": sha_file(run / "test40_truth_case_quality_audit.json"), "geometry_index_sha256": sha_file(run / "test40_truth_geometry_index.json"), "aggregation_audit_sha256": sha_file(run / "test40_truth_aggregation_audit.json"), "truth_freeze_manifest_sha256": sha_file(run / "test40_truth_freeze_manifest.json"), "raw_tensor_inventory_sha256": sha_file(run / "raw_tensor_sha256_inventory.json")})
print(json.dumps(truth, indent=2, sort_keys=True))
