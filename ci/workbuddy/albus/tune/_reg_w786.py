# -*- coding: utf-8 -*-
"""W786 结果登记：P87 作废 + 新增 P91（新三档基线）/ P92（prefill 硬地板）/ P93（对话复用）。
"""
import io, shutil, time

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_w786_" + time.strftime("%Y%m%d_%H%M%S"))

lines = io.open(REG, encoding="utf-8-sig").read().splitlines()
out = []

P91 = "\t".join([
    "P91", "REF", "decode 分阶段基线 v2（三档）", "S/M/L", "decode", "REFERENCE", "-", "-", "-",
    "【W786 实测 2026-10-25 04:3x-04:5x】生产 = 0.2.4/0.1.49.2，已去 --resident-experts，HC_Q8=1，"
    "STRATA_DECODE_TIMING=1 + STRATA_VERIFY_PROFILE=1，每档 4 runs（L 档 1 run），稳态 94-100 窗口，四轮极差 <1.7%。"
    "ms/window（M 21,827 / S 2,813 / L 99,387）：总 46.35 / 47.35 / 39.90；"
    "专家流 10.08(21.9%) / 10.58(22.3%) / 8.24(20.7%)；HC 7.42(16.1%) / 7.78(16.4%) / 5.91(14.8%)；"
    "量化+dense GEMV 6.13(13.3%) / 6.40(13.5%) / 4.88(12.2%)；router 3.74(8.1%) / 3.72(7.9%) / 3.70(9.3%)；"
    "注意力 3.31(7.2%) / 2.88(6.1%) / 4.30(10.8%)；out-proj 3.20 / 3.34 / 2.51；z 2.63 / 2.79 / 1.99；"
    "shared+quant 2.66 / 2.75 / 2.21；head 1.94 / 2.02 / 1.53；ab+rec 1.72 / 1.77 / 1.53。"
    "自校验：分项和与总数差 -0.02 / -0.01 / 0.00 ms。每 token 13.85 / 13.76 / 18.82 ms。"
    "端到端：S 11.6s=prefill 6.5+decode 4.9；M 49.5s=44.4+5.1；L 212s=211+1.1 => prefill 占 57%/90%/99.5%。",
    "supersedes P87（P87 基线含 --resident-experts 且分项和差 15%）"])

P92 = "\t".join([
    "P92", "REF", "prefill 性质判定", "算力 bound", "prefill", "REFERENCE", "-", "-", "-",
    "【W786 实测 2026-10-25 04:4x】三条证据同向："
    "① rocm-smi --showuse 每 1s 采样 49 次，M 档请求（prefill 44.4s + decode 5.1s）：100 x42 / 99 x4 / 98 x1 / 68 x1 / 0 x1，"
    "中位 100，零值占比 2% => prefill 期间 GPU 满载（推翻 W784 的「GPU util=0%」，那是 netdata 口径错）。"
    "② 日志 prefill plan 逐字「file set 0.3 GiB fits the page cache 78.9 GiB -> about 0.0 GB read from the drive」"
    "「55.4 GiB experts, 22.3 GiB in the GPU caches, 36.6 GiB RAM copy (1553 lend slots kept), file tier 0.0 GiB; "
    "PCIe 12.0 GB/s」=> 磁盘 0 读、PCIe 未饱和、全部专家在 GPU 或 RAM。"
    "③ 历史记录 22 核 CPU 满载，且 CPU 无 AVX-512（日志「this CPU has no AVX-512」）。"
    "=> prefill 是纯算力 bound，不是 I/O bound。故 --prefill-pipe（前提是读写未重叠）、STRATA_PREFILL_CPU_SHARE"
    "（前提是有 idle CPU 池）、--prefill auto:16384（只减 chunk 数不减总计算，且 P10 已证改答案）均不排。",
    "prefill 490 tok/s 判为硬地板"])

P93 = "\t".join([
    "P93", "REF", "对话复用缺 final checkpoint", "R1", "prefill", "PENDING", "-", "-", "-",
    "【W786 实测 2026-10-25 04:5x，0.2.4/0.1.49.2】同一前缀连发三轮只改结尾三个字："
    "7,343 token 三轮 reused=0 / 0 / 0，prompt_ms 15,327 / 15,021 / 15,219，cc parked 2->4、bytes 994->1,649 MB"
    "（缓存在存但从不恢复）；19,469 token 第 2 轮 reused=16,384，prompt_ms 40,140 -> 7,761（5.2x），但 read=3,085 仍重算。"
    "源码根因 generate.cpp:9907/9911：periodic 需 done>=pp_next_check(8192)，tail 需 pp_total-done>max(1,short_read)；"
    "7,343 时 done=7343<8192 且 pp_total-done=0 => 两个条件全不满足，永不 checkpoint；"
    "19,469 的 done 序列 8192/16384/19469，16384 后 pp_next_check=24576，故尾段 3,085 亦不存。"
    "修复：加 final_checkpoint = prompt_cache>0 && prompt_cache_every>0 && !multi_gpu && done>=pp_total && done>=1，"
    "并入同一 if 分支。checkpoint_at 的 as_tail 只影响淘汰优先级（!as_tail && L==tail_ckpt_len 时置 -1），不改 KV 内容；"
    "函数内按 ids.size()==L 去重，不会重复存。"
    "预期：7343 第二轮 15.0s -> ~0.5s（30x）；19469 第二轮 7.8s -> ~0.5s（15x）；M 档 21,827 第二轮 44s -> ~0.5s（88x）。"
    "代价：每次 prefill 多存一份约 100-300 ms + 300-500 MB 缓存。不改答案。",
    "待执行：改 1 行 + 重编 25min + 三档复测；同时报上游 #3950/#3667"])

hit87 = False
for ln in lines:
    if ln.startswith("P87\t"):
        f = ln.split("\t")
        f[5] = "REJECTED"
        f[9] = ("【2026-10-25 04:5x W786 作废】本行基线有两个缺陷：① 测于 --resident-experts 开着时，该参数已于 03:5x 从生产移除，"
                 "基线整体失效；② 本行记录的 74.76 ms/window 与其分项和（verify 56.36 + commit/emit 0.05 + draft 7.04 = 63.45）"
                 "差 11.31 ms（15%），从未被校验。=> 以 P91 的三档新基线取代。")
        f[10] = "已废：基线含 resident 且分项和差 15%；见 P91"
        ln = "\t".join(f)
        hit87 = True
    out.append(ln)

assert hit87, "P87 not found"
# 去掉可能已存在的 P91-P93，再追加
out = [ln for ln in out if not ln.split("\t")[0] in ("P91", "P92", "P93")]
out += [P91, P92, P93]
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("register updated, rows =", len(out))
