from __future__ import annotations

from pathlib import Path

from metasurface.stage12_7_meeting_narrative import build_figure_qa_rows, qa_pass


def test_stage12_7_figure_qa_detects_existing_nonempty_files(tmp_path: Path) -> None:
    png = tmp_path / "a.png"
    svg = tmp_path / "a.svg"
    png.write_bytes(b"png")
    svg.write_text("<svg></svg>", encoding="utf-8")
    rows = build_figure_qa_rows([{"figure": "fig", "png": str(png), "svg": str(svg), "claim": "claim"}])
    assert len(rows) == 2
    assert qa_pass(rows) is True
    assert all(row["status"] == "PASS" for row in rows)


def test_stage12_7_figure_qa_flags_missing_file(tmp_path: Path) -> None:
    png = tmp_path / "a.png"
    png.write_bytes(b"png")
    rows = build_figure_qa_rows([{"figure": "fig", "png": str(png), "svg": str(tmp_path / "missing.svg"), "claim": "claim"}])
    assert qa_pass(rows) is False
    assert [row for row in rows if row["status"] == "FAIL"][0]["format"] == "svg"
