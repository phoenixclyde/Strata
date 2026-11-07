# -*- coding: utf-8 -*-
"""W792：register 增行 + 修正 P102，然后 gen_config --write。
fail-closed：先备份；写入后校验 11 列 / ID 无重复 / P103 存在。
"""
import io, shutil, time, subprocess, sys

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"

rows_new = [
    dict(id="P103", scope="ENV", name="STRATA_HIP_PROMPT_F16", value="1", family="prefill",
         status="ADOPTED", requires="-", conflicts="-", synergizes="P78",
         evidence=("【W792 实测 2026-10-25 15:16-15:32，同轮 B/F 交错 A/B，M 档 21,822 tokens，唯一 nonce reused=0，"
                   "governor=schedutil 44 核，0.2.4/0.1.49.2】B（bf16 GEMM）prompt_ms 45333/45690/45207/45238（中位 45286）；"
                   "F（+STRATA_HIP_PROMPT_F16=1）36095/35936/35899/35878（中位 35917）=> **-20.7%**，墙钟 51.2/50.7/51.4/50.6 -> 42.0/40.9/42.5/40.9 s。"
                   "归因（prefill timing，ms）：hc read 8199->3501(-57.3%)、gdn 6105->3718(-39.1%)、qsa proj 2621->1757(-33.0%)、"
                   "gdn out proj 2146->1623(-24.4%)、router+shared 1852->1057(-43%)；而 gemm gate/up 7054->7083(+0.4%)、"
                   "gemm down 3806->3800(-0.2%)、qsa attn 6928->6908、qsa select 717->716、gdn recurrence 2500->2462、dequant 1416->1402 "
                   "**一个没动** => 开关精确命中它声明的那部分（rocBLAS 稠密 16-bit GEMM），不是整体提速。"
                   "机制：gfx906 无 bf16 点积，bf16 GEMM 只能按 F32 速率（MI50 13.2 TFLOPS）；FP16 有 v_dot2_f32_f16（26.5 TFLOPS）。"
                   "hc read 等效吞吐 3.4 -> 7.7 TFLOPS（正好 2 倍硬件通路）；带宽侧 39 GB/s = 峰值 5%，不是瓶颈。"
                   "质量门：needle 32k 深度 10%/90% 两臂各 2/2 FOUND；F 臂同 prompt 55s/53s vs B 68s/67s（1.24x）。"
                   "上游同类证据：PR #835 在 gfx103x（同样无 bf16 点积）上 prompt 读取 ~2x。"),
         verdict=("采纳。数值改变是设计内的（每个 16-bit GEMM 输出舍入到 FP16，上游逐字 not bit-identical）；"
                  "任务级门（needle）已过，分布门（KL）只能判不同不能判更坏，故不做。回滚：删本行 gen_config --write + 重启即回 bf16 路径。")),
    dict(id="P104", scope="prefill", name="prefill 分相位账（STRATA_PREFILL_TIMING=1）", value="M 21,822 / L 99,382 tokens",
         family="measure", status="REFERENCE", requires="-", conflicts="-", synergizes="P103",
         evidence=("【W792 实测 2026-10-25 15:06-15:16，零代码开关，4 次 M + 1 次 L】M（44.5 s，4 次极差 0.24%）："
                   "hc read 8100(18.2%) / gemm gate/up 7057(15.9) / qsa attn 6910(15.5) / gdn 6102(13.8) / gemm down 3805(8.6) / "
                   "qsa proj 2620(5.9) / gdn recurrence 2504(5.6) / gdn out proj 2146(4.8) / router+shared 1667(3.7) / dequant 1433(3.2) / "
                   "qsa select 717(1.6)。L（214.5 s）：hc read 36956(17.2) / qsa attn 32876(15.3) / gemm gate/up 31306(14.6) / gdn 27842(13.0) / "
                   "gemm down 16833(7.8) / **qsa select 14812(6.9，随上下文 4.3x)**。按后端归并：rocBLAS 稠密 GEMM 46.4%(M)/43.8%(L)、"
                   "专家 MMQ+dequant 27.6/25.2、自研 kernel 22.7/27.6。chunk=8192。"),
         verdict=("这是 prefill 的第一份分相位账，也是此后所有 prefill 项目的排序依据。"
                  "可判性：prefill 相位 4 次极差 0.14-0.24%，比 decode 的 6-7% 门槛低两个数量级 => 门槛按相位给（规则 M）。")),
    dict(id="P105", scope="prefill", name="rocBLAS 解题表（STRATA_ROCBLAS_TUNING）", value="gfx906 分支未定义 STRATA_ROCBLAS_AVAILABLE",
         family="container", status="CANDIDATE", requires="一次重编", conflicts="-", synergizes="P103",
         evidence=("【W792 源码 + 容器核查 2026-10-25】`CMakeLists.txt:112` 只在 `STRATA_ENABLE_HIP` 时 include `cmake/hip_backend.cmake`；"
                   "gfx906 走 `:149` 的独立分支，只 find_package(hip)+find_package(hipblas)，**不 find rocblas** => "
                   "`STRATA_ROCBLAS_AVAILABLE` 未定义（容器 `build-906/build.ninja` 里 grep 不到，也不链接 rocblas）=> "
                   "`gemm.cu` 的 try_rocblas_f16o 整段被 #if 掉 => **STRATA_ROCBLAS_TUNING 设了也没用**。"
                   "容器内 `/opt/rocm/lib/cmake/rocblas/rocblas-config.cmake` 与 rocblas-targets.cmake **都存在**（不是缺包），"
                   "只差 gfx906 分支补一次 find_package。上游 `tools/hip/tune_rocblas.cpp` 在我们树里，可直接编出 gfx906 表。"
                   "旁证：Docker Hub `xxdoman/strata-mi50`（0.2.3 gfx906 专版）逐字写着同一件事，并自带一份 108 行 gfx906 表。"
                   "上游注释称 rocBLAS 自选解最差可比它自己持有的最优解慢 6x（gfx1030，tools/hip/tune_rocblas.cpp）。"),
         verdict=("排队（P2）。范围：① 一行 CMake 接线；② 编 tune_rocblas 并在我们的真实形状上调表（T=8192/5438/2048…，N/K 为模型几何）；"
                  "③ A/B 判据：只换解题、不改算术 => 必须 bit 一致，再比 prefill timing。")),
    dict(id="P106", scope="prefill", name="STRATA_SELECT_SIMT=2（HIP）", value="被静默退路挡住", family="container",
         status="CANDIDATE", requires="-", conflicts="-", synergizes="-",
         evidence=("【W792 源码核查 2026-10-25】`qsa_select.cu:1838` 的 HIP 分支逐字 `return v[0] == '1';` => 给 `=2` 直接落到 warp kernel；"
                   "同文件 CUDA 分支才认 `=1/2`。上游 PR #3073（open）正是修这条，并称 gfx1030 上 119K prompt **-6.5%**。"
                   "我们的 qsa select 占比：M 1.6%（717 ms）/ **L 6.9%（14,812 ms）**。`=1` 可用（FP32 tiled，另一种求和顺序）。"),
         verdict=("排队（P4）。先测 `=1`（零代码），再决定要不要移植 #3073 的 `=2`。判据：L 档 qsa select 降 >=30%，且 needle 不变。")),
]

# --- P102 判定补 W792 撤回 ---
P102_ADD = ("；**【W792 撤回 2026-10-25 15:0x】本条「其机制是 R5 的正解」的判断建立在「上游 K 切分只支持 bf16」之上，该前提**错**："
            "Q8 的 down 内核本身就是 K 切分（`launch_q8_t`: `Q8_KC=640, Q8_NKC=16` => 11x16=176 block，每片 partial 由 `gr_up_q8_kernel` 合成），"
            "而 `STRATA_GR_SPLIT` 的 bf16 版是 5 片 x 2048（41x5 block）=> 把它「移植」到 Q8 是**把 16 片改成 5 片（变粗）**，"
            "不是新增能力；它真正的收益来源（占用率 41->205 block）Q8 版早已吃掉。**R5a-down 作废。**")

def main():
    bak = REG + ".bak_w792_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(REG, bak)
    txt = io.open(REG, encoding="utf-8-sig").read()
    lines = txt.splitlines()
    hdr = lines[0]
    ncol = len(hdr.split("\t"))
    assert ncol == 11, "header columns %d != 11" % ncol

    # P102 修正
    hit = 0
    for i, ln in enumerate(lines):
        if ln.startswith("P102\t"):
            f = ln.split("\t")
            assert len(f) == 11, "P102 cols %d" % len(f)
            f[10] = f[10] + P102_ADD
            lines[i] = "\t".join(f)
            hit += 1
    assert hit == 1, "P102 hits=%d" % hit

    # 新行
    ids = {ln.split("\t")[0] for ln in lines if ln and not ln.startswith("id\t")}
    out = []
    for r in rows_new:
        assert r["id"] not in ids, "dup id %s" % r["id"]
        f = [r[k] for k in ("id", "scope", "name", "value", "family", "status", "requires", "conflicts", "synergizes", "evidence", "verdict")]
        assert len(f) == 11
        for x in f:
            assert "\t" not in x and "\n" not in x
        out.append("\t".join(f))
        ids.add(r["id"])
    lines.extend(out)

    body = "\n".join(lines) + "\n"
    io.open(REG, "w", encoding="utf-8", newline="\n").write(body)

    # 自检
    chk = io.open(REG, encoding="utf-8-sig").read().splitlines()
    assert chk[0] == hdr
    bad = [i + 1 for i, ln in enumerate(chk) if len(ln.split("\t")) != 11]
    allids = [ln.split("\t")[0] for ln in chk[1:] if ln.strip()]
    assert not bad, "col mismatch at %r" % bad[:5]
    assert len(allids) == len(set(allids)), "dup ids"
    for pid in ("P103", "P104", "P105", "P106"):
        assert pid in allids, pid
    assert "W792 撤回" in body
    print("REGISTER OK rows=%d cols=11 bak=%s" % (len(allids), bak))

    p = subprocess.run([sys.executable, r"D:/workbuddy_space/strata_ws/deploy/params/gen_config.py", "--write"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout.decode("utf-8", "replace")[-1500:])
    assert p.returncode == 0, "gen_config failed"


main()
