# W775 生产容器体检报告（2026-10-11 04:10 CST / 20:10 UTC）

> 触发：机主令「你测一下现在的生产容器有没有问题」。
> 方式：**只读**（docker inspect / docker logs / /proc / /v1/status / verify_config.py），**未做任何写操作**。
> 目标：远端 166 `albus@192.168.50.166`，生产容器 **`strata166-407`**（@8090）。

---

## 0 结论：**正常，无问题**

**`verify_config.py` PASS=26 FAIL=0**；服务面 `/health` 200、`/v1/status` 正常返回；运行期进程三件齐全且命令行逐字与 register 一致。

---

## 1 容器与镜像

| 项 | 值 |
|---|---|
| 容器 | **`strata166-407`** ｜ **Up 2 hours** ｜ 镜像 `strata-gfx906:0.1.42` |
| 端口 | `0.0.0.0:8090->8090/tcp` ｜ `ss` 确认 **LISTEN 0.0.0.0:8090** |
| Created | `2026-10-10T18:26:58Z`（CST 02:26:58） |
| StartedAt | `2026-10-10T18:30:01Z`（CST 02:30:01） |
| **RestartCount** | **0**（从未自动重启） |
| 日志 | **1,405 行** |
| 镜像 | `strata-gfx906:0.1.42` `e5d422d32700` 6.59GB（2026-10-11 00:39 CST） |
| 回滚位 | `strata166-407_0141bak`（Exited 0，0.1.41）｜ `strata166-406`（Exited 0，0.1.41） |

> **时点自洽性**：核验器锚定的引擎日志行 `engine started: 2026-10-10 18:30:04` 与容器 `StartedAt 18:30:01Z` 只差 3 秒（引擎日志不带 Z，为 UTC 本地表示）-- **一致，非缺陷**。

---

## 2 服务面

| 检查 | 结果 |
|---|---|
| `/health` | **200**，`time=0.0015 s` |
| `/v1/status` | 正常 JSON：`engine=0.1.42`、`loaded=true`、`uptime_s=5777`、`cache_max_tokens=262144`、`context.native=262144` |
| `vision` | `{enabled:true, available:true, error:null}` |
| `activity` | `requests=19`、`in_flight=0` |
| `last_timings` | `prompt_n=13995`、`prompt_per_second=462.5`、`predicted_per_second=37.3`、`draft_n=370 / accepted=303` |
| `machine.gpu` | `name=Radeon Instinct MI50 32GB`、`used 32452 / 32752 MiB`、`util 0%`、`temp 46 C`、`power 16 W` |

---

## 3 运行期进程（容器内 `/proc` 实读）

| 角色 | pid | 内存 | 线程 | 状态 |
|---|---|---|---|---|
| `serve/server.py` | 1 | RSS 333,880 kB (≈326 MiB) | -- | Ssl（父） |
| `/src/build-906/strata`（引擎） | 12 | **VmRSS 99,305,908 kB ≈ 94.7 GiB**；VmPeak 225,273,628 kB ≈ 214.8 GiB | **59** | S |
| `/data/vision/strata-vision` | 9 | RSS 1,641,536 kB (≈1.57 GiB) | -- | S |

**引擎命令行（逐字，与 register 一致）**：
```
/src/build-906/strata --serve --pack /data/packs/huihui-ud-iq4_xs --native /models/.../Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf   --resident-budget-gib 76 --expert-profile /src/data/expert-profile.bin --expert-cache auto   --pcie-frac 0.20 --spec 4 --spec-min-p 0.70 --mtp /data/mtp/rt --max-context 262144   --kv k8v4 --prefill auto --prompt-cache-every 8192   --expert-profile-save /data/profiles/huihui-ud-iq4_xs-learned.bin   --conversation-cache-mib 4096 --vision --mtp-window 8192
```

**关键 env（引擎子进程实读）**：`STRATA_PREFILL_CPU_SHARE=0` [?]（P23 显式关，已生效）、`HSA_OVERRIDE_GFX_VERSION=9.0.6` [?]、`STRATA_SRC=/src` [?]

---

## 4 主机资源

| 项 | 值 |
|---|---|
| loadavg | `0.68 0.94 3.81` |
| 内存 | total 125 GiB / used 51 GiB / available **74 GiB** |
| 磁盘 | `/` 935G，已用 **772G**，可用 163G，**83%** |
| GPU | temp edge 46 C / junction 46 C / memory 45 C；power **17 W**（空闲） |

---

## 5 配置面终审（`verify_config.py`）

**`PASS=26  FAIL=0`**（SKIP 3 项均为 scope=TOOL/PATCH，非 config 项，按设计跳过）

| 面 | 结果 |
|---|---|
| 参数面（P00-P99） | 全 PASS：`--pcie-frac 0.20` / `--spec-min-p 0.70` / `--prompt-cache-every 8192` / `--conversation-cache-mib 4096` / `--kv k8v4` / `--max-context 262144` / `--mtp-window 8192` |
| ENV 面 | `HSA_OVERRIDE_GFX_VERSION 9.0.6` PASS；**`STRATA_PREFILL_CPU_SHARE 0` PASS** |
| 数据面(2) | 容器 Cmd -> LIVE config 映射 PASS |
| 数据面(5) | SETUP_KEYS 17 键全部有着落 PASS |
| 数据面(6) | serve 覆写生效 PASS：`serve-telemetry.py ON 3d464198`、`serve-web-app.js ON 026ceb18`；`/metrics` 出 `gpu_pcie_gen:3 / gpu_pcie_width:16`、`gpu_name= Radeon Instinct MI50 32GB` |

---

## 6 观察项（非缺陷）

1. **磁盘 83%**（772G/935G，余 163G）-- 尚有余量，但接近需关注线。上一轮 W725 已清理释放 3 GB。
2. **`uptime_s=5777` ≈ 1h36m**，与容器 Running 时长吻合；**RestartCount=0** => 本轮**无异常重启**。
3. 引擎 VmRSS ≈ 94.7 GiB（`--resident-budget-gib 76` + 元数据/缓存），与 125 GiB 主机内存搭配 **available 74 GiB**，余量健康。
4. 主机 loadavg 1 分钟 0.68 => **空闲**，无异常负载。

---

## 7 一句话

**生产容器 `strata166-407`（0.1.42 @8090）当前健康：配置面 PASS=26/FAIL=0、服务面 200、运行期三进程在位、无重启、GPU 46 C 空闲。**


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `2e0b572d8a076cdc08914f41c8d69b4e`（字节 4909）。
