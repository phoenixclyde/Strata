set +e
cd /home/albus/strata166/gfx906 || exit 1
python3 - <<'PY'
import io, sys
p = "src/kernels/cuda/qsa_select.cu"
s = io.open(p, encoding="utf-8").read()
orig = s

OLD = """    static const bool simt_on = [] {
        const char* v = std::getenv("STRATA_SELECT_SIMT");
        return v != nullptr && v[0] == '1';
    }();
"""
NEW = """    // W842 local (ports upstream #3073): the HIP branch used to read only '1', so STRATA_SELECT_SIMT=2
    // silently kept the warp kernel.  Now 0/1/2, and 2 takes block_scores_simt2_kernel (same bits as 1).
    static const int simt_level = [] {
        const char* v = std::getenv("STRATA_SELECT_SIMT");
        return v == nullptr ? 0 : v[0] == '1' ? 1 : v[0] == '2' ? 2 : 0;
    }();
    const bool simt_on = simt_level != 0;
"""
assert s.count(OLD) == 1, "anchor A count=%d" % s.count(OLD)
s = s.replace(OLD, NEW, 1)

ANCHOR2 = """        const bool rdna2 = sel_gfx103_device();
"""
INS = """        const bool rdna2 = sel_gfx103_device();
        if (simt_level >= 2) {
            static std::atomic<bool> said2{false};
            if (!said2.exchange(true))
                std::fprintf(stderr, "qsa select: FP32 tiled scorer (STRATA_SELECT_SIMT=2), tiles 32/128\\n");
            const dim3 grid2((unsigned) ((reach + 127) / 128), (unsigned) ((nq + 31) / 32));
            if (grid2.y > 65535) return false;
            block_scores_simt2_kernel<32, 128><<<grid2, 256, 0, (cudaStream_t) stream>>>(pooled, q_idx, steps, nq,
                                                                                        max_blocks, reach, scores);
            block_scores_tail_kernel<<<(unsigned) nq, 32, 0, (cudaStream_t) stream>>>(dead, q_idx, steps, max_blocks,
                                                                                      scores);
            const cudaError_t e2 = cudaGetLastError();
            if (e2 != cudaSuccess) {
                std::fprintf(stderr, "qsa_block_scores (simt2): %s\\n", cudaGetErrorString(e2));
                std::exit(1);
            }
            return true;
        }
"""
assert s.count(ANCHOR2) == 1, "anchor B count=%d" % s.count(ANCHOR2)
s = s.replace(ANCHOR2, INS, 1)

if s == orig:
    print("NO CHANGE"); sys.exit(1)
io.open(p, "w", encoding="utf-8").write(s)
print("patched: simt_level + simt2 dispatch inserted")
PY
echo "--- 验证锚点与改动 ---"
grep -n "W842 local\|simt_level\|simt2_kernel<32, 128>" src/kernels/cuda/qsa_select.cu | head
echo "--- 逐行 diff ---"
git diff --stat && git diff -- src/kernels/cuda/qsa_select.cu | head -60
