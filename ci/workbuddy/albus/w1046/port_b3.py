"""W1046: add an opt-in DP4A HC down kernel; production branch is restored by caller.
Run on 166. Only src/kernels/cuda/fused_gr.cu is changed.
"""
import pathlib
import shutil
import subprocess

R = pathlib.Path("/home/albus/strata166/pr/k10")
F = R / "src/kernels/cuda/fused_gr.cu"
BASE = "gfx906/attn-opt"
BR = "gfx906/hc-dp4a"


def git(*args):
    return subprocess.run(["git", "-C", str(R)] + list(args), check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


if git("status", "--porcelain"):
    raise SystemExit("tree not clean; refusing")
branches = git("branch", "--list", BR)
if branches:
    git("checkout", BR)
    git("checkout", BASE, "--", "src/kernels/cuda/fused_gr.cu")
else:
    if git("rev-parse", "--abbrev-ref", "HEAD") != "gfx906/lcpp-k10":
        raise SystemExit("production tree is not on gfx906/lcpp-k10; refusing")
    git("checkout", "-b", BR, BASE)
backup = pathlib.Path("/home/albus/strata166/tmp/w1046/fused_gr.cu.before_w1046")
shutil.copyfile(F, backup)
s = F.read_text(encoding="utf-8")

inc = '#include "strata/kernels/q8_1_finite.hpp"   // #606: q8_1_ds\n'
assert s.count(inc) == 1
s = s.replace(inc, inc + '#include "strata/kernels/dp4a.hpp"   // W1046: opt-in HC down DP4A candidate\n', 1)

start = s.index("template <int T>\n__global__ void __launch_bounds__(THREADS) gr_down_q8_kernel(")
end = s.index("template <int T>\n__global__ void __launch_bounds__(THREADS) gr_up_q8_kernel(", start)
orig = s[start:end]
new = orig.replace("gr_down_q8_kernel", "gr_down_q8_dp4a_kernel", 1)

old_decl = "    __shared__ __align__(16) float xs[T][Q8_KC];\n    __shared__ float red[WARPS][T];"
new_decl = ("    __shared__ __align__(16) float xs[T][Q8_KC];   // retained for the BF16 inject rows\n"
            "    __shared__ __align__(16) uint32_t xq[T][Q8_KC / 4];   // four signed int8 activations\n"
            "    __shared__ float xd[T][Q8_KC / 32];               // one fp32 scale per 32 activations\n"
            "    __shared__ float red[WARPS][T];")
assert new.count(old_decl) == 1
new = new.replace(old_decl, new_decl, 1)

old_store = "            *reinterpret_cast<float4*>(&xs[k][4 * i]) = make_float4(r.x * g.x, r.y * g.y, r.z * g.z, r.w * g.w);"
new_store = old_store + """
            // W1046: quantize once while staging. Eight consecutive lanes own one 32-value
            // group, so xor 4/2/1 never crosses a group boundary. The same qx/xd are reused
            // by all four down rows; no per-use FP32->INT8 conversion in the dot loop.
            {
                const float4 x = make_float4(r.x * g.x, r.y * g.y, r.z * g.z, r.w * g.w);
                float amax = fmaxf(fmaxf(fabsf(x.x), fabsf(x.y)), fmaxf(fabsf(x.z), fabsf(x.w)));
#pragma unroll
                for (int o = 4; o > 0; o >>= 1)
                    amax = fmaxf(amax, __shfl_xor_sync(0xffffffffu, amax, o));
                const float d = q8_1_finite(q81_div(amax, 127.0f));
                const uint32_t q0 = (uint8_t) q8_1_quant(x.x, d, amax);
                const uint32_t q1 = (uint8_t) q8_1_quant(x.y, d, amax);
                const uint32_t q2 = (uint8_t) q8_1_quant(x.z, d, amax);
                const uint32_t q3 = (uint8_t) q8_1_quant(x.w, d, amax);
                xq[k][i] = q0 | (q1 << 8) | (q2 << 16) | (q3 << 24);
                if ((i & 7) == 0) xd[k][i >> 3] = d;
            }"""
assert new.count(old_store) == 1
new = new.replace(old_store, new_store, 1)

old_dot = """            float4 w;
            if (inj_bf16) {
                const uint2 b = *reinterpret_cast<const uint2*>(m.a[0].w_inject + (size_t) row0 * D + (size_t) kc * Q8_KC + v);
                w = make_float4(__uint_as_float(b.x << 16), __uint_as_float(b.x & 0xffff0000u),
                                __uint_as_float(b.y << 16), __uint_as_float(b.y & 0xffff0000u));
            } else {
                w = q8_four(q[r][s], dq[r][s]);
            }
#pragma unroll
            for (int k = 0; k < T; ++k) {
                const float4 x = *reinterpret_cast<const float4*>(&xs[k][v]);
                acc[k] = fmaf(w.x, x.x, acc[k]); acc[k] = fmaf(w.y, x.y, acc[k]);
                acc[k] = fmaf(w.z, x.z, acc[k]); acc[k] = fmaf(w.w, x.w, acc[k]);
            }"""
new_dot = """            float4 w;
            if (inj_bf16) {
                const uint2 b = *reinterpret_cast<const uint2*>(m.a[0].w_inject + (size_t) row0 * D + (size_t) kc * Q8_KC + v);
                w = make_float4(__uint_as_float(b.x << 16), __uint_as_float(b.x & 0xffff0000u),
                                __uint_as_float(b.y << 16), __uint_as_float(b.y & 0xffff0000u));
            }
#pragma unroll
            for (int k = 0; k < T; ++k) {
                if (inj_bf16) {
                    const float4 x = *reinterpret_cast<const float4*>(&xs[k][v]);
                    acc[k] = fmaf(w.x, x.x, acc[k]); acc[k] = fmaf(w.y, x.y, acc[k]);
                    acc[k] = fmaf(w.z, x.z, acc[k]); acc[k] = fmaf(w.w, x.w, acc[k]);
                } else {
                    const int block = 4 * s + bl;
                    const int sumi = STRATA_DP4A((int) q[r][s], (int) xq[k][v / 4], 0);
                    acc[k] = fmaf(dq[r][s] * xd[k][block], (float) sumi, acc[k]);
                }
            }"""
assert new.count(old_dot) == 1
new = new.replace(old_dot, new_dot, 1)

banner = """// W1046 / R103-B3: opt-in symmetric INT8 activation x INT8 weight DP4A down projection.
// The original gr_down_q8_kernel remains byte-for-byte the off arm. The candidate changes
// arithmetic (not bit-identical): Q8_0 weight scale x per-32 activation scale is applied after
// the integer dot. No zero-point is needed because both operands are symmetric signed INT8.
// Inject rows keep the original BF16 x FP32 path. Gate: build floor, gr_parity/fused_gr_bench,
// prompt logits + anchored KL/top-1, task grid, then paired production A/B. Default OFF.
"""
s = s[:start] + orig + banner + new + s[end:]

old_launch = """    static const bool ts = [] { const char* v = std::getenv("STRATA_TSUM"); return v && v[0] == '1'; }();
    if (stamp_buf) gpu_stamp(stamp_buf, stamp_i0, (void*) st);"""
new_launch = """    static const bool ts = [] { const char* v = std::getenv("STRATA_TSUM"); return v && v[0] == '1'; }();
    static const bool dp4a = [] {
        const char* v = std::getenv("STRATA_HC_DOWN_DP4A");
        return v != nullptr && std::atoi(v) != 0;
    }();
    if (stamp_buf) gpu_stamp(stamp_buf, stamp_i0, (void*) st);"""
assert s.count(old_launch) == 1
s = s.replace(old_launch, new_launch, 1)
old_disp = "    if (ts && pfs) gr_down_q8_fast_kernel<T, 4, true><<<dim3(LR / (WARPS * 4) + 1, Q8_NKC), THREADS, 0, st>>>(m, part, ssg);"
new_disp = ("    if (dp4a) gr_down_q8_dp4a_kernel<T><<<dim3(Q8_RG + 1, Q8_NKC), THREADS, 0, st>>>(m, part, ssg);\n"
            "    else " + old_disp.strip())
assert s.count(old_disp) == 1
s = s.replace(old_disp, new_disp, 1)

F.write_text(s, encoding="utf-8", newline="\n")
git("add", "src/kernels/cuda/fused_gr.cu")
git("commit", "-m", "gfx906: add opt-in DP4A HC down candidate (W1046)")
print("branch", BR, "commit", git("rev-parse", "--short", "HEAD"))
print(git("diff", "--stat", BASE + ".." + BR))
