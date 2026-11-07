#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_patch_memset.py -- 让 hipblasLtCreate 不再因 hipMemset 的 comgr JIT 失败而 exit。

背景（W858 §7.1 + 本轮上网核实）：
  ROCm 10.1 的 comgr 仍向 clang 24 传 `--amdhsa-code-object-version=5` / `-amdgpu-prelink`，
  这两个参数官方在 ROCm 5.4.2 就弃用了 ⇒ OpenCL JIT 失败 ⇒ hipMemset 失败 ⇒
  CHECK_HIP_ERROR 里 exit(EXIT_FAILURE)。同类现象见 ROCm/TheRock#9291、llama.cpp#27275
  （ROCm 7.x comgr 在 gfx1030 上直接 segfault，AMD 已不修旧架构）。

本补丁只把两处 memset 的**致命性**去掉（返回码忽略、继续），不清零本身的语义保留调用：
  - :170  d_Synchronizer（GSU reduction 同步区）
  - :176  d_StreamKFlags（Stream-K flags）
副作用：若 kernel 真用到这两个缓冲区且依赖初值 0，结果可能错。
        探针的 heuristic 路径不执行 matmul，所以不受影响；生产不可用（见 W861 §4.5）。
"""
P = "/src/projects/hipblaslt/library/src/amd_detail/hipblaslt.cpp"
src = open(P, encoding="utf-8").read()
if "_W861_MEMSET_SOFT" in src:
    print("already patched")
    raise SystemExit(0)

a = "    CHECK_HIP_ERROR(hipMemset(d_Synchronizer, 0, gsuBytes));"
b = "    if(hipError_t e = hipMemset(d_StreamKFlags, 0, skBytes); e != hipSuccess)"
assert a in src, "memset A not found"
assert b in src, "memset B not found"

src = src.replace(a,
    "    { hipError_t _e = hipMemset(d_Synchronizer, 0, gsuBytes); (void)_e; }  // _W861_MEMSET_SOFT")
src = src.replace(b,
    "    if(hipError_t e = hipMemset(d_StreamKFlags, 0, skBytes); false && e != hipSuccess)  // _W861_MEMSET_SOFT")
open(P, "w", encoding="utf-8").write(src)
print("patched", P)
i = src.find("_W861_MEMSET_SOFT")
print(src[max(0, i - 260):i + 90])
