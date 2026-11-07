# -*- coding: utf-8 -*-
"""W793：给 gfx906 分支接上 rocBLAS 解题表（STRATA_ROCBLAS_AVAILABLE）。

上游 0.2.4.2 的现状（逐字）：
  * `CMakeLists.txt:112`  `if(STRATA_ENABLE_HIP) include(cmake/hip_backend.cmake) endif()`
  * `cmake/hip_backend.cmake:84`  `if(TARGET roc::rocblas) set(STRATA_ROCBLAS_AVAILABLE ON)`
  * gfx906 走 `CMakeLists.txt:149` 的独立分支，只 find_package(hip) + find_package(hipblas)
=> `STRATA_ROCBLAS_AVAILABLE` 永不定义 => `gemm.cu` 的 try_rocblas_f16o 整段被 `#if` 掉
   => `STRATA_ROCBLAS_TUNING` 是死开关（容器 build-906/build.ninja 里 grep 不到）。

本补丁只做两件事（不改任何算术）：
  1) 在 gfx906 分支里 find_package(rocblas) 并按 roc::rocblas 目标置 STRATA_ROCBLAS_AVAILABLE
  2) 把 729 行的前置条件从 `STRATA_ENABLE_HIP` 放宽到 `STRATA_ENABLE_HIP OR STRATA_HIP_GFX906`
"""
import io
import sys

ANCHOR1 = ("  set(_strata_gpu_include_directories ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})\n"
           "elseif(STRATA_ENABLE_CUDA)")
INSERT1 = """  set(_strata_gpu_include_directories ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})
  # W793: this branch never includes cmake/hip_backend.cmake, so STRATA_ROCBLAS_AVAILABLE was never defined and
  # the prompt path's rocBLAS solution table (STRATA_ROCBLAS_TUNING) compiled to nothing on gfx906.  The package
  # is present in the ROCm image; wire it exactly as the hip_backend path does.
  find_package(rocblas CONFIG QUIET)
  if(TARGET roc::rocblas)
    set(STRATA_ROCBLAS_AVAILABLE ON)
  else()
    set(STRATA_ROCBLAS_AVAILABLE OFF)
    message(STATUS "Strata: gfx906 rocBLAS package not found; the solution table is unavailable")
  endif()
elseif(STRATA_ENABLE_CUDA)"""

OLD2 = "  if(STRATA_ENABLE_HIP AND STRATA_ROCBLAS_AVAILABLE)\n"
NEW2 = "  if((STRATA_ENABLE_HIP OR STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE)\n"


def main(path):
    t = io.open(path, encoding="utf-8").read()
    if "W793" in t:
        print("already patched")
        return 0
    assert t.count(ANCHOR1) == 1, "anchor1 count=%d" % t.count(ANCHOR1)
    t = t.replace(ANCHOR1, INSERT1, 1)
    assert t.count(OLD2) == 1, "anchor2 count=%d" % t.count(OLD2)
    t = t.replace(OLD2, NEW2, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("patched", path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
