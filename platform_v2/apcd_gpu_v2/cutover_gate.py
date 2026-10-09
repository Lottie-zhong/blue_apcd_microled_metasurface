"""Read-only qualification gate; it cannot install, enable or launch anything."""


def evaluate_cutover(
    owner,
    native_load,
    importer,
    systemcheck,
    license_scope,
    *,
    production_ingress_qualified=False,
):
    blockers = []
    if not owner.get("owner_isolation_proven") or owner.get("unknown_live_count", 1):
        blockers.append("V1_OWNER_ISOLATION_NOT_PROVEN")
    if owner.get("confirmed_v1_active_count", 1):
        blockers.append("V1_ACTIVE_OWNER_PRESENT")
    if any(owner.get("markers", {}).values()) or owner.get("pending_requests"):
        blockers.append("V1_MARKER_OR_PENDING_REQUEST_PRESENT")
    checks = {
        "G025_NATIVE_LOAD_FAILED": native_load.get("verdict") == "PASS"
        and native_load.get("original_unchanged"),
        "G025_IMPORTER_FAILED": importer.get("verdict") == "PASS"
        and importer.get("outputs") == 609,
        "G027_SYSTEMCHECK_FAILED": systemcheck.get("verdict") == "PASS"
        and systemcheck.get("files_unchanged"),
        "API_LICENSE_UNAVAILABLE": license_scope.get("API_LICENSE_AVAILABLE") is True,
    }
    blockers += [key for key, passed in checks.items() if not passed]
    if blockers:
        status = "BLOCKED"
    elif not production_ingress_qualified:
        status = "PARTIAL"
        blockers.append("PRODUCTION_INGRESS_LEDGER_AND_DEPLOYMENT_NOT_QUALIFIED")
    else:
        status = "READY_FOR_CONTROLLED_CUTOVER"
    return {
        "status": status,
        "blockers": blockers,
        "scientific_launch_authorized": False,
        "scheduler_change_performed": False,
        "gpu_engine_license_confirmed": license_scope.get(
            "GPU_ENGINE_LICENSE_CONFIRMED"
        )
        is True,
        "gpu_engine_license_not_tested": license_scope.get(
            "GPU_ENGINE_LICENSE_NOT_TESTED"
        )
        is True,
    }
