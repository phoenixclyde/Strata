#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_patch_msgpack_cmake.py -- 把 msgpack 路径在 YAML 模式下也编进来（W858 §8.1）。

根因（源码级）：
  tensilelite/CMakeLists.txt 是 if(HIPBLASLT_ENABLE_YAML) ... else() ... endif()
    YAML  分支 -> 只定义 TENSILE_YAML
    msgpack 分支 -> 才定义 TENSILE_MSGPACK
  而 `TensileLite::LoadLibraryMapping` 的定义在 `#ifdef TENSILE_MSGPACK` 里
  ⇒ 开 YAML 编出来的 libhipblaslt 里它是 **U（undefined）**，
    运行时一进库加载就崩（不是 comgr，不是 gfx906）。
  证据：nm -D 里 MessagePack 符号 0 个、LoadLibraryMapping 为 U。

修法：YAML 分支里额外补上 msgpack 的源文件与宏，两条路径同时存在。
"""
P = "/src/projects/hipblaslt/tensilelite/CMakeLists.txt"
src = open(P, encoding="utf-8").read()
if "_W861_MSGPACK_ALSO" in src:
    print("already patched")
    raise SystemExit(0)

old = """    if(HIPBLASLT_ENABLE_YAML)
        target_link_libraries(tensilelite-host PRIVATE LLVMObjectYAML)
        target_include_directories(tensilelite-host PRIVATE ${LLVM_INCLUDE_DIRS})
        target_compile_definitions(tensilelite-host PUBLIC $<BUILD_INTERFACE:TENSILE_YAML>)
    else()"""
new = """    if(HIPBLASLT_ENABLE_YAML)
        target_link_libraries(tensilelite-host PRIVATE LLVMObjectYAML)
        target_include_directories(tensilelite-host PRIVATE ${LLVM_INCLUDE_DIRS})
        target_compile_definitions(tensilelite-host PUBLIC $<BUILD_INTERFACE:TENSILE_YAML>)
        # _W861_MSGPACK_ALSO: LoadLibraryMapping 只在 #ifdef TENSILE_MSGPACK 里定义，
        # YAML 模式不定义它 -> libhipblaslt 里该符号是 U -> 运行时崩。
        # 这里把 msgpack 路径一并编进来（同时保留 YAML 读取能力）。
        target_sources(tensilelite-host PRIVATE src/msgpack/MessagePack.cpp)
        target_compile_definitions(tensilelite-host PUBLIC $<BUILD_INTERFACE:TENSILE_MSGPACK>)
        target_link_libraries(tensilelite-host PRIVATE ${hipblaslt_msgpack_target})
    else()"""
assert old in src, "pattern not found"
open(P, "w", encoding="utf-8").write(src.replace(old, new))
print("patched", P)
