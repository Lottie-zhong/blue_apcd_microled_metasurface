#!/usr/bin/env python3
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/np_k6_coupling_forward_feature_interface_v1"
def main():
    manifest = json.loads((OUT/"interface_manifest.json").read_text(encoding="utf-8"))
    support = json.loads((OUT/"coupling_20g_domain_support.json").read_text(encoding="utf-8"))
    cap = json.loads((OUT/"capability_boundary.json").read_text(encoding="utf-8"))
    prov = json.loads((OUT/"provenance.json").read_text(encoding="utf-8"))
    assert manifest["interface_name"] == "NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_V1"
    assert manifest["status"] == "NP_COUPLING_FORWARD_FEATURE_INTERFACE_READY"
    assert support["coupling_20g_case_count"] == 20
    assert support["exact_overlap_count"] == 0
    assert support["extrapolative_count"] == 20
    assert support["all_20g_ordered_domain_extrapolative"]
    assert not cap["complex_capabilities"]["COMPLEX_SCATTERING_STATE_AVAILABLE"]
    assert prov["governance"]["solver_calls"] == 0
    assert prov["governance"]["sealed_hf_target_reads"] == 0
    assert prov["governance"]["coupling_target_or_performance_labels_read"] == 0
    print("NP_K6_COUPLING_FORWARD_FEATURE_INTERFACE_VALIDATOR_PASS")
if __name__ == "__main__":
    main()
