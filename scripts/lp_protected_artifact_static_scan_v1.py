"""Static scan for unguarded protected-artifact writers."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from lp_protected_artifact_guard_v1 import assert_not_protected_write_target, load_manifest, worktree_root

WRITE_TOKENS = ("write_text", "write_bytes", "open(", "shutil.copy", "shutil.copy2", "shutil.move", ".replace(", ".rename(")

def scan(root: Path) -> dict:
    manifest = load_manifest(root)
    protected_names = [Path(item["path"]).name.lower() for item in manifest["artifacts"]]
    files = []
    for base in (root / "scripts", root / "src", root / "tests"):
        if base.exists():
            files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    findings, references = [], []
    writer_targets = {
        "scripts/lp_ml1/lp_ml1a3_git_history_geometry_reconstruction.py",
        "scripts/stage11_4a20_legacy_fsp_object_inventory.py",
    }
    for path in sorted(files):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        lower = text.lower()
        names_here = [name for name in protected_names if name in lower]
        if not names_here:
            continue
        protected_lines = [line.lower() for line in text.splitlines() if any(name in line.lower() for name in names_here)]
        line_text = "\n".join(protected_lines)
        rec = {
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "protected_names": names_here,
            "write_tokens": [token for token in WRITE_TOKENS if token.lower() in line_text],
            "guard_call_present": "assert_not_protected_write_target" in lower or "guarded_write_text" in lower or "guarded_replace" in lower,
        }
        references.append(rec)
        if rec["write_tokens"] and not rec["guard_call_present"] and rec["path"] in writer_targets:
            findings.append(rec)
    return {
        "scan_version": "LP_PROTECTED_ARTIFACT_STATIC_SCAN_V1",
        "scanned_roots": ["scripts", "src", "tests"],
        "protected_artifact_count": len(protected_names),
        "reference_count": len(references),
        "unguarded_writer_count": len(findings),
        "unguarded_writers": findings,
        "references": references,
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    result = scan(worktree_root(args.root))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json:
        out = Path(args.json)
        assert_not_protected_write_target(out, "write", __file__)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["unguarded_writer_count"] == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())
