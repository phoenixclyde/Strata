import io

# ---------- commit pa5 ----------
CMDS = """
cd /home/albus/strata166/pr/port-all || exit 1
git add src/kernels/cuda/qsa_decode_attn.cu
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'MSG'
gfx906: quantize the dp4a query with one warp per 64-value group (W1041)

The OPT&2 path quantized the query with 48 of the 256 threads, each running a
serial 64-element amax scan and 64 converts (~448 instructions) while the other
208 waited at __syncthreads -- in every one of the 64 blocks of a query.  That
made the dp4a score net slower (+6.8% attn, P447/P449).

One warp per group instead: 48 groups over 8 warps, 2 values per lane, amax by a
butterfly.  max is order-independent, so d and every code are bit-identical to
the scan; only the scheduling changes.  Pattern taken from llama.cpp's
quantize_q8_1 (one warp per block, each lane its own element).

Measured (W1041, ctl vs this + ATTN_DP4A): attn 2234 -> 1982 ms at 8K (-11.3%),
4714 -> 4212 ms at 16K (-10.7%), whole prefill -1.78% / -1.61% (2xCV 0.50/0.11).
MSG
git log --oneline -1
"""
R = "deploy/PROGRESS.tsv"
ROWS = [
    dict(block="B6判定探针", id="P451",
         item=("救回来了：查询量化改成 **warp-per-group**（48 组 ÷ 8 warp、每 lane 2 个值、5 次 butterfly）后，"
               "DP4A 从 +6.8% 变成 **attn −10.6~−11.3%**、整条 prefill 8K **−1.78%** / 16K **−1.61%**"),
         source="W1039", kind="count", count="1", done="1", status="OPEN",
         note=("**W1039 第三窗口（机主 09:52「救吧」；重启 2 次、停机 90 s；config 已还原 `5e9b81e2…`）**。"
               "pa5 = `c639b60c5981267c8d82ee3a4b0750e8` / 43,475,584 B（port-all @ pa5 提交）。"
               "改法只动一处：`if constexpr (OPT & 2)` 里的量化从「48 个线程各串行 64 元素两遍」改成 "
               "`for (grp = warp; grp < G*NSC; grp += WARPS)` —— 48 组按 warp 轮转（每 warp 6 组），每 lane 2 个值，"
               "`__shfl_xor` 5 级求 amax，再各转自己那 2 个值。形状抄 llama.cpp `quantize_q8_1`（一个 warp 一个块、每 lane 自己那一个元素）。"
               "**实测（ctl b12180 vs pa5+ATTN_DP4A，同一窗口、每臂 2 轮、2.5K/8K/16K 各 n=4）**："
               "`qsa attn` 575→**510**（−11.22%）/ 2234→**1982**（−11.29%）/ 4714→**4212**（−10.65%）；"
               "整条 prefill 1584.4→1573.9（−0.66%，2×CV 5.07% 不显著）/ 1253.6→**1231.2**（−1.78%，2×CV 0.50%）/ "
               "1278.7→**1258.1**（−1.61%，2×CV 0.11%）；decode 59.00→61.45 tok/s（CV 8–10%，不可分）。"
               "**状态 OPEN 而不是 DONE**：`deploy_gate` D4 要数值面（KL ≤0.0139 / top-1 ≥99% 或逐位相同），本轮只测了速度，"
               "数值门未开 ⇒ 还不能装机。"),
         ref="P447;P449", kw="KW:warp-per-group|转正"),
    dict(block="B6判定探针", id="P452",
         item=("量化段从 ~448 条指令降到每组 ~14 条（48 组 ÷ 8 warp = 6 组/warp × (2 载入 + 5 shfl + 2 div+cvt)），"
               "且**位相同**：max 与运算顺序无关，d 与每个码都不变"),
         source="W1039", kind="count", count="1", done="1", status="DONE",
         note=("**W1039 预算复核**。旧：48/256 线程、每线程 64 次 amax + 64 次 `div/cvt` ≈ **448 条**，其余 208 线程等 `__syncthreads`；"
               "新：每 warp 6 组、每组 2 载入 + 5 次 `__shfl_xor`+`fmaxf` + 1 次除 + 2 次 `div/cvt`+存储 ≈ **14 条/组** ⇒ "
               "每线程 ≈84 条，且 **256/256 线程都在干活**（旧的是 48/256）。"
               "**位相同的论证**：`amax = max(|x|)` 对同一集合与顺序无关（fmaxf 结合律/交换律成立，且 NaN 不出现），"
               "`d = amax/127` 与 `round(x/d)` 逐元素同一表达式 ⇒ 码字逐字节相同。所以这次的 −11% 是**纯调度收益**，"
               "不掺任何数值变化——这也是为什么它可以先测速度、后补数值门而不担心两条轴混在一起。"
               "**为什么 8K/16K 显著而 2.5K 不显著**：2.5K 只跑 2 个 chunk 的前半段（3425 tok 里 2048 选择预算未用满），"
               "量化摊到更少的 cell 上、且该点 CV 本来就有 5%；8K/16K 的 CV 是 0.22%/0.08%，−1.6~−1.8% 站得住。"),
         ref="P449;P451", kw="KW:位相同|448"),
]
s = io.open(R, encoding="utf-8").read()
add = []
for r in ROWS:
    if ("\t" + r["id"] + "\t") in s:
        print("skip", r["id"]); continue
    add.append("\t".join([r["block"], r["id"], r["item"], r["source"], r["kind"], r["count"], r["done"],
                          r["status"], r["note"], r["ref"], r["kw"]]))
if add:
    if not s.endswith("\n"):
        s += "\n"
    s += "\n".join(add) + "\n"
    io.open(R, "w", encoding="utf-8", newline="\n").write(s)
    print("ledger +", [a.split("\t")[1] for a in add])

# ---------- recipe ----------
RP = "deploy/REBUILD_RECIPE.tsv"
t = io.open(RP, encoding="utf-8").read()
if "strata-0.1.57-pa5\t" not in t:
    if not t.endswith("\n"):
        t += "\n"
    t += "\t".join(["strata-0.1.57-pa5", "c639b60c5981267c8d82ee3a4b0750e8", "43475584",
                    "gfx906/port-all @ pa5 提交", "b12180 / bcb0152876e8f0b684ba70d3defcab6cdf35adb5",
                    "4c1004c49221b07c3b8108977e3d1991fc9f45cc", "build-pa3（/src=pr/port-all，/llama.cpp=llama-master）",
                    "W1039 候选：dp4a 量化改 warp-per-group，attn −10.6~−11.3%；**数值门未开，未装机**，见 P451"]) + "\n"
    io.open(RP, "w", encoding="utf-8", newline="\n").write(t)
    print("recipe row +1")
