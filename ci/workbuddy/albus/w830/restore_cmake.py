# -*- coding: utf-8 -*-
"""Restore our two local CMake patches that the 0.2.8 file copy overwrote (W793 rocBLAS wiring, W776 dflash2 scope).
Idempotent: refuses to double-apply, asserts every anchor."""
import io, sys

P = sys.argv[1] if len(sys.argv) > 1 else '/home/albus/strata166/src028/CMakeLists.txt'
t = io.open(P, encoding='utf-8').read()
changed = []

# ---- W793 part 1: wire rocBLAS into the gfx906 branch
A_OLD = ("  set(_strata_gpu_include_directories ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})\n"
         "elseif(STRATA_ENABLE_CUDA)")
A_NEW = ("  set(_strata_gpu_include_directories ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})\n"
         "  # W793: this branch never includes cmake/hip_backend.cmake, so STRATA_ROCBLAS_AVAILABLE was never defined and\n"
         "  # the prompt path's rocBLAS solution table (STRATA_ROCBLAS_TUNING) compiled to nothing on gfx906.  The package\n"
         "  # is present in the ROCm image; wire it exactly as the hip_backend path does.\n"
         "  find_package(rocblas CONFIG QUIET)\n"
         "  if(TARGET roc::rocblas)\n"
         "    set(STRATA_ROCBLAS_AVAILABLE ON)\n"
         "  else()\n"
         "    set(STRATA_ROCBLAS_AVAILABLE OFF)\n"
         "    message(STATUS \"Strata: gfx906 rocBLAS package not found; the solution table is unavailable\")\n"
         "  endif()\n"
         "elseif(STRATA_ENABLE_CUDA)")

if 'W793' not in t:
    assert t.count(A_OLD) == 1, 'W793 anchor count=%d' % t.count(A_OLD)
    t = t.replace(A_OLD, A_NEW)
    changed.append('W793a')

# ---- W793 part 2: let the gfx906 branch use the table
B_OLD = "  if(STRATA_ENABLE_HIP AND STRATA_ROCBLAS_AVAILABLE)\n"
B_NEW = "  if((STRATA_ENABLE_HIP OR STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE)\n"
if 'STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE' not in t:
    assert t.count(B_OLD) == 1, 'W793b anchor count=%d' % t.count(B_OLD)
    t = t.replace(B_OLD, B_NEW)
    changed.append('W793b')

# ---- W776: scope STRATA_USE_HIP to dflash2.cpp only
C_OLD = ("  target_link_libraries(strata_engine PUBLIC strata_core strata_kernels strata_kernels_cpu ${_strata_gpu_runtime_target})\n")
C_NEW = C_OLD + (
    "\n"
    "  # [W776 local] gfx906 (STRATA_HIP_GFX906) does not define STRATA_USE_HIP, but dflash2.cpp keys its\n"
    "  # CUDA-vs-HIP branches on it (stream priority + the fork default). Scope the definition to that one\n"
    "  # file: a global STRATA_USE_HIP would switch CUDA-only paths elsewhere (W717/P23 measured that).\n"
    "  if(STRATA_HIP_GFX906)\n"
    "    set_source_files_properties(src/core/dflash2.cpp PROPERTIES COMPILE_DEFINITIONS \"STRATA_USE_HIP=1\")\n"
    "  endif()\n")
if 'W776 local' not in t:
    assert t.count(C_OLD) == 1, 'W776 anchor count=%d' % t.count(C_OLD)
    t = t.replace(C_OLD, C_NEW)
    changed.append('W776')

if changed:
    io.open(P, 'w', encoding='utf-8', newline='\n').write(t)
print('applied:', changed if changed else '(already patched, nothing to do)')
print('markers now:', {m: t.count(m) for m in ('W793', 'W776', 'W717')})
