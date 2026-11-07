"""W1047: build a versionable CI/provenance bundle from the WorkBuddy workspace.

Scope is deliberate:
- actual script/patch source is copied into ci/workbuddy/** so GitHub's existing
  `ci/**` path filter really covers it;
- all workspace files get a SHA-256 manifest, so even excluded historical source
  snapshots remain auditable without pushing 2 GiB into the engine repo;
- secrets and caches are excluded by name/extension.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import tarfile
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(r"D:/workbuddy_space/strata_ws")
OUT = ROOT / "albus/w1047/bundle"
STAGE = OUT / "stage"
WORK = STAGE / "ci/workbuddy"
PROV = STAGE / "ci/provenance"

CODE_EXT = {
    ".py", ".sh", ".cu", ".cuh", ".hpp", ".h", ".cpp", ".c", ".md", ".json",
    ".tsv", ".txt", ".yaml", ".yml", ".csv", ".ts", ".mjs", ".svelte", ".rs",
}
SKIP_NAMES = {
    "_tok.txt", "conversation-data.json", "_server_b64.txt", ".DS_Store",
    "Thumbs.db", "desktop.ini",
}
SKIP_PARTS = {".workbuddy", "forks", "snapshots_premigrate", "__pycache__", ".git", "tmp"}
SKIP_SUBSTR = ("token", "secret", "credential", "password", "private_key")
SKIP_SUFFIX = {".log", ".bin", ".o", ".so", ".a", ".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".7z", ".rar", ".gz", ".xz", ".tar"}


def is_own_output(rel: pathlib.Path) -> bool:
    s = rel.as_posix()
    return s.startswith("albus/w1047/bundle/") or s.startswith("albus/w1047/stage/")


def safe_name(p: pathlib.Path) -> bool:
    if p.name in SKIP_NAMES:
        return False
    low = p.name.lower()
    if any(s in low for s in SKIP_SUBSTR):
        return False
    return True


def include_source(p: pathlib.Path) -> bool:
    rel = p.relative_to(ROOT)
    if is_own_output(rel):
        return False
    if any(part in SKIP_PARTS for part in rel.parts):
        return False
    if not safe_name(p):
        return False
    if p.suffix.lower() in SKIP_SUFFIX:
        return False
    if "gfx906_survey/src" in rel.as_posix():
        return False
    if p.suffix.lower() not in CODE_EXT:
        return False
    # Current authoritative snapshots are copied separately below.
    if rel.parts[:2] in (("deploy", "PROGRESS.tsv"), ("deploy", "W832_OPT_PLAN_V2.md")):
        return False
    return True


def include_manifest(p: pathlib.Path) -> bool:
    rel = p.relative_to(ROOT)
    if is_own_output(rel):
        return False
    if any(part in SKIP_PARTS for part in rel.parts):
        return False
    return safe_name(p)


def copy_file(src: pathlib.Path, dst: pathlib.Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sha256(p: pathlib.Path) -> str:
    try:
        with p.open("rb") as f:
            h = hashlib.sha256()
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
            return h.hexdigest()
    except OSError as e:
        return "UNREADABLE:%s" % type(e).__name__


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    WORK.mkdir(parents=True)
    PROV.mkdir(parents=True)

    selected = []
    for p in ROOT.rglob("*"):
        if p.is_file() and include_source(p):
            rel = p.relative_to(ROOT)
            copy_file(p, WORK / rel)
            selected.append(rel)

    # Always carry the current authoritative snapshots and core identity docs.
    for rel in [
        "deploy/PROGRESS.tsv",
        "deploy/W832_OPT_PLAN_V2.md",
        "deploy/REBUILD_RECIPE.tsv",
        "deploy/REPORT_TEMPLATE.md",
        "deploy/REPORT_STANDARD.md",
        "deploy/params/PARAM_REGISTER.tsv",
        "albus/gfx906_survey/PORT_PLAN.md",
        "PROJECT.md",
        "SESSION_KICKOFF.md",
        "HANDOVER.md",
        "MAP_OLD_TO_NEW.md",
    ]:
        src = ROOT / rel
        if src.is_file():
            copy_file(src, WORK / "authoritative_snapshot" / rel)
            selected.append(pathlib.Path("authoritative_snapshot") / rel)

    # Full workspace manifest: every non-secret file is auditable even if excluded above.
    rows = []
    candidates = []
    for p in ROOT.rglob("*"):
        if p.is_file() and include_manifest(p):
            try:
                candidates.append((p, p.stat().st_size))
            except OSError:
                candidates.append((p, -1))
    with ThreadPoolExecutor(max_workers=16) as pool:
        digests = list(pool.map(lambda item: sha256(item[0]), candidates))
    for (p, size), digest in zip(candidates, digests):
        rel = p.relative_to(ROOT).as_posix()
        rows.append((rel, size, digest))
    rows.sort()
    with (PROV / "workspace_manifest.tsv").open("w", encoding="utf-8", newline="\n") as f:
        f.write("path\tsize\tsha256\n")
        for rel, size, digest in rows:
            f.write(f"{rel}\t{size}\t{digest}\n")

    with (PROV / "selected_scripts.tsv").open("w", encoding="utf-8", newline="\n") as f:
        f.write("path\tsize\tsha256\n")
        for rel in sorted(selected):
            p = WORK / rel
            f.write(f"{rel.as_posix()}\t{p.stat().st_size}\t{sha256(p)}\n")

    readme = """# WorkBuddy provenance bundle

This directory makes the previously local WorkBuddy toolchain reviewable by the
same static CI that watches `ci/**`.

- `workbuddy/**`: actual project-created scripts, patch helpers, reports and
  experiment code that used to live only in `D:/workbuddy_space/strata_ws`.
- `provenance/workspace_manifest.tsv`: SHA-256 for every auditable workspace
  file, including large historical snapshots excluded from this repo.
- `provenance/selected_scripts.tsv`: SHA-256 for every file actually copied here.

Excluded by design: `.workbuddy/`, fork/source snapshots, caches, binaries,
logs and secret-looking filenames. The manifest still records non-secret
historical files so omissions are explicit.

The upstream GitHub workflow is static-only: it syntax-checks and runs gate
self-tests, but it does not compile the ROCm engine or run GPU benchmarks.
"""
    (PROV / "README.md").write_text(readme, encoding="utf-8", newline="\n")

    tar_path = OUT / "workbuddy_ci_bundle.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(STAGE, arcname=".")
    print("selected", len(selected), "manifest_rows", len(rows))
    print("stage_bytes", sum(p.stat().st_size for p in STAGE.rglob("*") if p.is_file()))
    print("tar", tar_path, tar_path.stat().st_size)


if __name__ == "__main__":
    main()
