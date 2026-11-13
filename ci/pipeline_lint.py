#!/usr/bin/env python3
"""ci/pipeline_lint.py — 流水线禁令 lint（三条造假绿 + 阶段定义完整性）。

立：2026-11-14（机主总纲令：三条造假绿禁令长期有效并写进流水线 lint）
语义：本脚本是 fail-closed 检查，不是建议。命中即 FAIL，禁止部署。

检查项：
  FG-1 把 int32 expert_bounds 指针强转成 ggml_cuda_mm_id_tile_spec*
  FG-2 构造伪造的 tile_spec 数组
  FG-3 故意让 overlay 锚点失效以降级走 FP16 冒充通过
  PL-1 ci/pipeline.yml 存在且含 stages 0..5
  PL-2 三条禁令文本仍在 pipeline.yml 中
  PL-3 Stage 3 的 forbidden_shortcuts 至少 8 条
用法：python3 ci/pipeline_lint.py [--root .]
退出码：0 PASS / 1 FAIL
"""
import argparse
import os
import re
import sys

FG_PATTERNS = [
    ("FG-1", re.compile(
        r"\(\s*(?:const\s+)?ggml_cuda_mm_id_tile_spec\s*\*\s*\)\s*"
        r"[A-Za-z_][A-Za-z0-9_]*\s*(?:bounds|expert_bounds)", re.I)),
    ("FG-1b", re.compile(
        r"reinterpret_cast\s*<\s*(?:const\s+)?ggml_cuda_mm_id_tile_spec\s*\*\s*>\s*"
        r"\(\s*[A-Za-z_][A-Za-z0-9_]*\s*(?:bounds|expert_bounds)", re.I)),
    ("FG-2", re.compile(
        r"(?:make_|build_|fake_|fabricat)\w*\s*tile_spec|"
        r"tile_spec\s*\[\s*\w+\s*\]\s*\.\s*(?:expert|col_low|col_high)\s*=", re.I)),
    ("FG-3", re.compile(
        r"(?:disable|break|invalidate|corrupt)\w*\s*(?:the\s*)?overlay\w*\s*anchor|"
        r"STRATA_TQ_OVERLAY_SOFT\s*=\s*ON.*(?:pass|green)|"
        r"anchor\w*\s*(?:missing|absent).*(?:fallback|fp16)\s*(?:path)?\s*(?:as\s*)?pass", re.I)),
]
# 白名单：本脚本自身、pipeline.yml（文本定义）、文档里的「禁令」描述
SKIP_DIRS = {".git", "build-r28", "build-r29", "build-r29b", "build-w1093-fix5", "__pycache__"}
SKIP_EXT = {".md", ".txt", ".tsv", ".json", ".yml", ".yaml", ".log", ".patch", ".diff", ".html"}


def iter_sources(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in SKIP_EXT:
                continue
            if ext not in (".c", ".cc", ".cpp", ".cu", ".cuh", ".h", ".hpp"):
                continue
            yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    root = a.root
    fails, checks = [], 0

    # ---- FG-1/2/3 源码扫描 ----
    hits = []
    for p in iter_sources(root):
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for name, pat in FG_PATTERNS:
            for m in pat.finditer(txt):
                line = txt[:m.start()].count("\n") + 1
                hits.append((name, os.path.relpath(p, root), line, m.group(0)[:80]))
    checks += 1
    if hits:
        fails.append("FG: %d hit(s)" % len(hits))
        for h in hits[:20]:
            print("  FAIL %s %s:%d  %r" % h)
    else:
        print("  PASS FG-1/2/3: no fake-green pattern in C/C++/CUDA sources")

    # ---- PL-1/2/3 pipeline.yml ----
    yml = os.path.join(root, "ci", "pipeline.yml")
    checks += 1
    if not os.path.isfile(yml):
        fails.append("PL-1: ci/pipeline.yml missing")
    else:
        t = open(yml, encoding="utf-8").read()
        missing = [s for s in ("  - id: 0", "  - id: 1", "  - id: 2", "  - id: 3", "  - id: 4", "  - id: 5")
                   if s not in t]
        checks += 1
        if missing:
            fails.append("PL-1: stages missing %s" % missing)
        else:
            print("  PASS PL-1: stages 0..5 present")
        checks += 1
        for tag in ("FG-1", "FG-2", "FG-3"):
            if tag not in t:
                fails.append("PL-2: %s not listed in pipeline.yml" % tag)
                break
        else:
            print("  PASS PL-2: FG-1/2/3 listed")
        checks += 1
        m = re.search(r"forbidden_shortcuts:\n((?:\s+- .*\n)+)", t)
        n = len(re.findall(r"^\s+- ", m.group(1), re.M)) if m else 0
        if n < 8:
            fails.append("PL-3: forbidden_shortcuts=%d (<8)" % n)
        else:
            print("  PASS PL-3: forbidden_shortcuts=%d" % n)

    print("")
    if fails:
        for f in fails:
            print("FAIL " + f)
        print("PIPELINE_LINT: FAIL (%d checks)" % checks)
        return 1
    print("PIPELINE_LINT: PASS (%d checks)" % checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
