"""Lightweight integrity checks for the frozen MDC V3 stage-conclusion figure."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def load(p: Path): return json.loads(p.read_text(encoding="utf-8-sig"))
def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b: break
            h.update(b)
    return h.hexdigest()

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--package", required=True); a = ap.parse_args(); root = Path(a.package)
    required = {"stage_conclusion_figure.png", "stage_conclusion_figure.tiff", "stage_conclusion_figure.pdf", "stage_conclusion_figure.svg", "sample_selection_manifest.json", "caption_draft.md", "figure_readme.md", "layout_refinement_note.md", "completion_manifest.json", "artifact_sha256.json"}
    assert all((root / x).exists() for x in required)
    comp = load(root / "completion_manifest.json"); sel = load(root / "sample_selection_manifest.json"); man = load(root / "artifact_sha256.json")
    assert comp["status"] == "PASS" and comp["backend"] == "python_matplotlib" and comp["rows"] == 3 and comp["layout_refined"] is True
    assert comp["figure_id"] == "MDC_HF_SURROGATE_V3_STAGE_CONCLUSION_FIGURE_LAYOUT_REFINED_NATURESTYLE_V1"
    assert comp["columns"] == ["Truth", "V3-C prediction", "Absolute error"]
    assert comp["png_dpi"] == 600 and comp["solver_calls"] == comp["training_fits"] == comp["pca_fit_calls"] == comp["scaler_fit_calls"] == 0
    assert comp["new_evaluation_metric"] is False and sel["no_new_metric"] is True
    assert len(sel["rows"]) == 3 and sel["difficult_control"]["included"] is False
    assert [r["role"] for r in sel["rows"]] == ["best", "median", "worst"]
    assert all(r["case_count"] == 6 and len(r["case_uids"]) == 6 for r in sel["rows"])
    assert sel["rows"][-1]["topology"] == "ZL2"
    assert man["file_count"] == len(man["files"])
    for rel, expected in man["files"].items(): assert sha(root / rel) == expected, rel
    print(json.dumps({"status":"PASS","rows":len(sel["rows"]),"file_count":man["file_count"],"solver":comp["solver_calls"],"training":comp["training_fits"]},sort_keys=True))

if __name__ == "__main__": main()
