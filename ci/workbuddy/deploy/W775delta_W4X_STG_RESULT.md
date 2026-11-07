# W775delta W4x 第 3 车 ---- `STRATA_STAGER_SSD=1` A/B（W28E §6 车序 **B8**）

> 时间：2026-10-11 **16:55:06 -> 17:10:24**（15m18s）　机主令：「按计划据实推进」
> 靶：**`STRATA_STAGER_SSD=1`** ---- 强制 prompt 路 stager 取 **SSD 档（32 线程 / ring 128）**，对照默认 **RAM 档（4 线程 / ring 16）**（`prefill.cpp:1065-1073`）。治 **M3**。

## 0 结论（先行）

**无增益，且条件未充分复现。** 冷 `read_ms` A 25,735 / B 25,804（**+0.27%**，两臂 spread 均 **7%**）=> 无差异；decode `ms/step` −2.85%（spread 31%/27%）=> 噪声；parity **5/5 逐位相同**。
**[!] 但本 harness 的 `major faults = 0`、file-tier OS 读中位仅 18 MB（专家读 ~11.2 GB/请求）** => **页缓存基本是温的** => B8 靶向的「磁盘慢路径」在本 harness 里**不是主成本**。故本条应读作「**温页缓存下无增益；机制未被充分激发**」，而非「SSD 档无效」。

## 1 车体断言（逐字，来自车日志）

```
ARM blk1 env=(none)                    changed=['log','port']          <- A
ARM blk2 env=STRATA_STAGER_SSD=1       changed=['env','log','port']    <- B
ARM blk3 env=STRATA_STAGER_SSD=1       changed=['env','log','port']    <- B
ARM blk4 env=(none)                    changed=['log','port']          <- A
ARM DT   env=STRATA_STAGER_SSD=1 (+VERIFY_TRACE)
CFG_OK
```
- **单变量**：A 臂只差 `log`/`port`；B 臂只多 `env`（`args` 逐字不动）=> 生产同构。
- **运行期旁证**：`engine environ opt-ins: ... STRATA_STAGER_SSD=1` 出现在 blk2/blk3（各 1 次）；blk1/blk4 **不含**。
- ABBA 顺序、每块 5 runs、`L=16384`、`max_tokens=256`、每 run 新 salt。

## 2 读数（A = blk1+blk4 共 10 点；B = blk2+blk3 共 10 点）

| 口径 | A | B | delta | spread A / B |
|---|---|---|---|---|
| **冷 `read_ms`**（主口径）mean | **25,735** | **25,804** | **+0.27%** | 7% / 7% |
| 冷 `read_ms` med / p90 / max | 25,419 / 27,068 / 27,068 | 25,481 / 27,158 / 27,158 | -- | -- |
| `read_tok`（每请求读入 tokens） | 11,445 | 11,445 | 0 | 0% |
| decode `ms/step` mean | 23.0 | 22.3 | −2.85% | 31% / 27% |
| file-tier **OS 读 MB/请求** med / mean | 18.2 / 122.4 | 13.8 / 119.4 | −2.49% | 448% / 461% |
| **major faults** | **0** | **0** | -- | -- |
| parity（5 处） | `5a4b25aaed25c2ee1b74de72dc03c14e`（答 `391`） | 同 | -- | -- |

> 每 run 唯一 salt => **前缀冷（`reused=0`）**成立（`read_tok ≈ prompt_tokens`，`reused=0`）。
> **[AUDIT5-A4]** 本表 `med` 用**上中位数**（n=10 取排序后第 6 个），`p90` 亦未声明方法；本机复算：`file-tier OS 读` 标准中位 = **17.2 / 13.05 MB**（本表 18.2 / 13.8 = 上中位）；冷 `read_ms` 标准中位 25,417 ≈ 表中 25,419。
> **[AUDIT5-A5]** 「冷 `read_ms`（主口径）mean」= **全 10 点（含每臂 r0 冷启动点）**；`W775delta_W4X_RES_RESULT.md` §2 同栏用的是「**去 r0** 8 点」—— 口径不同。本车去 r0 后 = A **25,410** / B **25,466**（**+0.22%**，结论不变）。

## 3 为什么"无差异"（据实，不猜因果）

1. **页缓存是温的**：`major faults = 0`；`file tier I/O this request` 的 OS 读**中位仅 18.2 MB**，而同一行的**专家读约 11.2 GB/请求**。=> 磁盘读在本次不是主成本，**改 staging 并行度自然无用**。
2. 与**上游自述一致**：`DETAILS.md:241-242` 逐字 *"With the experts warm in the page cache ... the file tier already runs at the resident speed, so there is nothing to win"*。
3. 对照**生产冷读**（`W775delta_W28_COLD_PATH_REDESIGN.md`）：那里 OS 读占专家读 **33.8%（371 GB / 1.10 TB）** => **本 harness 低估了 file 层**（因为 5 run 同形状连跑，把 blob 页读进页缓存）。

## 4 方法论收获（两条，可复用）

1. **两种"冷"必须分开**：本 harness **每 run 换 salt ⇒ 前缀冷（`reused=0`）**；而**页缓存冷**是另一回事，需 `drop_caches`。把两者混称"冷请求"就会误判 ---- 本车即例。（W28E §5 车纪律已写「页缓存状态两侧对称，必要时两臂都先 `drop_caches`」，本车未做 => 判据受限，已记。）
2. **stager 档的日志判据有坑**：设了 `STRATA_STAGER_SSD` 后，`prefill.cpp:1068-1071` 的 **else 分支不执行**，所以那句 `the stager takes the RAM profile` **根本不打印**（也无 "SSD profile" 行）=> 「日志无该行」**不能**判「没生效」；**须以 environ 在位为准**。（本车 DT 日志确无该行，但 environ 实含。）

## 5 处置

- **不采纳**（温页缓存下无增益）；**`P67` status 不动（仍 CANDIDATE）**，verdict 追加本条 + 条件说明。
- **要"决定性"须**：两臂**对称 `drop_caches`** 后再跑（或改用生产形态的长冷首读）。**但**在温缓存下 file 层占比仅约 5%，即便决定性其上限也小；=> **本车不作为优先项**。
- **下一车转 `B7`**（`--resident-experts` + `STRATA_RESIDENT_HEADROOM_GIB=0.5`，治 **M1/M2** = 借区无 RAM 副本导致每 chunk 从模型文件补回）；其验收硬证按 AUDIT4 更正为 `FileExpertSource: N of M of the prompt path … lendable slots keep their experts in RAM too` 的 **N == M**（`expert_source.cpp:3105-3109`）。

## 6 复现命令

```bash
L=/home/albus/strata166/data/_w4x_stg_*_ab.out
grep -aE 'ARM |CFG_OK|BLOCK_' $L
# 每 run 的冷读：看 _w4x_stg_speed_blk*.json 的 engine_prompt_line / engine_io_lines
```

## 7 生产恢复（本车后）

`restore` 17:10:24 -> **HTTP=200 @ 17:11:37**；cfg md5 `6261ddf8a81bf0ebe90101d3b0cf8455`、引擎 md5 `5efa1d45c2e8c6f14b62a96b32d03155` **均未变**；`verify_config` **PASS=26 FAIL=0**（落档 `deploy/params/_verify_20261011_1712.txt`）。
