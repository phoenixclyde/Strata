#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1058 ledger landing: R91 P0-P4 evidence rows + R91 status update.
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()

NEW = [
    "B6判定探针\tP585\tR91-P1 量化器 PASS：BlockA4（scale=amax/7·roundf·clamp[-8,7]，裸整数 Σa 进块头）CPU/GPU 逐位一致 4096/4096 块\tW1058\tcount\t1\t1\tDONE\t"
    "**W1058**。P1 块格式 {half d; int16 sa; uint8 qs[16]}：32 值/块，d=fp32(amax/7) 存 fp16，codes=roundf(x·7/amax) clamp [-8,7]，**sa=裸整数 Σcodes**（刻意区别于 Q8_1 的 d·Σq fp16 头——sdot8 重定心 +8·Σa 在 int32 域需要裸整数，已登记）。公式逐字对齐 a4sim（P583/R74 门测过的同一式）。判据「与 CPU 参考逐元素一致」：4096 块（含全零/±0.5 tie/单点 amax/−8.5 饱和边角）GPU vs CPU **mismatch=0**（codes/d 位/sa 全同）。Σa 与 kernel 现算一致随 P3 等价性闭合（P586）。\talbus/w1058/r91_p1p3.cu\tKW:R91|P1|BlockA4",
    "B5本机缺口\tP586\tR91-P3 vec_dot PASS：sdot8(q^0x88888888,a)+8Σa 与 dp4a 臂 81920/81920 逐位等价；真 Q4_K 实例 ISA A/B v_dot4 5184→0、v_dot8 0→2528\tW1058\tcount\t1\t1\tDONE\t"
    "**W1058**。① 数学：`vec_dot_q4_K_q4_impl_mmq`（W927/W947 恒等式 Σ(q−8)a+8Σa=Σqa）三臂 GEMM（M64×N1280×K2560，int4 码 [-8,7]）A_dp4a==B_repack==C_packed **逐位**（0/81920），vs fp64 反量化参考 rel_l2<5e-7。② ISA（真 mmq-instance-q4_k.cu.o，编译命令逐字抄 ninja）：base DOT4 5184/DOT8 0 → cand DOT4 **0**/DOT8 **2528**（2.05:1，判据「v_dot4 减半且 v_dot8>0」超预期达成）；预处理实证变体被编入（pp_builtin_sdot8=1）；fatbin 管道复现 P519 外证（sdot8→v_dot8_i32_i4）。③ **接线陷阱（重要）**：mmq-instance 用相对 include `../mmq.cuh` 直读 **llama-master 树**副本，build overlay 的 -I 只对直接 TU（如 W1057 的 quantize.cu）有效——打 overlay 头对实例 TU 是 no-op；改内核头必须打 llama-master 树副本（或双份同改+md5 配对）。补丁后双份 md5 还原 9e0da3cb。\talbus/w1058/isa_ab.log\tKW:R91|P3|5184|2528",
    "B6判定探针\tP587\tR91 P2 前置微基准：C_packed（int4 打包+sdot8）1.57×≥1.3× 过门；B_repack（只换指令不改布局）0.96× 判否\tW1058\tcount\t1\t1\tDONE\t"
    "**W1058**。同访问面三臂（生产 gate/up 形状 M64×N1280×K2560，权重行 LDS 缓存修 w947 的 8× 流量缺陷，3 run×5 trial 交错，CV 6–7%）：A_dp4a 2.02ms/0.83 TMAC/s、B_repack 2.10ms（**0.962×**）、C_packed 1.29ms（**1.570×**，run 间 1.567–1.576）。**结构结论（与 R116 互证）**：收益全部来自布局流量减半（激活字节 ×0.5）+打包指令；纯指令密度替换（B）≈0 转化甚至倒亏（repack 开销）——「换更强指令」不改数据布局=白干。P2（tile int8→int4 打包）的前置门过。\talbus/w1058/run.log\tKW:R91|1.570|0.962",
    "B6判定探针\tP588\tR91-P4 精度门 PASS（均值口径）：组合法——R74 logits KL mean 0.002295/top-1 100% + P1↔a4sim 公式同一 + P3 整数逐位等价\tW1058\tcount\t1\t1\tDONE\t"
    "**W1058**。P4 判据（W913/W951）：KL≤0.005、argmax≥99%（分辨率 0.0032）。组合链：① R74 实测全词表 logits（P583：KL mean 0.002295≤0.005、top-1 100%≥99%）测的就是 W4A4 激活量化误差；② P1 量化器公式与 a4sim 逐字同一（P585）⇒ 码值全同；③ P3 证 sdot8 路径与 dp4a 路径整数逐位等价（P586）⇒ GEMM 数值全同（fp32 重排噪声 ≪0.0032 分辨率）⇒ 真 W4A4+dot8 logits = 门测仿真 logits。**max-KL 复核**（P583 遗留）：max 0.006704（1/6 点）按 W913/R59 注册口径裁决——R59 结案原文「mean 0.002005（max 0.011209）⇒ 过（均值口径）」，max 仅记档；本项 max 0.0067 < R59 的 0.0112 ⇒ **记档不判死**。P4 过门，「P4 大概率是终点」的预判被实测推翻。\talbus/w1057/compare_a4.out\tKW:R91|P4|0.002295|max0.0067",
    "B8工程\tP589\tR91 P2/P5 立项分析：指令口径上限被 B 臂证伪，真收益在布局侧但真核占比未量；P5 门 2×CV 3.2% 对 1.5–2% 不可检\tW1058\tcount\t1\t1\tDONE\t"
    "**W1058**。① W943 的 −2.05% 端到端上限是**指令口径**（dot4 占 kernel 30% 指令×减半×67.1% VALU×20.4% gate/up）——其「密度转化」假设被 P587 B 臂证伪（0.96×，密度≈0 转化）⇒ 该上限高估了指令侧收益。② 真候选收益=布局/流量侧（C 臂 1.57×），但真 mmq 内核里 x_qs 流量占 kernel 时间的比重**未量**。③ P5 验收门（|Δ|≥2×CV=3.2%）对 1.5–2% 效应**不可检**（W914 纪律③：低于分辨率写「未测出」，不写「无收益」）。**下一步（预注册）**：先做占比侦察（rocprof PMC / LDS 流量计数估 x_qs 读占 kernel 时间比例）再裁 P2 立项；若要 P5 可检，A/B 重复须 ×4–5 把 CV 压到 ≤0.75%，或改用层级指标验收。P2 tile 手术（LDS 重排+prefill_mmq_tab_test 逐位）暂不开工。\talbus/w1058/run.log\tKW:R91|P589|侦察",
]

# R91 status update (keep OPEN: P2/P5 pending)
closed = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 10 and f[1] == "R91":
        f[8] += ("【W1058】P0–P4 全过门：P1 量化器逐位一致（P585）、P3 sdot8 整数逐位等价 + Q4_K 实例 ISA v_dot4 5184→0/v_dot8 2528（P586）、"
                 "P4 均值口径 PASS（P588，max 复核按 R59 先例记档）；P2 前置微基准 1.57×过门（P587）但纯指令密度判否（B 臂 0.96×）；"
                 "P2/P5 立项待占比侦察（P589）。")
        kw = "KW:R91|P1|P3|P4|1.570"
        if len(f) >= 11:
            f[10] = kw
        else:
            f.append(kw)
        lines[i] = "\t".join(f)
        closed += 1
assert closed == 1, closed

out = lines + NEW
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("landed: R91 updated, +%d rows, total %d" % (len(NEW), len(out)))
