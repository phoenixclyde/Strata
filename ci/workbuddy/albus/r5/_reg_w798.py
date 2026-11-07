import io, shutil, time, subprocess, sys, json
REG = "deploy/params/PARAM_REGISTER.tsv"
E = "【W798 实测 2026-10-25 19:47-20:45，p4 镜像，多轮（8K 建会话 + 4-6 轮追加，256 tok），STRATA_VERIFY_PROFILE=1 分相位】"
COST = " 口径：端到端 decode 不可判（v1 同问题重复 27% 假趋势；v2 问题各异轮间差 25%；同一开关两次测量方向相反），故按 `decode GPU stages` 分相位判。"
rows = [
 dict(id="P119", scope="ENV", name="STRATA_SH_STREAM", value="1", family="decode", status="REJECTED",
      requires="-", conflicts="-", synergizes="-",
      evidence=(E + " 端到端 decode_ms r4/r5/r6：A 4062/3483/3198 vs B 4077/3860/3618 ⇒ **慢 10.8%（三个轮次同向）**。"
                "源码注释逐字已预示：HIP 上跨流 event 依赖比共享专家本身还贵，R9700 上 fork 开 62.9 -> **43.4 t/s**，"
                "gfx1030 同；只有 gfx1151（统一内存）例外。默认 `#if defined(STRATA_USE_HIP) return false` 正确。" + COST),
      verdict="**否决**。且**带 profiler 测不了它**（源码逐字「The profiler turns the fork off to time the stages」），只能靠端到端 + 源码注释。"),
 dict(id="P120", scope="ENV", name="STRATA_Q8_PACKED", value="1", family="decode", status="REJECTED",
      requires="-", conflicts="-", synergizes="-",
      evidence=(E + " 引擎逐字 `native dense: STRATA_Q8_PACKED=1 packed 84 Q8_0 matrices for decode (+1912.5 MiB)`；"
                "**专家槽 9901 -> 9046（-855，-8.6%）**，而 vram_free 只有 606 MiB。"
                "相位：靶 `q8+qkv/q-idx gemv` **+8.1%**（确实生效）、`waitB` **+21.6%**、`waitCPU` **+25.0%**、`Q:waitA` +25.0%。" + COST),
      verdict=("**否决**。它确实生效（靶相位 +8.1%），但方向是变慢，且要 1.9 GB 显存 —— 在「余量 606 MiB、专家槽还要兜 prefill」的前提下没有采纳理由。"
               "另：本开关在两次测量里端到端方向相反（W798 慢 6.7-38.9%，W798d 快 2.8%），是「端到端不可判」的最直接证据。")),
 dict(id="P121", scope="ENV", name="STRATA_EXPERT_V2", value="1", family="decode", status="REJECTED",
      requires="-", conflicts="-", synergizes="-",
      evidence=(E + " 相位：`VRAM hits` **+37.7%**（GDN 段）、`Q:VRAM hits` **+38.6%**（QSA 段），同时 `waitCPU` **-39.3%**、`PCIe grp` +20.0%；"
                "其余相位 `q8+qkv gemv` +0.7%、`out-proj` 0.0%、`router/plan/bell` +0.3% 基本不动。端到端 r2-r4 中位 3766 -> 3960（+5.1%）。" + COST),
      verdict=("**否决**。机制：`waitCPU` 与 `VRAM hits` 之和近常数，它把 39% 的 CPU 等待换成了 38% 的专家流时间 —— "
               "在 gfx1151（统一内存、带宽充裕）上是省钱，在 gfx906（离散显存）上是把重叠算成串行。")),
 dict(id="P122", scope="ENV", name="STRATA_LFUSE", value="1", family="decode", status="REJECTED",
      requires="-", conflicts="-", synergizes="-",
      evidence=(E + " 相位全平：`q8+qkv gemv` +0.4%、`rec` -2.7%、`shared+quant` -0.6%、`VRAM hits` +0.1%、`waitB` 0.0%、`copy+combine` -1.6%；"
                "端到端 r2-r4 中位 3766 -> 3776（+0.3%）。" + COST),
      verdict="**否决（无效）**。相位没有实质变化 ⇒ 它省的 launch 在这个负载形态下不构成瓶颈。"),
 dict(id="P123", scope="ENV", name="STRATA_GDN_SPLIT", value="1", family="decode", status="REJECTED",
      requires="-", conflicts="STRATA_GDN_HEAD（同族，但 prefill 侧）", synergizes="-",
      evidence=(E + " 相位：`rec` **+37.8%**，其余全平（`q8+qkv gemv` +0.4%、`VRAM hits` +0.2%、`waitB` +1.1%、`Q:attention` +2.0%）；"
                "端到端 r3/r4 慢 6.7% / 9.7%。" + COST),
      verdict=("**否决**。与 `P115`/`P116`（prefill 的 GDN_HEAD/PP，`gdn recurrence` **-50%**）方向完全相反，原因是 T："
               "prefill 是 4 lane/列 + HT=4 tokens 流水（LDS 复用摊得开）；decode 是 4 块/head + T=1（每块只算 32 列，同步与 launch 摊不开）。"
               "⇒ **同一算子的分块策略不能跨 prefill/decode 平移**。")),
 dict(id="P124", scope="ENV", name="STRATA_TSUM", value="1", family="decode", status="REJECTED",
      requires="-", conflicts="-", synergizes="-",
      evidence=(E + " 相位全平：`q8+qkv gemv` 0.0%、`rec` -1.4%、`out-proj` 0.0%、`VRAM hits` +0.3%、`Q:VRAM hits` -6.8%；端到端 r2-r4 基本无差。" + COST),
      verdict="**否决（无效）**。"),
 dict(id="P125", scope="ENV", name="STRATA_QFUSE", value="1", family="decode", status="PENDING",
      requires="-", conflicts="-", synergizes="-",
      evidence=(E + " **数据自相矛盾**：端到端出现 **488 / 2012 ms**（256 tokens 不可能低于 3 s）与 4734/3572 交替；"
                "相位全面下降（`VRAM hits` -15.5%、`Q:VRAM hits` -24.8%、`out-proj` -13.4%、`shared+quant` -12.5%、`waitCPU` -39.0%）"
                "却同时 `waitB` **+20.7%**。"),
      verdict=("**未判（PENDING），不采纳**。suspicion：某些轮次 draft 一次性接受了大量 token，导致 `ms/window` 与总时长不同口径；"
               "也可能是 QFUSE 改了 q8_1 量化的产生点从而影响 draft 与 target 的一致性。复测须固定 window 数而非固定 output tokens。")),
]
bak = REG + ".bak_w798_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(REG, bak)
lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
hdr, old = lines[0], [l for l in lines[1:] if l.strip()]
ids = {l.split("\t")[0] for l in old}
out = []
for r in rows:
    assert r["id"] not in ids, r["id"]
    f = [r[k] for k in ("id","scope","name","value","family","status","requires","conflicts","synergizes","evidence","verdict")]
    assert len(f) == 11
    for x in f: assert "\t" not in x and "\n" not in x
    out.append("\t".join(f)); ids.add(r["id"])
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join([hdr] + old + out) + "\n")
chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
bad = [i+1 for i, l in enumerate(chk) if len(l.split("\t")) != 11]
allids = [l.split("\t")[0] for l in chk[1:] if l.strip()]
assert not bad, bad
assert len(allids) == len(set(allids))
print("REGISTER OK rows=%d bak=%s" % (len(allids), bak.split("/")[-1]))
q = subprocess.run([sys.executable, "deploy/params/gen_config.py", "--write"], capture_output=True, text=True)
print("gen rc", q.returncode)
d = json.load(open("deploy/params/generated/strata-huihui-ud-iq4_xs.json"))
print("env n=%d" % len(d["env"]))
