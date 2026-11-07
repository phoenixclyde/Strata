# W775delta W4x 第 4 车 ---- 驻留模式 A/B：`--resident-budget-gib 76` vs `--resident-experts` + headroom 0.5（W28E 车序 **B7**）

> 时间：2026-10-11 **17:15 -> 17:31:49**（约 17 min）　机主令：「继续」
> 靶：**去掉 `--resident-budget-gib 76`，改用 `--resident-experts`，并加 `STRATA_RESIDENT_HEADROOM_GIB=0.5`** ---- 治 **M1/M2**（借区无 RAM 副本 ⇒ 每 chunk 从模型文件补回）。**单一概念变更**（args 两 token + env 一键）。

## 0 结论（先行）—— **正果（本会话 W28 线第一个正向结果）**

1. **验收硬证通过**：`FileExpertSource: **1554 of the prompt path's 1554 lendable slots keep their experts in RAM too**`（**N == M**）；补集 **36.93 GiB**（A 模式 33.44 GiB = base；+3.49 GiB = 借区），**与 W28D 预测值逐字一致**。
2. **文件层读被消除**：A 臂 tiers 行 `files **1554 -> 7770** blobs`（每 run 累加 +1554）；**B 臂全部 10 run = `files 0 blobs`**。
3. **冷 `read_ms` = −2.50%**（去 r0 热机项：A 25,416 / B 24,780），且**两臂区间不重叠**：A [25,378 - 25,455] vs B [24,763 - 24,810] ⇒ **真效应，非噪声**。
4. **parity 5/5 逐位相同**（`5a4b25aa...`，答 `391`）⇒ **不改答案**。
5. 生产已恢复、配置面未变（本车未动 register/config）。

## 1 车体断言（逐字，车日志）

```
B removed=['--resident-budget-gib', '76'] added=['--resident-experts'] budget_value=76
ARM blk1 mode=A changed=['log', 'port']                 <- A = 生产同构
ARM blk2 mode=B changed=['args', 'env', 'log', 'port']  <- B
ARM blk3 mode=B changed=['args', 'env', 'log', 'port']
ARM blk4 mode=A changed=['log', 'port']
ARM DT   mode=B changed=['args', 'env', 'log', 'port']
CFG_OK
```
- **单概念变量**：A 只差 `log`/`port`；B 只差 `args`（删 `--resident-budget-gib 76`、加 `--resident-experts`）+ `env`（加 `STRATA_RESIDENT_HEADROOM_GIB=0.5`）。发起前已在**本机用 166 真 config 模拟** builder（`SIM_OK`）。
- **运行期旁证**：B 臂 environ 实读 `STRATA_RESIDENT_HEADROOM_GIB=0.5`（A 臂不含）。
- ABBA **A B B A** ×5、`L=16384`、`max_tokens=256`、每 run 新 salt。

## 2 读数

| 口径 | A（budget 76） | B（resident-experts + hd 0.5） | delta | 备注 |
|---|---|---|---|---|
| **冷 `read_ms`（去 r0，主口径）** | **25,416**（n=8） | **24,780**（n=8） | **−2.50%** | A [25,378-25,455] / B [24,763-24,810] **不重叠** |
| 冷 `read_ms`（全 10 点）mean | 25,743 | 25,096 | −2.51% | spread 7% / 6%（含 r0） |
| decode `ms/step` mean | 22.7 | 21.8 | −3.92% | spread 35%/32%（含 r0；未单独判） |
| **文件层 blobs/run** | **1554, 3108, ... 7770** | **0 x10** | **消除** | tiers 行 |
| 补集 | 33.44 GiB | **36.93 GiB** | +3.49 | `allocating` / `cache complement ready` |
| 借区覆盖 | （无借区，`lend=false`） | **1554 / 1554** | -- | 验收硬证 |
| parity | `5a4b25aa...` | 同 | -- | 5/5 逐位相同 |

## 3 机制归因（源码）

- `expert_source.hpp:550-552`：`budget_bytes > 0`（`--resident-budget-gib`）⇒ **`lend=false`** ⇒ *"a lent slot's expert is read from the files"* ---- 即 A 臂每 chunk 从模型文件补回那 1,554 槽。
- 换 `--resident-experts`（`resident_budget = 0`）⇒ `lend=true`（`expert_source.cpp:2638`）⇒ 借区其专家**留在 RAM**（`expert_source.cpp:3105-3109` 打印 N of M），refill 走 RAM。
- 与上游 `AMD_HIP.md:222-228` 的"报告者 6,201/6,201 快、5,093/6,202 慢"同一机制、同一方向。

## 4 局限（必须随行）

1. 只覆盖 **11.4K-token 冷请求**；本 harness 页缓存温（OS 读仍小）；单卡；**未测长 prompt / 多轮**。
2. **两 token 同变**：本车证明"mode+headroom 组合"有效；**headroom 0.5 是否必要未单独测** —— 启动时 `MemAvailable` 约 80 GB，默认 headroom 4 也很可能容得下 36.93 GiB。若要**最简生产配置**，建议再跑一车只验 `--resident-experts`（headroom 默认 4）。
3. `read_ms` 是 prompt 读入耗时；decode 未单独判（但 parity 同 ⇒ 答案不变）。
4. `read_ms` 的 −2.5% 是**相对本 harness**的冷读；生产长 prompt 的绝对收益应按 W28 的"冷读占比"外推，未实测。

## 5 处置建议（**待机主签字** —— 改生产 `args` 属签字项）

| 方案 | 内容 | 备注 |
|---|---|---|
| **推荐** | 采纳 **`--resident-experts`**（去 `--resident-budget-gib`），`STRATA_RESIDENT_HEADROOM_GIB` 取 **0.5**（本车已验） | 即刻可用；已验 N==M |
| 更简 | 采纳 `--resident-experts`，headroom **留默认 4** | 更安全（RAM 余量），但**须补一车验 N==M** |
| 不采纳 | 维持 budget 76 | 保留 −2.5% 冷读收益的损失 |

落 register 时为：`P66 --resident-experts` → `ADOPTED`（若采纳）；`P65 STRATA_RESIDENT_HEADROOM_GIB` → 按选定值 `ADOPTED` 或留 `CANDIDATE`。

## 6 生产恢复（本车后）

`restore` 17:31:49 -> **HTTP=200 @ 17:32:25**；cfg md5 `6261ddf8a81bf0ebe90101d3b0cf8455`、引擎 md5 `5efa1d45c2e8c6f14b62a96b32d03155` **均未变**；`verify_config` **PASS=26 FAIL=0**（落档 `deploy/params/_verify_20261011_1733.txt`）。

## 7 复现命令

```bash
# 借区覆盖（验收硬证）
grep -a "lendable slots keep their experts" /home/albus/strata166/data/_w4y_res_*.log
# 补集大小
grep -aE "allocating .* complement|cache complement ready" /home/albus/strata166/data/_w4y_res_blk*.log
# 文件层 blobs（tiers 行）
grep -a "expert tiers" /home/albus/strata166/data/_w4y_res_*.log | tail
# A/B 冷读
python3 deploy/tmp/_res_report.py
```


## 8 固化上线 + 生产验证（2026-10-11 17:37-17:5x，机主令「都你定，继续推进」）

**固化（register 通道）**：`P09`(`--resident-budget-gib 76`) -> `REJECTED`；`P66`(name 清为 `--resident-experts`、`value=(flag)`) 与 `P65`(`0.5`) -> `ADOPTED`；计数 **26·33·21·6 -> 27·34·19·6**（86 行不变）。`gen_config --live` diff **只三处**；`--write` => cfg md5 **`ff8cb97379f0bdbe76ee555da6d8729c`**；推 166（旧 cfg 备份 `...json.bak_b7_20261011_173722`）；`docker restart strata166-407` => **200 @ 17:38:12**；`verify_config` **PASS=27 FAIL=0**。

**生产实证（三条，本机读 166）**
1. **上游成功判据达成**：`resident RAM: 36.93 GiB of experts in RAM, N exchanged, **0 blob reads from the file**`（改前该行是 22,114 / 23,166 / 24,720）。
2. **`file tier I/O this request: the OS read X MB (0 major faults) for **0.0 MB** of expert reads`** ---- 专家读归 0。
3. **长冷请求（49,720 tokens，`reused=0`）**：`read in **105,606 / 106,108 ms**`（470.8 / 468.6 tok/s），`files **0** blobs`；该请求 `file tier` 真存储读 **1,312.8 MB（0 major faults）**。
   同期 netdata（**探针窗 17:45-17:52，参数 `after=-420&points=70&group=average`，脚本 `deploy/tmp/_b7_nd.py`；[!] 该次输出未落盘**）：`gpu_utilization` 均值 **70.1%**（峰 100%） · `disk.sda` 读 **48,602.4 KiB/s ≈ 47.5 MB/s**（**7.7 s 分箱均值序列的 max，非真峰**） · `iowait` 峰 7.6% · cpu.user 峰 43.9%。
   **[AUDIT5-A2 更正]** (1) 均值原写 79%，同参数复算 = **70.1%**；(2) 同窗 `group=max` 真峰 = `disk.sda` **201,635.7 KiB/s ≈ 197 MB/s**、`iowait` **31.6%**、`cpu.user` **52.5%** => 「48 MB/s」与「改前 356 MB/s」**口径不同（降采样均值峰 vs 48h 真峰）不可直接相比**；同口径降幅约 **1.8x**（非 7x）。(3) 改前 48h `cpu.user` max = 51.46% ≈ 改后 52.5% => **「CPU 满载不复现」证据不成立，已撤回**。
   => **GPU 不动**已不复现（均值 70-83% / 峰 100%）；**硬盘读满**显著缓解但**未归零**（首条长冷仍读 1.3 GB）；**CPU 满载**一条撤回。**「稳态不读盘」以日志为准**（第 2 条与 §11：专家读 `0.0 MB` / OS 读 6-8 MB）。

**旁证（**非受控**，只作方向）**：改前生产日志里 64K 冷读 = **251,925 ms（254.1 tok/s）**；其**自己**的 `file tier` 真存储读 = **27,429.5 MB（222,659 major faults）**（**[AUDIT5-A1 更正]** 此前写「该请求 64,649 MB」—— 实为同日志里**另一条 60-token 首请求**（`L2829/L2834`）的读数）；改后 49.7K = 105.6 s（470.8 tok/s）。**长度 / 内容 / 时点都不同 => 不作定量结论**；受控量化由本车第 2 轮（§9）给出。

**方法论（新增，已入记忆）**：`STRATA_RESIDENT_HEADROOM_GIB` 只**上限**补集（`budget = available - headroom`），不造成超额占用 => **headroom 0.5 不比 4 更危险**，且更能保证借区进 RAM => **无需为此补车**。

## 9 B7-long 受控车（长 prompt，2026-10-11 17:52 起）

A = **现行生产**（resident-experts + headroom0.5） · B = **17:37 备份的旧 config**（budget 76，逐字）；`L=65536`、`RUNS=2`、ABBA **A B B A**。harness `deploy/tmp/_w4z_rc.sh`（A/B 臂分别直取现役与旧 config，只改 `log`/`port`）。=> 用于把 §8 的"方向"变成受控读数。

### 9.1 结果（17:52 - 18:10，**页缓存温**）

| 块 | 臂 | 冷 `read_ms`（2 run） | wall_s | `files N blobs` |
|---|---|---|---|---|
| blk1 | A(resident) | **107,218 / 106,123** | 110.69 / 109.37 | 0 / 0 |
| blk2 | B(budget) | **108,246 / 107,019** | 111.92 / 110.30 | 1554 / 3108 |
| blk3 | B(budget) | **108,224 / 108,301**（从 blk2.log 补回） | 111.92 / 111.66 | 1554 / 3108 |
| blk4 | A(resident) | **107,219 / 106,276**（从 blk1.log 补回） | 110.87 / 109.41 | 0 / 0 |

=> **A(n=4) 均值 = 106,709 ms / B(n=4) 均值 = 107,948 ms ⇒ B 慢 1.16%**（区间 A[106,123, 107,219] / B[107,019, 108,301]，略重叠）。

**[!] 判定：本车测不出收益 ---- 页缓存温。** B 臂确实读了 `files 1554 blobs（52,981.0 MB read）`—— **[AUDIT5-A6 更正] 该 MB 是 `tiers` 行的 `since the start` 累计**（= 起机 23,613.1 + 本请求 29,367.9），**不能**除以单请求时长当速率（旧写「52,981 MB / 108 s ≈ 490 MB/s」属口径混用）。同件 §10.1 已改用**本请求口径**：该请求 `for 29,369.5 MB of expert reads`，其中仅 **1,873.7 MB 来自存储**（42 major faults）⇒ **约 94% 由页缓存供给** => A/B 无法区分。**与 B8 车同型**。
=> **判据修正**：本 harness **测不到「冷盘」收益**；生产上的真收益（改后 `0 blob reads`；改前**单请求** OS 读最高 **64,649.1 MB**（属一条 60-token 首请求，`L2829/L2834`）、冷读最长 **251,925 ms**（属 64,026-token 请求，`L2837`））**必须用冷页缓存车**才能受控复现。**[AUDIT5-A1 补遗]** 此前两值被并成同一请求。

**本车 bug（自纠）**：`mk(src, tag)` 把 log 名按**调用时的 tag** 写死，而 blk3/blk4 直接复用了 A/B 的 dict ⇒ 这两块写到 blk1.log/blk2.log ⇒ engine 行缺失。**已在 `_w4z2_rc.sh` 修为 per-tag log 并加断言。**

## 10 冷页缓存受控车（tag `cold`）

`deploy/tmp/_w4z2_rc.sh`：**每个 run 前在 host 执行 `sudo -n sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'`**（`DROP_OK` 已验），再发 1 个 65K 冷请求；A = 现行生产 / B = 旧 config 备份；`L=65536`、`RUNS=2`、ABBA。18:12:39 - 18:32:42。

### 10.1 结果 ---- **`drop_caches` 也没能制造"冷盘"**

| 块 | 臂 | 冷 `read_ms`（2 run） | `files N blobs` |
|---|---|---|---|
| blk1 | A(resident) | **107,567 / 106,482** | 0 / 0 |
| blk2 | B(budget) | **108,579 / 108,542** | 1554 / 3108 |
| blk3 | B(budget) | **108,574 / 107,250** | 1554 / 3108 |
| blk4 | A(resident) | **107,670 / 106,334** | 0 / 0 |

=> **A(n=4) 均值 107,013 ms / B(n=4) 均值 108,236 ms ⇒ B 慢 1.14%**（区间 A[106,334, 107,670] / B[107,250, 108,579]，略重叠）。

**[!] 判定：`drop_caches` 没能把"文件层读"变冷**（结论不变，但**论据我改过一次**，见下"自纠"）。

**正确的证据**（车的 `file tier I/O` 行，本机现读）：B 臂该请求 **`for 29,369.5 MB of expert reads`，而 OS 只读 `1,873.7 MB`（42 major faults）** ⇒ **29 GB 里约 94% 由页缓存供给**；A 臂 `0.0 MB` 专家读（OS 1,872.5 MB）。
**根因**：引擎以 `--mmap-experts` 把 GGUF **mmap 在案**，而页缓存回收**不驱逐进程正在映射的页** ⇒ `drop_caches` 无法把这层读**定价**。

**[自纠 ---- 一小时内我改过一次论据]** 我先前写「`490 MB/s` **>** 磁盘峰 `356 MB/s` ⇒ 是缓存命中」= **量纲错**：`356 MB/s` 是**生产某请求窗口的平均**（含计算），**不是盘的能力**；**实测冷盘 = 524 MB/s（读）/ 439 MB/s（写）**，490 MB/s **本来就可能是真磁盘读**。=> 结论（harness 造不出冷文件层）**不变**，**论据换成上面那条 `29,369 MB` vs `1,874 MB`**。
**另一条同源观察（支持 drop_caches 确有作用）**：§11 那次冷态首次请求确实发生了**一次性 6,687.5 MB 的 OS 回填**，随后稳态降到 6-8 MB ⇒ `drop_caches` 生效过，但**驱逐量远小于文件层总量**。

### 10.2 结论（三种 harness 变体一致）

| 变体 | A vs B（resident - budget，负=resident 快） |
|---|---|
| 16K、温缓存（B7 车） | **-2.50%** |
| 65K、温缓存（B7-long） | **-1.16%** |
| 65K、每 run `drop_caches`（本车） | **-1.14%** |

=> **受控 harness 一致给出 A≈B（resident 略快 1.1-2.5%）**；而**生产上的大差**（改前**两条不同请求**：OS 读最高 **64,649.1 MB**（60-token 首请求 `L2834`）、冷读最长 **251,925 ms**（64,026-token 请求 `L2837`）**[AUDIT5-A1 补遗]** ⇒ 改后 **0 blob reads**、`105,606 ms` @471 tok/s）**只能在「真实内存压力把 mmap 页驱逐」的条件下出现** ⇒ **以生产读数为准（§8）**。

**方法论（入记忆）**：`drop_caches` **不能**重置 mmap 活跃页 => 复现 cold-disk 必须靠**内存压力驱逐**（生产自然发生），不能靠 `drop_caches`。

### 10.3 连带判定

`B10`（`STRATA_RESIDENT_PIN=0`）的动机（G4「pinned 副本挤 CPU workers」）**已弱化**：**[AUDIT5-A2 更正]** 原论据「生产冷探针 `cpu.user` 峰 43.9% ⇒ CPU 不再满载」**撤回**：该 43.9% 系**降采样均值序列的 max**，同窗真峰 **52.5%**，且改前 48h `cpu.user` max = **51.46%** => 改前改后**无变化**。方向保留（CPU 从未真正「满载」，`B10` 仍为条件性候选）。

**本 harness 线到此收束**：受控侧能给的数已达上限（A≈B ≈1-2.5%）；**要更高，只能靠生产真实冷窗**（下一条真用户冷请求）。



## 11 用 open-webui 容器验证（机主提示「我就是在用那个的时候遇到的」）

**接线**（本机读 open-webui 容器）：`openai.enable=true`，`openai.api_base_urls` 含 **`http://host.docker.internal:8090/v1`** ⇒ **open-webui 直接打我们的引擎**；`api_key` 表 **0 条**（故不改它的 DB，改用 `docker exec open-webui python3` 作客户端，走同一条路径）。

**A. 冷盘实测（新，重要）**：`dd` 1 GiB → 冷读 **524 MB/s**（写 439 MB/s）。=> 本机磁盘**不慢**；此前"490 MB/s 一定是缓存"的推断作废。

**B. 生产（现行 = resident-experts + hd0.5）× 3 条 60K 冷请求（client = open-webui 容器）**

| # | wall | prompt_tokens | 引擎行 |
|---|---|---|---|
| 1 | 128.4 s | 60,024 | `read in 127,839 ms (469.5 tok/s)`；`resident RAM 36.93 GiB, **0 blob reads**`；`file tier: OS read **6,687.5 MB** for 23,613.1 MB`（**一次性冷回填**） |
| 2 | 128.0 s | 60,026 | `read in 127,539 ms (127.5 s)`；`**0 blob reads**`；`OS read **8.1 MB** (0 faults) for **0.0 MB**` |
| 3 | 128.1 s | 60,027 | `read in 127,699 ms (127.7 s)`；`OS read **5.7 MB** (0 faults) for **0.0 MB**` |

=> **稳态 = 文件层基本不读盘**（OS 读 ~6-8 MB/请求、专家读 **0.0 MB**、`0 blob reads`）；首条 6.7 GB 只是**冷缓存回填**（冷车刚 `drop_caches`+重启所致）。
=> 对照**改前生产真实请求**（同一张卡）：110,793 tokens `read 244,400 ms (453.3 tok/s)` ，其**自己**的 `file tier` 真存储读 = **3,375.7 MB（0 major faults）**（**[AUDIT5-A1 更正]** 此前写「64,649 MB」—— 那是同日志里一条 60-token 首请求的读数）。

**C. 连带（修正 §10.3 的一条措辞）**：`B9`（`IO_PREFETCH`/`IO_PF_STAGE`）**仍作废** ---- 稳态文件层专家读 = **0.0 MB**，它没有靶。
