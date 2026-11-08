#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1052/R112: instrument qsa_decode_attn.cu with an env-gated one-shot P/V dump
# (probe binary only -- production never carries this).  Captures the chunk-local
# probabilities sp[h][c] (exactly what the PV loop feeds the dot8 scheme) and the
# raw Q4_0 V blocks + row map for the offline P(int4)xV(int4) error budget.
import io
import os

P = "/home/albus/strata166/pr/k10/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()
orig = s

# ---------- 1. file-scope dump machinery (before attn_chunk_body) ----------
anchor = "__device__ __forceinline__ void attn_chunk_body("
assert s.count(anchor) == 1, s.count(anchor)
_i = s.find(anchor)
_t = s.rfind("\ntemplate <", 0, _i)          # attn_chunk_body is a template: insert before its template header
if _t >= 0 and _i - _t < 300:
    anchor = s[_t + 1:_i]
    assert anchor.startswith("template <"), repr(anchor[:60])
block = r'''// ---- R112 PV-dump probe (W1052): one-shot capture of the chunk-local probabilities
// and the raw Q4_0 V blocks for the offline PV-dot8 error budget.  Probe builds only.
#define PV_DUMP_MAX 32
#define PV_DUMP_CELLS 64
struct PvDumpRec {
    int n_here, slot, chunk, kvh, query_z;
    long long srow[PV_DUMP_CELLS];
    float sp[G][PV_DUMP_CELLS];
    unsigned char vraw[PV_DUMP_CELLS][8][18];
};
__device__ PvDumpRec pv_recs[PV_DUMP_MAX];
__device__ int pv_cnt = 0;
__device__ int pv_on = 0;

static void pv_dump_arm() {
    static bool armed = false;
    if (armed) return;
    armed = true;
    if (std::getenv("STRATA_PV_DUMP") == nullptr) return;
    int one = 1;
    cudaMemcpyToSymbol(pv_on, &one, sizeof(int));
    std::fprintf(stderr, "pv_dump: armed\n");
}
static void pv_dump_sync_flush() {
    static int last_written = 0;
    if (std::getenv("STRATA_PV_DUMP") == nullptr) return;
    int cnt = 0;
    cudaMemcpyFromSymbol(&cnt, pv_cnt, sizeof(int));
    if (cnt <= last_written) return;
    cudaDeviceSynchronize();
    cudaMemcpyFromSymbol(&cnt, pv_cnt, sizeof(int));
    if (cnt > PV_DUMP_MAX) cnt = PV_DUMP_MAX;
    static PvDumpRec host[PV_DUMP_MAX];
    cudaMemcpyFromSymbol(host, pv_recs, sizeof(PvDumpRec) * (size_t) cnt);
    const char* path = std::getenv("STRATA_PV_DUMP");
    std::FILE* f = std::fopen(path, "wb");
    if (!f) { std::fprintf(stderr, "pv_dump: cannot write %s\n", path); last_written = cnt; return; }
    std::fwrite(&cnt, sizeof(int), 1, f);
    std::fwrite(host, sizeof(PvDumpRec), (size_t) cnt, f);
    std::fclose(f);
    std::fprintf(stderr, "pv_dump: wrote %d records to %s\n", cnt, path);
    last_written = cnt;
}

'''
s = s.replace(anchor, block + anchor, 1)

# ---------- 2. device capture before the PV loop ----------
anchor = "    // values: thread t owns dimension t for all 12 heads."
assert s.count(anchor) >= 1, s.count(anchor)   # first hit = attn_chunk_body (pre75 reuses the comment)
capture = r'''    static_assert(CHUNK <= PV_DUMP_CELLS, "pv_dump record is sized for CHUNK<=64");
    if (pv_on && KV_MODE == 3 && t == 0 && n_here >= 32 && blockIdx.y == 0 && blockIdx.z == 0) {
        const int idx = atomicAdd(&pv_cnt, 1);
        if (idx < PV_DUMP_MAX) {
            PvDumpRec& r = pv_recs[idx];
            r.n_here = n_here; r.slot = slot; r.chunk = (int) blockIdx.x;
            r.kvh = (int) blockIdx.y; r.query_z = (int) blockIdx.z;
#pragma unroll
            for (int c = 0; c < PV_DUMP_CELLS; ++c) r.srow[c] = srow[c];
#pragma unroll
            for (int h = 0; h < G; ++h) {
#pragma unroll
                for (int c = 0; c < PV_DUMP_CELLS; ++c) r.sp[h][c] = sp[h][c];
            }
            constexpr int bytes_per_head = (HD / QK4_0) * sizeof(block_q4_0);
            for (int c = 0; c < PV_DUMP_CELLS; ++c) {
                const long long row = srow[c];
                if (row < 0) {
                    for (int b = 0; b < 8; ++b) for (int k = 0; k < 18; ++k) r.vraw[c][b][k] = 0;
                    continue;
                }
                const unsigned char* src = p.v_q4 + row * bytes_per_head;
                for (int b = 0; b < 8; ++b)
                    for (int k = 0; k < 18; ++k) r.vraw[c][b][k] = src[b * 18 + k];
            }
        }
    }
'''
s = s.replace(anchor, capture + anchor, 1)


def insert_after_brace(text, decl, line):
    i = text.find(decl)
    assert i >= 0, decl[:60]
    j = text.find("{", i)
    assert j >= 0
    k = text.find("\n", j) + 1
    return text[:k] + line + text[k:]


# ---------- 3. host hooks ----------
s = insert_after_brace(s, "void launch_chunks_batch(", "    pv_dump_arm();\n")
s = insert_after_brace(s, "void launch_merge(", "    pv_dump_sync_flush();\n")
s = insert_after_brace(s, "void qsa_decode_attn_step(", "    pv_dump_arm();\n")

assert s != orig
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", P, len(orig), "->", len(s))
for k in ("pv_dump_arm", "pv_dump_sync_flush", "pv_recs", "STRATA_PV_DUMP", "atomicAdd(&pv_cnt"):
    print(k, s.count(k))
