# W739 R0a/R0b 实测：`STRATA_EXPERT_V2` 与 `STRATA_TSUM` 的 gfx906 单变量 A/B

> 触发：机主令「你先把一和二做了」= 落 `W738` 候选里的前两项（R0a 开 `STRATA_EXPERT_V2`、R0b 试 `STRATA_TSUM`）。
> 基线：Strata **0.1.41**（镜像 `strata-gfx906:0.1.41`，引擎二进制 md5 `160611838796d4b172ec3a642ccd988d`），生产 `strata166-407` / 8090。
> **本轮动了生产**：为腾显存跑臂，`-407` 被停（两次），均由远端驱动器的 `trap ... EXIT` 恢复；末次恢复时间 00:35:36，`/v1/models` HTTP=200。
> 证据等级：**[实测]** / **[Strata源码]** / **[上游文档]**。
> 现场声明（Z0）：`rocm-smi --showperflevel` = **auto**，无人工 power cap；uptime 3 d 11 h；1 min load ≈ 1.28~1.38；GPU 空闲 45 C / 17 W。

---

## §0 结论

| 开关 | 速度（decode，5 请求 / 2000 token） | 正确性 | 裁决 |
|---|---|---|---|
| **`STRATA_EXPERT_V2=1`**（S26 流） | **慢 5.60%**（基线均值 47,694.9 ms；B/B2 = 50,358.2 / 50,375.0，两臂 spread **0.03%**） | **位等成立**：输出与基线**逐请求 5/5 相同** | **REJECTED**（纯性能否决，不改答案） |
| **`STRATA_TSUM=1`** | **-0.32%（噪声内，中性）**（T/T2 = 47,390.6 / 47,691.9；spread 0.63%） | **失去复现性**：T 偏离基线 **0/5**，T2 与基线相同 **5/5**；`V2+TSUM` 臂同型（C 偏离 0/5、C2 相同 5/5），且该臂 spread 恶化到 **2.51%** | **REJECTED**（触「改答案 / 不可复现」一票否决） |

**两条都已登记进 `PARAM_REGISTER.tsv`：P36 / P37 = REJECTED**（两侧 md5 `8430bac271bf596828a274de9231d1da`）。

**本波附带的一条一般性结论**：上游 `docs/STRIX_HALO.md` §4 那族「**gfx1151 默认开、byte-identical、change speed not answers**」的开关，
**在 gfx906 上不能假定成立** -- `EXPERT_V2` 的位等在本卡**成立**（好），但 `TSUM` 的位等在本卡**不成立**。
=> 该族只能**逐个体检**，不能整族照搬。

---

## §1 方法（可复现）

**臂容器模板**（与生产逐字对齐；取自 `docker inspect strata166-407`）：

```
docker run -d --name w738_arm \
  --device=/dev/kfd --device=/dev/dri --group-add video --ipc=host --ulimit memlock=-1 \
  -v /home/albus/strata166/data:/data -v /models:/models:ro -p 8095:8095 \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src -e STRATA_PREFILL_CPU_SHARE=0 \
  [-e STRATA_EXPERT_V2=1] [-e STRATA_TSUM=1] \
  strata-gfx906:0.1.41 \
  bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/_w738_cfg.json --port 8095"
```

**隔离措施（三条，都是为了不污染生产）**：
1. **臂 config 单独一份** `/data/_w738_cfg.json` = 生产 config 的副本，**只改 `log` 与 `port` 两个键**；
   驱动器内**断言** `ARM_CFG_DIFF == ['log','port']`（实测通过）=> 臂不会写生产日志。
2. `--expert-profile-save` 会重写 `/data/profiles/huihui-ud-iq4_xs-learned.bin` => 开跑前备份、`trap` 里还原；
   实测还原后两侧 md5 相同（`d66d0781574d66f6906a38c6276a26d4`）。
3. 驱动器整体 `trap restore EXIT`：**无论哪一臂失败都会把 `-407` 拉回**并轮询就绪。

**臂设计**：交错 8 臂 -- `A B C A2 B2 C2`（第一轮）+ `T T2`（第二轮）。
每臂 = 独立容器（同一镜像、同一 config），跑 **5 次同一 prompt 的 400-token 贪心**（`max_tokens=400`），
读数取引擎自己的 `/metrics`（`decode_ms` / `decode_tok_s` / `drafts_offered` / `drafts_accepted`）而不是客户端墙钟。
每臂用 `/proc/1/environ` **实证 env 已生效**（否则不算）。

**为什么交错**：routeK 的同机教训 -- 「**主机态退化解会伪装成性能回归**」（`RETRACTED - the "regression" was host-state degradation`）。
A/A2 交错复现给出本波**噪声底 = 0.13%**（`decode_ms`）。

---

## §2 结果

| 臂 | 额外 env | decode_ms | decode tok/s | drafts off/acc | prompt_ms |
|---|---|---|---|---|---|
| **A** | - | 47,726.0 | 41.91 | 1145 / 901 | 2937.3 |
| **A2** | - | 47,663.7 | 41.96 | 1145 / 901 | 2885.9 |
| **B** | `EXPERT_V2=1` | 50,358.2 | 39.72 | 1145 / 901 | 2887.9 |
| **B2** | `EXPERT_V2=1` | 50,375.0 | 39.70 | 1145 / 901 | 2904.7 |
| **C** | `EXPERT_V2=1 TSUM=1` | 48,437.7 | 41.29 | **1197 / 972** | 2888.0 |
| **C2** | `EXPERT_V2=1 TSUM=1` | 49,670.8 | 40.27 | 1145 / 901 | 2884.4 |
| **T** | `TSUM=1` | 47,390.6 | 42.20 | **1150 / 909** | 2974.4 |
| **T2** | `TSUM=1` | 47,691.9 | 41.94 | 1145 / 901 | 2891.1 |

**按臂型聚合（vs 基线 A/A2 = 47,694.9 ms）**：

| 臂型 | n | decode_ms 均值 | 臂内 spread | vs 基线 |
|---|---|---|---|---|
| 基线（-） | 2 | 47,694.9 | **0.13%** | 0.00% |
| `EXPERT_V2` | 2 | 50,366.6 | **0.03%** | **+5.60%** |
| `EXPERT_V2 + TSUM` | 2 | 49,054.2 | **2.51%** | +2.85% |
| `TSUM` | 2 | 47,541.2 | 0.63% | -0.32% |

**读法**：
- `EXPERT_V2` 的两臂差 **0.03%**、且同时高于基线 5.6% => **不是噪声，是稳定的退化**。
- `TSUM` 的 -0.32% **小于**其自身 spread（0.63%）=> **中性**。
- `V2+TSUM` 的 spread 2.51%（是 `V2` 的 84 倍）=> 这一组合**计时本身就不可复现**，与 §3 的输出现象一致。
- VRAM 在 serve 时六臂几乎相同（33,895,9xx,xxx B，散布约 0.001%）=> 两条开关都**不改变显存占用**。

---

## §3 正确性：逐请求 sha16 矩阵（本波最有价值的一张表）

同 prompt、同 `max_tokens`、贪心；**同一臂内 5 次输出本就各不相同**（`reused` 0 -> 80 的会话态递进使然，见 §5-1）。
因此正确性判据取「**同 index 跨臂是否一致**」：

| req | A | A2 | B (V2) | B2 (V2) | C (V2+TSUM) | C2 | T (TSUM) | T2 | 不同值 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 26b20aa3 | 26b20aa3 | 26b20aa3 | 26b20aa3 | **b6819459** | 26b20aa3 | **c4b792a1** | 26b20aa3 | 3 |
| 1 | abe7f263 | abe7f263 | abe7f263 | abe7f263 | **99e0988e** | abe7f263 | **a54316fa** | abe7f263 | 3 |
| 2 | 20df0cb9 | 20df0cb9 | 20df0cb9 | 20df0cb9 | **6b470998** | 20df0cb9 | **316778ae** | 20df0cb9 | 3 |
| 3 | 30fc3e22 | 30fc3e22 | 30fc3e22 | 30fc3e22 | **b4138926** | 30fc3e22 | **e1bc3188** | 30fc3e22 | 3 |
| 4 | dea5cb7e | dea5cb7e | dea5cb7e | dea5cb7e | **ee9c9b01** | dea5cb7e | **4c1690f3** | dea5cb7e | 3 |

与基线 A 的一致数：`A2 5/5` · `B 5/5` · `B2 5/5` · `C2 5/5` · `T2 5/5` · **`C 0/5`** · **`T 0/5`**。

=> **`EXPERT_V2` 不改答案（位等成立）**；**`TSUM` 使输出失去复现性**（同一臂型两次运行，一次偏离、一次回到基线）。

---

## §4 裁决与登记

- **P36 `STRATA_EXPERT_V2` = REJECTED**：条件完全命中（我们的 pack 就是 `IQ3_S gate/up + IQ4_NL down`、`n_embd 2560 / n_ff 640`）、
  符号在二进制里（`s26_gu_l_kernel` / `s26_down_l_kernel` / `s26_swiglu_q8_1_kernel`）、正确性也好 -- **唯一的问题是它在 gfx906 上更慢**。
  上游那条 `docs/STRIX_HALO.md` §4 逐字说「**on a gfx1151 it sets the switches below**」=> 它是为 **gfx1151** 调的表，本卡不适用。
- **P37 `STRATA_TSUM` = REJECTED**：速度中性，但**引入不可复现性** => 触一票否决。
  且它**与上游「bitwise the same values（S26 ws4 harness, every output equal）」的声明在本卡不符**。

两条都是 `status=REJECTED`，被核验器 `if r['status'] != 'ADOPTED': continue` 跳过 => **不改变 `verify_config.py` 的 PASS 计数**。

---

## §5 本波附带的三条一般性发现

1. **本服务的输出是「按会话态递进」的确定序列，不是「同请求同答」**：
   同一 prompt 连发 5 次，`reused` 从 0 变 80，5 次输出**互不相同**（chars 628/604/610/622/641），
   但**同一 index 在不同臂/不同轮次之间可以逐字节复现**（见 §3 矩阵）。
   => 以后做「改答案」判定，**必须按 index 对齐**，不能拿两次任意请求的输出直接比。
2. **`TSUM` 类「改位但声称位等」的开关，在本卡至少要跑 2 次同型臂**：本轮若只跑一次（T 或 T2），
   会分别得到「改答案」或「位等」两个相反结论 -- 正是「**一次测量不是规律**」的现场。
3. **`V2+TSUM` 的 spread（2.51%）比 `V2`（0.03%）差 84 倍** => 不可复现性同时污染**计时**与**输出**，
   两者互为旁证。

---

## §6 生产影响与恢复核对

| 项 | 结果 |
|---|---|
| 停/起次数 | 2 次（第一轮 6 臂、第二轮 2 臂）；每次由 `trap restore EXIT` 自动恢复 |
| 末次恢复 | **00:35:36**，`/v1/models` **HTTP=200** |
| 生产 config | md5 `a8706bed59d0bab3260e427b43b9e8b9`（**未变**） |
| 引擎二进制 | md5 `160611838796d4b172ec3a642ccd988d`（**未变**） |
| serve 覆写 | telemetry `3d464198e925926914cbd62c2c4dcf24` / app.js `026ceb188117f412a7d320c4657db8c0`（**均在位**） |
| 生产日志 | 臂写的是 `/data/_w738_arm.log`，生产日志未被臂污染 |
| profiles | 已按备份还原（两侧 md5 同 `d66d0781574d66f6906a38c6276a26d4`） |
| 核验器 | `verify_config.py` **EXIT=0** |
| 镜像/容器 | 臂容器 `w738_arm` 已删；`-406` 回滚位仍在（Exited 0） |

---

## §7 落盘与出处

- 本件：`deploy/W739_V2_TSUM_AB.md`
- **证据（本地）**：`deploy/tmp/_w738_out_{A,A2,B,B2,C,C2,T,T2}.json`（8 份逐臂原始 JSON，含每请求 sha16 / usage / `/metrics` 表）
  · `deploy/tmp/_w738_ab.out`（第一轮完整 stdout，16,853 B）· `deploy/tmp/_w738_ab2.out`（第二轮，4,869 B）
- **驱动器（166 上，可复现）**：`/home/albus/strata166/_w738_ab.sh`（md5 `8490d589ddec45d27faa1dedd2a60468`）
  · `/home/albus/strata166/_w738_ab2.sh` · `/home/albus/strata166/data/_w738_client.py`（md5 `0ed10a650df5bb7cc908e69a1508a238`）
- **register**：`PARAM_REGISTER.tsv` **P36 / P37 = REJECTED**（53 行；两侧 md5 `8430bac271bf596828a274de9231d1da`）；
  本机备份 `PARAM_REGISTER.tsv.bak_w738_20261010_003916`（32,611 B）
- **Strata 源码依据**：`src/kernels/cuda/iq_kernels.cu:2005-2008`（S26 段头逐字）
  · `:3459-3500`（`v2` / `v2k` 入口与 `amd_gu` 表）· `src/kernels/cuda/fused_gr.cu:1380-1381`（TSUM 作用于 down/up 行）
  · `docs/STRIX_HALO.md`（§4「on a gfx1151 it sets the switches below」+ §5 改位族与 KL 门）

---

## §8 不确定项（诚实账）

1. **`TSUM` 的「不可复现」我只做过 2 次同型臂**（T 偏离、T2 回归）。要把它从「观察」升成「规律」，
   应在**另一次主机态**下再跑 2~4 次；本轮**没有**做。
2. **`EXPERT_V2` 的 -5.60% 只在「85-token prompt + 400-token 解码」这一种负载上测过**；
   该开关走的是 `native_expert_grouped`（**decode 侧** MoE），长 prompt 下的占比更低 => 对预填的影响未测。
3. **本轮全部读数取自引擎自报的 `/metrics`**，未与客户端墙钟交叉（两者在 `prompt_ms` 侧本就会因排队而不同）。
4. **臂容器的 serve 层是镜像原版**（`telemetry.py`/`app.js` 未覆写）-- 对 decode 吞吐无影响，但臂与生产**并非逐字节同一个容器**。
5. **`Z0=off` 我未能机械化证实**：本会话在两台机的脚本/文档里都没找到叫 `Z0` 的开关
   （`rocm-smi --showperflevel` 报 `auto`、无人工 cap）；按纪律**声明现场**为「perflevel=auto / 无 cap / uptime 3d11h / load≈1.3」。
