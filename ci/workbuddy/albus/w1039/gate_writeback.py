import io

P = "albus/w1039/reply.md"
s = io.open(P, encoding="utf-8").read()

# --- H1 + intro
old_h = s.split("\n", 1)[0]
new_h = ("# W1039 — port-all 按 b12180 重编：pa3 可复现、pa4 抓到死代码、pa5 把 DP4A 从 +6.8% 救到 −11%"
         "——**但数值门判否，不装机**")
s = new_h + s.split("\n", 1)[1]

old_i = ("> 一句话：**同一个开关，改一行调度，从\"慢 7%\"变成\"快 11%\"**；差的是量化放进哪个线程，不是指令本身。\n"
         "> 生产全程未换件，config 逐字节还原（`5e9b81e2…`），在产仍是 `b12180`。")
new_i = ("> 一句话：**同一个开关，改一行调度，从\"慢 7%\"变成\"快 11%\"**——然后数值门说这 1.8% 是拿 6.45 个百分点的 top-1 换的，**不换**。\n"
         "> 生产全程未换件，config 逐字节还原（`5e9b81e2…`），在产仍是 `b12180`；pa5 留在分支上、开关默认关。")
if old_i in s:
    s = s.replace(old_i, new_i, 1)
    print("intro updated")

# --- §三 table: add the two gate windows
old_t = """| ③ pa5 救法 | 09:55–10:04 | 2 次 | 90 s |

**前三窗口合计 重启 6 次 / 停机 264 s（129+135）**；救法窗口 重启 2 次 / 停机 90 s ⇒ 本回合合计 **重启 8 次 / 停机 354 s / 回滚 0 次 / 装机 0 次**。"""
new_t = """| ③ pa5 救法 | 09:55–10:04 | 2 次 | 90 s |
| ④ 数值门试跑 | 10:13–10:14 | 1 次 | 52 s |
| ⑤ 数值门正式 | 10:18–10:29 | 1 次 | 683 s |

**前三窗口合计 重启 6 次 / 停机 264 s（129+135）**；救法窗口 重启 2 次 / 停机 90 s；数值门两次 重启 1+1 次 / 停机 52 s + **683 s**
⇒ 本回合合计 **重启 10 次 / 停机 1089 s / 回滚 0 次 / 装机 0 次**。最长单次停机 **683 s**（数值门三臂独占 GPU）。"""
if old_t in s:
    s = s.replace(old_t, new_t, 1)
    print("§三 table updated")

# --- §四 denominator
s = s.replace("**395 条 / 已结 310 / 78.5%**（本轮 +8：`P445`–`P452`）",
              "**396 条 / 已结 311 / 78.5%**（本轮 +9：`P445`–`P453`）", 1)

# --- replace the closing section
old_c = """## 还差的一半：数值门（`P451` 保持 OPEN 的理由）

`deploy_gate` D4 要数值面（KL ≤0.0139 / top-1 ≥99%，或与 fp32 路径逐位相同）。本轮只测速度 ⇒ **pa5（`c639b60c5981267c8d82ee3a4b0750e8` / 43,475,584 B）没有装机**，在产仍是 `b12180`。
顺序定死：**数值门 → 装机**；数值不过直接回滚，不为了 1.8% 破质量线。"""
new_c = """## T7 数值门：判否（`P453`）

工具 `tools/quant_quality.py`（`run` / `compare`），5 段 × 999 位 = **4995 个配对点**，三臂：

| 臂 | 内容 | top-1 | KL | KL p99 | PPL（run / ref） |
|---|---|---|---|---|---|
| A vs Ab | pa5 + `ATTN_DP4A=0`，同 argv 两容器（**自一致地板**） | **100.00%** | **0.00000** | 0.0000 | 4.048 / 4.048 |
| A vs B | pa5 + `ATTN_DP4A=1`（开关） | **93.55%** | **0.04130** | 0.6109 | 4.057 / 4.048 |

- **地板是 0**（100% / 0.00000）⇒ 环境完全确定，0.0413 不是噪声，是开关本身；
- 两条判据**都破线**：KL 0.0413 是阈值 0.0139 的 **3.0 倍**，top-1 93.55% 差 99% 线 **6.45 个点**；
- 归因干净（技能 §6）：A 与 B **同 exe、只差一个 env** ⇒ 这一门归因到 `ATTN_DP4A` 一个开关，不是整栈。

**⇒ 判决：pa5 不装机。** 它用 1.78% 的 prefill 换掉 6.45 个百分点的 top-1 与 3 倍的 KL——按项目标尺这是负优化，
`P451` 从 OPEN 改 **DONE_NEG**，`deploy_gate` D4 保持红。代码留在 `gfx906/port-all`、开关默认关。

**偏差（必须写，否则会被当生产值）**：工具 FIXED 强制 `--expert-cache 1500` / `--pcie-frac 0` / `--adapt-every 100000` /
`STRATA_PREFILL_CPU_SHARE=0` / `STRATA_ROUTE_TAIL_SKIP=0`；**`--kv` 从工具默认 fp16 改为 `k8v4`** ——
否则 `kv_mode=0`、dp4a 派发条件（`kv_mode==3||kv_mode==1`，`qsa_decode_attn.cu:1146`）永不成立，这一门会测出「零差异」的假通过。
它测的是 **GPU MMQ 内核的 prefill 数值**，不含主机侧 CPU share。"""
if old_c in s:
    s = s.replace(old_c, new_c, 1)
    print("closing section replaced")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("len", len(s))
