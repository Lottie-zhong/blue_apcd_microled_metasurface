from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_v1"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_nature_figure_v1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_rows(name: str) -> list[dict[str, str]]:
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check(ok: bool, label: str, errors: list[str]) -> None:
    if not ok:
        errors.append(label)


def main() -> None:
    errors: list[str] = []
    manifest = json.loads((OUT / "figure_manifest.json").read_text(encoding="utf-8"))
    contract = json.loads((OUT / "figure_contract.json").read_text(encoding="utf-8"))
    selections = json.loads((OUT / "representative_cases.json").read_text(encoding="utf-8"))["selected_cases"]
    ranking = csv_rows("heldout_geometry_ranking_data.csv")
    spectral = csv_rows("representative_spectral_data.csv")
    check(manifest["artifact_id"] == "NP_K6_FROZEN_FORWARD_SURROGATE_NATURE_FIGURE_V1", "artifact_id", errors)
    check(manifest["scope"] == {"u_x": [0.0], "normal_incidence_only": True, "geometries": 22, "polarizations": ["p", "s"], "wavelengths_nm": list(range(445, 456)), "hf_rows": 484}, "scope", errors)
    check(manifest["providers"]["ranking"]["model"] == "LF_only", "ranking_provider", errors)
    check(manifest["providers"]["spectral"]["model"] == "LF_ridge_residual", "spectral_provider", errors)
    check(abs(manifest["metrics"]["ranking_spearman"] - 0.961603613777527) < 1e-12, "ranking_rho", errors)
    check(len(ranking) == 22 and len({r["geometry_id"] for r in ranking}) == 22, "ranking_units", errors)
    check(all(r["sample_unit"].startswith("one held-out K6 geometry") for r in ranking), "ranking_unit_definition", errors)
    check(len(spectral) == 66, "spectral_rows", errors)
    check({r["selection"] for r in spectral} == {"Best", "Median", "Worst"}, "spectral_selection_labels", errors)
    check({int(r["wavelength_nm"]) for r in spectral} == set(range(445, 456)), "wavelength_support", errors)
    check({r["polarization"] for r in spectral} == {"p", "s"}, "polarization_scope", errors)
    check([x["rank_ascending_eta_plus1_mae"] for x in selections] == [1, 11, 22], "programmatic_rank_selection", errors)
    check(all(x["geometry_count"] == 22 for x in selections), "selected_geometry_count", errors)
    check(manifest["data_governance"] == {"heldout_oof_only": True, "training_predictions_used": False, "new_solver_calls": 0, "new_rcwa_calls": 0, "new_ml_training": 0, "external_hf": 0, "inverse": 0, "data_regeneration": 0}, "zero_compute_governance", errors)
    check("separate frozen components" in contract["reviewer_risk"], "provider_distinction", errors)
    for entry in manifest["source_artifacts"].values():
        p = ROOT / entry["path"]
        check(p.is_file() and sha(p) == entry["sha256"], f"source_hash:{entry['path']}", errors)
    for suffix in ("png", "pdf", "svg"):
        p = FIG / f"np_k6_frozen_forward_surrogate_nature_figure_v1.{suffix}"
        check(p.is_file() and p.stat().st_size > 10_000, f"figure_output:{suffix}", errors)
    check(not list(OUT.rglob("*.fsp")) and not list(FIG.rglob("*.fsp")), "no_fsp", errors)
    report = {"status": "PASS" if not errors else "FAIL", "errors": errors, "heldout_geometries": len(ranking), "hf_rows": manifest["scope"]["hf_rows"], "representative_spectral_rows": len(spectral), "solver_calls": 0, "rcwa_calls": 0, "ml_training": 0}
    (OUT / "figure_validator_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
