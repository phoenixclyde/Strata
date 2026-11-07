# W775delta W12 D 臂 ---- 0.1.42 gfx906 `P59`+`P60` 复测（A 基线 vs D，serve 同构，ABBA x5）

> 时间：2026-10-11 11:10:56 -> 11:39:48（车）。负载 = `data/_w773_speed.py`；读数取自**引擎自报行**。
> 判据：`decode ms/step = gen_ms / gen_tok`（W774 §7.4 口径）。**Z0=off**（`rocm-smi` 实读 perflevel=auto，现场取）。
> 前置：`W775delta_W12_PRECHECK.md`（靶向核实）+ `W775delta_W12_BANNER.md`（P55/P56 不可达）。

## 0 结论（先行）

1. **输出逐位相同**：五次启动的固定 prompt parity **md5 全同**（`5a4b25aaed25c2ee1b74de72dc03c14e`，答 `391`）
   => `P59`/`P60` **不改答案**。与上游 #1479 逐字 *"answers identical in all runs"* 一致。
2. **无速度增益**：decode `ms/step` 的 D-A 差 = **+1.89%（全 10 点）/ +3.11%（温 8 点）/ +4.82%（温 6 点）**；
   符号一致指向 **D 略慢**，但**始终小于臂内 spread（12.9~40%）** => 按项目纪律（**臂内 spread 才是真判据**）
   **不判为真实差异**。=> **判定：exact but no gain；不采纳**（与上游 *"no gain we can show here; opt-in it stays"* 一致）。
3. **运行期旁证（本车新增）**：`STRATA_VERIFY_TRACE=1` 会打 **`strata verify trace (#649): on`**，并列出
   `capturing the 6/3/1/4-token window ... captured` => **verify/commit 图确在工作**；D 臂 `/proc/PID/environ` 实读含
   `STRATA_HEAD_MIX_MULTI=1` `STRATA_ONE_TOKEN_COMMIT=1`。
   **但两者均无 P59/P60 专属 banner** => "路径确被选中"只能到「env 在位 + verify 图在跑」这一层（局限，见 §6）。

## 1 臂设计（生产同构）

- 同一镜像 `strata-gfx906:0.1.42`；config 的 `args` **逐位不动**；只差 `log`/`port`（A 臂）或 `env`+`log`+`port`（D 臂）。
  造臂断言实得：A `changed=[log,port]`；D `changed=[env,log,port]`（`env` 只多两键）。
- 生产同构面全在：`--vision --mtp --conversation-cache-mib 4096 --mtp-window 8192 --kv k8v4 --spec 4 --prompt-cache-every 8192`。
- 顺序 **ABBA**（A D D A），每块 5 runs，L=16384（实得 prompt ~11,443 tok），`max_tokens=256`，`temperature=0`，
  每 run 新 salt（`reused` 全 0，10/10 核实）。
- 每块启动前先发一条固定 prompt 做 **parity**（正确性门）。

## 2 原始读数（`decode ms/step = gen_ms / 256`）

| 块 | 臂 | r0 | r1 | r2 | r3 | r4 |
|---|---|---|---|---|---|---|
| blk1 | A | 26.289 | 23.039 | 20.609 | 20.914 | 21.926 |
| blk4 | A | 28.219 | 23.758 | 22.207 | 19.172 | 20.039 |
| blk2 | D | 26.973 | 22.543 | 21.781 | 20.711 | 22.387 |
| blk3 | D | 26.477 | 23.570 | 22.926 | 20.777 | 22.309 |

| 口径 | A 均 | D 均 | **D-A** | A spread | D spread |
|---|---|---|---|---|---|
| 全 10 点 | 22.617 | 23.045 | **+1.89%** | 40.0% | 27.2% |
| 温 8 点（剔 r0） | 21.458 | 22.126 | **+3.11%** | 21.4% | 12.9% |
| 温 6 点（剔 r0,r1） | 20.811 | 21.815 | **+4.82%** | 14.6% | 10.2% |

## 3 方法学发现（供下一车继承）

1. **每块首跑是热机项**：r0 比稳定态高 15~25%（26-28 对 20-22）。**一条 parity 请求不足以为引擎热机。**
   => 下一车每块应**先跑 1-2 条丢弃的热机请求**（或按 r0 剔除处理）。
2. 三次口径的 delta **符号一致**（D 略慢），但**量级始终 < spread** => 这一对差值在「5 runs/块、10 点/臂」下仍**不可判**。
   要判 2-5% 量级需更多 runs，或更稳的负载（锁频 / 固定 prompt 长度）。
3. **parity 是有效的正确性门**且成本低（一条短请求）=> 建议作为本类车的标配。

## 4 推荐的 register 变更（**待机主签字**）

| ID | 现值（status） | 建议 |
|---|---|---|
| `P59` | `1(已测-prefill中性)` / CANDIDATE | `value` 改 **`1(exact but no gain;W12D)`**；verdict 记 W12D；**status -> REJECTED**（判过、不采纳；体例同 `P40`） |
| `P60` | `1(已测-prefill中性)` / CANDIDATE | 同上（与 P59 同一 patch 两半：**合并结论、编号分开**） |

> 依据：§0.1（exact）+ §0.2（无增益、落在 spread 内）。**改裁定属机主签字项**（`W775_HANDOVER §5`）。

## 5 现场与产物

- 车脚本：`/home/albus/strata166/_w12d_rc.sh`（`flock` 单实例 + `trap restore EXIT`）。
- 产物：`data/_w12d_speed_blk{1..4}.json`、`data/_w12d_parity_{DT,blk1..4}.txt`、`data/_w12d_{DT,blk1..4}.log`。
- 生产恢复：`[restore] 11:39:48` -> **HTTP=200 @ 11:43:39**（本次 RAM 补页拷贝较慢）；
  引擎 md5 `5efa1d45c2e8c6f14b62a96b32d03155`；cfg md5 `6261ddf8a81bf0ebe90101d3b0cf8455`；残留 **0**；VRAM 33.46/34.34 GB。
- 备份：`deploy/tmp/_w12d_bak/`（prod cfg / profile / prod log）；分析脚本 `deploy/tmp/_w12d_final.py`。

## 6 局限

- 单机单卡、**单负载面**（文本续写 filler）；只 L=16384 一档；ABBA 控线性漂移但**未锁频**。
- **无 P59/P60 专属运行期 banner** => 不能直接证"该分支被执行"，只能到「env 在位 + verify 图在跑」。
- 本车只答「速度有无差」；命中率 / 专家块 / 质量分布未并入（质量面由 parity 覆盖到"逐位相同"）。
- 与 W774 的关系：W774 的 prefill 中性是**靶选错**（PRECHECK 已证），本车改 **decode** 主口径**重测**；结论由"弃权"推进到"**exact but no gain**"。
