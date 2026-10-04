"""Fail-closed Coupling-side queue21 truth-consumer quarantine."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[3]
REGISTRY_RELATIVE = Path("reports/coupling/COUPLING_ML_QUEUE21_CONSUMER_EXCLUSION_V1/CONSUMER_EXCLUSION_REGISTRY_V1.json")
REGISTRY_SHA256 = "01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261"
ALLOWED_CONSUMERS = frozenset({
    "training", "candidate_ranking", "candidate_evaluation",
    "truth_import", "truth_handoff", "confirmation_import", "diagnostic_import",
})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

class ConsumerExclusionError(ValueError):
    """Raised before quarantined or weakly sourced truth can reach a consumer."""

def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_consumer_exclusion_registry(root=None):
    repo = Path(root) if root is not None else ROOT
    path = repo / REGISTRY_RELATIVE
    if not path.is_file() or sha256_file(path) != REGISTRY_SHA256:
        raise ConsumerExclusionError("consumer_exclusion_registry_missing_or_sha_mismatch")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConsumerExclusionError("consumer_exclusion_registry_invalid_json") from exc
    identity = doc.get("case_identity", {})
    sources = doc.get("source_authorities", {})
    markers = doc.get("linkage_markers", {})
    hold = sources.get("hold", {})
    if (doc.get("schema") != "COUPLING_ML_TRUTH_CONSUMER_EXCLUSION_REGISTRY_V1"
            or doc.get("version") != 1 or doc.get("status") != "ACTIVE"
            or identity.get("case_id") != "K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1"
            or identity.get("attempt_id") != "attempt_001"
            or identity.get("branch_id") != "traditional"
            or identity.get("event_ids") != [1499, 1506]
            or identity.get("physical_solver_entry_count") != "UNKNOWN"
            or set(doc.get("decision", {}).get("exclude_from", ())) != {
                "training", "candidate_ranking", "candidate_evaluation",
                "scientific_conclusions", "formal_truth_handoff",
            }
            or sources.get("gpu_runner_worktree_head") !=
                "88c8ba7afe99ab8e58a4f41f0698b56f65bc0b35"
            or sources.get("exception_disposition_v2_sha256") !=
                "468331313528c2a1d68e079617d84c8cac7baceff329e1384a65a38d1ec7de97"
            or sources.get("owner_decision_record_sha256") !=
                "da6176fe98a1e7f38e149db417e419455720922527d6d9699772456f308a752a"
            or sources.get("owner_execution_delegation_sha256") !=
                "14ee2b2e84fb291775b9e2c4dbfb501b253c3d10b5ab88ecda9abea2575d55f1"
            or doc.get("decision", {}).get("owner_v2_status") !=
                "OWNER_ACCEPTED_UNRECOVERABLE_LINEAGE_QUARANTINE_PENDING_COUPLING_CONSUMER_ENFORCEMENT"
            or doc.get("decision", {}).get("conditional_hold_release_performed") is not False
            or doc.get("decision", {}).get("owner_v2_quarantine_status") !=
                "QUARANTINED_PENDING_COUPLING_CONSUMER_ENFORCEMENT"
            or sources.get("gpu_runner_handoff_sha256") !=
                "8b5760d81adb3830d84d0277e8c8d203ead0545cc27a6b8a8bbff106601191b1"
            or sources.get("exception_disposition_sha256") !=
                "5e2ba9d6de8c94e2f4fe0af89ba9fc7b5a523763d35b863e083888f3f06c5065"
            or sources.get("quarantine_manifest_sha256") !=
                "f5c058bea0a38c8e900d8019b6fb33e4a34d450411980765598007bc1b9d6cbf"
            or sources.get("coupling_handoff_sha256") !=
                "aa9c55f2bec48694bd99806d50878a09c5d3b0345c03ad77e6b95d83051cb2a9"
            or hold.get("status") != "ACTIVE" or hold.get("released") is not False
            or hold.get("generation") != 26
            or markers.get("case_id") != identity.get("case_id")
            or markers.get("event_ids") != identity.get("event_ids")):
        raise ConsumerExclusionError("consumer_exclusion_registry_semantics_mismatch")
    return doc

def _as_mapping(value):
    if isinstance(value, Mapping):
        return value
    try:
        return vars(value)
    except TypeError:
        return value

def _link_signals(value, doc):
    identity = doc["case_identity"]
    markers = doc["linkage_markers"]
    exact_case_id = identity["case_id"]
    fixed_strings = {
        exact_case_id.casefold(),
        str(markers["incident_id"]).casefold(),
        str(markers["disposition_sha256"]).casefold(),
        str(markers["quarantine_manifest_sha256"]).casefold(),
        str(markers["hold_id"]).casefold(),
    }
    event_ids = {int(x) for x in markers["event_ids"]}
    signals = set()
    def visit(node, path=()):
        node = _as_mapping(node)
        if isinstance(node, Mapping):
            for key, child in node.items():
                key_text = str(key).casefold()
                child_path = path + (key_text,)
                if key_text.isdigit() and int(key_text) in event_ids and any("event" in part for part in path):
                    signals.add("queue21_event_id")
                if key_text in {"case_id", "source_case_id", "origin_case_id",
                                "parent_case_id", "related_case_id", "logical_case_id"}:
                    if str(child).casefold() == exact_case_id.casefold():
                        signals.add("case_identity")
                if "event" in key_text:
                    if isinstance(child, (list, tuple, set)):
                        if event_ids.intersection(int(x) for x in child if str(x).isdigit()):
                            signals.add("queue21_event_id")
                    elif str(child).isdigit() and int(child) in event_ids:
                        signals.add("queue21_event_id")
                visit(child, child_path)
        elif isinstance(node, (list, tuple, set)):
            for child in node:
                visit(child, path)
        elif isinstance(node, int) and not isinstance(node, bool):
            if node in event_ids and any("event" in part for part in path):
                signals.add("queue21_event_id")
        elif isinstance(node, str):
            folded = node.casefold()
            if any(marker in folded for marker in fixed_strings) or "queue21" in folded:
                signals.add("queue21_link_marker")
    visit(value)
    return tuple(sorted(signals))

def assert_no_quarantine_linkage(value, *, consumer, root=None):
    if consumer not in ALLOWED_CONSUMERS:
        raise ConsumerExclusionError("unknown_truth_consumer:" + str(consumer))
    doc = load_consumer_exclusion_registry(root)
    signals = _link_signals(value, doc)
    if signals:
        raise ConsumerExclusionError(
            "queue21_linked_artifact_excluded:" + consumer + ":" + ",".join(signals)
        )

def validate_independent_truth_provenance(cases, *, consumer, root=None):
    """Require pinned old32 or verified Runner-import provenance."""
    from . import contracts as C
    cases = tuple(cases)
    assert_no_quarantine_linkage(cases, consumer=consumer, root=root)
    def valid_sha(value):
        return isinstance(value, str) and bool(_SHA256.fullmatch(value))
    for case in cases:
        provenance = getattr(case, "provenance", None)
        case_id = str(getattr(case, "case_id", ""))
        role = getattr(case, "role", None)
        if not isinstance(provenance, Mapping):
            raise ConsumerExclusionError("independent_truth_provenance_missing:" + case_id)
        if role == C.ROLE_OLD32:
            okay = (
                provenance.get("dataset_npz_sha256") ==
                    "fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28"
                and provenance.get("dataset_authority_sha256") == C.DATASET_AUTHORITY_SHA256
                and valid_sha(provenance.get("state_sha256"))
                and (provenance.get("state_metadata_sha256") is None
                     or valid_sha(provenance.get("state_metadata_sha256")))
            )
        elif role in {C.ROLE_LOCAL_AXIS, C.ROLE_GLOBAL_DEV}:
            required = (
                "source_manifest_sha256", "state_npz_sha256", "state_metadata_sha256",
                "raw_npz_sha256", "raw_metadata_sha256", "orders_sha256",
            )
            okay = (
                all(valid_sha(provenance.get(key)) for key in required)
                and provenance.get("physical_contract_sha256") == C.PHYSICAL_CONTRACT_SHA256
                and provenance.get("truth_extractor_sha256") == C.H1_EVALUATOR_SOURCE_SHA256
                and provenance.get("reference_plane_nm") == C.REFERENCE_PLANE_NM
                and provenance.get("normalization") == C.PSCALE_DEFINITION
                and provenance.get("truth_schema") == C.STATE_SCHEMA
            )
        else:
            okay = False
        if not okay:
            raise ConsumerExclusionError(
                "independent_truth_provenance_missing_or_invalid:" + case_id
            )
