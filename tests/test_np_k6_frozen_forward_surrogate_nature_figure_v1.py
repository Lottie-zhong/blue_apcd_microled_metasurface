from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
OUT = ROOT / "outputs/np_k6_frozen_forward_surrogate_nature_figure_v1"
FIG = ROOT / "figures/np_k6_frozen_forward_surrogate_nature_figure_v1"


def j(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def c(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_frozen_provider_and_scope_contract():
    m = j("figure_manifest.json")
    assert m["scope"]["geometries"] == 22
    assert m["scope"]["hf_rows"] == 484
    assert m["scope"]["u_x"] == [0.0]
    assert m["providers"]["ranking"]["model"] == "LF_only"
    assert m["providers"]["spectral"]["model"] == "LF_ridge_residual"
    assert m["data_governance"]["training_predictions_used"] is False
    assert all(m["data_governance"][key] == 0 for key in ("new_solver_calls", "new_rcwa_calls", "new_ml_training", "external_hf", "inverse", "data_regeneration"))


def test_geometry_level_ranking_and_programmatic_representatives():
    ranking = c("heldout_geometry_ranking_data.csv")
    assert len(ranking) == 22
    assert len({r["geometry_id"] for r in ranking}) == 22
    assert all(r["sample_unit"].startswith("one held-out K6 geometry") for r in ranking)
    selected = j("representative_cases.json")["selected_cases"]
    assert [r["rank_ascending_eta_plus1_mae"] for r in selected] == [1, 11, 22]
    assert {r["selection"] for r in selected} == {"Best", "Median", "Worst"}


def test_spectral_and_export_bundle():
    spectral = c("representative_spectral_data.csv")
    assert len(spectral) == 66
    assert {int(r["wavelength_nm"]) for r in spectral} == set(range(445, 456))
    assert {r["polarization"] for r in spectral} == {"p", "s"}
    assert not list(OUT.rglob("*.fsp"))
    for suffix in ("png", "pdf", "svg"):
        p = FIG / f"np_k6_frozen_forward_surrogate_nature_figure_v1.{suffix}"
        assert p.is_file() and p.stat().st_size > 10_000
