#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059 ledger landing #2: existing-data disposals (data-miner + code-census ②/③).
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()

CLOSE = {
    "R64": ("DONE_NEG",
            "【W1059 收口·存量实测】前置门不满足：32K 档 qsa attn 实测 15.3–19.0%（引擎日志 `prefill timing: 31633 tokens`，W1035 318 点源）< 25% 门；长度指数 1.20（attn 随 L^1.20、占比平坦，W926 拟合）⇒ 131K 外推 15–18% 也不会过线（99K 实测 15.3%、165K 实测 17.7%）。「算术受限」无 PMC 证据（VALUBusy 67% 是占用不是算术受限）。W1058 P587 亦证 int8 点积密度≈0 转化。判据「32K/131K ≥25% 且算术受限才动码」两条都不成立 ⇒ 关。口径=引擎日志实测相位行 + W926 拟合。",
            "KW:R64|15.3|W926"),
    "R81": ("DONE_NEG",
            "【W1059 收口·存量实测】宽度 6→12 不建议：①现役 window-12 日志 `spec depth` 行 d4+/d5+ 桶恒 **0/0**（窗口装不满，实测 1464/2022·577/789·223/310·0/0·0/0）⇒ 加宽 12 无数据可填；②W809 六臂已证同 min_p 下 **spec 6 830.1 < spec 4 854.0 tok/s**（接受率 73.9<74.7）；③window-6 按 prompt 长度分桶基线（W860 §2.4，n=5356：69.8–86.1%）显示短档本就低、加宽不解。0.2.10 的 +5%（79.44→83.7）未归因且 0.2.10 未上线。口径=W809 实跑 + 现役日志 spec-depth 累计行。",
            "KW:R81|0/0|W809"),
    "R91": ("DONE_NEG",
            "【W1059 收口】dot8 生产接入判否于 ROI（P2/P5 不立项）：P0–P4 精度链全过门（W1058 P585–P588：P1 逐位/P3 整数等价+ISA v_dot4 5184→0·v_dot8 2528/P4 均值口径 KL 0.0023）；但收益上界 <2×CV 3.2%（W921 计算阶段判死）——①指令口径 W943 census：dot4=30% kernel 指令、理想减半 ⇒ e2e −2.05%；②布局口径：LDS 读=10.6% kernel 指令（ds_read2_b32 8.9%+其余），激活侧子集 ≤10.6%、减半 ⇒ ≤−5.3% 指令 × VALUBusy 67% 转化 ⇒ **≤−0.7% e2e**；③纯密度实测 0.962×（P587 B 臂，repack 反亏）。**修正**：MemUnitStalled/LDS 流量计数我方从未采集（CSV 只有 VALUBusy；前稿误把 hipfire 外证 0.3 当自家数）——如需更强证据可补 4 min rocprof（W942 §7 流程）。dot8 工程形态（P1 量化器/恒等式/ISA 链）可复用。口径=P587 实跑 + W942/W943 实测 census。",
            "KW:R91|DONE_NEG|0.7"),
    "R84": ("DONE_NEG",
            "【W1059 收口】已并入 R91 的 P0（W987 BLOCKED 解除条件=dot8 微基准出数，P587 已出 0.962×/1.570×）⇒ 随 R91 一并判否收口，不双记。口径=P587 + P586（ISA 5184→0/2528）。",
            "KW:R84|并入R91"),
    "R50": ("DONE_NEG",
            "【W1059 收口·code-census①】两路实测全判否：MFMA 8×8×8 单发射 fp16 反而输 dp4a（W945/W946）；内层拆分 multi-K 2×MAC/地址+scale 剥离 −1~+3% 全 <2×CV（W948/P427）。破 60 GB/s 下界的两条路（bf16-mix ISA gfx906 无、重排多头交换成本压过节省）判死。口径=W945/W948 实跑。",
            "KW:R50|W945|W948"),
    "R94": ("DONE_NEG",
            "【W1059 收口·code-census②】判据从一开始就不可能过：r2v3(0.4.1)/r33(0.2.8)/r34(0.2.9) 三版基线 KL 0.0733-0.0770 全部 ≫ 门 0.0139（P539）——该门卡的是文本分布，不是单版回归（R69 先例）⇒ v0.9.0 换版在此门面前无差别可言；欠账注销，改由 R55 族逐项消 KL。口径=P539 实测三版。",
            "KW:R94|P539|0.0733"),
    "R49": ("DONE",
            "【W1059 收口·code-census②】主手法已实测拿走：w4a8 双缓冲 LDS + 按行 pick+add（P427，+0.0~+1.1% 六形状逐位）；流水残差=pack8_u4+scale 解析标量段（P428 上限 −0.44%）——按 W945 统一处理（−1% 内不开刀）⇒ 标 DONE，余项归 R63。口径=P427/P428 实跑。",
            "KW:R49|P427"),
    "R45": ("DONE",
            "【W1059 收口·code-census②】清理对象已清完：RING_RESERVE=4G 已删（P154）；RESIDENT_HEADROOM_GIB=0.5 是 auto 机制显式档（P65 判词过时，非惰性）；file-backed 0 是默认留显式作自文档 ⇒ 随 R54 一并收口（标题「惰性 env」已名不副实，判词更新为「显式档保留」）。",
            "KW:R45|P154"),
    "X5": ("DONE",
           "【W1059 收口·code-census②】HOLD 无实义：KV 行为已变——grow 常开（244 GiB 虚拟 / 驻留 13.3 GiB）、实测立即喂 40K token 无回归（W866）⇒ 关（保留 env 不清，行为已由 grow 覆盖）。",
           "KW:X5|W866"),
    "X7": ("DONE",
           "【W1059 收口·code-census②】主形态已在且默认开：w4a8 双行融合=4.75/p74 生产常态（+4.75% / −38% 窗口）；X7 原意的闲置接线无独立价值 ⇒ 关。",
           "KW:X7|p74"),
    "G3": ("DONE_NEG",
           "【W1059 收口·code-census②】重构级不立项：P343/P433 实测判「融合 GLU 与现存 gu 融合的差 = 布局级（一读一写 vs 两读一写），在读影子主导的 roofline 上是舍入」；全融合需引擎重构级+500 行接口、投影端到端 <0.4% <2×CV ⇒ 判否。",
           "KW:G3|P343"),
    "G5": ("DONE_NEG",
           "【W1059 收口·code-census②】优先级机制无终态收益：R95 族 A/B/C 全出局（W990/W1005/W1008 实跑）+ 建表/调度事后归因 ≈0（P328/P329）⇒ GRAPH_PRIO 判否。",
           "KW:G5|P328"),
    "G7": ("DONE_NEG",
           "【W1059 收口·code-census②】wave64 替代无实测收益：现役 3 波前缀实测正收益 +13.1–24.5%（P558），按 R114 先例（无实测收益不立项）⇒ fused_gr wave64 通道判否；:3101 硬拒是正确的现状。",
           "KW:G7|P558"),
    "G8": ("DONE_NEG",
           "【W1059 收口·code-census②】实跑判死：P428 硬件计数 LDS bank 冲突候选 **0 命中**（DMA beat 0/512 行）⇒ +1 padding 系统化无收益 ⇒ 判否（比 P438 静态判死强一级）。",
           "KW:G8|P428"),
    "G9": ("DONE_NEG",
           "【W1059 收口·code-census②】实跑判死：P428 hazard2/hazard3 计数 **0**（相邻周期 0 读）⇒ 无 ds_bpermute 可消 ⇒ DPP 归约判否。",
           "KW:G9|P428"),
}

NOTES = {
    "R46": "【W1059】data-miner：粗粒度反量化相位已可引（PREFILL_PHASES dequant 列 2.4–5.1% wall、32K 日志 2.7–3.3%）；attn 占比 8→17%（L^1.20 指数，**占比平坦**）⇒ 3.3× 天花板的 e2e 口径 = 0.16×(1−1/3.3)≈11%（若全兑现）。细粒度（qsa attn 内 K/V 反量化 vs 点积）仍需 STRATA_QSA_DUMP 一次重建录（W887）⇒ 下一手=该重建 + 录 dump，之后 pa_bench 零停机。",
    "R89": "【W1059】data-miner：depth 1x/3x/6x **零存量**（qsa attn 绝对 ms 有、depth 变体无）；最省方案已定：3 次 STRATA_PREFILL_TIMING 同 ids（tmp/w1044/set32k.ids.json），每臂只改 selection depth 旋钮，判据=core 恒定 vs 随 depth 涨；每臂 1 冷跑 ~4 min。G4（GDN 分块）拟归并入本条。",
    "R95": "【W1059】data-miner：P309（busy/phase 事件）零存量未做——实验树 16 专家 launch 前后加事件 + 2K/16K 各一跑，判据 busy/phase<0.80；P418 固定项结论仍在（2K wall 固定项 21–24% 住 gate/up+down）；P331 d2h_sync 假说已被 W1016 否证。DECODE_TIMING 可引（verify 56.36=GPU-reach 34.64+host 18.83）。",
    "R85": "【W1059】R91 判否后手段序剩 R46>R60（R64 已关）；验收口径（801→≥850）随行不单列。",
    "U2": "【W1059】R91 已判否（0.7–2.05% 族 ROI 逻辑同源）⇒ 复核结论：#3987 端到端 +4.2% <8% 预注册门，维持 BACKLOG/BLOCKED，不捞。",
    "G2": "【W1059】归并 R89/R117（head 宽度统一后自动满足）；状态 BLOCKED-on-R117。",
    "G6": "【W1059】R42 异步族判死 + Amdahl 2.85%<3.2% ⇒ 归 R117 搭车；状态 BLOCKED-on-R117。",
    "G4": "【W1059】归并 R89（32K attn 15-17% 上限同源）；R89 出数后一并判。",
    "R101": "【W1059】LOGPOS 窗口在跑（五臂：s001a/s001b 地板、s010 K10 栈、sum0/sum1 单变量 Σx↔d·Σq）——sumx 探针 strata-0.1.57-sumx 已建（STRATA_SUMX env 门控、marker 进二进制、RECONF 坑已绕过）。",
    "P392": "【W1059】prefill-only LOGPOS 数值门在跑（W824 §10 协议：STRATA_LOGPOS+TOPK=64+CPU_SHARE=0，kl_prop 口径）——s001a/s001b 地板 + s010 K10 整栈 + sum0/sum1 R101 单变量。",
    "P309": "【W1059】实验设计定死可跑：build-tab 实验树 16 专家 launch 前后各加一个事件，2K 与 16K 各一次；判据 busy/phase<0.80 ⇒ 主机饿 GPU（建表挪 issuer/组批提交）；≥0.95 ⇒ 回查激活布局与 group strides。零存量（data-miner 证实）。",
}

n_c = n_n = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) < 10:
        continue
    rid = f[1]
    if rid in CLOSE:
        st, det, kw = CLOSE[rid]
        f[7] = st
        if st.startswith("DONE") or st == "REJECTED":
            f[6] = "1"
        f[8] += det
        if kw:
            if len(f) >= 11:
                f[10] = kw
            else:
                f.append(kw)
        lines[i] = "\t".join(f)
        n_c += 1
    elif rid in NOTES:
        f[8] += NOTES[rid]
        lines[i] = "\t".join(f)
        n_n += 1

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("closures=%d notes=%d" % (n_c, n_n))
missing = [k for k in list(CLOSE) + list(NOTES)
           if not any(l.split("\t")[1] == k for l in lines if len(l.split("\t")) > 1)]
print("missing:", missing)
