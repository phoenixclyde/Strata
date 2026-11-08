#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059 ledger landing #1: code-census ① group closures (existing-arm disposals).
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()

# id -> (new_status, detail_append, kw)
CLOSE = {
    "P424": ("DONE_NEG",
             "【W1059 收口·code-census①】按既有臂判否：W949/W953 整周 A/B（P428 行，iacop 三件 + i+1 预取）s_waitcnt −0.44% < 2×CV(3.2%)，方向一致但全在门内；「真构建验证=逐位+400ms」在 R117/R118 整树统一时做。口径=实跑 A/B（P428）。",
             "KW:P424|P428|s_waitcnt"),
    "P455": ("DONE_NEG",
             "【W1059 收口·code-census①】救法靶子不存在：W975 层审（P454 行）判该层「roofline 天花板 0%、架构无解」，不是 q 误差问题（P456 已撤回 q 主因）；dot2 相关问题已由 P541/P545/P553-P555 关闭（dot2 文化 P545 重登记；GLU=双 GEMM 无 dot2 收益）。口径=W975 层审 + P456 撤回行。",
             "KW:P455|P456|W975"),
    "P1c": ("DONE",
            "【W1059 收口·code-census①】pcie_frac_auto 第 1 块已放开：0.1.54n4 起 auto=0.20 生效（P259x 行），生产 0.2.27s/335ms 优于 auto 的 0.35/410ms ⇒ auto 关闭正确，P227 族实证完毕。口径=P259x 实跑。",
            "KW:P1c|P259x|auto"),
    "D28": ("DONE_NEG",
            "【W1059 收口·code-census①】按 W839 §6 判读收口（不再逐块 A/B）：28 块全有 `#else` 生产等价回退（P281 行已证实）；有意义差异仅 3713（安全网，缺它只报错更晚）与 2111/4208（≡P1c，已放开验证）；598 ADAPT_KERNEL_COPY 是 W717/P23 已知反向优化，永不放开。逐块 A/B（W717 教训：不许批量）的边际价值≈0。口径=P281 运行日志 + P23/P259x。",
            "KW:D28|P281|§6.6"),
    "R19": ("DONE_NEG",
            "【W1059 收口·code-census①】短档固定开销按 W861 算术上限判死：k570 张量同步 54 µs/tok → 1k tok = 54 ms ≈ 1.2% < 2×CV 3.2%（W921「计算阶段判死」规则）；19.4 s/1k 的实测主成分是首轮 mmap 缺页（W948/P408：18–37 KB/token），修复在 R103/V2 已上线。口径=W861 实测分解 + W948 归因。",
            "KW:R19|W861|54µs"),
    "R42": ("DONE",
            "【W1059 收口·code-census①】move-only 形态已在产：rest 226→~120 ms（W870）+ R15 pinned ring（W847）落地生产 config；异步族（KV/prefill）= G6 专项、R15 早证总收益 <3%。存量清零。口径=W870 生产实跑。",
            "KW:R42|W870|120ms"),
    "R72": ("DONE_NEG",
            "【W1059 收口·code-census①】目标已被超越：R104 三开关省 2.7 GiB（目标 1.03 GiB）+ R66 缓冲收紧省 2.33 GiB ⇒ VRAM free 811→2245 MiB，expert cache 自动 7463→8301 槽，比手动扩到 ~7800 更多。口径=R104/R66 生产实测。",
            "KW:R72|R104|8301"),
    "R39": ("DONE_NEG",
            "【W1059 收口·code-census①】四轴全部单测完毕且全判否：--pcie-frac（W826 2×2）、--spec 九臂（W874/W879）、--prompt-cache-every（W880 8192 保留）、chunk 6 档（W941/W987 16384 保留）；全因子组合期望 <<2×CV，不立项（W921 计算阶段判死）。口径=W826/W874/W880/W941 实跑。",
            "KW:R39|W826|全因子"),
    "G1": ("DONE_NEG",
           "【W1059 收口·code-census①】热路径外：W870 400 窗 profiling（P259 谱）量化 provider 不在前 10 耗时；quantize_q8_0_scaled 串行分支只在 K-quants 权重量化时走一次，不在推理热路径。口径=W870 profiling。",
           "KW:G1|W870|热路径外"),
    "G10": ("DONE_NEG",
            "【W1059 收口·code-census①】fp16 dot2 分子项逐项关：fp16 权重（R114 DONE_NEG）/fp16 KV（P553）/fp16 激活（P554）/fp16 点积算子（P555）全实测判否；分母=score 分支 6-9% 延迟=W870 结构上限（intra+inter 串行），指令换不动结构（R116 同族）。救法 P455 亦判否。口径=P553-P555 实跑族。",
            "KW:G10|P555|R114"),
    "X3": ("DONE_NEG",
           "【W1059 收口·code-census①】机械冻结不需要引擎改动：R41/W862 已定「关 conversation-cache 即安全」（开 4096 MiB 只保 UI 刷新语义）；R40/T1 跨进程续传正确（122 行无损）。转上游讨论（同 U4 族，机主批准制）。口径=R41/R40 实跑。",
           "KW:X3|R41|R40"),
    "P481": ("OPEN",
             "【W1059】code-census②：三开关本体按 W1035/P483 纪律永不关（P482 实测 173.7→210.4 tok/s 掉 21%），本条存续价值=防回归 + 搭车 3-4 号 R117/R118 整树统一一并做。保持 OPEN（搭车）。",
             None),
}

# detail-only updates (progress notes, stay OPEN)
NOTES = {
    "R63": "【W1059】code-census②：内层手法本体在 W949/W953 落地 + 单测 P427/P428（s_waitcnt −0.44%<2×CV）；readfirstlane hoist 未实测（R51 教训：R51 的 hoist 推断漂亮、实测 −6~10%）⇒ 下一手=hoist 变体单测，不动生产。",
    "M2": "【W1059】code-census②：首探针已在实验树（W957/W958/vleak 补丁），但路径判死（P346/P347：分支末读+128B 每 token 恒越界 65KiB/s，撞 PLE 累积墙 4.4h）⇒ 解法=紧缓冲=钳 PLE 上限（J5，−3.6% 族），开探针不急。",
    "K8": "【W1059】code-census②：三用例 0.82 s 本地可跑、无需 GPU（P565 审计实证）⇒ 下一手=cron/CI 挂 task #29953 挂钩，挂上即关。",
    "R45": "【W1059】code-census②：RING_RESERVE=4G 已删（P154）；RESIDENT_HEADROOM_GIB=0.5 是 auto 机制的显式档、非惰性（P65 判词过时）；file-backed 0 是默认、留显式作自文档 ⇒ 建议改标题后关。",
    "R49": "【W1059】code-census②：流水残差在 pack8_u4+scale 解析标量段（P428 上限 −0.44%）；主手法（w4a8 双缓冲 LDS）在 P427 实测 +0.0~+1.1% 已拿 ⇒ 标 DONE、余项归 R63。",
    "R50": "【W1059】code-census②：MFMA（W945/W946）与内层拆分（W948）两次实测全判否；破 60 GB/s 下界的两条路（bf16-mix ISA、重排）分别被 gfx906 缺 ISA 与多头交换成本判死 ⇒ 建议 DONE_NEG。",
    "R94": "【W1059】code-census②：r2v3(0.4.1)/r33(0.2.8)/r34(0.2.9) 三版基线 KL 全部未过（0.0733-0.0770 vs 门 0.0139，P539）⇒ 按 R69 先例，任何 v0.9.0 换版在 KL 门面前无差别 ⇒ 建议 DONE_NEG（判据从一开始就不可能过）。",
    "R79": "【W1059】code-census②：现役未编入 #3747（P403 实测空转 60s 0 次重启）⇒ ①判现役行为（轻）②#3747 纳入 3-4 号（与 713 同批）。",
    "R80": "【W1059】code-census②：工具已备（binary_integrity 磁盘/镜像/容器三方、round_ledger 有账本行）⇒ ①并入 round_close HARD ②再加 ci/gate.py 三查（config.exe md5==账本 exe_md5 等）。",
    "R81": "【W1059】code-census②：0.2.10 未上线（0.2.9 在产，MEMORY 铁律）⇒ ①修 0.2.9 表面（40 个 token 墙，W796）②窗口宽度归 R117 的 verify 窗口（0.2.10+）。",
    "X4": "【W1059】code-census②：空钩子分支已在（W805 正确性过）；未开=开=关 draft 词表 ≈ R102 依赖 v0.9.0 ⇒ 随 3-4 号 v0.9.0 统一。",
    "X5": "【W1059】code-census②：KV 行为已变（grow 常开 244 GiB 虚拟、驻留 13.3 GiB、实测立即喂 40K 无回归 P392-W866）⇒ 建议关（HOLD 无实义）。",
    "X7": "【W1059】code-census②：融合内核已在且默认开（w4a8=4.75/p74 生产常态）；X7=另一版接线闲置 ⇒ 建议关（主形态已实测正收益）。",
    "G2": "【W1059】code-census③：判据写死「绑定在 head 宽度 2560」（统一宽度 3-4 号后自动满足）；且 R42 族已判否会话分块收益 ⇒ 归 R117 搭车，状态 BLOCKED-on-R117。",
    "G3": "【W1059】code-census②：机制收益（20s+15s）在 P343 已判「引擎重构级且需喂 500+ 行接口」，投影端到端 <0.4% ⇒ 建议 DONE_NEG。",
    "G4": "【W1059】code-census②：目标=32K 14.9%→7%（上限 8%，P259 谱）；W838 判 CUDA 移植巨大、W949 手法已捡、QSA 侧 R89 在队 ⇒ 建议归并 R89 后关。",
    "G5": "【W1059】code-census②：R95 族 A/B/C 全出局 + 建表/调度两项事后归因≈0（P328/P329）⇒ GRAPH_PRIO 无终态收益 ⇒ 建议 DONE_NEG。",
    "G8": "【W1059】code-census②：P428 实测 LDS bank 冲突候选 0 命中（DMA beat 0/512 行）⇒ 建议 DONE_NEG（实跑判死，比 P438 更强）。",
    "G9": "【W1059】code-census②：P428 实测 hazard2/hazard3 计数 0（相邻周期 0 读）⇒ 无 ds_bpermute 可消 ⇒ 建议 DONE_NEG（实跑判死）。",
    "U2": "【W1059】code-census③：kernel 2.4-2.7×→端到端 +4.2%<8%（R88 预注册未达标，W983）⇒ 降 backlog，OPEN=「等 R88 的 R91 落地后复核」，状态 BLOCKED-on-R91。",
    "U4": "【W1059】code-census③：外发 PR 须机主批准且不产本机收益 ⇒ 状态 BLOCKED-on-机主。",
    "G6": "【W1059】code-census③：R42 异步族已判死（free≥want+3GiB 门）+ Amdahl 2.85%<3.2% ⇒ 归 R117 搭车，状态 BLOCKED-on-R117。",
    "G7": "【W1059】code-census③：现役 3 波前缀后实测正收益 +13.1-24.5%（P558），按 R114 先例，没有 wave64 替代的实测收益 ⇒ 建议 DONE_NEG。",
    "X6": "【W1059】code-census③：两开关全闲置（ROCm pinned 拷贝引擎只写不读 / exchange_rotate 未接线）⇒ 按 W1035 §6.6 判读收口，建议关（与 D28 同口径）。",
    "R85": "【W1059】code-census③：手段序中 R91 已关 P2（W1058 P589），R46 上限 3.3× 在队 ⇒ 保持验收口径随行，不单列。",
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
