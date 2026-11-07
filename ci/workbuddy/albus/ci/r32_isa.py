# -*- coding: utf-8 -*-
"""[W863 R32] Instruction mix of the real HC kernels, from the shipped device assembly.

The read probe says the same bytes run at ~650-800 GB/s as a pure read and at ~100-300 GB/s once
dequant + FMA are added. So the cost is per-byte arithmetic, not the load. This counts what the
compiler actually emitted, per kernel, and converts it into instructions per 34-byte Q8 block.
"""
import re, collections

S = "/home/albus/strata166/ci/state/vgpr/fused_gr.s"
lines = open(S, errors="replace").read().splitlines()

# split the file into functions: a label line "<name>:" .. ".Lfunc_end<n>:"
funcs, cur, name = {}, [], None
for l in lines:
    # clang emits:  <mangled>: ; @<mangled>
    if l and not l[0].isspace() and ": ; @" in l and not l.startswith("."):
        name, cur = l.split(": ; @")[0], []
    elif name:
        cur.append(l)
        if l.startswith(".Lfunc_end"):
            funcs[name] = cur
            name, cur = None, []
if name:
    funcs[name] = cur

TARGETS = [n for n in funcs if re.search(r"gr_(down|up)_q8_(fast_)?kernel", n)]

def stats(body):
    ops = collections.Counter()
    for l in body:
        s = l.strip()
        if not s or s.startswith(";") or s.startswith(".") or s.startswith("//"):
            continue
        m = re.match(r"([a-z0-9_]+)", s)
        if m:
            ops[m.group(1)] += 1
    return ops

print("%-42s %6s %6s %6s %6s %6s %6s" %
      ("kernel", "total", "cvt", "fma", "load", "alu%", "per34B"))
print("-" * 84)
rows = []
for n in sorted(TARGETS, key=lambda x: (("down" in x), x)):
    ops = stats(funcs[n])
    tot = sum(ops.values())
    cvt = sum(v for k, v in ops.items() if "cvt" in k)
    fma = sum(v for k, v in ops.items() if "fma" in k or "mac" in k)
    ld = sum(v for k, v in ops.items() if "load" in k or "buffer_load" in k)
    alu = sum(v for k, v in ops.items()
              if any(t in k for t in ("v_add", "v_mul", "v_sub", "v_and", "v_or", "v_lshl",
                                      "v_lshr", "v_ashr", "v_cmp", "v_cndmask", "v_mov",
                                      "v_bcnt", "v_perm", "v_alignbit")))
    short = re.sub(r"_ZN6strata7kernels12_GLOBAL__N_1", "", n)
    short = re.sub(r"^(\d+)", "", short)[:42]
    # per 34-byte block: a kernel iterates over Q8 blocks; the load count is a proxy for how many
    # blocks one pass covers, so report ALU instructions per 34 B of weights moved.
    per34 = (cvt + fma + alu) / max(1, ld) * (34.0 / 32.0)
    rows.append((short, tot, cvt, fma, ld, 100.0 * (cvt + fma + alu) / max(1, tot), per34))

for r in rows[:14]:
    print("%-42s %6d %6d %6d %6d %5.0f%% %6.1f" % r)

print()
print("读法：")
print("  * cvt = int8→float 的转换；fma = 乘加；load = 全局/缓冲读指令")
print("  * per34B = 每搬 34 字节（一个 Q8_0 块）要发多少条算术指令")
print("  * 这个数就是「每字节的工作量」，它决定了算术能不能跟上带宽")
tot_cvt = sum(r[2] for r in rows)
tot_fma = sum(r[3] for r in rows)
print("  合计：cvt %d，fma %d  （同一段代码被 T=1..8 各实例化一次）" % (tot_cvt, tot_fma))
