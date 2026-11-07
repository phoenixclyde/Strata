#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W940 register: R84 (dot8 kernel implementation) + report-standard + objcopy discipline."""
import io, os

D = "D:/workbuddy_space/strata_ws/deploy"
P = os.path.join(D, "PROGRESS.tsv")

row = ["B5本机缺口", "R84",
       "dot8 接进 MMQ 内核（仅 gate/up 的 Q4_K 实例）：权重 ^0x88888888 + 修正项 8*sum(x)，激活 Q8_1 -> int4；down(Q5_1/Q8_0) 保持 dp4a",
       "W940 §3", "count", "1", "0", "OPEN",
       "**W940 立（2026-11-04 13:2x）**：机主问「方案里含 dot4/dot8 移植吗」，审计发现**缺口** —— 与 dot8 相关的只有 R73(验证 DONE) 与 R74(精度门 OPEN)，"
       "「改内核」这一步没有任何条目。**现状实测**（0.1.56 fatbin，68 个 code object）：`v_dot4_i32_i8` **146,604 条**（0.1.55 是 130,808，+12.1%）、"
       "`v_dot8_i32_i4` **0 条**；源码 `sdot8`/`__builtin_amdgcn_sdot8` 在 strata 与 llama.cpp **各 0 处**（`dot8` 命中的 4 个文件是 FP32 辅助函数名，W909 已核）。"
       "**dot4 不是移植项**：它一直在跑，问题是供给率 4.55/21.52=21%，不是有没有。**R84 范围**：只 gate/up 的 Q4_K（20.4% of prefill），"
       "down 的 Q5_1 是 5-bit 塞不进；**前置** R74 的 KL≤0.005（分辨率 0.0032）；**路径断言** Q4_K 实例内 `v_dot4` 应减半且出现 `v_dot8`；"
       "**上限** 端到端 3.22%（W928），不预设收益。**依据复用**：`vecdotq.cuh` md5 与 W924 当时那份逐字节相同（llama.cpp 固定 3cf03257、rebase 未动 third_party/ggml）"
       "⇒ W924 的三段配比 5,184/1,437/1,204/1,064/824 对 0.2.10 仍成立，无需重算",
       "W940;W927;W924"]
with io.open(P, "a", encoding="utf-8") as f:
    f.write("\t".join(row) + "\n")
print("R84 appended")

r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()

# 1) 重开区后追加 R84 的说明
anchor = "> **依据分级（此后所有条目强制标注）**"
add = ("> **dot4 / dot8 的定性与缺口（`W940`）**：**dot4 = 现役 146,604 条，不是移植项**（差距在供给率 21%，不在指令）；"
       "**dot8 = 0 条**，只有 R73 验证 + R74 精度门，**缺「改内核」这一步 ⇒ 已立 R84（仅 gate/up 的 Q4_K，down 保持 dp4a）**。\n"
       "> \n")
assert anchor in s
s = s.replace(anchor, add + anchor, 1)

# 2) 纪律 16
a2 = "> **方法纪律追加（`W938` 2026-11-04 12:5x · 上游同步）**"
rule = ("> **方法纪律追加（`W940` 2026-11-04 13:2x · 只读铁律）**：⑯ **任何分析工具对生产二进制必须只读** —— "
        "`objcopy` / `strip` / `patchelf` / `llvm-strip` 在**只给输入不给 `-o`** 时会把结果**写回输入文件**。"
        "本轮实测：`llvm-objcopy --dump-section=.hip_fatbin=f.bin /data/bin/strata-0.1.56` 把磁盘件从 42,924,432 改成 42,898,432（md5 ae085365→7afc2bbf），"
        "而进程仍持旧 inode ⇒ 服务无感、账本失真、下次重启静默换版本。**改法**：先 `cp` 到 /tmp，或显式 `-o`。\n"
        "> ⑰ **四件套第一项固定 8 个字段**（见 `deploy/REPORT_STANDARD.md`），其中第 8 项 `disk/build/running 三方 md5 一致` 是硬要求 —— "
        "缺它就会漏掉 ⑯ 这类污染。\n>\n")
assert a2 in s
s = s.replace(a2, rule + a2, 1)

# 3) 队列插入 R84（依赖 R74）
old_seq = [l for l in s.split("\n") if l.startswith("> **执行顺序（2026-11-04 13:0x")]
if old_seq:
    new = ("> **执行顺序（2026-11-04 13:3x 修）：R61（独立进程拿 PMC）→ R60（stream-k A/B）→ R63（readfirstlane）→ R72（reserve 600）→ "
           "R64（Q·K int8，窄化）→ R81（窗口 12 归因）→ R79（重启后会话）→ R80（gate provenance）→ **R74 → R84**（W4A4 门 → dot8 内核）→ "
           "R49 → R50 → R30′")
    s = s.replace(old_seq[0], new, 1)
    print("queue updated with R84")
io.open(r, "w", encoding="utf-8").write(s)
print("W832 updated")
