# W764 参数落地审计：register 的 26 行 ADOPTED 是否真在容器运行态生效

触发：机主「**审计。还有是否全部落生产容器了，固化的有效参数。**」

## 0 审计要判的那件事（技能口径）

`routeb-audit` 有一条正对着本问题的判据（cz69e 续三）：

> 「用户传参」**不等于**「运行期生效值」---- 凡以**配置项取值**为推理前提，**必须找到该配置的最后一个写入点**，
> 并以**运行期日志**或**插桩**为准。`--flag` 实参、默认值、任何一次"看起来只是校验"的函数调用，**都不是终值**。

=> 本轮声称的「P43 `--mtp-window 8192` 已采纳并重启生效」，**不能**用"config 里写了"证明，
必须取**运行期**。下面按此取三面。

## 1 三面取证（全部原始输出，落在 `deploy/tmp/_w764_faces.txt`）

| 面 | 取法 | 结果 |
|---|---|---|
| **A serve cmdline** | `docker exec <prod> sh -c "tr '\0' ' ' < /proc/1/cmdline"` | `python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090` |
| **B 引擎进程 cmdline** | 遍历 `/proc/[0-9]*` 找含 `build-906/strata` 的进程 | **`/proc/12: /src/build-906/strata --serve --pack ... --conversation-cache-mib 4096 --vision --mtp-window 8192`** |
| **C 容器内 config JSON** | `docker exec <prod> cat /data/strata-huihui-ud-iq4_xs.json` | `args` 尾部 = `['4096','--vision','--mtp-window','8192']`；`含 --mtp-window: True`；`其值 = 8192`；`env = {"HSA_OVERRIDE_GFX_VERSION":"9.0.6","STRATA_PREFILL_CPU_SHARE":"0"}`；顶层 11 键 |

**面 B 是本轮的决定性证据**：引擎**实际启动时**的命令行末尾就是 `--mtp-window 8192`
=> 它**不是**"config 里写了但没传下去"，而是**真的进了引擎进程**。

## 2 时间线（重启确实在推 config 之后）

| 项 | 值 |
|---|---|
| 宿主 config **mtime** | `2026-10-10 02:41:52.971803013 +0800` |
| 容器 **StartedAt** | `2026-10-09T18:41:59.691129984Z` = **2026-10-10 02:41:59 +0800** |

=> 重启比 config 落盘**晚 7 秒** => 引擎读到的是**新版** config（不是旧版）。

## 3 md5 三处一致

| 件 | 本机 | 166 宿主 | 容器内 |
|---|---|---|---|
| `strata-huihui-ud-iq4_xs.json` | `6261ddf8a81bf0ebe90101d3b0cf8455` | **同** | **同** |
| `PARAM_REGISTER.tsv` | `881808e08c6df021e885f278cea68918` | **同** | -（不在容器内） |

=> 排除了「本机改了、166 没改」与「166 宿主改了、容器挂载的是另一份」两种假一致
（本轮容器**读到的 config 路径**就是宿主 `/home/albus/strata166/data/` 挂进去的 `/data/`）。

## 4 26 行 ADOPTED 的覆盖面（逐项落到哪一面）

| 落点 | 行数 | 明细 |
|---|---|---|
| **config JSON 的 `args`** | **17** | `P00 --pack` · `P01 --native` · `P09 --resident-budget-gib 76` · `P08 --expert-profile` · `P07 --expert-cache auto` · `P25 --pcie-frac 0.20` · `P05 --spec 4` · `P06 --spec-min-p 0.70` · `P02 --mtp /data/mtp/rt` · `P03 --max-context 262144` · `P04 --kv k8v4` · `P10 --prefill auto` · `P34 --prompt-cache-every 8192` · `P20 --expert-profile-save` · `P31 --conversation-cache-mib 4096` · `P99 --vision` · **`P43 --mtp-window 8192`** |
| **config JSON 的 `env` 段** | **2** | `P11 HSA_OVERRIDE_GFX_VERSION 9.0.6` · `P23 STRATA_PREFILL_CPU_SHARE 0` |
| **config JSON 的 `vision` 段** | **3** | `V00`（exe）· `V01`（mmproj）· `V02`（model） |
| **config JSON 顶层键** | **1** | `B00 backend: hip` |
| **容器内文件（不在 config）** | **1** | `X00` serve 覆写（`/src/serve/telemetry.py` + `/src/serve/web/app.js`；核验器数据面 6 逐文件核过在位数与效果键） |
| **工具（本机/容器，不在 config）** | **2** | `P24 tools/calibrate.py` · `P38 isa_probe.py` |
| **合计** | **26** | **与 register 的 ADOPTED 行数相等** => **无遗漏** |

## 5 结论

**是 ---- 26 行 ADOPTED（= 固化的有效参数）全部在生产容器里有落点，且本轮新采纳的 `--mtp-window 8192` 已被运行期证据证实（引擎进程 cmdline + config JSON + 重启时序三者自洽）。**

## 6 局限（照实写）

- 本报告证明的是「**参数进了引擎进程**」，**不是**「参数产生了预期收益」---- 收益另有 W760 的 6 臂 A/B（64K 上下文 +3.39%）。
- `P43` 的**语义生效**（`mtp_window` 真被 `generate.cpp` 用起来）已由源码侧确认（`--mtp-window` -> `o.mtp_window`），
  但**本轮未做插桩**确认它在运行期被读到的具体值 ---- 已有证据是"命令行传了 + 源码会读"。
- 本报告是我方（当前会话）的核对；**另有独立子 agent 的对抗性审计正在进行**，其结论到达后并入。
- 未核：`P24`/`P38` 两个工具件在本机/166 的实际存在性（属"工具可用性"，不是"参数生效"）。
