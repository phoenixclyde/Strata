# W915 · 三个"测试参数"为什么在生产里：一条是主动保留，一条是漏执行

> 2026-11-03 21:5x。**1 次重启**（约 4.5 min），生产已恢复健康。对象是 config 里那三个观测类 env：
> `STRATA_DECODE_TIMING` / `STRATA_SPEC_DEPTH` / `STRATA_VERIFY_NODES`（`STRATA_CKPT_MOVE_PARK` 是**功能项**，不算）。

---

## 0 结论

| env | 登记册 | 该不该在 | 实际 |
|---|---|---|---|
| `STRATA_DECODE_TIMING=1` | **P248** MEASUREMENT，生产已开 | **在**：它是 decode 窗口预算的唯一口径（`W873` 起所有窗口 ms 都从它来） | 保留 |
| `STRATA_SPEC_DEPTH=1` | **P251** MEASUREMENT，1（保留） | **在**：MTP 按深度接受率，`R44` 立 | 保留 |
| `STRATA_VERIFY_NODES=1` | **P252** MEASUREMENT，**REJECTED**，原文"**下次重启应移除**" | **不该在** | **今天 6 次重启都没执行** ⇒ 本条已按判决撤除 |

**为什么会在生产**：`ENV_PACKAGING_RULE.md:42-43` 明文分类——

```
| STRATA_CKPT_MOVE_PARK | 独立 | 只改搬运方式，不改比特，不与他项交互 |
| STRATA_DECODE_TIMING / SPEC_DEPTH / VERIFY_NODES | 独立（观测） | 只打印；合并会导致「为了看一个数被迫开三个」 |
```

⇒ 规则要求观测项**独立且可常开**，所以它们进生产是**按规则**，不是随手。问题只出在 P252：判决写了，执行没做。

---

## 1 代价：两个是"关掉也不省"，一个是"撤掉真省"

### 1.1 `STRATA_DECODE_TIMING` —— 计数是无条件的，env 只控制打印

`generate.cpp:17160-17166`：

```cpp
{
    const Clock::time_point tw3 = Clock::now();
    auto msd = [](Clock::time_point a0, Clock::time_point b0) { … };
    dt_run += msd(tw0, tw1); dt_commit += msd(tw1, tw2); dt_draft += msd(tw2, tw3);
    ++dec_windows; dec_T += merged ? 1 : T;
}
```

这个块**没有** `if (dec_timing)` 包裹；env 只在 `:16805` 和 `:17229` 控制 `fprintf`。
⇒ 每窗口 4 次 `Clock::now()`（vDSO 约 20–25 ns）≈ **80–100 ns**，对 ~48 ms 的窗口是 **0.0002%**；
**把 env 关掉不会变快**，只有删掉这段代码才会。

### 1.2 `STRATA_SPEC_DEPTH` —— 同一模式

`:17099` 的 `++dp_tested[d]; dp_ok[d] += d < a;` 在窗口循环里无条件执行；env 只在 `:17735` 控制打印。
两次 64 位加法，量级同上。

### 1.3 `STRATA_VERIFY_NODES` —— 整块在门内，而且**没有信息量**

`verify.cpp:2621-2655`：整段在图捕获后、`if (std::getenv("STRATA_VERIFY_NODES") != nullptr)` 之内，
遍历 `hipGraphGetNodes` 并对每个节点调 `hipKernelNameRefByPtr`。日志实测：

```
strata verify: the 1-token window graph has 2162 nodes: 2149 x type0; 13 x memcpy;
strata verify: the 3-token window graph has 2186 nodes: 2183 x type0; 3 x memcpy;
strata verify: the 5-token window graph has 2210 nodes: 2205 x type0; 5 x memcpy;
```

**65 条**这样的行，**节点名全部解析失败打成 `type0`** —— 正是 P252 判它"留着不下蛋"的原因：
`hipKernelNameRefByPtr` 在本机拿不到符号。撤掉它省的是**每次 capture 的整图枚举**（2162–2210 个节点 × 60+ 个图）。

---

## 2 已执行

1. 备份 `/data/strata-huihui-ud-iq4_xs.json.bak_w915`；
2. 从 config 的 `env` 删掉 `STRATA_VERIFY_NODES`（**config env 10 → 9 项**）；
3. 重启，`/health` 275 s 恢复；
4. 验证：新 run（`engine started 13:50:15` 之后）日志里 `window graph has` **0 条**（此前 65 条）；
5. 新 config 归档到 `deploy/params/generated/strata-huihui-ud-iq4_xs.json.w915`；
6. `PARAM_REGISTER` 的 **P252** 改为"0（已撤）"并附执行记录。

**没有**撤 `DECODE_TIMING` / `SPEC_DEPTH`：它们的计数是无条件的，撤了只丢观测、不省时间（§1.1/§1.2）。

---

## 3 举一反三：判决 → 执行 缺一个闭环

这次的根因不是"参数该不该开"，而是**登记册里有判决、配置里没执行，两者没人对账**。三条改进：

1. **lint 一条**：`PARAM_REGISTER` 里状态为 `REJECTED` / 值写作"建议撤 / 待撤"的项，若仍出现在 `params/generated/*.json` 的 `env` 里 ⇒ 报警。
   （现有 `tools/param_pair_lint.py` 只查"参数成对"，不查这一条。）
2. **重启清单**：任何一次重启前先跑上一条 lint——今天的 6 次重启就是"下次重启"的六次机会。
3. **观测项要定期算性价比**：`VERIFY_NODES` 属于"打印了但读不出信息"的典型——**打印内容为全 type0 时应当自动停用**，
   而不是等人工发现。可以给每个观测口配一句"若输出退化成常量则关闭"的判据。

---

## 4 复现

```bash
# 判决原文
grep -P "^P252\t" deploy/params/PARAM_REGISTER.tsv | cut -f3,6,10

# 代价（是否在门内）
sed -n '17160,17166p' src/program/generate.cpp     # DECODE_TIMING：无 if 包裹
sed -n '17099p'       src/program/generate.cpp     # SPEC_DEPTH：无 if 包裹
sed -n '2621,2655p'   src/core/verify.cpp          # VERIFY_NODES：整块在 if 内

# 撤除验证
docker exec strata166-407 awk 'NR>108911 && /window graph has/' /data/strata-huihui-ud-iq4_xs.log | wc -l   # → 0
```
