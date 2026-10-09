from apcd_gpu_v2.cutover_gate import evaluate_cutover


def values():
    return [
        {
            "owner_isolation_proven": True,
            "unknown_live_count": 0,
            "confirmed_v1_active_count": 0,
            "markers": {},
            "pending_requests": [],
        },
        {"verdict": "PASS", "original_unchanged": True},
        {"verdict": "PASS", "outputs": 609},
        {"verdict": "PASS", "files_unchanged": True},
        {
            "API_LICENSE_AVAILABLE": True,
            "GPU_ENGINE_LICENSE_CONFIRMED": False,
            "GPU_ENGINE_LICENSE_NOT_TESTED": True,
        },
    ]


def test_unknown_owner_blocks_even_if_all_native_checks_pass():
    args = values()
    args[0]["unknown_live_count"] = 1
    result = evaluate_cutover(*args, production_ingress_qualified=True)
    assert result["status"] == "BLOCKED" and not result["scientific_launch_authorized"]


def test_pending_old_request_or_expired_marker_not_ignored():
    args = values()
    args[0]["markers"] = {".runner.lock": True}
    assert (
        evaluate_cutover(*args, production_ingress_qualified=True)["status"]
        == "BLOCKED"
    )
    args[0]["markers"] = {}
    args[0]["pending_requests"] = ["OLD_REQUEST"]
    assert (
        evaluate_cutover(*args, production_ingress_qualified=True)["status"]
        == "BLOCKED"
    )


def test_api_license_is_not_engine_license_confirmation_or_launch_authority():
    result = evaluate_cutover(*values(), production_ingress_qualified=True)
    assert result["status"] == "READY_FOR_CONTROLLED_CUTOVER"
    assert (
        result["gpu_engine_license_not_tested"]
        and not result["gpu_engine_license_confirmed"]
    )
    assert not result["scientific_launch_authorized"]


def test_offline_mvp_cannot_be_called_production_ready():
    assert evaluate_cutover(*values())["status"] == "PARTIAL"
