import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


ML = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
COUPLING = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
NP = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")


def run_git(path, args):
    p = subprocess.run(["git", *args], cwd=str(path), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"returncode": p.returncode, "stdout": p.stdout[:8000], "stderr": p.stderr[:2000]}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def walk_files(root, max_size=20_000_000):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in {".git", "__pycache__", ".venv", "node_modules"}]
        for fn in fns:
            p = Path(dp) / fn
            try:
                if p.stat().st_size <= max_size:
                    yield p
            except OSError:
                pass


def text_hits(root, patterns):
    out = []
    rx = re.compile("|".join(re.escape(x) for x in patterns), re.I)
    for p in walk_files(root):
        if p.suffix.lower() not in {".json", ".csv", ".md", ".yaml", ".yml", ".txt", ".py"}:
            continue
        try:
            s = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if rx.search(s) or rx.search(p.name):
            out.append({"path": str(p), "size": len(s), "sha256": sha(p)})
    return out


def json_summary(p):
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"path": str(p), "error": repr(e)}
    def shape(x, depth=0):
        if depth > 2:
            return type(x).__name__
        if isinstance(x, dict):
            return {k: shape(v, depth + 1) for k, v in list(x.items())[:40]}
        if isinstance(x, list):
            return {"type": "list", "len": len(x), "item": shape(x[0], depth + 1) if x else None}
        return type(x).__name__
    return {"path": str(p), "sha256": sha(p), "shape": shape(obj), "keys": list(obj)[:80] if isinstance(obj, dict) else None}


def main():
    print(json.dumps({
        "git": {
            "ml": {"path": str(ML), "head": run_git(ML, ["rev-parse", "HEAD"]), "branch": run_git(ML, ["branch", "--show-current"]), "status": run_git(ML, ["status", "--short", "--untracked-files=no"]), "upstream": run_git(ML, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])},
            "coupling": {"path": str(COUPLING), "head": run_git(COUPLING, ["rev-parse", "HEAD"]), "branch": run_git(COUPLING, ["branch", "--show-current"]), "status": run_git(COUPLING, ["status", "--short", "--untracked-files=no"]), "upstream": run_git(COUPLING, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])},
            "np": {"path": str(NP), "head": run_git(NP, ["rev-parse", "HEAD"]), "branch": run_git(NP, ["branch", "--show-current"]), "status": run_git(NP, ["status", "--short", "--untracked-files=no"]), "upstream": run_git(NP, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])},
        },
        "np_candidate_hits": text_hits(NP, ["geometry", "candidate", "K6", "ordered", "D1", "D2", "D3", "D4", "D5", "D6", "rank"]),
        "np_key_json": [json_summary(p) for p in walk_files(NP) if p.suffix.lower() == ".json" and any(t in p.name.lower() for t in ["geometry", "candidate", "selection", "manifest", "rank", "doe", "k6", "pool"])],
        "ml_outputs": [{"path": str(p), "size": p.stat().st_size, "sha256": sha(p)} for p in walk_files(ML / "outputs" / "coupling_ml")],
        "coupling_key_files": text_hits(COUPLING / "outputs" / "coupling", ["level1", "provider", "geometry", "manifest", "freeze", "source"]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
