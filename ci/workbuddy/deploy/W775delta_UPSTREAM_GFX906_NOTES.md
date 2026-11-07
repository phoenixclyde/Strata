# W775delta ---- 上游 issue：MI50/gfx906 对 v0.1.42 的三条文档级更正（**已发**）

> 用途：本件保存**已发上游的正文逐字**（便于回读核验与后续跟进）。
> 事实来源：本机 166（单卡 Radeon Instinct MI50 32GB / gfx906，引擎 0.1.42）实测 + 0.1.42 镜像源码。

**Title**

```
MI50 (gfx906) against v0.1.42: four doc-level notes (decode-half defaults, IO_PREFETCH, ROUTE_TAIL_SKIP wording, dump-logits)
```

**Body**

```
Context: one Radeon Instinct MI50 32GB (gfx906), engine 0.1.42, a native UD-IQ4_XS pack, --kv k8v4, single GPU.
Everything below was measured on that box; every comparison was single-variable (the two configs differ only in the
config `env` block, the engine `args` are asserted byte-identical), interleaved, and read from the engine's own
"256 generated in N ms" line.  Raw data and the exact commands are available on request.

1) `arch_defaults.cpp`: the decode half of the gfx1151 table does not transfer to gfx906
----------------------------------------------------------------------------------------
`arch_default_env()` returns the table only for gfx12 (prompt half) and gfx1151; on gfx906 it returns the empty table
and nothing is auto-enabled.  That part is clear.  What we measured is the value of one entry on gfx906:

  `STRATA_Q8_PACKED=1` (the packed Q8_0 decode layout, annotated "+2.3% (S26)" in the table), A baseline vs Q,
  ABBA x5 interleaved, L=16384, max_tokens=256, decode ms/step:
      all 10 points:                        A 23.436   Q 23.805   (+1.57%)
      warm 8 (first run of a block dropped) A 22.656   Q 23.286   (+2.78%)
  Arm-internal spread: A 6.6%, Q 18.8%, so the delta is inside the spread => we read it as no gain.
  Cost: +1,912.5 MiB VRAM ("native dense: STRATA_Q8_PACKED=1 packed 84 Q8_0 matrices for decode (+1912.5 MiB)").
  Correctness: bit-identical outputs in all 5 launches (same fixed-prompt md5), i.e. lossless as documented.

The table's own gfx12 comment already says "the decode half measured slower on that card, so it stays out"; gfx906 is
a third card with the same outcome.  Suggestion: state "decode half = not universal" in the table comment or the docs,
so MI50 and other users do not copy it.

2) `STRATA_IO_PREFETCH`: on a large-RAM host it is a no-op
----------------------------------------------------------
Host: 128 GiB RAM, `--resident-budget-gib 76`.  The switch is taken (it is in the engine's /proc environ, and the
start line says "file tier io prefetch ON ... 8 I/O threads"), but the per-request line is

  `io prefetch: 0 read ahead (0.0 MB by pread), 0 used, 0 unused, 0 skipped (cached), 0 dropped`

in 4/4 readings, and the same request reports "the OS read 998.5 MB from storage ... for 42282.7 MB of expert reads;
page cache held 78191.7 MB at the read".  The switch is on, there is just nothing to prefetch.
Suggestion: one line in the notes that the benefit requires the experts to be *not* resident in RAM.

3) `STRATA_ROUTE_TAIL_SKIP`: "off ... on AMD and Intel" does not match a gfx906 build here
--------------------------------------------------------------------------------------------
On our gfx906 build:
  - the start line prints `STRATA_ROUTE_TAIL_SKIP=7 is ON (default)` in 12/12 starts;
  - the running counter prints `route tail skip: <N> missed experts skipped (<M> entries) since the start`, N reaching
    672,855.
Mechanism: `generate.cpp` guards that default with `#if !defined(STRATA_USE_HIP)`.  In this build `STRATA_USE_HIP` is
defined only on the INTERFACE target `strata_hip_runtime`, which the main engine target does not link, so the CUDA
branch is compiled in and the default applies.  `CMakeLists.txt` sets `STRATA_HIP_GFX906=1` globally, and its option
text reads "Build the CUDA targets for AMD gfx906 through HIP (wave64 compat layer)".

So the sentence is correct for a HIP-target build and incorrect for ours; would you like it checked / reworded?
(The practical consequence for us is that our answers differ slightly from the exact 0.1.41 ones; setting
`STRATA_ROUTE_TAIL_SKIP=0` restores them, which matches the documented explicit override.)

4) `--dump-logits` and native packs
-----------------------------------
`generate.cpp` comments "A native pack never runs the per-token loop `--dump-logits` reads", so on a native pack the
flag returns nothing.  Suggest one line in its help text.
```
