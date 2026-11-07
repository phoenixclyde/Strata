#!/usr/bin/env python3
"""S1 of R99: port the pointer-table MMQ to #31047's tile_spec.

#31047 replaced `mmq_args.expert_bounds` (per-expert column ranges) with
`tile_spec` (one 16-byte record per tile, precomputed by mmid.cu).  We have no `ids`
for the helper to walk, only the bounds our pointer-table path already builds, so the
same table is built here -- single-threaded and in expert order, because upstream's
per-expert blocks write overlapping seam slots and GPU block order is not defined.

Also required by the new layout: `nchannels_y` becomes 1 (the grid's z dimension), the
expert index now travels inside tile_spec.  Upstream does exactly this (mmq.cu:384).
"""
import io

HPP = "/home/albus/strata166/pr/strata-fork/include/strata/prefill/moe_mmq.hpp"
CU = "/home/albus/strata166/pr/strata-fork/src/prefill/moe_mmq.cu"


def patch(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:70])
        s = s.replace(a, b, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", path.split("/")[-1])


patch(HPP, [
    ("""private:
    void* ctx_ = nullptr;""",
     """private:
    void* ctx_ = nullptr;
    void* spec_ = nullptr;      // tile_spec for ggml-cuda with #31047 (device memory, grown on demand)
    size_t spec_cap_ = 0;"""),
])

KERNEL = """namespace {
// #31047: one record per tile (expert, column range).  Single thread on purpose: upstream writes
// the seam slots from one block per expert and lets the later expert win, which is a race on any
// GPU.  With <=16 experts and a few hundred tiles this costs microseconds and is deterministic.
__global__ void build_tile_spec(const int32_t* __restrict__ bounds, int n_experts, int n_slots, int J,
                                ggml_cuda_mm_id_tile_spec* __restrict__ spec) {
    if (blockIdx.x || threadIdx.x) return;
    for (int z = 0; z < n_experts; ++z) {
        const int lo = bounds[z], hi = bounds[z + 1];
        if (lo >= hi) { spec[n_slots + z] = {z, lo, lo, 0}; continue; }
        int col_low  = lo;
        int col_high = min(col_low + J, hi);
        while (col_high > ((col_low + J - 1) / J) * J) {
            spec[(col_low + J - 1) / J] = {z, col_low, col_high, 0};
            col_low  = col_high;
            col_high = min(col_high + J, hi);
        }
        spec[n_slots + z] = {z, col_low, col_high, 0};
    }
}
}  // namespace

"""

patch(CU, [
    ("Context::~Context() { delete (ggml_backend_cuda_context*) ctx_; }",
     "Context::~Context() {\n    if (spec_) cudaFree(spec_);\n    delete (ggml_backend_cuda_context*) ctx_;\n}"),

    ("void Context::run(const Product& p, void* stream) {", KERNEL + "void Context::run(const Product& p, void* stream) {"),

    ("""    const int  J_best = pick_J((int) t, p.max_rows, mmq_fb);
    const mmq_args a = {(const char*) p.w, t, (const int*) p.xq, p.ids, p.bounds, p.dst, p.y_scale,
                        p.w_cols, p.w_rows, p.total_rows, bpr, p.total_rows, p.ld_dst,
                        p.n, p.n, p.tab ? 0 : (int64_t) (p.expert_bytes / type_bytes((int) t)), 0, 0,
                        1, 1, 0, 0, 0,
                        (int) p.max_rows, (int) J_best};""",
     """    const int  J_best = pick_J((int) t, p.max_rows, mmq_fb);
    // #31047: expert->column mapping moved from `expert_bounds` into a per-tile table.
    const int    n_slots    = (int) ((p.total_rows + J_best - 1) / J_best);
    const int    ntj        = n_slots + p.n;
    const size_t spec_bytes = (size_t) ntj * sizeof(ggml_cuda_mm_id_tile_spec);
    if (spec_cap_ < spec_bytes) {
        if (spec_) cudaFree(spec_);
        if (cudaMalloc(&spec_, spec_bytes) != cudaSuccess) {
            std::fprintf(stderr, "prefill mmq: tile_spec alloc failed (%zu bytes)\\n", spec_bytes);
            std::exit(1);
        }
        spec_cap_ = spec_bytes;
    }
    build_tile_spec<<<1, 1, 0, (cudaStream_t) stream>>>(p.bounds, p.n, n_slots, J_best,
                                                        (ggml_cuda_mm_id_tile_spec*) spec_);
    // nchannels_y = 1: the new grid takes z from tile_spec, not from the channel index (mmq.cu:384).
    const mmq_args a = {(const char*) p.w, t, (const int*) p.xq, p.ids,
                        (const ggml_cuda_mm_id_tile_spec*) spec_, p.dst, p.y_scale,
                        p.w_cols, p.w_rows, p.total_rows, bpr, p.total_rows, p.ld_dst,
                        p.n, 1, p.tab ? 0 : (int64_t) (p.expert_bytes / type_bytes((int) t)), 0, 0,
                        1, 1, 0, 0, 0,
                        ntj, (int) J_best};"""),
])
print("ok")
