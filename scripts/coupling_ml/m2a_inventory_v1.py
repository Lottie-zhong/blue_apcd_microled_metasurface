import hashlib
import json
import os
import re
from pathlib import Path

NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {".git", "__pycache__", "node_modules"}]
        for fn in fns:
            p = Path(dp) / fn
            try:
                if p.stat().st_size <= 50_000_000:
                    yield p
            except OSError:
                pass


def selected_paths(root, tokens):
    out = []
    for p in files(root):
        n = p.name.lower()
        if any(t in n for t in tokens):
            out.append(str(p.relative_to(root)))
    return sorted(out)


def print_text(root, rel, max_chars=30000):
    p = root / rel
    if not p.exists():
        print(json.dumps({"missing": str(p)}))
        return
    s = p.read_text(encoding="utf-8", errors="replace")
    print(json.dumps({"path": str(p), "sha256": sha(p), "chars": len(s), "text": s[:max_chars]}, ensure_ascii=False))


def main():
    print("=== NP_MATCHED_FILENAMES ===")
    print(json.dumps(selected_paths(NP, ["22g", "geometry", "candidate", "selection", "rank", "library", "freeze", "handoff", "scope", "manifest"]), ensure_ascii=False, indent=2))
    print("=== NP_OUTPUT_DIRS ===")
    print(json.dumps(sorted(str(p.relative_to(NP / "outputs")) for p in (NP / "outputs").iterdir() if p.is_dir()), ensure_ascii=False, indent=2))
    print("=== COUPLING_MATCHED_FILENAMES ===")
    print(json.dumps(selected_paths(COUPLING, ["level2", "level1", "provider", "benchmark", "manifest", "freeze", "handoff"]), ensure_ascii=False, indent=2))
    print("=== SELECTED_TEXTS ===")
    for rel in [
        r"outputs\np_k6_final_freeze_closeout_v1\freeze_manifest.json",
        r"outputs\np_k6_final_freeze_closeout_v1\provider_manifest.json",
        r"outputs\np_k6_formal_source_scope_v1\coupling_handoff_manifest_v1.json",
        r"docs\np_k6_m9a_normal_incidence_plateau_reassessment_and_coupling_handoff_v1.md",
        r"docs\np_k6_m9_22g_forward_retraining_v1.md",
        r"docs\np_k6_m8a_final_targeted_acquisition_design_only_v1.md",
    ]:
        print_text(NP, rel)
    print("=== POTENTIAL_TABLE_HEADERS ===")
    for p in files(NP):
        if p.suffix.lower() not in {".csv", ".json", ".yaml", ".yml"}:
            continue
        n = p.name.lower()
        if any(t in n for t in ["22", "candidate", "selection", "rank", "geometry", "library", "dataset", "label"]):
            try:
                s = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            first = s.splitlines()[0][:1000] if s.splitlines() else ""
            if any(t in first.lower() for t in ["geometry", "d1", "d2", "candidate", "rank", "case"]):
                print(json.dumps({"path": str(p), "sha256": sha(p), "first_line": first}, ensure_ascii=False))


if __name__ == "__main__":
    main()
