"""Outcome-blind final-epoch policy for MDC HF Surrogate V3.

This module only validates synthetic/future fit metadata and derives an epoch
from eligible inner-stop values.  It has no solver, model-fit, optimizer,
backward, PCA, scaler, or label-loading entry point.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "mdc_hf_surrogate_v2" / "v3_final_epoch_policy_v1" / "v3_final_epoch_policy_v1.json"
MIN_EPOCH = 50
MAX_EPOCH = 400
EXPECTED_FITS = 15
FROZEN_SEEDS = (20260810, 20260811, 20260812)
ALLOWED_ARCHITECTURES = ("V3-A", "V3-B", "V3-C")


class FinalEpochPolicyError(ValueError):
    """Raised when a proposed epoch derivation violates the frozen policy."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path = CONTRACT_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_policy(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract_id") != "MDC_HF_SURROGATE_V3_FINAL_EPOCH_POLICY_V1":
        raise FinalEpochPolicyError("unexpected final epoch contract id")
    return payload


def round_half_up(value: float | int | Decimal) -> int:
    """Decimal round-half-up; never Python bankers rounding."""
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def eligible_best_epoch(
    history: Mapping[int | str, float],
    *,
    monitor: str = "inner_stop_validation_geometry_level_profile_only_composite",
    source: str = "inner_stop_validation",
    uses_outer_fold: bool = False,
    uses_power: bool = False,
    uses_auxiliary: bool = False,
    uses_v3_test40: bool = False,
    uses_final_development_loss: bool = False,
) -> dict[str, Any]:
    """Select the earliest epoch at the minimum metric in [50, 400]."""
    forbidden = uses_outer_fold or uses_power or uses_auxiliary or uses_v3_test40 or uses_final_development_loss
    if monitor != "inner_stop_validation_geometry_level_profile_only_composite" or source != "inner_stop_validation" or forbidden:
        raise FinalEpochPolicyError("checkpoint monitor/source is outside frozen inner-stop profile-only contract")
    candidates: list[tuple[Decimal, int]] = []
    ignored_before_min: list[int] = []
    ignored_after_max: list[int] = []
    for raw_epoch, raw_metric in history.items():
        epoch = int(raw_epoch)
        metric = float(raw_metric)
        if not (metric == metric and abs(metric) != float("inf")):
            raise FinalEpochPolicyError("inner-stop metric contains NaN/Inf")
        if epoch < MIN_EPOCH:
            ignored_before_min.append(epoch)
        elif epoch > MAX_EPOCH:
            ignored_after_max.append(epoch)
        else:
            candidates.append((Decimal(str(metric)), epoch))
    if not candidates:
        raise FinalEpochPolicyError("no eligible checkpoint in epochs [50,400]")
    metric, epoch = min(candidates, key=lambda item: (item[0], item[1]))
    return {
        "eligible_best_epoch": epoch,
        "minimum_metric": float(metric),
        "eligible_epoch_min": MIN_EPOCH,
        "eligible_epoch_max": MAX_EPOCH,
        "ignored_before_min_epochs": sorted(ignored_before_min),
        "ignored_after_max_epochs": sorted(ignored_after_max),
        "tie_rule_applied": "earliest_epoch_for_machine_equal_minimum",
        "monitor": monitor,
        "source": source,
    }


def _validate_fit_records(records: Sequence[Mapping[str, Any]]) -> list[int]:
    if len(records) != EXPECTED_FITS:
        raise FinalEpochPolicyError(f"expected exactly {EXPECTED_FITS} eligible OOF fit records")
    identities = set()
    epochs: list[int] = []
    fold_seed_pairs = set()
    for record in records:
        fit_id = str(record.get("fit_id", ""))
        if not fit_id or fit_id in identities:
            raise FinalEpochPolicyError("missing or duplicate OOF fit identity")
        identities.add(fit_id)
        epoch = int(record.get("eligible_best_epoch", -1))
        if not MIN_EPOCH <= epoch <= MAX_EPOCH:
            raise FinalEpochPolicyError("eligible_best_epoch outside [50,400]")
        if record.get("status") not in (None, "VALID", "COMPLETE"):
            raise FinalEpochPolicyError("failed OOF fit cannot derive final epoch")
        if any(bool(record.get(key, False)) for key in ("fold_leakage", "case_leakage", "pca_scaler_leakage", "outer_fold_used_for_stopping", "v3_test40_used", "power_used", "auxiliary_used")):
            raise FinalEpochPolicyError("leakage or forbidden target marked in OOF fit record")
        fold = int(record.get("outer_fold", -1))
        seed = int(record.get("seed", -1))
        if fold not in range(5) or seed not in FROZEN_SEEDS:
            raise FinalEpochPolicyError("OOF fit fold/seed outside frozen 5x3 matrix")
        fold_seed_pairs.add((fold, seed))
        epochs.append(epoch)
    if len(fold_seed_pairs) != EXPECTED_FITS:
        raise FinalEpochPolicyError("OOF fold/seed matrix is incomplete")
    return epochs


def derive_final_epoch(records: Sequence[Mapping[str, Any]], selected_architecture: str) -> dict[str, Any]:
    """Derive E_final only from 15 complete eligible OOF fits."""
    if selected_architecture not in ALLOWED_ARCHITECTURES:
        raise FinalEpochPolicyError("final epoch derivation requires selected architecture A/B/C, not NONE")
    epochs = _validate_fit_records(records)
    median_epoch = median(epochs)
    final_epoch = round_half_up(median_epoch)
    count_at_max = sum(epoch == MAX_EPOCH for epoch in epochs)
    saturation = median_epoch == MAX_EPOCH
    return {
        "selected_architecture": selected_architecture,
        "fit_count": len(records),
        "eligible_best_epochs": list(epochs),
        "median_best_epoch": median_epoch,
        "final_epoch": final_epoch,
        "rounding": "round_half_up",
        "max_epoch_count": count_at_max,
        "max_epoch_saturation_warning": "MAX_EPOCH_SATURATION_WARNING" if saturation else None,
        "full_development_validation": "none",
        "full_development_early_stopping": False,
        "status": "PASS",
    }


def validate_full_development_training_plan(plan: Mapping[str, Any], *, derived_final_epoch: int) -> dict[str, Any]:
    """Validate the future plan without dispatching training."""
    required = {
        "geometry_count": 200,
        "case_count": 1200,
        "validation_split": "none",
        "early_stopping": False,
        "checkpoint_hunting": False,
        "loss_based_epoch_adjustment": False,
        "v3_test40_access": False,
    }
    checks = {key: plan.get(key) == value for key, value in required.items()}
    checks["epoch_fixed"] = plan.get("final_epoch") == derived_final_epoch
    if not all(checks.values()):
        raise FinalEpochPolicyError(f"full-development plan violates frozen semantics: {checks}")
    return {"status": "PASS", "checks": checks, "training_dispatched": False}


def policy_audit() -> dict[str, Any]:
    policy = load_policy()
    return {
        "status": "PASS",
        "contract_id": policy["contract_id"],
        "contract_sha256": sha256_file(),
        "eligible_epoch_range": [MIN_EPOCH, MAX_EPOCH],
        "rounding": "round_half_up",
        "source_fit_count": EXPECTED_FITS,
        "outer_fold_forbidden": True,
        "v3_test40_forbidden": True,
        "final_training_validation": "none",
        "final_training_early_stopping": False,
        "max_epoch_saturation_warning": "MAX_EPOCH_SATURATION_WARNING",
        "final_seed_ensemble_status": "NOT_FROZEN_PRE_FINAL_TRAINING_ITEM",
        "solver_calls": 0,
        "training_fits": 0,
    }


if __name__ == "__main__":
    print(json.dumps(policy_audit(), sort_keys=True))
