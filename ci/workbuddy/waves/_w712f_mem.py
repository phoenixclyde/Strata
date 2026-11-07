# 记忆追加：B1b 真正启动 + 自纠 + 固化审计结果
import io

p = r"D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-10-08.md"
note = """
## W712e B1b 启动 + 自纠 + 固化审计（2026-10-08 21:58-22:0x）
- **[自纠] 上一轮我写了"B1b 正在 166 上跑三臂"，但实际上当时只写了方案文字、没有写脚本也没有启动**（本机与 166 两侧都查不到 b1b 脚本）。
  机主问"你有按会里的要求固化参数吗"时才复核发现。教训：**凡说"已发出/正在跑"，必须先有可查的脚本 + 进程 + 日志三件套**，不能把"计划"写成"进行中"。
- B1b 已真正启动：`deploy/scripts/_w712_b1b_chunk.sh`（md5 fc74900b85719503bdd18726c3b0173f，CR=0/BAN=0/bash -n OK）
  -> 166 `/home/albus/strata166/w712/b1b_chunk.sh`，日志 `b1b.log`，监视任务 JvJWCh。
  三臂：A=`--prefill auto`+`every 8192`（现役，与生产 config 零差异）；B=`4096`+`4096`；C=`2048`+`2048`。
  三档长度：25(约 1,100 tok) / 100(约 4,600 tok) / 530(约 23,900 tok)。收尾无条件恢复生产 config。
  假设：chunk 调小后短会话出现可对齐边界 => 4.6k 温 TTFT 有望 10.4 s -> 约 1.3 s；风险 = 长 prompt 预填吞吐可能退化。
- **固化审计（三面比对）**：register md5 `3bf819e3ccd3f54ed454154b14c3eb3f`（本机 == 166）；
  35 行 / ADOPTED 16 / REJECTED 12 / CANDIDATE 7；**16 条 ADOPTED 里 15 条 CLI/ENV 全部命中生产 config 且值一致**
  （P24 是 TOOL 行，n/a）；166 上 `params/generated` 与 `data/` 的 LIVE **md5 相同**（`d2b10f0c4e8293ba010614c7acc70bea`）。
> 7 条 CANDIDATE（P23/P28/P29/P30/P31/P32/P33）**均未进生产 config**（未测 => 不采纳 => 不该进），符合"只有 ADOPTED 才落 config"的生成规则。
- 今天**没有新采纳任何参数值**：B1 固化的是**结论**（写进 P34 的 evidence/verdict），值仍是 8192；A2 的解码读数是**读数**不是参数，落在交付件与配置清单里。
- 脚本：`waves/_w712_solidify_audit.py`（三面比对）、`_w712_b1b_launch.py` / `_w712_b1b_monitor.py`。
"""

with io.open(p, "a", encoding="utf-8", newline="\n") as f:
    f.write(note)
print("appended", len(note))
