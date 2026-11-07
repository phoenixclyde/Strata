#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_patch_mxdatagen.py -- 用 HIPBLASLT_ENABLE_MXDATAGENERATOR 把 mxdatagen 那段包起来。

clients/common/CMakeLists.txt 里这段是**无条件**的：
    add_library(hipblaslt-mxdatagen STATIC "src/mxDataGen.cpp")
    ...
    target_link_libraries(hipblaslt-mxdatagen PUBLIC ... roc::mxDataGenerator)
而 roc::mxDataGenerator 来自 `shared/mxdatagenerator`（本树里没有，是 hipBLASLt 的兄弟仓库）。
镜像里有 `-DHIPBLASLT_ENABLE_MXDATAGENERATOR` 这个开关，但这段没用它。

我们只需要 tensilelite-client（跑 benchmark 出 LibraryLogic），MX 数据生成器与它无关，
所以把这段声明包进开关里，OFF 时整段不存在。
"""
P = "/src/projects/hipblaslt/clients/common/CMakeLists.txt"
src = open(P, encoding="utf-8").read()
if "_W861_MXDATAGEN_GUARD" in src:
    print("already patched")
    raise SystemExit(0)

start = src.find("add_library(hipblaslt-mxdatagen STATIC")
if start < 0:
    print("FATAL: anchor not found")
    raise SystemExit(1)
# 找到该 target 相关声明的结尾（target_compile_features 那一行之后）
tail_anchor = "target_compile_features(hipblaslt-mxdatagen PUBLIC cxx_std_20)"
end = src.find(tail_anchor, start)
if end < 0:
    print("FATAL: tail anchor not found")
    raise SystemExit(1)
end += len(tail_anchor)

block = src[start:end]
patched = (
    "if(HIPBLASLT_ENABLE_MXDATAGENERATOR)  # _W861_MXDATAGEN_GUARD\n"
    + block
    + "\nendif()  # _W861_MXDATAGEN_GUARD"
)
open(P, "w", encoding="utf-8").write(src[:start] + patched + src[end:])
print("patched, block lines:", block.count("\n") + 1)
