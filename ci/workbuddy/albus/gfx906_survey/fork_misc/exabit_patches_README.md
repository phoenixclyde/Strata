> **2026-09-24:** all code is in `exabit-io/mx-llama.cpp` (substrate = `master`; REQUIREMENTS R3.7) and the Exabit patches live on its `gfx906-candidates` / `gfx906-*` branches. Everything below describes the 2026-09-07..09 patch files and is kept as history.

# patches/ — the gfx906 kernel changes behind the production build

> **2026-09-09:** production is `/opt/llama.cpp-prod` → `/opt/llama.cpp-mxxm-fh-nq` (the fork + both MMVQ patches + the 0001–0009 series below); the `gfx906` branch of https://github.com/exabit-io/llama.cpp carries the same series on current upstream (`gfx906-branch/`), and `upstream-S1/` is the tile-table patch prepared for upstream. The first section below is the 2026-09-07 state, kept as written.

The 2026-09-07 run-through produced two source patches and a build recipe. Both patches are in this folder (against upstream b10288); the fork itself is a source tree, not a patch, and lives on the box at `/root/mx-llama.cpp-b10254` (the ML-gfx906 project checkout is `/root/ML-gfx906`). Installed builds: production `/opt/llama.cpp-mxxm-fh`, stock `/opt/llama.cpp`. **Run any /opt build with `LD_LIBRARY_PATH=<prefix>/lib`**: the binaries carry no rpath and the system loader path points at the stock lib directory, so the production `llama-server` otherwise loads the stock kernels (`settings/launch.sh` sets it).

| File | What | Measured effect (run-through s.9, s.10c, s.11) |
|---|---|---|
| `mmvq-max-batch-16-b10288.patch` | `MMVQ_MAX_BATCH_SIZE` 8 → 16 plus the template instantiations in `ggml/src/ggml-cuda/mmvq.cu` (the header half must go in first when applying to the fork) | removes the 9–16 slot cliff on the tensor split: batch 9 96.5 → 162.6, 12 122.5 → 174.6, 16 152.5 → 170.7 tok/s; loses on a single die (113 VGPRs, two waves/SIMD) |
| `mmvq-gfx906-knobs-and-q8-fastpath-b10288.patch` | Q8_0 fast path in the MMVQ kernel: each weight block's quants and scale loaded once per row, each activation block's once per column, the two scales applied as one product per pair; gfx906 launch table set to rows 4 / warps 1 for ≤ 8 columns and rows 2 / warps 1 above (iteration 5) | on upstream b10288 (s.10c): tp4 b8 +8%, b12 +62%, b16 +36%; one die b4 +14%, b8 +37%. In the production build (s.11): +9 / +62 / +34% and +10 / +31%. 1186/1186 `test-backend-ops` mul_mat cases pass; perplexity unchanged (5.5969) |
| ML-gfx906 fork, b10254 (`/root/mx-llama.cpp-b10254`, `ggml/src/ggml-cuda/mmq-config-gfx906.cuh`) | gfx906-specific tile table for the integer matrix (MMQ) kernels plus a 14-line K-quant patch | prefill +33% at Q8_0 (848 → 1130 tok/s on four dies, 234 → 315 on one), +26% Q6_K, +7% Q4_K_M; decode +4% single-stream |
| build recipe | `GPU_TARGETS=gfx906`, HIP graphs on, `-DGGML_CUDA_FA_ALL_QUANTS=ON` if the 4-bit value cache is wanted (run-through s.8: 8 × 256K fits at q8_0 keys / q4_0 values) | the production build "mxxm+fh" = fork + both patches |

Variants measured and rejected, so nobody re-tries them: rows 1 at any warp count (−20 to −36%), rows 2 / warps 2 (−14 to −17%), rows 8 (register pressure), whole-32-weight-block load per thread (−16 to −32% at batch 8; +5% only at batch 1), LDS-staged shared activations (−16 to −52%), aligned-dword weight load with or without a parity branch (−9 to −17%), `GGML_CUDA_FORCE_CUBLAS` for prefill (tie, retired).

The rule the ten builds agreed on: fewer instructions per dot product wins; anything that adds a barrier or lengthens a dependent chain loses; registers beyond about 64 per thread lose.

## The 2026-09-08 series (NEXT-STEPS S2/S3/S6; `git format-patch 3d13157..HEAD` of the `fusion` worktree, on the production state)

Apply in order on the fork tree after the two MMVQ patches above (that state is commit 3d13157 in `/root/mx-llama.cpp-fusion`). Build = `/opt/llama.cpp-mxxm-fh-nq`; measured in `reports/2026-09-08-next-steps-measurements.md`.

| # | Patch | What | Measured | Switch |
|---|---|---|---|---|
| 0001 | fused RMS_NORM+MUL emits the Q8_1 copy into the q8_1 cache | removes 128 quantize launches | exact; 0% (the fused kernel costs what norm + quantize cost) | `GGML_CUDA_NORM_Q8=0` |
| 0002 | residual ADD inside the fused norm kernel | 129 launches | exact; +1.6% single stream | `GGML_CUDA_ADD_NORM=0` |
| 0003 | delta-net producers (q/k L2 norms, beta sigmoid) folded into the GDN kernel | 144 launches | +1.8% single stream; bit-exact after 0009 | `GGML_CUDA_GDN_PREFUSE=0` (bitmask 1/2/4) |
| 0004 | one-column MMVQ knobs (`GGML_MMVQ_GCN_ROWS1`, `_NWARPS1`, `_Q8_VDR8_1COL`) | — | see 0008 | compile-time |
| 0005 | `GGML_TP_AR_MAX_NE`: explicit size gate for the fork's peer-write allreduce | — | with `=20481`: +14.5% single stream, +19% at 2 streams, 8+ unchanged | env |
| 0006 | add+norm and GDN folds restricted to ≤ 64 rows | fixes −7% prefill of 0003 | — | — |
| 0007 | GDN fold bitmask; `GGML_CUDA_GRAPH_OPT=2` allows multi-stream graph optimisation on split lanes | — | graph optimisation: 0 on both placements | env |
| 0008 | whole-block (vdr 8) load at one column by default | — | +2.8% single stream on the split, +7.1% on one die | compile-time |
| 0009 | q/k L2 fold with the standalone kernel's summation order | bit-exact for S_v 128 on wave64 | checked by `tools/final-config.sh` | — |

Files: `0001-ggml-cuda-fused-RMS_NORM-MUL-ADD-also-emits-the-Q8_1.patch`, `0002-ggml-cuda-compute-the-residual-ADD-inside-the-fused-.patch`, `0003-ggml-cuda-fold-the-gated-delta-net-producers-into-th.patch`, `0004-mmvq-gfx906-batch-1-knobs-rows-warps-per-block-at-on.patch`, `0005-tp-allreduce-GGML_TP_AR_MAX_NE-explicit-size-gate-fo.patch`, `0006-ggml-cuda-restrict-the-add-norm-and-GDN-producer-fus.patch`, `0007-ggml-cuda-GDN-producer-fold-as-a-bitmask-GGML_CUDA_G.patch`, `0008-mmvq-whole-block-vdr-8-load-at-one-column-by-default.patch`, `0009-gated_delta_net-fold-the-q-k-L2-norms-with-the-stand.patch`

## The `gfx906` branch series (2026-09-08 evening; `patches/gfx906-branch/`, `git format-patch 59c8be7fd..gfx906` of https://github.com/exabit-io/llama.cpp)

The same changes as the two MMVQ patches plus 0001–0009 above, re-based onto the merge of upstream master (2026-09-08, 5d806aa25) into the mx-llama.cpp fork state (tag b10912), plus three branch-only commits. Apply in order on that merge commit; the build recipe is `scripts/gfx906/build.sh` in the repository and the installed build is `/opt/llama.cpp-gfx906-master` (validated by `tools/gfx906-master-validate.sh`).

| # | Patch | Corresponds to |
|---|---|---|
| 0001 | MMVQ 16-column width + gfx906 launch knobs and Q8_0 fast path | `mmvq-max-batch-16` + `mmvq-gfx906-knobs-and-q8-fastpath` |
| 0002–0004 | fused norm emits Q8_1; residual add in the fused norm; GDN producer fold | 0001–0003 |
| 0005–0010 | batch-1 knobs; `GGML_TP_AR_MAX_NE`; ≤ 64-row restriction; fold bitmask + `GGML_CUDA_GRAPH_OPT=2`; whole-block load default; exact-order L2 fold | 0004–0009 |
| 0011 | `GFX906.md`, `scripts/gfx906/build.sh`, `scripts/gfx906/env.sh` | branch only |
| 0012 | fold of upstream's `build_gdn_l2_norm` (`rms_norm(eps/n)` + `scale(1/√n)`, the q/k norm form upstream switched to on 2026-09-05) into the GDN kernel (`norm_kind 1`), so the 2026-09-08 fold still applies on current upstream | branch only |
| 0013–0014, 0016 | `docs/gfx906-patches.md`, the inventory of every non-upstream commit, and `scripts/gfx906/patch-inventory.sh` that regenerates it | branch only |
| 0015 | `ggml_cuda_mul_mat_id_needs_sync` tests the MUL_MAT_ID window (8), not the 16-wide dense constant: the 9–16-token f16/bf16 expert case on AMD asserted (`test-backend-ops -o MUL_MAT_ID`, validation 2026-09-08) | branch only (upstream added the predicate after the production lineage) |
