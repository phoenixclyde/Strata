# ggml-tq, the trellis expert types (TQ2_T, TQK6, TQK7)

The two files here (`tq.cuh`, `tq-mmq-tiles.cuh`) are derived from the trellis
quantisation implementation in agentionai/llama.cpp
(`ggml/src/ggml-cuda/tq.cuh`, `mmq-load-tiles.cuh`), MIT License, by the ggml
authors and Laurent Zuijdwijk. Only what Strata's MMQ path needs is kept (no
mat-vec kernels); `tq-mmq-tiles.cuh` carries the upstream loader function
unchanged. The files read Strata's copies of the codebook tables
(`third_party/ggml/ggml-common-tq.h`, `src/kernels/cuda/tq_lut_i8.cuh`).

The MIT licence text is in `LICENSE` beside this file. This notice stays with
every copy.

Copyright (c) 2023-2026 The ggml authors; (c) Laurent Zuijdwijk.

Upstream: agentionai/llama.cpp (fork of ggml-org/llama.cpp); the quantisation
types themselves originate in the ggml trellis work. Retrieved via the pinned
llama.cpp tree (see `ci/lcpp_picks/PIN.toml` for the pin in force).
