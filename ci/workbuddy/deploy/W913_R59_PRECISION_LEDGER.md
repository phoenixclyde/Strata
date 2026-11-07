# W913 · R59 精度账：TUNED 包的代价**低于引擎自身的跨进程噪声**

> **【AUDIT24 P2 · 2026-11-04】§6 的算术注记**：`arch_defaults.cpp` 那五个 KL
> （0.0011 / 0.0004 / 0.0008 / 0.0026 / 0.0171）是**逐开关单点**，加总 **0.0220**，而整包实测 **0.002005**
> —— 相差 11 倍，**既不能相加，也不能与整包噪声底 0.0032 直接比大小**。本件末段已自述"不能当作整机已验证"，
> 这里补一条算术注记，防止被后续引用成"五个开关总代价 2.2%"。

> 2026-11-03 21:0x–21:2x。**6 次重启**（每次约 4–4.5 min 停机，累计约 26 min）。生产已恢复原配置。
> 结论先说：**门的均值判据过了（KL 0.0020 ≤ 0.005、argmax 12/12），但效应比噪声底还小 ⇒ 真正的结论是"测不出来"，
> 而顺带挖出的"引擎跨进程不确定"比这件事本身更重要。**

---

## 0 结果表

| 对照 | 含义 | mean KL | median | max | argmax 一致 |
|---|---|---|---|---|---|
| 同进程，两次相同请求（TUNED=1） | 仪器自身噪声 | **0.000000** | 0 | 0 | 12/12 |
| 同进程，两次相同请求（TUNED=0） | 同上 | **0.000000** | 0 | 0 | 12/12 |
| **跨进程，同配置**（TUNED=1 两次） | **噪声底** | **0.003239** | 0.000718 | 0.016604 | 12/12 |
| **TUNED=1 vs TUNED=0** | **待测效应** | **0.002005** | 0.000704 | 0.011209 | 12/12 |

⇒ **效应（0.0020）< 噪声底（0.0032）**，中位数几乎相同（0.000704 vs 0.000718）。
在这套引擎上，"打开 7 项 rounding 开关"造成的分布位移，**和换一个进程重跑同一配置造成的位移，大小一样**。

---

## 1 仪器怎么来的（第一版是错的，记下来）

### 1.1 第一版：API 的 top-20 logprobs

服务端支持 `logprobs=true, top_logprobs≤20`（`server.py:4041`，`top_logprobs()` 上限 20），
引擎侧对应 `logprobs=K` 的 `LP` 行。四个 prompt × 96 token，三臂（A1 / B / A2）。

**问题**：贪心生成一旦在某个位置分叉，后面每个位置都在**不同上下文**里比较，KL 不再是 rounding 差，而是两句话的差。
实测 A1 vs A2（同配置）在 p2 的第 43 个 token 就分叉，于是全序列 KL 均值 4.82、argmax 只有 79.4% —— 纯属污染。

**修法**：只统计**首个分叉点之前**的位置。重算后：
- 噪声底（A1 vs A2）：mean **0.00903**，median 0.00003，p95 0.0482，max 0.287（279 个位置）
- 效应（A1 vs B）：mean **0.01270**，median 0.00008，p95 0.0782，max 0.311（199 个位置）

两者只差 1.4×，且都被少数大值主导 ⇒ **这个仪器的分辨率不够**。

### 1.2 第二版：全词表首窗 logits（作者预留的入口）

源码 `generate.cpp:18784` 有一段：

```cpp
// Diagnostics: the first window runs the prompt's last token over the state the prompt path left …
// A native pack never runs the per-token loop --dump-logits reads; this is where prompt paths can be
// compared by output.
if (const char* fl = std::getenv("STRATA_DUMP_FIRST_LOGITS")) {
    std::vector<float> row((size_t) ver.vocab());
    std::FILE* f = ver.copy_logits(0, row.data()) ? std::fopen(fl, "wb") : nullptr;
```

⇒ **`--dump-logits` 在 native pack 下永远写不出东西**（`generate.cpp:8041` 的注释就写着
"a native pack never reaches the per-token dump site"，不是 bug）。正确入口是 `STRATA_DUMP_FIRST_LOGITS`：
每请求一个 **248,320 维全词表 logits**（993,280 B，无头），首窗、prompt 一致 ⇒ 没有分叉问题，KL 是精确的。

**踩到的坑**：引擎给文件加序号后缀（`first.bin.0`、`.1`…），不是覆盖同一个路径。第一版脚本按固定路径搬文件，扑空。

---

## 2 为什么会有"跨进程噪声"——这才是真发现

同进程内，两次相同请求的 logits **逐位相同**（KL 精确 0，两臂都是）。所以不确定性不在 kernel 的浮点归约，
而在**进程状态**。最可能的机制，引擎自己的日志就写着：

```
strata generate: the GPU computes the experts in the cache; it rounds differently from the CPU,
                 so a reply can differ slightly from a run without the cache (same quality)
```

专家 cache 的**驻留状态**（哪些专家在 GPU、哪些走 host/CPU）随预热与预取时序变化，而 GPU 与 CPU 的舍入不同
⇒ 同一个配置、不同进程，logits 就会有 ~0.003 的 KL。这也解释了 `W899 §7.11` 里"同配置 A 臂跑两次文本哈希不同"。

**后果（必须写进方法）**：
1. 任何 **< 0.003 KL** 的端到端精度断言，在这套引擎上**不可测**；
2. R60（stream-k 改求和序）的精度门必须按这个分辨率来定，否则会把噪声当效应；
3. 想要更高分辨率，只能先**钉死驻留**（固定 cache 内容/关掉 prompt 路径借用槽位），而不是加更多 prompt。

---

## 3 判定

| 判据（R59 原定） | 实测 | 判定 |
|---|---|---|
| KL ≤ 0.005 | mean **0.002005**（median 0.000704，max 0.011209） | **过**（均值口径） |
| top-1 ≥ 99% | **12/12 = 100%** | 过 |
| — | 效应 0.0020 < 噪声底 0.0032 | **分辨率不足，不能宣称"代价很小"** |

⇒ R59 **DONE**，但结论写成两句：**①TUNED 包没有出现超过门的精度损失（均值 0.0020、argmax 全同）；
②这个 0.0020 与"换个进程重跑"的 0.0032 不可区分，所以它更像"噪声的一部分"，而不是"可忽略的真实代价"。**
后续任何"精度换速度"的条目（R60/R64）都要附带这条分辨率说明。

**样本量**：12 个短提示、每个只取**首个生成位置**。不做长生成逐位置 KL —— 因为一旦分叉就回到 §1.1 的污染。

---

## 4 操作记录（含生产状态变化，必须披露）

1. 备份 `/data/strata-huihui-ud-iq4_xs.json` → `.bak_w912`；
2. **6 次重启**：B(TUNED=0) → 恢复A → A+dump → TUNED=0+dump → TUNED=1(跨进程) → 最终恢复；
   每次 `/health` 恢复 230–275 s；
3. 最终：config `md5 89cd61d7…`（与备份逐字节一致，已核）、`/health ok`、横幅重新出现 "rounding-level recipe is on"、
   引擎进程内 **无** `STRATA_DUMP_FIRST_LOGITS`；
4. **生产二进制发生切换（不是我改的，是重启的副作用）**：重启前进程跑的是已删除 inode `e0c6f250…`，
   重启后跑的是磁盘上的 **`a97f4479…`**（40,746,776 B）。两者 `.hip_fatbin` 逐字节相同（`b4f1e26a…`，`W909 §4`），
   差的是主机侧约 25 KB。**这意味着"磁盘件 vs 运行件"的老问题被这次重启消解了**，但也意味着生产现在跑的是那个
   从未做过 A/B 的主机侧构建。设备代码一致，性能预期不变；仍建议找窗口做一次 6.4K prompt 的 TTFT 复核。
5. 测量产物：容器 `/data/w912/`（48 个 `.bin` + JSON），已归档到宿主机 `~/strata166/w913/`（57 MB）。

---

## 5 复现

```bash
# 1 设置全词表 dump（需要重启）
docker exec strata166-407 python3 -c "import json;p='/data/strata-huihui-ud-iq4_xs.json';d=json.load(open(p));d['env']['STRATA_DUMP_FIRST_LOGITS']='/data/w912/first.bin';json.dump(d,open(p,'w'),indent=2)"
docker restart strata166-407

# 2 每请求一个首窗全词表（注意引擎会加 .N 后缀）
docker cp first_dump.py strata166-407:/tmp/ && docker exec strata166-407 python3 /tmp/first_dump.py collect t1 2

# 3 计算 KL（float32 全词表，softmax 前减 max）
#    同一进程两次 → 应为 0；换进程 → ~0.0032；TUNED 1↔0 → ~0.0020
```


---

## 6 交叉引用 `W914`：tuned 表里 5 个开关的 KL 低于这个噪声底

`arch_defaults.cpp:195-214` 逐条写着每项的代价：`HC_Q8` **0.0011**、`SELECT_SIMT` **0.0004**、
`ROUTE_TAIL_SKIP` **0.0008**、`HIP_PROMPT_F16` **0.0026**、`MMQ_KQ` **0.0171**（argmax 全 100%）。
对照本节实测的跨进程噪声 **0.0032**：**前四项都低于噪声底**，用端到端手段**无法复核**；
只有 `MMQ_KQ`（0.0171）在噪声之上、可测。表中那些数应来自逐开关的单点/微基准，不能当作"整机已验证"。
