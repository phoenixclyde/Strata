# -*- coding: utf-8 -*-
"""W793：register 增 P107（rocBLAS 表）/ P108（镜像 p3 = max-ilp）/ P109（SIMT=1 否决），然后 gen_config --write。"""
import io, json, shutil, time, subprocess, sys

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
ARMED = ("【W793 实测 2026-10-25 16:19-16:32，同一镜像 0.2.4p3 内三臂交错 A B C A B C，各臂独立 restart，"
         "M 档 21,822 tokens，唯一 nonce reused=0，governor=schedutil 44 核）")

rows = [
    dict(id="P107", scope="ENV", name="STRATA_ROCBLAS_TUNING", value="/data/gfx906-rocblas-5.5.0.txt",
         family="prefill", status="ADOPTED", requires="p3 镜像(STRATA_ROCBLAS_AVAILABLE=1)", conflicts="-",
         synergizes="P103",
         evidence=(ARMED + " A（无表）prompt_ms 35419/35537；B（+表）34356/34486 => **-3.0%**（两组样本不重叠）。"
                   "相位：hc read 3307->2625（-20.6%）、893 token 草稿段 hc read 629->223（-64%）。"
                   "引擎逐字：`prefill gemm: rocBLAS tuning enabled (56 rows, 47 with a solution, gfx906, rocBLAS 5.5.0.cd957402309)`。"
                   "表由上游 `tools/hip/tune_rocblas.cpp` 生成（单文件 4.6 s 编译，56 行/47 有解，--min-gain 1.03，"
                   "token 桶 1024/2048/4096/8192）；每行都过 rel_l2<=2e-3、max_abs<=4ulp、padding 无写、且必须接受 T-1/T-37/T-63。"
                   "关键形状 T=8192 的 gain：4x10240 2.38、320x10240(HC down) 1.27、512x2560 1.14、10240x320 1.06；"
                   "大形状 10240x2560 / 12288x2560 / 6144x2560 是 1.00（rocBLAS 默认已最优）。"
                   "needle 32k@50% FOUND（52 s）。"),
         verdict=("采纳。表文件在 /home/albus/strata166/data/（bind 到容器 /data），**不在镜像里**："
                  "文件缺失时引擎打印错误并退回默认核，是 fail-safe。"
                  "上游说的 6x 是 gfx1030 在 T<1152 上量的；我们 chunk=8192，落在那张表收益最少的桶里，实得 -3.0%。")),
    dict(id="P108", scope="container", name="生产镜像 strata-gfx906:0.2.4p3（max-ilp）",
         value="gfx906 分支接 rocBLAS + -mllvm -amdgpu-sched-strategy=max-ilp", family="build", status="ADOPTED",
         requires="-", conflicts="-", synergizes="P107",
         evidence=("【W793 2026-10-25 16:13 构建（129 s），16:19-16:32 实测】配方 `deploy/docker/Dockerfile-0.2.4.p3` + "
                   "`patch_gfx906_rocblas.py`。与 0.2.4 的差异两处：① gfx906 分支补 find_package(rocblas) => "
                   "`STRATA_ROCBLAS_AVAILABLE=1` 进了 4 个 prefill DEFINES 且二进制链接 librocblas.so.5（旧镜像两样都没有，"
                   "这就是 STRATA_ROCBLAS_TUNING 一直是死开关的原因）；② CMAKE_HIP_FLAGS 加 max-ilp（build.ninja 里 168 处）。"
                   "max-ilp 效果：旧镜像 restart 后首请求 36,095 ms vs 新镜像 35,419/35,537 => **-1.7%**（旧侧 n=1，弱）；"
                   "新镜像不重启的两次 34,655/34,573 vs 旧镜像四样本中位 35,917 => -3.6%（口径不同，取保守值）。"
                   "max-ilp 只改指令调度、不改算术。needle 32k 在 p3 上两次 FOUND（53 s / 52 s）。"),
         verdict=("采纳。-1.7%~-3.6% 是弱信号但方向一致且零风险（codegen only）；真正的价值是它顺带把 rocBLAS 接线带进来了。"
                  "回滚位：容器 `strata166-407.bak_w793`（= 0.2.4），镜像 `strata-gfx906:0.2.4`。")),
    dict(id="P109", scope="ENV", name="STRATA_SELECT_SIMT", value="1", family="prefill", status="REJECTED",
         requires="-", conflicts="-", synergizes="-",
         evidence=(ARMED + " C（SIMT=1）prompt_ms 35210/35489 vs A 35419/35537 => **-0.36%（不是收益，是噪声；A 自身极差 0.33%）**。"
                   "`qsa select` 相位 716->664 ms（-7%），但该相位只占 prefill 1.9% => 上限 -0.13%。"
                   "顺带查实：`qsa_select.cu:1838` 的 HIP 分支逐字 `v[0] == '1'`，所以上游 PR #3073 的 `STRATA_SELECT_SIMT=2` "
                   "在 HIP 上**静默退回 warp 核**（我们树没有 #3073 的修）。"),
         verdict=("否决（不值一次重编/一条 env）。若将来打 #3073 的 =2，必须先量 `qsa select` 的 scores/topk 拆分，"
                  "该相位在 L 档是 6.9%，比 M 档大 4 倍 —— 只有 L 档才可能值。")),
]

main_reg = REG


def main():
    bak = REG + ".bak_w793_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(REG, bak)
    txt = io.open(REG, encoding="utf-8-sig").read()
    lines = txt.splitlines()
    hdr = lines[0]
    assert len(hdr.split("\t")) == 11
    ids = {ln.split("\t")[0] for ln in lines[1:] if ln.strip()}
    out = []
    for r in rows:
        assert r["id"] not in ids, "dup %s" % r["id"]
        f = [r[k] for k in ("id", "scope", "name", "value", "family", "status", "requires", "conflicts",
                            "synergizes", "evidence", "verdict")]
        assert len(f) == 11
        for x in f:
            assert "\t" not in x and "\n" not in x
        out.append("\t".join(f))
        ids.add(r["id"])
    lines.extend(out)
    body = "\n".join(lines) + "\n"
    io.open(REG, "w", encoding="utf-8", newline="\n").write(body)

    chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
    bad = [i + 1 for i, ln in enumerate(chk) if len(ln.split("\t")) != 11]
    allids = [ln.split("\t")[0] for ln in chk[1:] if ln.strip()]
    assert not bad, bad[:5]
    assert len(allids) == len(set(allids))
    for pid in ("P103", "P107", "P108", "P109"):
        assert pid in allids, pid
    print("REGISTER OK rows=%d bak=%s" % (len(allids), bak))

    p = subprocess.run([sys.executable, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout.decode("utf-8", "replace")[-800:])
    assert p.returncode == 0


main()
