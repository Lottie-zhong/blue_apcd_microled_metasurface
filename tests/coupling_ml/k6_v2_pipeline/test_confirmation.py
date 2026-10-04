from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest

from scripts.coupling_ml.k6_v2_pipeline import confirmation as cf
from scripts.coupling_ml.k6_v2_pipeline import contracts as C
from scripts.coupling_ml.k6_v2_pipeline.ingest import ConfirmationCaseTruth, RevealAuthorization
from scripts.coupling_ml.k6_v2_pipeline.contracts import CaseTruth


def _repo():
    return Path(__file__).resolve().parents[3]


def test_freeze_prediction_artifacts_roundtrip_without_response_access(tmp_path):
    root = _repo()
    reg = cf.load_frozen_case_registry(root)
    pred_paths, artifacts = {}, {}
    for name in ("RBF_KRR", "CARTESIAN_MLP", "LOCAL_AFFINE"):
        ids = cf._ids(reg, name)
        nseed = 3 if name == "CARTESIAN_MLP" else 1
        seeds = (0, 1, 2) if nseed == 3 else (-1,)
        c = np.ones((nseed, len(ids), 21, 7, 2), dtype=np.complex128)
        p = np.ones((nseed, len(ids), 21), dtype=np.float64)
        pp = tmp_path / f"{name}.npz"
        cf.write_prediction_bundle(pp, name=name, case_ids=ids,
                                   c_hat_by_seed=c, p_scale_by_seed=p, seed_values=seeds)
        pred_paths[name] = pp
        artifacts[name] = {}
        for kind in ("config", "model", "preprocessing"):
            artifact = tmp_path / f"{name}.{kind}.bin"
            artifact.write_bytes((name + kind).encode())
            artifacts[name][kind] = artifact
    manifest, digest = cf.freeze_prediction_artifacts(
        output_path=tmp_path / "freeze.json", prediction_paths=pred_paths,
        artifacts=artifacts, repository_root=root,
    )
    loaded = cf.load_frozen_predictions(manifest, digest, repository_root=root)
    assert set(loaded.bundles) == {"RBF_KRR", "CARTESIAN_MLP", "LOCAL_AFFINE"}
    assert loaded.bundles["CARTESIAN_MLP"].c_hat_by_seed.shape == (3, 28, 21, 7, 2)
    assert loaded.bundles["RBF_KRR"].p_scale_by_seed.shape == (1, 28, 21)
    assert json.loads(manifest.read_text())["confirmation_responses_opened"] is False


def test_confirmation_evaluation_reports_all_strata_and_is_one_shot(tmp_path, monkeypatch):
    root = _repo()
    reg = cf.load_frozen_case_registry(root)
    gids, lids = cf._ids(reg, "RBF_KRR"), cf._ids(reg, "LOCAL_AFFINE")
    allids = tuple(reg.confirmation)
    cases = []
    for cid in allids:
        row = reg.confirmation[cid]
        role = row["effective_role"] if row.get("effective_role") else row["role"]
        truth = CaseTruth(cid, "attempt_001", role, tuple(row["ordered_D_nm"]),
            np.ones((21, 7, 2), complex), np.ones(21), np.full((21, 7), 1/7),
            np.full((21, 7), 1/7), {})
        cases.append(ConfirmationCaseTruth(truth, row["role"], "CORE"))
    bundles = {}
    for name, ids, ns, seeds in (
        ("RBF_KRR", gids, 1, (-1,)),
        ("CARTESIAN_MLP", gids, 3, (0, 1, 2)),
        ("LOCAL_AFFINE", lids, 1, (-1,)),
    ):
        bundles[name] = cf.PredictionBundle(
            name, ids, np.ones((ns, len(ids), 21, 7, 2), complex),
            np.ones((ns, len(ids), 21)), {},
        )
    freeze = tmp_path / "freeze.json"
    freeze.write_text("synthetic frozen marker")
    frozen = cf.FrozenPredictions(freeze, "frozen-sha", bundles)
    auth = object.__new__(RevealAuthorization)
    auth.freeze_sha = "frozen-sha"
    auth.freeze_path = str(freeze.resolve())
    auth.ids = frozenset(allids)
    auth.used = set(allids)
    monkeypatch.setattr(cf, "load_frozen_case_registry", lambda root: reg)
    monkeypatch.setattr(cf, "load_frozen_predictions", lambda *a, **k: frozen)
    calls = []
    def fake_h1(ct, cp, pt, pp, et, at, decoder=None):
        calls.append(len(ct))
        return {
            "all_applicable_numeric_gates_attained": True,
            "seed_stability_status": "PASS" if len(cp) == 3 else "NOT_APPLICABLE_DETERMINISTIC_CANDIDATE",
        }
    monkeypatch.setattr("scripts.coupling_ml.k6_v2_pipeline.h1.evaluate_original_h1", fake_h1)
    monkeypatch.setattr("scripts.coupling_ml.k6_v2_pipeline.h1.load_h2_decoder", lambda: object())
    output = cf.evaluate_confirmation_once(
        cases, frozen, auth, evaluation_ledger_path=tmp_path / "ledger.jsonl",
        report_path=tmp_path / "report.json", repository_root=root,
    )
    assert output["counts"] == {"local": 4, "global_core": 27, "global_stress": 1, "global_all": 28}
    assert len(calls) == 6 and sorted(calls) == [1, 1, 27, 27, 28, 28]
    assert output["decision"] == "exactly_one_candidate_passes"
    assert output["global"]["RBF_KRR"]["all28"]["all_original_gates_pass"] is False
    assert output["global"]["CARTESIAN_MLP"]["all28"]["all_original_gates_pass"] is True
    assert output["production_admission"] is False
    with pytest.raises(FileExistsError, match="already_started"):
        cf.evaluate_confirmation_once(
            cases, frozen, auth, evaluation_ledger_path=tmp_path / "ledger.jsonl",
            report_path=tmp_path / "report.json", repository_root=root,
        )
