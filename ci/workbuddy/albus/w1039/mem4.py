import io

P = ".workbuddy/memory/2026-11-07.md"
ADD = """
### W1039 数值门（10:10–10:30）pa5 判否：1.8% 的速度换 6.45 点 top-1

- **三臂**（工具 `tools/quant_quality.py run/compare`，5 段 × 999 位 = 4995 点，`--kv k8v4`）：
  - A vs Ab（自一致地板，同 argv 两容器）：top-1 **100.00%** / KL **0.00000** / PPL 4.048 vs 4.048 ⇒ 环境完全确定；
  - A vs B（`ATTN_DP4A=1`）：top-1 **93.55%** / KL **0.04130**（p99 0.6109）/ PPL 4.057 vs 4.048 ⇒ **两条都破线**（KL 3.0× 阈值 0.0139、top-1 差 6.45 点）。
- **判决：pa5 不装机**，`P451` OPEN → **DONE_NEG**，代码留 `gfx906/port-all`、开关默认关，`deploy_gate` D4 保持红。
- **技能偏差（必须写）**：工具 FIXED 强制 `--expert-cache 1500`/`--pcie-frac 0`/`--adapt-every 100000`/`CPU_SHARE=0`/`ROUTE_TAIL_SKIP=0`；**`--kv` 要手动改成 k8v4**，否则 `kv_mode=0`、派发条件（`qsa_decode_attn.cu:1146`）永不成立 ⇒ 会假通过。归因边界：A/B 同 exe 只差一个 env。
- **门的新增（报告漂移）**：`tools/report_consistency.py` 加了「四、进度 的分母必须等于账本派生值」，负例自测（写 386/302 应 FAIL）通过。起因：一个回合里分母 386→391→393→395→396 一路改，而 report_lint 只查格式、report_depth 只数 R 号，**没有人比对**。
- **停机**：两个门窗口 52 s + 683 s，本回合累计 10 次 / 1089 s。
"""
with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD)
print("mem appended", len(ADD))
