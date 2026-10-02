import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUILDER_PATH = ROOT / "scripts" / "coupling_ml" / "build_pw_k6_5nm_full_period_prefsp_v1.py"
SPEC = importlib.util.spec_from_file_location("pw_k6_full_period_builder", str(BUILDER_PATH))
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def test_ordered_geometry_hash_matches_frozen_seed():
    assert BUILDER.geometry_hash([155, 105, 195, 150, 180, 145]) == (
        "75df0936fdab6c7431e2b47672614105b900e61b71058c6fdaeb9ada0fb2bd81"
    )
    assert BUILDER.geometry_hash([155, 105, 195, 150, 180, 145]) != BUILDER.geometry_hash(
        [105, 155, 195, 150, 180, 145]
    )


def test_full_period_mesh_covers_worst_case_edge_geometry():
    result = BUILDER.validate_geometry([230, 230, 230, 230, 230, 230])
    assert result["minimum_lateral_margin_nm"] == 30.0
    assert result["minimum_vertical_margin_nm"] == 100.0
    assert all(row["inside_mesh"] for row in result["pillar_coverage"])


def test_invalid_diameter_fails_closed():
    try:
        BUILDER.validate_geometry([235, 230, 230, 230, 230, 230])
    except ValueError as exc:
        assert "5 nm grid values" in str(exc)
    else:
        raise AssertionError("out-of-domain diameter was accepted")


def test_every_frozen_20g_manifest_geometry_fits_the_mesh():
    manifest = BUILDER.load_json(BUILDER.SEED_MANIFEST)
    assert BUILDER.sha256_file(BUILDER.SEED_MANIFEST) == BUILDER.EXPECTED["seed_manifest"]
    for row in manifest["entries"]:
        checked = BUILDER.validate_geometry(row["ordered_D_nm"], row["geometry_hash_sha256"])
        assert checked["minimum_lateral_margin_nm"] >= 30.0
        assert checked["minimum_vertical_margin_nm"] >= 100.0


def test_mesh_authority_has_exact_artifact_bounds_and_step():
    assert BUILDER.core_bounds_nm() == {"x": [-870.0, 870.0], "y": [-145.0, 145.0], "z": [1112.0, 1812.0]}
    assert BUILDER.CORE_MESH["step_nm"] == [5.0, 5.0, 5.0]


def test_builder_contains_no_solver_run_call():
    tree = ast.parse(BUILDER_PATH.read_text(encoding="utf-8"))
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run"
    ]
    assert calls == []
