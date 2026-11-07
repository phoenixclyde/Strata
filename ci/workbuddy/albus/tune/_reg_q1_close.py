# -*- coding: utf-8 -*-
"""收口 Q1：P32 补证据（三臂实测 + vmm 源码门 + 修正算术），新增 P88（decode 噪声口径）。"""
import io, time, shutil

REG = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
shutil.copy2(REG, REG + ".bak_q1c_" + time.strftime("%Y%m%d_%H%M%S"))

ADD32 = ("【W785-Q1 2026-10-25 三臂实测收口】A0 现行(resident 开/kv-grow 关) M 487.9tok/s prompt、decode 中位 54.6；"
         "A2 去 --resident-experts（kv-grow 仍关）489.1 / 66.0；A1 去 resident + --kv-grow 489.0 / 67.3。"
         "**三臂 expert_slots 全部 9901 / 22841 MiB，一个槽都没变**；引擎日志打出 "
         "'strata generate: --kv-grow is off (one GPU, a profile, the whole K/V in VRAM, every expert in RAM, no --batch, "
         "--vram-elastic or --peer-device)'。"
         "**根因（源码级，比实测更硬）**：`src/core/vmm.cpp:158/167` 把 HIP VMM 实现整段限定在 "
         "`defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)`；我们是 `STRATA_HIP_GFX906` 构建，落到 `:299-303` 的 "
         "`vmm_available() { return false; }`。同一处注释逐字：'Everything else (Metal, **gfx906**, ROCm older than 6): "
         "no virtual memory, the elastic K/V stays off.' => **kv-grow 在 gfx906 上不可能开启**，与参数怎么配无关。"
         "**同时修正原证据的算术**：816 B/cell 是**每层**（`kv_pool_bytes` 的 rows = pages x page_size x n_head_kv，"
         "每层一个 pool；hybrid 公式 2 x (256 + 16 + 144) = 832 B），P32 原文把它当成整机总量算出 214 MiB / 93 槽，"
         "真实总量应是 layers x 816 B/cell（W782 引用的源码注释为 262K 上下文 3.35 GiB）。算术虽错，"
         "**结论不变且更强：不是收益太小，而是根本不可达**。"
         "另：`--expert-cache` 的 VMM 路径（expert_cache.cpp:509 `g_cache_vmm && vmm_available()`）同样不可用。")

ADD88 = ("【W785-Q1 2026-10-25 实测发现，方法论】同一条 21,827 token 的 M 档、每臂 5 runs，`decode_tps` 中位数在 "
         "**54.6 / 58.6 / 60.1 / 61.3 / 66.0 / 67.3** 之间摆动（±10%），而 `prompt_tps` 同时在 **486.6-489.1** 之间"
         "（±0.3%）。原因：bench 的 nonce 带时间戳 => 每次 prompt 略有不同 => 生成文本不同 => **spec 草稿接受率不同** => "
         "decode tok/s 随文本波动。"
         "=> 纪律：**decode 的 <5% 级结论不得用 5 runs 的 tok/s 中位数判定**；改用 (a) `STRATA_DECODE_TIMING=1` 的 "
         "ms/window 分阶段值（P87 口径），或 (b) >=10 runs 并报中位数与四分位。"
         "此前凡以 5 runs decode 中位数下的 'decode +2~5%' 结论（含 P78 HC_Q8 的 decode 部分）都应视为**未定**，"
         "其 prompt 部分（三档一致 +0.6%）不受影响。")

rows = io.open(REG, encoding="utf-8-sig").read().splitlines()
out = []
for ln in rows:
    if ln.startswith("P32\t"):
        f = ln.split("\t")
        f[9] = (f[9] + " || " + ADD32) if len(f) > 9 else ADD32
        f[10] = "不采纳/不可达：gfx906 构建无 VMM（vmm.cpp:299 return false），三臂实测槽位不变"
        ln = "\t".join(f)
    out.append(ln)

out = [ln for ln in out if not ln.startswith("P88\t")]
out.append("\t".join(["P88", "REF", "decode 指标口径（噪声边界）", "5runs=±10%", "measure", "REFERENCE",
                      "-", "-", "-", ADD88, "decode 判据改用分阶段 ms 或 >=10 runs"]))
io.open(REG, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("rows:", len(out))
