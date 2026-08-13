"""Contract tests for the frozen MDC V3 -> MDC-NP handoff."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            block = f.read(1 << 20)
            if not block:
                break
            h.update(block)
    return h.hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--package", required=True); a = ap.parse_args(); root = Path(a.package)
    required = {
        "mdc_v3_model_identity.json", "mdc_v3_capability_scope.json", "mdc_v3_external_evidence.json",
        "mdc_v3_diversity_limitations.json", "level0_mdc_provider_contract.json",
        "level1_direct_hf_provider_contract.json", "level2_joint_hf_boundary.json",
        "mdc_np_error_attribution_roadmap.json", "source_artifact_registry.json",
        "completion_manifest.json", "artifact_sha256.json",
    }
    assert all((root / p).exists() for p in required)
    ident = load(root / "mdc_v3_model_identity.json")
    scope = load(root / "mdc_v3_capability_scope.json")
    ext = load(root / "mdc_v3_external_evidence.json")
    div = load(root / "mdc_v3_diversity_limitations.json")
    l0 = load(root / "level0_mdc_provider_contract.json")
    l1 = load(root / "level1_direct_hf_provider_contract.json")
    l2 = load(root / "level2_joint_hf_boundary.json")
    road = load(root / "mdc_np_error_attribution_roadmap.json")
    reg = load(root / "source_artifact_registry.json")
    comp = load(root / "completion_manifest.json")
    assert ident["model_id"] == "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1"
    assert ident["architecture"] == "V3-C" and ident["epochs"] == 117 and len(ident["seeds"]) == 5
    assert ident["development_membership"] == {"geometries": 200, "cases": 1200}
    assert scope["scope"] == "RANKING_SCREENING_ONLY"
    assert "quantitative FDTD replacement" in scope["not_supported"]
    assert ext["global"]["profile_composite"] == 1.0085589544190385
    assert ext["topology"]["ZL2"]["profile_composite"] > ext["topology"]["Explicit"]["profile_composite"]
    assert div["canonical_decoded_profile_pca_variance_median_ratio"] == 0.09777830417863428
    assert div["canonical_decoded_profile_components_below_0_25"] == 30
    assert div["formal_direct_latent_ratio_interpretation"].startswith("numerically valid")
    assert l0["power_claim"] is False and "V3 predicted power" in l0["forbidden_outputs"]
    assert l1["provider"] == "direct MDC HF provider" and l1["v3_power_in_formula"] is False
    assert l2["provider"] == "integrated joint HF" and l2["standalone_v3_substitution_for_truth"] is False
    assert road["authorized_now"] is False and road["future_trigger"] == "MDC_STANDALONE_PROFILE_ERROR_DOMINANT"
    assert reg["read_only"] is True and reg["coupling_worktree_written"] is False and reg["test40_new_reads"] == 0
    for k in ("solver_calls", "training_fits", "backward_calls", "optimizer_calls", "pca_fit_calls", "scaler_fit_calls", "test40_new_reads", "test40_new_generation", "checkpoint_modifications"):
        assert comp[k] == 0
    manifest = load(root / "artifact_sha256.json")
    assert manifest["file_count"] == len(manifest["files"])
    for rel, expected in manifest["files"].items(): assert sha(root / rel) == expected, rel
    print(json.dumps({"status": "PASS", "required": len(required), "sha_entries": manifest["file_count"], "solver": comp["solver_calls"], "training": comp["training_fits"], "test40_new_reads": comp["test40_new_reads"]}, sort_keys=True))

if __name__ == "__main__": main()
