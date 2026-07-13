from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_mdc_p1_asymmetric_static_v1 as p1


def test_static_p1_compilation_invariants():
    rows, audit = p1.build_rows()
    assert len(rows) == 15
    assert audit["summary"]["symmetric_existing_controls"] == 3
    assert audit["summary"]["proposed_novel_geometries"] == 12
    assert len({r["canonical_sequence_hash"] for r in rows}) == 15
    assert len({r["geometry_hash"] for r in rows}) == 15
    assert all(int(r["N_GaN"]) + int(r["N_Air"]) == 6 for r in rows)
    explicit = [r for r in rows if r["seed_id"] == "explicit_fab"]
    nominal = [r for r in rows if r["seed_id"] == "zl1_nominal"]
    alternative = [r for r in rows if r["seed_id"] == "zl1_alternative"]
    assert {(r["layer_count"], r["total_thickness_nm"]) for r in explicit} == {(13, 900)}
    assert {(r["layer_count"], r["total_thickness_nm"], r["effective_center_nm"]) for r in nominal} == {(12, 978, 312)}
    assert {(r["layer_count"], r["total_thickness_nm"], r["effective_center_nm"]) for r in alternative} == {(12, 975, 316)}
    assert all(p1.material_adjacent_ok(p1.parse_seq(r["sequence_GaN_to_Air"])) for r in rows)


def test_solver_free_source_and_symmetric_replay():
    source = (ROOT / "scripts" / "build_mdc_p1_asymmetric_static_v1.py").read_text(encoding="utf-8").lower()
    assert "import lumapi" not in source and ".run(" not in source and "fdtd()" not in source
    rows, _ = p1.build_rows()
    assert sum(r["existing_geometry_status"] != "proposed_novel" for r in rows) == 3
