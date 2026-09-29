import csv, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "np_k6_complex_two_port_reference_plane_contract_v1"

def j(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def main():
    m, c, s, p, d = (j(n) for n in ("contract_manifest.json", "coordinate_audit.json", "coefficient_semantics_audit.json", "incident_phase_audit.json", "deembedding_transform_audit.json"))
    cg, cm = j("coupling_geometry_domain_audit.json"), j("coupling_mapping_audit.json")
    assert m["primary_verdict"] == "NP_COMPLEX_COEFFICIENT_NOT_COMPOSABLE_AS_SCATTERING_STATE"
    assert m["scientific_authority"]["frozen_commit"] == "c8e6eb422ed7d63d6a4608fd823341c929bd2b8f"
    assert m["scope"] == {"hf_geometries": 22, "logical_cases": 44, "rows": 484, "wavelengths_nm": list(range(445, 456)), "u_x": 0.0, "k_y": 0.0, "ordered_geometry": ["D1", "D2", "D3", "D4", "D5", "D6"], "polarizations": ["P", "S"]}
    assert c["coordinate_values_nm"]["candidate_input_port"] == "0^-" and c["coordinate_values_nm"]["candidate_output_port"] == "500^+"
    assert s["incident_complex_amplitude_division"] is False and s["source_reference_deembedding"] is False and s["per_case_phase_rescaling"] is False
    assert p["status"] == "HARD_GATE_INCIDENT_COMPLEX_PHASE_REFERENCE_NOT_RECOVERABLE" and d["status"] == "CONDITIONAL_ANALYTIC_ONLY_NOT_FROZEN"
    assert cg["coupling_case_count"] == 20 and cg["exact_geometry_overlap_count"] == 0 and cg["coupling_performance_labels_read"] == 0 and cg["coupling_h1_errors_read"] == 0 and cg["sealed_target_read"] == 0 and cm["target_reads"] == 0
    rows = list(csv.DictReader(open(OUT / "coupling_geometry_domain_audit.csv", encoding="utf-8-sig")))
    assert len(rows) == 20 and all(x["classification"] == "extrapolative" for x in rows)
    for name, item in j("artifact_checksums.json").items():
        if name == "artifact_checksums.json":
            continue
        path = ROOT / name if name.startswith("reports/") else OUT / name
        assert path.exists() and sha(path) == item["sha256"], name
    print("NP_K6_COMPLEX_TWO_PORT_REFERENCE_PLANE_CONTRACT_V1_VALIDATOR_PASS")

if __name__ == "__main__":
    main()
