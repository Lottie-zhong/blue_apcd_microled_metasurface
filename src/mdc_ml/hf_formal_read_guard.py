from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable


class FormalReadGuardError(RuntimeError):
    pass


def validate_evaluation_source_static(path: Path) -> None:
    """Reject direct parquet materialization in evaluation modules before execution."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    if "hf15" in lowered and ("read_parquet(" in lowered or "read_table(" in lowered or "to_table(" in lowered or ".scanner(" in lowered):
        raise FormalReadGuardError("DIRECT_UNGUARDED_FORMAL_PARQUET_READ:" + str(path))


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_prelabel_contract(prelabel_dir: Path, registry: dict, requested_columns: Iterable[str] | None, allowed_columns: set[str], diagnostics_roots: Iterable[Path] = ()) -> None:
    required = ["prelabel_model_lock.json", "prelabel_target_comparability_contract.json", "prelabel_evaluation_plan.json", "hf15_prelabel_feature_matrix.parquet", "hf15_prelabel_regression_predictions.parquet", "hf15_prelabel_eligibility_routing.parquet", "prelabel_fresh_replay_1.json", "prelabel_fresh_replay_2.json", "prelabel_prediction_sha.json", "prelabel_routing_sha.json"]
    missing = [x for x in required if not (prelabel_dir / x).is_file()]
    if missing:
        raise FormalReadGuardError("PRELABEL_ARTIFACT_MISSING:" + ",".join(missing))
    if registry.get("blind_status") != "BLIND_ACTIVE":
        raise FormalReadGuardError("DATASET_NOT_BLIND_ACTIVE")
    if int(registry.get("formal_value_read_count", 0)) != 0:
        raise FormalReadGuardError("FORMAL_READ_COUNTER_NONZERO")
    if requested_columns is None:
        raise FormalReadGuardError("REQUESTED_COLUMNS_MUST_BE_EXPLICIT")
    req = set(requested_columns)
    if not req or not req.issubset(allowed_columns):
        raise FormalReadGuardError("REQUESTED_COLUMNS_OUTSIDE_ALLOWLIST")
    for root in diagnostics_roots:
        if Path(root).exists():
            raise FormalReadGuardError("DIAGNOSTICS_ROOT_REGISTERED")


def guarded_read_formal_labels(path: Path, *, dataset_root: Path, registry: dict, prelabel_dir: Path, requested_columns: Iterable[str] | None, allowed_columns: set[str], access_log: Path, diagnostics_roots: Iterable[Path] = ()):
    if _under(path, dataset_root):
        validate_prelabel_contract(prelabel_dir, registry, requested_columns, allowed_columns, diagnostics_roots)
        if path.name.endswith("case_diagnostics_v1.parquet"):
            raise FormalReadGuardError("CASE_DIAGNOSTICS_FORBIDDEN")
    else:
        raise FormalReadGuardError("PATH_NOT_REGISTERED_FORMAL_ROOT")
    import pyarrow.parquet as pq
    before = int(registry.get("formal_value_read_count", 0))
    if before != 0:
        raise FormalReadGuardError("FORMAL_READ_COUNTER_NONZERO")
    table = pq.read_table(path, columns=list(requested_columns))
    record = {"path": str(path), "columns": list(requested_columns), "rows": table.num_rows, "formal_value_read_count_before": before, "formal_value_read_count_after": 1}
    access_log.parent.mkdir(parents=True, exist_ok=True)
    with access_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    registry["formal_value_read_count"] = 1
    return table


def schema_only(path: Path, *, dataset_root: Path, registry: dict):
    if _under(path, dataset_root) and registry.get("blind_status") == "RETIRED_DUE_TO_PRELABEL_FORMAL_VALUE_EXPOSURE":
        raise FormalReadGuardError("RETIRED_DATASET_REJECTS_BLIND_ENTRYPOINT")
    import pyarrow.parquet as pq
    return pq.ParquetFile(path).schema_arrow
