# Third-Party Notices

This file aggregates the third-party components vendored under `third_party/`
(and the one idea-borrowed library) so that licence, copyright and pinned
version of each are visible in one place. Every vendored subdirectory also
carries its own `LICENSE` with the full licence text and a `NOTICE.md` with the
provenance detail; this file must stay consistent with those.

Strata itself is MIT License, Copyright (c) 2026 Niko1221 and the Strata
contributors (see `LICENSE` at the repository root).

## Inventory

| Component | Licence | Copyright | Pinned version | Source | Local modifications |
| --- | --- | --- | --- | --- | --- |
| `third_party/ggml` | MIT | 2023-2026 The ggml authors | tree copy `3cf03257` (`VERSION.txt`); build pin is the composite `b12180` = `bcb01528` + `mmq*@4c1004c` (`ci/lcpp_picks/PIN.toml`) | ggml-org/llama.cpp | `ggml-common-tq.h` (trellis codebook tables, project's copy) |
| `third_party/ggml-tq` | MIT | 2023-2026 The ggml authors; Laurent Zuijdwijk | agentionai/llama.cpp `93a24e5` (tq files) + `073bc9e68` (codebook); TQP5-7 from `release/gyro-l` (no sha recorded) | agentionai/llama.cpp `ggml/src/ggml-cuda/tq.cuh` | derived subset (MMQ path only); `tq-mmq-tiles.cuh` loader function unchanged; type routing via build-time overlay |
| `third_party/libstrix` | MIT | asf0 and the libstrix contributors | n/a (idea and wording only) | github.com/asf0/libstrix | `barrier()` idea/wording used in `src/prefill/moe_fused_iq.cu`; no code copied |
| `third_party/antirez-ds4` | MIT | 2026 The ds4.c authors; 2023-2026 The ggml authors; 2023 DeepSeek | commit `890898cf` | github.com/antirez/ds4 | Metal vision-tower kernels derived (BF16 rounding, 2-D rotary, unfold order, polynomial erf); host side and `src/dsv41/ds4_vision.cu` wiring are Strata's own |
| `third_party/project-maya` | MIT | 2026 Peasant Smith and the Project Maya contributors; 2026 Niko1221 and the Strata contributors (per its LICENSE) | release v1.1.17, commit `8d9a9b5d`; selective merges through v1.1.42 (per-PR list in its NOTICE) | github.com/mw00/project-maya | ported into `src/dsv41/` etc.; changes listed in the git history of those directories (first commit of each file = unmodified upstream copy) |
| `third_party/sfnx` | MIT | 2026 John Fink | commit `f9ba1e9` | github.com/johnfink8/sfnx | engine under `src/split/` ported in; changes listed in the git history of `src/split` (first commit of each file = unmodified upstream copy) |

## Component notices

### ggml (`third_party/ggml/`)

The ggml inference library (MIT). `VERSION.txt` records the tree copy's
commit; the reproducible build pin lives in `ci/lcpp_picks/PIN.toml` and is a
composite (base commit + `mmq*` files from a second commit) — see
`ci/lcpp_picks/recipe_k10.sh` for the rebuild recipe. Full text: `LICENSE`.

### ggml-tq (`third_party/ggml-tq/`)

The trellis expert types (TQ2_T, TQK6, TQK7) for the MMQ tile loader, derived
from agentionai/llama.cpp's ggml-cuda trellis implementation (Laurent
Zuijdwijk), MIT. Only what the MMQ path needs is kept. Full text: `LICENSE`;
provenance detail: `NOTICE.md`.

### libstrix (`third_party/libstrix/`)

The workgroup barrier with explicit LDS wait in `src/prefill/moe_fused_iq.cu`
takes the idea and the wording of `barrier()` from libstrix by asf0 (MIT).
No code is vendored; the notice accompanies the code that uses the idea.
Full text: `LICENSE`; provenance detail: `NOTICE.md`.

### antirez-ds4 (`third_party/antirez-ds4/`)

The Metal form of the DeepSeek-V4.1 vision tower follows antirez/ds4 (MIT,
commit `890898cf`). Derived files are listed in its `NOTICE.md`; the tiled
BF16 GEMM, the rest of the host side and the wiring into
`src/dsv41/ds4_vision.cu` are Strata's own. Full text: `LICENSE`.

### Project Maya (`third_party/project-maya/`)

The DeepSeek-V4.1 engine files under `src/dsv41/`, `include/strata/dsv41/`,
`tests/dsv41/` and `tools/dsv41/` come from mw00/project-maya (itself built on
Strata), MIT, release v1.1.17 (commit `8d9a9b5d`) plus selective merges
through v1.1.42 (per-PR list in its NOTICE) covered by the same notice. Full
text: `LICENSE`; provenance detail: `NOTICE.md`.

### sFNX (`third_party/sfnx/`)

The split-every-layer engine for Qwen3.8-Flash-Next under `src/split/` comes
from johnfink8/sfnx (MIT, commit `f9ba1e9`). Full text: `LICENSE`; provenance
detail: `NOTICE.md`.

### Scope notes

- This inventory covers the six component directories under `third_party/`.
  A second ggml copy exists at `sycl/third_party/ggml/` (same MIT / ggml
  authors licence and header) and is covered by the ggml entry above.
- Model weights under `data/` carry their own notices (e.g.
  `data/dflash2-tuned/NOTICE.md`, Apache-2.0, Inco AI,
  HuggingFace incoai/Qwen3.8-Flash-Next-DFlash2) and are outside this
  inventory's scope.
- The `third_party/<name>/` directories of antirez-ds4, project-maya, sfnx and
  libstrix are attribution directories (licence + notice only); the derived
  code lives in `metal/`, `src/dsv41/`, `src/split/` and `src/prefill/`
  respectively. Only `ggml` (two header copies) and `ggml-tq` (two `.cuh`
  files) carry code inside `third_party/`.
- libstrix has no pinned commit (it is borrowed as idea/wording only); the gap
  is recorded here rather than papered over.

---

Compliance basis: each vendored subdirectory carries the full licence text in
its own `LICENSE` (not a name or a link), per the Google open-source
third-party requirement. This inventory was assembled in W1080 (B2); if a
component is added, moved or its pin changes, update this file in the same
commit.
