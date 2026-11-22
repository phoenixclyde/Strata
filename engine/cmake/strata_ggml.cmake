# cmake/strata_ggml.cmake - where the engine's ggml comes from: the tree vendored in third_party/strata-ggml (default, no download), or -DSTRATA_GGML_DIR=<llama.cpp>.
#
# Every block below is a macro: it runs in the scope of the caller (CMakeLists.txt calls it where the block used to be), so variables, targets and
# their order are those of the single-file CMakeLists.txt it was cut from (cleanup 5.4; the build graph is identical).

# which ggml tree the engine builds from: the vendored third_party/strata-ggml, or the -DSTRATA_GGML_DIR override (repo_root: the checkout)
macro(strata_ggml_resolve repo_root)
set(STRATA_GGML_DIR "" CACHE PATH "llama.cpp checkout to take ggml from instead of the vendored third_party/strata-ggml (empty: the vendored tree)")
if(STRATA_GGML_DIR)
  set(_strata_ggml_root "${STRATA_GGML_DIR}")
else()
  get_filename_component(_strata_ggml_root "${repo_root}/third_party/strata-ggml" ABSOLUTE)   # (normalised: sycl/ and metal/ pass <repo>/sycl/..)
endif()
endmacro()

# the root project's ggml-base / ggml-cpu: the forced GGML_* options per build kind (portable, ISA floor, native) and the subproject
macro(strata_ggml_configure_root)
  set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
  set(GGML_STATIC ON CACHE BOOL "" FORCE)
  set(GGML_CUDA OFF CACHE BOOL "" FORCE)
  set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
  set(GGML_BACKEND_DL OFF CACHE BOOL "" FORCE)
  set(GGML_BUILD_TESTS OFF CACHE BOOL "" FORCE)
  set(GGML_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
  if(STRATA_PORTABLE AND NOT STRATA_CPU_X86)
    # arm64 (DGX Spark: Cortex-X925 + A725): ggml-cpu for any Armv8.2 CPU with dot product, FP16 and int8 matmul instead of the build
    # host's, so the engine built here does not depend on which core the compiler ran on.  Without it GGML_NATIVE OFF would leave
    # ggml-cpu at plain armv8-a, and a native pack's CPU experts would lose the NEON dot products.
    set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
    set(STRATA_ARM64_ARCH "armv8.2-a+dotprod+fp16+i8mm" CACHE STRING "arm64: ggml-cpu's -march for a STRATA_PORTABLE build")
    set(GGML_CPU_ARM_ARCH "${STRATA_ARM64_ARCH}" CACHE STRING "" FORCE)
  elseif(STRATA_PORTABLE)
    set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
    foreach(_f GGML_AVX GGML_AVX2 GGML_FMA GGML_F16C GGML_BMI2)
      set(${_f} ON CACHE BOOL "" FORCE)
    endforeach()
  elseif(STRATA_ISA_FLOOR)
    # the experimental older-CPU build (STRATA_ISA_FLOOR above): one ggml-cpu for the floor, ggml's "sandybridge"
    # feature set (SSE4.2 + AVX) or SSE4.2 alone - not the build host's, which may be newer than the PC it runs on.
    # From the Strata_Dirigo fork (rwkeyes).  ggml's defaults turn the rest on when GGML_NATIVE is off: all off here.
    set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
    set(GGML_CPU_ALL_VARIANTS OFF CACHE BOOL "" FORCE)
    set(GGML_SSE42 ON CACHE BOOL "" FORCE)
    if(STRATA_ISA_FLOOR STREQUAL "avx")
      set(GGML_AVX ON CACHE BOOL "" FORCE)
    else()
      set(GGML_AVX OFF CACHE BOOL "" FORCE)
    endif()
    foreach(_f GGML_AVX2 GGML_FMA GGML_F16C GGML_BMI2 GGML_AVX_VNNI GGML_AVX512 GGML_AVX512_VBMI GGML_AVX512_VNNI
               GGML_AVX512_BF16 GGML_AMX_TILE GGML_AMX_INT8 GGML_AMX_BF16)
      set(${_f} OFF CACHE BOOL "" FORCE)
    endforeach()
  else()
    set(GGML_NATIVE ON CACHE BOOL "" FORCE)
  endif()
  add_subdirectory(${_strata_ggml_root}/ggml ${CMAKE_BINARY_DIR}/ggml EXCLUDE_FROM_ALL)
endmacro()

# the CUDA/HIP prompt path compiles llama.cpp's MMQ kernel into the engine
# (src/prefill/moe_mmq.cu includes mmq.cuh and uses ggml_cuda_mm_id_tile_spec, which b12361
# introduced when it replaced mmq_args' expert_bounds with a device tile table).  A resolved
# tree older than that cannot compile the bridge: say so once, at configure time, instead of
# letting a hundred template errors stand in for "you are building against the wrong ggml".
# The vendored third_party/strata-ggml is still pinned at b11062, so the default path trips
# this on purpose -- the message names the override.
macro(strata_ggml_require_mmq_abi)
  # W1182/R101: the vendored tree is CPU/test-only (it is pinned at b11062, two months
  # behind the b12567 the engine is built against).  A GPU build that forgets the
  # override used to fall back to it and die in template errors; now it stops here with
  # one sentence.  This is the contract the plan asks for: the default cannot be wrong,
  # because for CUDA/HIP there is no default.
  if(NOT STRATA_GGML_DIR)
    message(FATAL_ERROR
      "Strata: a CUDA/HIP build needs -DSTRATA_GGML_DIR=<llama.cpp checkout>. "
      "third_party/strata-ggml is the CPU/test pin (b11062) and does not carry the "
      "ggml-cuda sources the prompt kernels compile against (b12361+). "
      "Use the tree the production image ships, e.g. -DSTRATA_GGML_DIR=/ggml.")
  endif()
  set(_mmq "${_strata_ggml_root}/ggml/src/ggml-cuda/mmq.cuh")
  if(NOT EXISTS "${_mmq}")
    message(FATAL_ERROR
      "Strata: no MMQ header at ${_mmq}. The CUDA/HIP prompt path builds llama.cpp's MMQ kernel. "
      "Pass -DSTRATA_GGML_DIR=<llama.cpp checkout at b12361 or newer>.")
  endif()
  file(READ "${_mmq}" _mmq_txt LIMIT 262144)
  if(NOT _mmq_txt MATCHES "ggml_cuda_mm_id_tile_spec")
    message(FATAL_ERROR
      "Strata: the resolved ggml tree is older than llama.cpp b12361: ${_mmq} has no "
      "ggml_cuda_mm_id_tile_spec, and engine/src/prefill/moe_mmq.cu uses it. "
      "Pass -DSTRATA_GGML_DIR=<llama.cpp checkout at b12361 or newer>. "
      "(The vendored third_party/strata-ggml is pinned at b11062 and cannot build this bridge.)")
  endif()
endmacro()
