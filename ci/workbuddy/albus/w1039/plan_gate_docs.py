import io
import re

PL = "deploy/W832_OPT_PLAN_V2.md"
t = io.open(PL, encoding="utf-8").read()

ADD = """
**八、数值门判否：pa5 不装机（`P453`）。** 工具 `tools/quant_quality.py` 的 `run`/`compare`，5 段 × 999 位 = **4995 点**，三臂 A/Ab/B。

| 臂 | top-1 | KL | KL p99 | PPL |
|---|---|---|---|---|
| A vs Ab（自一致地板） | **100.00%** | **0.00000** | 0.0000 | 4.048 / 4.048 |
| A vs B（`ATTN_DP4A=1`） | **93.55%** | **0.04130** | 0.6109 | 4.057 / 4.048 |

地板 0 ⇒ 环境确定，0.0413 是开关本身；两条都破线（KL 3.0× 阈值、top-1 差 6.45 点）。
**判决：`P451` 由 OPEN 改 DONE_NEG，pa5（`c639b60c`）不装机**，代码留分支、开关默认关，`deploy_gate` D4 保持红。
**必须照抄的偏差**：`--expert-cache 1500` / `--pcie-frac 0` / `--adapt-every 100000` / `STRATA_PREFILL_CPU_SHARE=0` /
`STRATA_ROUTE_TAIL_SKIP=0`，且 **`--kv` 由工具默认 fp16 改成 `k8v4`**（否则 `kv_mode=0`、派发条件 `qsa_decode_attn.cu:1146` 永不成立，
这一门会假通过）。**归因边界**：A/B 同 exe 只差一个 env ⇒ 归因到单个开关，不是整栈。
**代价**：本回合停机累计 10 次 / 1089 s，最长单次 683 s。
"""

anchor = "下一步顺序固定：**数值门 → 装机**；数值不过就直接回滚到 `b12180`，不因为 −1.8% 破质量线。"
i = t.find(anchor)
if i > 0 and "**八、数值门判否" not in t:
    j = t.find("\n---", i)
    t = t[:j] + "\n" + ADD + t[j:]
    print("plan §八 appended")

t = re.sub(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1039 校正", "**396 条 / 已结 311 / 78.5%**（W1039 校正", t, count=1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(t)
print("plan updated, len", len(t))
