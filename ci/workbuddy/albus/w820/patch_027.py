"""W820: 把我们的两处补丁打到上游 0.2.7 源码树上（在 166 宿主机上跑）。

用法: python3 patch_027.py <src_dir> <patched qsa_decode_attn.cu>

与 0.2.4.2 上的 W793/W776/W794 等价：
  A. gfx906 分支补 find_package(rocblas) —— 否则 STRATA_ROCBLAS_TUNING 编成空（生产在用该表）
  B. 让 gfx906 也走到链接 rocBLAS 表的那段
  C. 把 STRATA_USE_HIP=1 只作用于 src/core/dflash2.cpp
  D. qsa_decode_attn.cu 换成本地打好的版本（0.2.7 该文件与 0.2.4.2 逐字节相同）

0.2.7 的坑：`set(_strata_gpu_include_directories ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})` 出现两次
（gfx906 分支与 CUDA 分支各一），缩进是 2 空格。所以 A 必须靠 “gfx906 compat” 那句 message 定位。
"""
import os
import re
import sys

SRC = sys.argv[1]
QSA = sys.argv[2]

cm = os.path.join(SRC, "CMakeLists.txt")
lines = open(cm, encoding="utf-8").read().split("\n")
orig = "\n".join(lines)

m = re.search(r"project\(strata VERSION ([\d.]+)", orig)
assert m and m.group(1) == "0.1.52", "unexpected engine version: %s" % (m.group(1) if m else "?")


def find(pat, start=0, count_expected=None):
    hits = [i for i in range(start, len(lines)) if re.search(pat, lines[i])]
    if count_expected is not None:
        assert len(hits) == count_expected, "pattern %r -> %d hits (want %d)" % (pat, len(hits), count_expected)
    return hits


# ---- A: gfx906 分支 ----
gi = find(r"Strata: HIP \(gfx906 compat\) enabled", count_expected=1)[0]
inc = find(r"^\s*set\(_strata_gpu_include_directories \$\{CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES\}\)", start=gi)
assert inc, "gfx906 branch: include_directories anchor not found after line %d" % (gi + 1)
i = inc[0]
indent = re.match(r"^(\s*)", lines[i]).group(1)
block = [
    indent + "# W793: this branch never includes cmake/hip_backend.cmake, so STRATA_ROCBLAS_AVAILABLE was never defined and",
    indent + "# the prompt path's rocBLAS solution table (STRATA_ROCBLAS_TUNING) compiled to nothing on gfx906.  The package",
    indent + "# is present in the ROCm image; wire it exactly as the hip_backend path does.",
    indent + "find_package(rocblas CONFIG QUIET)",
    indent + "if(TARGET roc::rocblas)",
    indent + "  set(STRATA_ROCBLAS_AVAILABLE ON)",
    indent + "else()",
    indent + "  set(STRATA_ROCBLAS_AVAILABLE OFF)",
    indent + '  message(STATUS "Strata: gfx906 rocBLAS package not found; the solution table is unavailable")',
    indent + "endif()",
]
lines[i + 1 : i + 1] = block
print("A: inserted rocBLAS wiring after line %d" % (i + 1))

# ---- B: 链接条件 ----
b = find(r"^\s*if\(STRATA_ENABLE_HIP AND STRATA_ROCBLAS_AVAILABLE\)", count_expected=1)[0]
indent = re.match(r"^(\s*)", lines[b]).group(1)
lines[b] = indent + "if((STRATA_ENABLE_HIP OR STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE)"
print("B: link condition widened at line %d" % (b + 1))

# ---- C: dflash2 的 STRATA_USE_HIP ----
c = find(r"^\s*target_link_libraries\(strata_engine PUBLIC strata_core strata_kernels strata_kernels_cpu", count_expected=1)[0]
indent = re.match(r"^(\s*)", lines[c]).group(1)
block = [
    "",
    indent + "# [W776 local] gfx906 (STRATA_HIP_GFX906) does not define STRATA_USE_HIP, but dflash2.cpp keys its",
    indent + "# CUDA-vs-HIP branches on it (stream priority + the fork default). Scope the definition to that one",
    indent + "# file: a global STRATA_USE_HIP would switch CUDA-only paths elsewhere (W717/P23 measured that).",
    indent + "if(STRATA_HIP_GFX906)",
    indent + '  set_source_files_properties(src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS "STRATA_USE_HIP=1")',
    indent + "endif()",
]
lines[c + 1 : c + 1] = block
print("C: dflash2 scoped define inserted after line %d" % (c + 1))

t = "\n".join(lines)
assert t != orig
open(cm, "w", encoding="utf-8", newline="\n").write(t)
print("CMakeLists.txt: +%d bytes" % (len(t) - len(orig)))

# ---- D: qsa_decode_attn.cu ----
dst = os.path.join(SRC, "src/kernels/cuda/qsa_decode_attn.cu")
base = open(dst, "rb").read()
new = open(QSA, "rb").read()
assert base.count(b"attn_chunk_kernel<3") == 0, "base already carries the W794 hunks?"
assert new.count(b"attn_chunk_kernel<3") == 2, "patched file lacks the W794 instances"
open(dst, "wb").write(new)
print("qsa_decode_attn.cu: %d -> %d bytes" % (len(base), len(new)))

t = open(cm, encoding="utf-8").read()
for probe in ("find_package(rocblas CONFIG QUIET)", "(STRATA_ENABLE_HIP OR STRATA_HIP_GFX906)",
              "src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS", "W793", "W776"):
    print("  check %-52s %s" % (probe, "OK" if probe in t else "MISSING"))
