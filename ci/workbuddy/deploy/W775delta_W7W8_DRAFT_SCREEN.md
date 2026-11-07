# W775delta W7/W8 ---- 草稿/查找面源码级判定（`--suffix-draft` / `--lookup-chain` / `DraftPolicy.kShape`）

> 触发：`W750 §4` 的 **W7**（`P42`：`--lookup-chain` / `--suffix-draft` / `--kv` 四档）与 **W8**（`DraftPolicy.kShape` 标定）。
> 做法：只读 0.1.42 源码树（`deploy/tmp/src142/`）+ **零成本只读运行期取证**（`GET /metrics`）。时间 2026-10-11 19:4x。**0 发车、生产未动。**

## 0 结论（先行）

1. **[重大事实更正] 我们的 `--spec 4` 名不副实。** `--suffix-draft` **默认 = 3**（`generate.cpp:652`），而我们**未设 `--mtp-max-t`** => `generate.cpp:2406-2408` 在启动时把
   **`mtp_max_t = 4`、`spec = min(4+2, 8) = 6`**。
   **运行期硬证**（2026-10-11 19:4x 现取）：`GET /metrics` 的 `engine` 段 = `"spec": 6, "mtp_max": 4, "lookup": 3`（落档 `deploy/tmp/_audit5_metrics_engine.json`），
   而引擎 cmdline（PID 12）逐字仍 `--spec 4 ... --mtp-window 8192 --resident-experts`（无 `--mtp-max-t`）。
2. **`--suffix-draft` 不是"未采用的开关"**：它**默认开着并在生产生效**（`lookup=3`）=> `P42` 把它与 opt-in 的 `--lookup-chain` 并列成"CANDIDATE（未测）"**不准确**。
3. **`--lookup-chain K` 在 `K <= 2` 时是空操作**：`spec = max(spec, min(mtp_max + K, 8))` = `max(6, min(4+K, 8))` => `K=1/2` => **6（不变）**；`K=3` => **7**；`K>=4` => **8**。
4. **`DraftPolicy.kShape` 不是参数面旋钮**：`draft_policy.cpp:12` 是**编译期 `constexpr` 表**，作用只是"尚未实测过的窗口尺寸"的**先验形状**，运行期被实测 EMA（`cost_[]`）覆盖 => 「标定 `kShape`」在参数面**无靶**。
5. **处置**：W7 **判不发车**（`--suffix-draft` 已生效；`--lookup-chain` 需 `>=3` 且无独立收益出处 + 观测面弱）；W8 **转 REFERENCE**（非旋钮）。

## 1 源码事实（0.1.42 逐字 + 行号）

```cpp
// src/program/generate.cpp:652-658   （默认值）
int suffix_draft = 3;
/// --lookup-chain K (opt-in, 0 = off): prompt lookup CHAINED after the MTP's proposal. ...
int lookup_chain = 0;
int lookup_chain_min = 3;
// :654
int mtp_max_t = 0;                                    // 0 = --spec
// :1994
else if (a == "--lookup-chain") o.lookup_chain = std::clamp(std::atoi(next("--lookup-chain")), 0, 7);
// :2404-2413   （启动期的两次改写 ---- 本案的关键）
// Prompt lookup (the suffix drafter, on by default) ... Code edits +6-11%, ordinary text unchanged
// (bench/results/2026-09-27-spec). --suffix-draft 0 turns it off.
if (o.suffix_draft > 0 && o.spec >= 2 && o.mtp_max_t == 0) {
    o.mtp_max_t = o.spec;
    o.spec = std::min(o.spec + 2, 8);                 // kVerifyMaxT
}
if (o.lookup_chain > 0 && o.spec >= 2) {
    if (o.mtp_max_t == 0) o.mtp_max_t = o.spec;
    o.spec = std::max(o.spec, std::min(o.mtp_max_t + o.lookup_chain, 8));   // kVerifyMaxT
}
```

```cpp
// src/spec/draft_policy.cpp:12   （kShape 是编译期常量表，9 项索引 0..8）
constexpr double kShape[DraftPolicy::kMaxT + 1] = {0.0, 1.0, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6};
// :47 / :50   （唯一用途：给"未实测尺寸"推算成本）
num += w * cost_[u] * kShape[t] / kShape[u];
return den > 0 ? num / den : kShape[t];
```

- `DraftPolicy` **确实在生产路径上被使用**：`generate.cpp:8850` `DraftPolicy policy(S);` + `:11122/:11540/:12694` `policy.choose(...)`
  => 它不是测试件，但它的**代码**（含 `kShape`）不可由参数配置。
- `draft_policy.hpp` 头部逐字：*"the policy learns both sides online and compares expected committed tokens per millisecond"*
  + *"sizes not seen yet are scaled from seen ones by a prior shape"* => `kShape` 就是那个 "prior shape"。

## 2 运行期硬证（本波新取，只读）

| 面 | 值 | 来源 |
|---|---|---|
| 引擎 cmdline | `--spec 4 ... --mtp-window 8192 --resident-experts`（**无** `--mtp-max-t`、**无** `--lookup-chain`、**无** `--suffix-draft`） | 容器 PID 12 `/proc/12/cmdline` |
| **引擎上报的实际值** | **`spec=6` · `mtp_max=4` · `lookup=3`** | `GET /metrics` -> `engine` 段（落档 `tmp/_audit5_metrics_engine.json`） |
| 同段其它 | `kv=k8v4` · `kv_resident=0` · `expert_slots=9761` · `expert_cache_mib=22516` · `context=262144` · `spec_min_p=0.70` · `pcie_frac=0.20` | 同上 |

=> `:2406-2408` 那条改写**确已发生**（`4 -> mtp_max 4 / spec 6`），且 `lookup=3` 就是默认的 `--suffix-draft`。
> 取证路径备注：该 `INFO logit_bias=... spec=%d mtp_max=%d lookup=%d` 行是 `std::printf`（stdout）=> 进 serve 的 pipe（`serve/server.py:684` 解析进 `self.info`），**不写 stderr 日志** => 直接 grep `.log` 找不到；正确入口是 `GET /metrics`。

## 3 影响面（必须记住）

1. **`--spec` 不是孤立旋钮**：只改 `--spec` 会**连带**改 `mtp_max_t`（`:2407`）。若要单变量，必须**同时**给 `--mtp-max-t` 钉住。
2. **`--spec 4` 的历史读数口径**：`W760`（`--mtp-window` 8192 的 +3.39%）等车若以 `--spec 4` 为臂，需注意实际 `spec=6`（**同构两侧**则结论不受影响，但描述要写准）。
3. **`--lookup-chain` 的有效域**：本机（`spec` 已是 6）下 `K<=2` 无变化；`K=3 -> 7`、`K>=4 -> 8`。
4. **`--suffix-draft` 是"已在跑"的机制**：它的收益自述只覆盖 **代码编辑类请求**（*"Code edits +6-11%, ordinary text unchanged"*，上游 `bench/results/2026-09-27-spec`）=> 对**我们的典型负载**（长冷 prompt、单轮）**无上游数字**。

## 4 处置建议

| 项 | 现值 | 建议 |
|---|---|---|
| `P42` `--suffix-draft` | 与 `--lookup-chain` 并列 CANDIDATE | **verdict 追加**：默认已开、生产 `lookup=3` 在生效；**不是待采纳项** |
| `P42` `--lookup-chain` | CANDIDATE | **不发车**（`K<=2` 空操作；`K>=3` 仅抬 verify 上限，无独立收益出处；decode 轴 spread 16-41% 分辨力弱）。verdict 追加本条 |
| `P42` `--kv` 四档 | 已由 `W767-W770` 建门（`P50`/`P51`） | 不涉本轮 |
| **`DraftPolicy.kShape`（W8）** | 未登记 | **新增 `P72` = REFERENCE（非旋钮）**：编译期 `constexpr` 表 + 运行期被 EMA 覆盖 => 参数面无靶 |
| `--spec` 的连带改写 | 未登记 | **写入 `W750` §0.0 的"已收敛"行**（重要事实，防后续车踩） |

## 5 复现

```bash
sed -n '650,660p;1990,1996p;2400,2416p' deploy/tmp/src142/src/program/generate.cpp
sed -n '1,20p'     deploy/tmp/src142/include/strata/spec/draft_policy.hpp
sed -n '10,14p;44,52p' deploy/tmp/src142/src/spec/draft_policy.cpp
# 运行期：ssh albus@192.168.50.166 'curl -s http://127.0.0.1:8090/metrics' | python3 -m json.tool | head -30
#   => engine 段含 "spec": 6, "mtp_max": 4, "lookup": 3
```

## 6 局限

- 本件**未发车**：W7 的收益判断基于「上游自述的适用面（编辑类）+ 本项目观测面（decode spread 16-41%）」，**未做实车**。
- `--lookup-chain` 的「不改答案」来自 `draft_policy.hpp` 逐字 *"It only chooses which drafts to verify: the output is unchanged"*，**本机未实测**（若将来发车，parity 门不可省）。
- `kShape` 的"运行期被覆盖"是从 `draft_policy.cpp:47/50` 的分支逻辑推出（`den > 0` 时用实测加权、否则回落先验），**未做数值实验**。
