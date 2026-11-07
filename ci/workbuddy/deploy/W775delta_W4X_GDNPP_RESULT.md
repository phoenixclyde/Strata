# W775delta W4x 第 2 车 ---- `STRATA_GDN_PP=2` A/B 实测结果

车 tag=`gdnp` ｜ **13:52:59 -> 14:08:17**（15m18s）｜ ABBA x5 ｜ serve 同构 ｜ **0.1.42** ｜ `Z0=off`

## 1 靶与可及性

| 项 | 值 |
|---|---|
| 靶 | `STRATA_GDN_PP=2`（`P41` §4 族；上游 `arch_defaults.cpp:39` 注释 *"two columns per lane: **64K prompt +2.9%** (stream A, round 2)"*） |
| 编译期 | 二进制含该字面量；W17a 守卫 = `#if defined(__HIPCC__)` |
| 运行期 | **arch_defaults 表项** => gfx906 在 `arch_defaults.cpp:32` 已 `return t`（**空表**）=> **不自动设，须显式** |
| 同族前例 | 表内数值全是 **gfx1151/Aurora** 的；同族已测成员在本卡为负（`EXPERT_V2` -5.60% / `SH_STREAM` -0.13%） |

## 2 车体断言（车 transcript 逐字）

```
ARM blk1 env=(none)              changed=['log', 'port']       <- A
ARM blk2 env=STRATA_GDN_PP=2     changed=['env', 'log', 'port'] <- G
ARM blk3 env=STRATA_GDN_PP=2     changed=['env', 'log', 'port'] <- G
ARM blk4 env=(none)              changed=['log', 'port']       <- A
ARM DT   env=STRATA_GDN_PP=2     changed=['env', 'log', 'port']
CFG_OK
engine environ opt-ins: STRATA_PREFILL_CPU_SHARE=0 STRATA_GDN_PP=2 ...   (x3：blk2/blk3/DT)
engine environ opt-ins: STRATA_PREFILL_CPU_SHARE=0 ...                   (x2：blk1/blk4)
```

=> **生产同构**（A 臂与生产 config 只差 `log`/`port`，`args` 逐字不动）；**G 臂运行期 env 在位**（3 次有、2 次无，与 ABBA 的 3 G / 2 A 吻合）。

## 3 结果（20 点全表见 `deploy/tmp/_gdnp_out/`）

| 口径 | A | G | **delta** | A spread | G spread |
|---|---|---|---|---|---|
| **decode `ms/step`** 全 10 点 | 22.711 | 22.134 | **-2.54%** | 41.0% | 31.6% |
| **decode `ms/step`** 温 8 点 | 21.552 | 21.188 | **-1.69%** | 25.3% | 16.7% |
| **prefill `ms/tok`** 全 10 点 | 2.255 | 2.252 | **-0.14%** | 6.9% | 6.8% |
| **prefill `ms/tok`** 温 8 点 | 2.226 | 2.223 | **-0.13%** | **0.8%** | **0.4%** |

**正确性**：固定 prompt 的 parity **5/5 逐位相同**（`5a4b25aaed25c2ee1b74de72dc03c14e` = `md5("391")`）=> **不改答案**。

### 判定：`exact but no gain`，不采纳

- **本开关的标称轴是 prompt 侧**（上游写 "64K prompt +2.9%"）=> 看 **prefill `ms/tok`**：delta **-0.13%**，而 prefill 的臂内 spread 只有 **0.4-0.8%** => **在噪声内，未复现**。
- decode 侧 delta **-1.7~-2.5%**（G 略快）**小于** decode 的臂内 spread（16.7-31.6%）=> 按项目纪律**不判真实差异**。
- 与上游自己那句限定一致：**该表数值来自 gfx1151/Aurora**，`arch_defaults.hpp:3-6` 逐字 *"on by default on that architecture and **nowhere else**"*。

## 4 方法论收获（可直接用于后续车）

1. **prompt 侧开关应走 prefill 口径**：本车 prefill 的臂内 spread 仅 **0.4-0.8%**，而 decode 是 **16.7-41%** ---- 分辨力差 **20-50 倍**。
   => 凡"改 prompt 路径"的开关（`GDN_*` / `PF_*` / `PREFILL_*`），主口径用 `read_ms/read_tok`，别用 decode 去判。
2. **`r0` 是热机项，两臂都慢**（decode 25.8-28.2 vs 18.9-24.4；prefill 2.36-2.37 vs 2.22）=> 每块丢 `r0` 已是标准做法（本车沿用）。
3. **parity 是低成本高价值的正确性门**：本车 5/5 逐位相同，直接排除"改答案"这一整类风险。

## 5 `P41` 族进度

| 开关 | 结果 | 出处 |
|---|---|---|
| `STRATA_Q8_PACKED` | exact but no gain（+1.87 GiB VRAM） | `W775delta_W4X_Q8PACKED_RESULT.md` |
| **`STRATA_GDN_PP=2`** | **exact but no gain**（本车） | 本件 |
| `STRATA_ATTN_LANECELL` | **未测**（且与 `P55` swizzle 互斥；`P55` 在 `k8v4` 不可达 => 互斥实际不成立） | `W775delta_R4_P41_SCREEN.md` |

=> **族内已测 2 个，均为 `exact but no gain`**；本卡仍未出现"§4 族在本卡兑现"的样本。

## 6 产物

- 4 块 JSON：`deploy/tmp/_gdnp_out/blk{1,2,3,4}.json`（各 5 runs，含引擎自报行原文）
- 车 transcript：`deploy/tmp/_gdnp_about.txt`（102 行）
- 解析脚本：`deploy/tmp/_gdnp_parse.py` / `_gdnp_fetch.py`
- 核验留档：`deploy/params/_verify_20261011_141132.txt`（4,888 B / `f319f8e9a42918b34b856e4bb49fef6d` / CR=0）---- **PASS=26 FAIL=0**
