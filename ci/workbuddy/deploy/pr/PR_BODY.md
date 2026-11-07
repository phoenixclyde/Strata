Two gfx906 build failures on v0.1.40.2 (`main` = `e8ca9afd03d8`). Both are one-line gates that know about the wave32 HIP backend but not about `STRATA_HIP_GFX906` -- the same class as #808 and #1083, and neither is fixed on `main`.

## 1. `prefill.cpp` does not compile -- `cudaEventBlockingSync` is not mapped for gfx906

```
src/prefill/prefill.cpp:399:99: error: use of undeclared identifier 'cudaEventBlockingSync'
```

`hip_compat` has two headers. The wave32 one, `include/strata/hip_compat/cuda_runtime.h` (line 39), has the mapping:

```c
#define cudaEventBlockingSync hipEventBlockingSync
```

The gfx906 one, `include/strata/platform/hip_compat/strata_hip.h`, maps only its two neighbours:

```c
#define cudaEventDisableTiming hipEventDisableTiming
#define cudaEventDefault hipEventDefault
```

**Fix** -- add the one missing line:

```c
#define cudaEventDisableTiming hipEventDisableTiming
#define cudaEventBlockingSync hipEventBlockingSync
#define cudaEventDefault hipEventDefault
```

I diffed the whole set of `cuda*` defines between the two headers. The only other name the gfx906 header lacks is `cudaDevAttrIntegrated`, and that one is already handled: `src/core/expert_cache.cpp:31` guards its use with `#if defined(__linux__) && !defined(STRATA_HIP_GFX906)`. So this adds exactly the one mapping that a live call site needs, and nothing else.

## 2. The link fails -- the q6_k MMQ instance is never built

```
ld.lld: error: undefined symbol: void mul_mat_q_case<(ggml_type)14>(
    ggml_backend_cuda_context&, mmq_args const&, ihipStream_t*)
```

`(ggml_type)14` is `GGML_TYPE_Q6_K`. Two halves disagree:

- `src/prefill/moe_mmq.cu:219` is gated on **the compiler**, so any HIP compilation references it:

```c
#if defined(__HIPCC__) || defined(STRATA_Q6K_EXPERTS)
        case GGML_TYPE_Q6_K: mul_mat_q_case<GGML_TYPE_Q6_K>(ctx, a, s); break;
```

- `mmq.cuh`'s `DECL_MMQ_CASE` is an **`extern template`** (implicit instantiation suppressed), so the definition has to come from `template-instances/mmq-instance-q6_k.cu`, which the **CUDA branch** of `CMakeLists.txt` adds only under `STRATA_Q6K_EXPERTS` (line 1270):

```cmake
      set(_strata_mmq_cuda_types ${_strata_mmq_types})
      if(STRATA_MMQ_KQUANTS)
        list(APPEND _strata_mmq_cuda_types q4_k q5_k q5_1)
        if(STRATA_Q6K_EXPERTS)   # UD-Q6_K_XL gate/up (docs/UNSLOTH_Q6.md)
          list(APPEND _strata_mmq_cuda_types q6_k)
        endif()
      endif()
```

`STRATA_HIP_GFX906=ON` forces `STRATA_ENABLE_CUDA=ON`, so the gfx906 build takes the **CUDA branch** while its `.cu` files are compiled as HIP => `__HIPCC__` is defined => the call is there and the instance is not. The HIP branch (line 1330) already appends `q6_k` unconditionally under `STRATA_MMQ_KQUANTS`; the CUDA branch is the one that does not know about gfx906.

**Fix** -- widen the gate:

```cmake
        if(STRATA_Q6K_EXPERTS OR STRATA_HIP_GFX906)
          list(APPEND _strata_mmq_cuda_types q6_k)
        endif()
```

This adds **one MMQ instance** to `strata_mmq`. It does **not** enable `STRATA_Q6K_EXPERTS` (the grouped Q6_K expert kernels, which are what allocate the extra VRAM), and `STRATA_HIP_GFX906` is only ever ON in the gfx906 build, so CUDA and wave32 builds are untouched.

## Verified

Single Instinct **MI50 32 GB** (gfx906, wave64), ROCm/HIP 7.14, `-DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906 -DSTRATA_MMQ_KQUANTS=ON`:

- with both changes, `ninja strata` completes, and the engine serves UD-IQ4_XS (Qwen3.8-Flash-Next) end to end: `/v1/models`, chat completions, tool calls, MTP drafts accepted;
- `nm -C strata` shows `mul_mat_q_case<(ggml_type)14>` in the binary (13 instances: 7 8 12 13 14 16 17 18 20 21 22 23 42);
- change 2 is load-bearing, not cosmetic: `libstrata_mmq.a` holds exactly one `U` reference and one `W` definition of that symbol; after removing `mmq-instance-q6_k.cu.o` from the archive, relinking with the *same* link command line fails with exactly the error quoted above, while the untouched archive relinks cleanly;
- #808's `cudaFuncSetAttribute` and #1083's three `STRATA_USE_HIP` gates are already on `main`; this PR does not touch them.

## Notes

- No test added: these are compile/link-time failures for one build configuration, which the current CI does not cover. If you tell me where a gfx906 build would sit in `tests/`, I am happy to add one.
- Found while bringing up the gfx906 path of #638 on a second machine (single MI50 32 GB). A separate performance report for that machine is unrelated to this PR and not included here.
