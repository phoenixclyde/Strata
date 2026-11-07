import io
import shutil
import subprocess
import sys
import time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
ARMED = "【W795 实测 2026-10-25 17:32-18:04，p4/p5 镜像内同会话交错、每臂独立 restart，M 档 21,827 tokens，reused=0】"

rows = [
    dict(id="P112", scope="ENV", name="STRATA_PREFILL_MMQ", value="0", family="prefill", status="REJECTED",
         requires="-", conflicts="P113", synergizes="-",
         evidence=(ARMED + " 臂 B（= FP16 专家路径：每专家 dequant 到 f16 再 rocBLAS f16 GEMM）："
                   "prompt_ms **54,166**（54,069/54,263）vs 臂 A **33,627**（33,694/33,560）= **+61.1%**。"
                   "相位归因：gemm gate/up 7,129->19,452（**2.73x**）、gemm down 3,424->7,785（2.27x）、"
                   "dequant(gather) 1,419->5,024（3.54x）；而 qsa attn 6,202->6,202（**1.000**）、"
                   "hc read/gdn/qsa proj/router/select/recurrence 全在 0.97-1.01 => 开关精确命中专家乘积。"),
         verdict=("否决。FP16 专家 GEMM 实得 **3.5 TFLOPS = fp16 峰值 13%**：每专家只有 ~160 行"
                  "(chunk 8192 x 10 专家 / 512)，rocBLAS 在这个 N 上效率极低，抵不过 int8 的 2x 峰值优势。"
                  "**从 P1(W792) 起悬着的「rocBLAS 能不能打赢 MMQ」到此有答案：不能，差 2.3-2.7 倍。**"
                  "P1 的 -20.7% 只属于稠密 GEMM，与专家乘积无关。")),

    dict(id="P113", scope="ENV", name="STRATA_MMQ_TILE_J", value="8|16|24|32|40|48（上限）", family="prefill",
         status="REJECTED", requires="p5 镜像(patch_mmq_tile_j.py)", conflicts="-", synergizes="-",
         evidence=(ARMED + " 引擎逐字打印各臂实际选的瓦片：默认 21(IQ3_S)/20(IQ4_NL) -> **J=64, 48,000 B/block, "
                   "smpbo 65,536** => 2xLDS=96,000 > 65,536 => **1 个工作组/CU**；23(IQ4_XS) -> J=40(25,056 B, 2 WG)；"
                   "8(Q8_0) -> J=80(50,112 B, 1 WG)。封顶后：J=48(26,112 B, 2 WG) prompt **+7.2%** / gemm gate/up **+20.9%**；"
                   "J=40(25,056) +7.5%/+23.4%；J=24(22,944) +9.1%/+25.9%；J=8(20,832, 3 WG) **+34.6%/+117.7%**。单调变差。"),
         verdict=("否决（默认 J=64 已是最优）。机制：J 是「一次权重装入 LDS 能摊到多少行激活」，J 减半则每 MAC 的装填成本翻倍；"
                  "而 2 WG 只等于 2x(256 线程)=8 wave，**占用量没升，装填量却涨了**。上游 PR #28195 的"
                  "「小瓦片换第二个 workgroup」(+5.86%) 前提是 gfx115x 的 **128 KiB/WGP**；gfx906 是 **64 KiB/CU**，"
                  "同样的替换纯亏。**上游启发式在 gfx906 上选对了。**")),

    dict(id="P114", scope="ENV", name="STRATA_MMQ_GROUP_SORT", value="1", family="prefill", status="REJECTED",
         requires="-", conflicts="STRATA_MMQ_RESIDENT_SORT_NE", synergizes="-",
         evidence=(ARMED + " 臂 C：引擎逐字 `prompt MMQ sorts the full expert groups (STRATA_MMQ_GROUP_SORT=1): "
                   "**0 of 48 layers**` => whole_tiles(gt,1280,16)/whole_tiles(dt,2560,16) 对我们的形状全 false，"
                   "**这是死开关**。它仍量出 +1.7%（33,504 vs 32,930，两次都高）。"),
         verdict=("否决（不适用）。附带一条方法论：**同会话交错 + 每臂 restart 仍存在约 1.7% 的臂位漂移**"
                  "（规则 O）=> 总量口径只能判 >3% 的效应；<3% 必须看相位（相位 4 次极差 0.2%）。")),
]


def main():
    bak = REG + ".bak_w795_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(REG, bak)
    lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
    ids = {ln.split("\t")[0] for ln in lines[1:] if ln.strip()}
    out = []
    for r in rows:
        assert r["id"] not in ids, r["id"]
        f = [r[k] for k in ("id", "scope", "name", "value", "family", "status", "requires", "conflicts",
                            "synergizes", "evidence", "verdict")]
        f[7] = f[7]  # conflicts_with
        assert len(f) == 11
        for x in f:
            assert "\t" not in x and "\n" not in x
        out.append("\t".join(f))
        ids.add(r["id"])
    lines.extend(out)
    io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
    bad = [i + 1 for i, ln in enumerate(chk) if len(ln.split("\t")) != 11]
    allids = [ln.split("\t")[0] for ln in chk[1:] if ln.strip()]
    assert not bad, bad
    assert len(allids) == len(set(allids))
    for p in ("P112", "P113", "P114"):
        assert p in allids
    print("REGISTER OK rows=%d bak=%s" % (len(allids), bak))
    q = subprocess.run([sys.executable, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(q.stdout.decode("utf-8", "replace")[-600:])
    assert q.returncode == 0


main()
