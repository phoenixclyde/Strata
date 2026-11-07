#!/usr/bin/env python3
"""Classify upstream llama.cpp commits in (pin, HEAD] by the surface this fork actually builds.

Surface facts (verified from build-r32/build.ninja + cmake/strata_ggml_tq_overlay.cmake):
  * strata_mmq  <- ref/ggml/src/ggml-cuda/{mmq.cuh,mmq-load-tiles.cuh,mmq-config*.cuh,common.cuh,
                   quantize.cu,template-instances/mmq-instance-*.cu}  (overlay copy of the pinned tree)
  * ggml-base   <- ggml/src/{ggml.c,ggml-quants.c,ggml-alloc.c,ggml-backend*.cpp,gguf.cpp,...}
  * ggml-cpu    <- ggml/src/ggml-cpu/**  (16 TUs; includes arch/x86, amx/mmq, tiled, repack)
  * NOT built   <- ggml/src/ggml-cuda/*.cu except quantize.cu + mmq instances; no fattn/mmvq/cpy/etc.
"""
import subprocess, sys, collections, json, os

REPO = os.path.expanduser("~/strata166/w1031/lcpp")
PIN = "3cf03257f219afbe7334045ff7c6a06ac68c627d"

A_PREFIX = (
    "ggml/src/ggml-cuda/mmq", "ggml/src/ggml-cuda/moe_mmq.cu",
    "ggml/src/ggml-cuda/mmid", "ggml/src/ggml-cuda/quantize.cu",
    "ggml/src/ggml-cuda/common.cuh", "ggml/src/ggml-cuda/vecdotq.cuh",
    "ggml/src/ggml-cuda/dequantize.cuh", "ggml/src/ggml-cuda/vendors/",
    "ggml/include/ggml.h", "ggml/src/ggml-cuda/template-instances/mmq",
    "ggml/src/ggml-common.h",
)
B_PREFIX = ("ggml/src/ggml-cpu/",)
C_PREFIX = ("ggml/src/ggml.c", "ggml/src/ggml-quants.c", "ggml/src/ggml-impl.h",
            "ggml/src/ggml-alloc.c", "ggml/src/ggml-backend", "ggml/src/gguf.cpp",
            "ggml/src/ggml.cpp", "ggml/src/ggml-threading.cpp", "ggml/src/ggml-opt.cpp")


def cls(paths):
    a = [p for p in paths if p.startswith(A_PREFIX)]
    b = [p for p in paths if p.startswith(B_PREFIX)]
    c = [p for p in paths if p.startswith(C_PREFIX)]
    return a, b, c


def main():
    out = subprocess.run(
        ["git", "-C", REPO, "log", "--date=short", "--format=@@%H|%h|%ad|%s", "--name-only",
         f"{PIN}..HEAD"],
        capture_output=True, text=True, check=True).stdout
    commits = []
    cur = None
    for line in out.splitlines():
        if line.startswith("@@"):
            if cur:
                commits.append(cur)
            h, sh, d, s = line[2:].split("|", 3)
            cur = {"sha": h, "short": sh, "date": d, "subject": s, "paths": []}
        elif line.strip():
            cur["paths"].append(line.strip())
    if cur:
        commits.append(cur)

    tally = collections.Counter()
    rows = []
    for c in commits:
        a, b, cc = cls(c["paths"])
        if a:
            cat = "A_mmq"
        elif b:
            cat = "B_cpu"
        elif cc:
            cat = "C_core"
        else:
            cat = "D_other"
        tally[cat] += 1
        rows.append({"cat": cat, "sha": c["sha"], "short": c["short"], "date": c["date"],
                     "subject": c["subject"], "nfiles": len(c["paths"]),
                     "a": a, "b": b, "c": cc,
                     "other": [p for p in c["paths"] if p not in a + b + cc]})

    with open(os.path.expanduser("~/strata166/w1031/triage.json"), "w") as f:
        json.dump(rows, f, indent=1)

    print("total commits:", len(commits))
    for k in ("A_mmq", "B_cpu", "C_core", "D_other"):
        print(f"  {k}: {tally[k]}")
    print()
    for cat in ("A_mmq", "B_cpu", "C_core"):
        print(f"===== {cat} =====")
        for r in rows:
            if r["cat"] != cat:
                continue
            f = ",".join((r["a"] + r["b"] + r["c"])[:3])
            print(f"{r['short']} {r['date']} {r['subject'][:88]}  [{f}]")


main()
