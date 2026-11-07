import io, shutil, time, subprocess, sys, json

REG = "deploy/params/PARAM_REGISTER.tsv"

ARM = ("【W797 实测 2026-10-25 18:58-19:22，p4 镜像，M 21,827 / L 99,387 tokens，TIMING=1，"
       "五臂同会话交错 A B C D E、每臂 restart、丢前 2 请求】")
COST = ("完整 21 相位对账闭合（相位差之和 vs GPU 实差：M -854/-853、L -4378/-4377、B -273/-273/-2386/-2384、"
        "D -177/-177、E +312/+313）=> 规则 P 两条同时满足。")

rows = [
 dict(id="P115", scope="ENV", name="STRATA_GDN_HEAD", value="1", family="prefill", status="ADOPTED",
      requires="-", conflicts="STRATA_GDN_REC_HEADS", synergizes="P116",
      evidence=(ARM + " 臂 B（只加它）：`gdn recurrence` **M 2,416->1,729（-28.4%）、L 11,042->7,883（-28.6%）**，"
                "总量 **M -0.84% / L -1.56%**；`gdn` +0.05%、`gemm gate/up` -0.06%、`gemm down` +0.09%、"
                "`qsa attn` +0.02~1.1%、`dequant` +0.4% 全在门槛内。needle 32k@50% FOUND。" + COST +
                " 单测 `gfx906_gdn_rec_head` 在 gfx906 上编好跑过：variant 1 对 variant 0，全部 7 个 T（7/8/9/17/100/2048/2051）"
                "**y16 与 state 逐位相等（d16=0, dsn=0），FAILURES: 0**；T=2048 上 4.562 vs 7.651 ms = **1.68x**。"),
      verdict=("**采纳**。这是「gfx906 从不继承 `arch_default_env`」的第一个实证：`src/core/arch_defaults.cpp` 只对 "
               "gfx12 / gfx1151 返回表，gfx906 拿到空表 => 上游 20 个 S23/S25/S26 开关在这张卡上默认全关、从未被测过。"
               "上游注释逐字「the arch defaults set STRATA_GDN_HEAD=1 on gfx1151 and **leave other cards on the earlier kernels**」"
               "—— 不是遗漏，是只验证过 wave32。但 parity 单测证明它在 wave64 上逐位等价。"
               "残余：`qsa proj` 在 M 档 +15.2%（+252 ms）与 `router+shared` +19.9% 是相位间迁移，已在总量里抵掉。")),

 dict(id="P116", scope="ENV", name="STRATA_GDN_PP", value="2", family="prefill", status="ADOPTED",
      requires="P115", conflicts="-", synergizes="P115",
      evidence=(ARM + " 臂 C（= B + PP=2）：`gdn recurrence` **M 2,416->1,204（-50.2%）、L 11,042->6,011（-45.6%）**，"
                "总量 **M -2.62% / L -2.86%**（对本轮 A 基）=> 相对 B 再省 M 1.80% / L 1.32%。"
                "除 `gdn` +0.5/+2.4%、`gdn out proj` +4.5/+4.8%、`qsa proj` +4.5%(L) 这些迁移项外，"
                "`gemm gate/up` -0.04%、`gemm down` -0.18%、`qsa attn` 0.00%、`dequant` +0.6%、`hc read` +0.4% 全在门槛内。"
                "needle 32k@50% FOUND（51 s）。" + COST +
                " **单测三档同测（同一二进制，只换 env）**：PP=0（quad）1.68x、PP=1（quad_pp）1.88x、"
                "**PP=2（quad2c）3.186 vs 7.689 ms = 2.41x，三档全部 FAILURES: 0（y16/state 逐位相等）**。"),
      verdict=("**采纳**。PP=2 是 `gdn_rec_quad2c_kernel`（两列/lane），单测三档里最快且逐位等价；"
               "与引擎实测一致（C 的 rec -50% > B 的 -28%，单测 2.41x > 1.68x 同序）。"
               "注意它**只能与 P115 同用**（`gdn_recurrence_variant` 的 variant 1 内才查 PP）。")),

 dict(id="P117", scope="ENV", name="STRATA_GDN_NOY", value="1", family="prefill", status="REJECTED",
      requires="P115", conflicts="-", synergizes="-",
      evidence=(ARM + " 臂 D（= B + NOY）：`gdn recurrence` **-29.5%(M) / -29.8%(L)**，与 B 的 -28.4%/-28.6% **无差别**；"
                "总量 M -0.54%（比 B 的 -0.84% 差）、L -2.30%（比 B 的 -1.56% 好）—— 两档方向相反 => 不可判。"
                "M 档另有 `gemm down` **+12.5%（+428 ms）** 的异常跳变（NOY 只改 gdn 的 norm，不可能动专家 MMQ）。"),
      verdict=("**否决（无增量）**。源码与单测都说明原因：y（FP32 scratch）**不属于契约**"
               "（`tests/hip/gdn_rec_head.cpp` 逐字「y, the FP32 scratch, is not part of the contract: 0.1.39's norm kernel no longer "
               "stores the normalized value there, while the head kernels store it unless STRATA_GDN_NOY; what the out projection "
               "reads is y16, and the state」）=> 上游的 variant 0 早就不写它，省下来的写流量在 variant 1 上本来就已经没了。")),

 dict(id="P118", scope="ENV", name="STRATA_GDN_CONVL2", value="1", family="prefill", status="REJECTED",
      requires="-", conflicts="-", synergizes="-",
      evidence=(ARM + " 臂 E（独立）：总量 **M +0.96% / L +0.43%**；靶相位 `gdn` **+0.13%/+0.06%（没降）**，"
                "而 `gdn recurrence` **+9.3%**、L 档 `gather` **+103.8%（+432 ms）**、`wait copy` **+22.2%（+192 ms）**。"),
      verdict=("**否决（更慢）**。`gdn_conv_l2_kernel` 本身是纯逐列循环（无 warp 假设，与现役 `gdn_l2_kernel` 的 32-lane 归约同构），"
               "但把 conv 与 L2 norm 合成一次 launch 后，在 gfx906 上反而打乱了流水（`gather` 翻倍、`wait copy` +22%）"
               "—— 与 `P111`（LANECELL）同类：融合/换协作方式在这张卡上不必然更快。")),
]

bak = REG + ".bak_w797_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(REG, bak)
lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
hdr, rows_old = lines[0], [l for l in lines[1:] if l.strip()]
ids = {l.split("\t")[0] for l in rows_old}
out = []
for r in rows:
    assert r["id"] not in ids, r["id"]
    f = [r[k] for k in ("id", "scope", "name", "value", "family", "status",
                        "requires", "conflicts", "synergizes", "evidence", "verdict")]
    assert len(f) == 11, len(f)
    for x in f:
        assert "\t" not in x and "\n" not in x
    out.append("\t".join(f))
    ids.add(r["id"])
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join([hdr] + rows_old + out) + "\n")

chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
bad = [i + 1 for i, l in enumerate(chk) if len(l.split("\t")) != 11]
allids = [l.split("\t")[0] for l in chk[1:] if l.strip()]
assert not bad, bad
assert len(allids) == len(set(allids))
print("REGISTER OK rows=%d bak=%s" % (len(allids), bak.split("/")[-1]))

q = subprocess.run([sys.executable, "deploy/params/gen_config.py", "--write"],
                   capture_output=True, text=True)
print(q.stdout[-400:])
assert q.returncode == 0
d = json.load(open("deploy/params/generated/strata-huihui-ud-iq4_xs.json"))
print("env:", sorted(d["env"].items()))
