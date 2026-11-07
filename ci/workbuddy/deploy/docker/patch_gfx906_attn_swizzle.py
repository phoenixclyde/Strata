# -*- coding: utf-8 -*-
"""W794：让 gfx906 的 INT8 batch 注意力布局置换（query swizzle / reduce12）也接受 KV_MODE 3（k8v4）。

上游 #1661（closed，作者实测）：`STRATA_GFX906_ATTN_QUERY_SWIZZLE=1` 在 **int8 K+V（mode 1）** 上
内核组件吞吐 +14.65%、全模型提示 +1.19%，**输出逐位一致**。
我们的生产是 `--kv k8v4`（int8 K + q4_0 V = KV_MODE 3），而 `qsa_decode_attn.cu:969` 的判定逐字要求

    ... && kv_mode == 1 && query_swizzle_gfx906_device();

所以这条 gfx906 专用优化在我们配置下**永远关着**。本补丁只放宽策略判定并为 mode 3 补实例化；
置换本身是 q 在 LDS 里的双射 XOR（`sd = d ^ ((d >> 3) & 4)`）+ 读侧 `qflip = lane & 4` 还原，
与 KV_MODE 无关，因此**算术不变、逐位一致**（A/B 用输出 token 全等来验证）。
"""
import io
import sys

OLD_GUARD = ("    const bool use_query_swizzle = kernel < 0 && query_swizzle && !lane_cell && kv_mode == 1 &&\n"
             "                                   query_swizzle_gfx906_device();\n")
NEW_GUARD = ("    // W794: the permutation is a q-side LDS bijection, independent of the KV format, so KV_MODE 3\n"
             "    // (k8v4: int8 K + q4_0 V) takes it too (upstream #1661 measured it on int8 only).\n"
             "    const bool use_query_swizzle = kernel < 0 && query_swizzle && !lane_cell &&\n"
             "                                   (kv_mode == 1 || kv_mode == 3) && query_swizzle_gfx906_device();\n")

OLD_R12 = """        if (reduce12) {
            attn_chunk_kernel<1, false, true, true><<<grid, THREADS, 0, st>>>(q, pools, ids, steps,
                (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l, n_chunks, (int) cap, stride);
"""
NEW_R12 = """        if (reduce12) {
            if (kv_mode == 3)
                attn_chunk_kernel<3, false, true, true><<<grid, THREADS, 0, st>>>(q, pools, ids, steps,
                    (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l, n_chunks, (int) cap, stride);
            else
            attn_chunk_kernel<1, false, true, true><<<grid, THREADS, 0, st>>>(q, pools, ids, steps,
                (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l, n_chunks, (int) cap, stride);
"""

OLD_SW = """        } else {
            attn_chunk_kernel<1, false, true><<<grid, THREADS, 0, st>>>(q, pools, ids, steps,
                (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l, n_chunks, (int) cap, stride);
        }
"""
NEW_SW = """        } else {
            if (kv_mode == 3)
                attn_chunk_kernel<3, false, true><<<grid, THREADS, 0, st>>>(q, pools, ids, steps,
                    (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l, n_chunks, (int) cap, stride);
            else
            attn_chunk_kernel<1, false, true><<<grid, THREADS, 0, st>>>(q, pools, ids, steps,
                (int) s.n_head_kv, (int) s.page_size, scale, part_acc, part_m, part_l, n_chunks, (int) cap, stride);
        }
"""


def main(path):
    t = io.open(path, encoding="utf-8").read()
    if "W794" in t:
        print("already patched")
        return 0
    for name, old, new in (("guard", OLD_GUARD, NEW_GUARD), ("reduce12", OLD_R12, NEW_R12), ("swizzle", OLD_SW, NEW_SW)):
        n = t.count(old)
        assert n == 1, "%s anchor count=%d" % (name, n)
        t = t.replace(old, new, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(t)
    print("patched", path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
