# W726 ---- Web Monitor「很多数据抓不到」：根因定位与修复

- 日期：2026-10-09 20:35 - 20:5x（本机时间）
- 缘起：机主报「http://192.168.50.166:8090/#monitor 似乎很多数据都抓不到」
- **结论**：**我们自己的 config 漏了上游的标准键 `"backend": "hip"`** => telemetry 走 NVML 分支（本机无 NVIDIA 库）
  => **Monitor 的 5 个 GPU 指标全空**（CPU/RAM/Disk 正常）。**已修复并复验**，GPU 数据全部回来。
  另发现**上游一个缺口**：AMD 的 PCIe 读数（sysfs 有、代码没读）。

---

## 1 症状（复现，精确到字段）

`GET /metrics`（web app 的 Monitor tab 就读它）**修前**：

```json
"hardware_static": {"gpu_name": null, "gpu_count": 1, "gpu_note": null,
                    "cpu_name": "Intel(R) Xeon(R) CPU E5-2696 v4 @ 2.20GHz", "cores": 22, "threads": 44, "psutil": true}
"hardware":        {"cpu": 2.1, "ram_used": 48712945664, "ram_total": 134952771584,
                    "disk_read_mb": 0.0, "disk_write_mb": 0.023, "tok_s": 0.0}
"history":         {"gpu_util": [None x60], "gpu_mem_used": [None x60], "gpu_temp": [None x60],
                    "gpu_power": [None x60], "gpu_pcie_rx_mb": [None x60],
                    "cpu": [...有值], "ram_used": [...有值], "disk_read_mb": [...有值]}
```

=> **精确症状：8 个指标里 5 个 GPU 项全空**（GPU load / VRAM / GPU temp / Power / PCIe），
CPU / RAM / Disk 正常 ---- 与机主"很多数据抓不到"吻合。

`app.js:281-297` 的取值证实这是**同一批字段**：

```js
const hw = m.hardware || {}, st = m.hardware_static || {};
setMetric("gpu",   hw.gpu_util == null ? null : ...);      // 空
setMetric("vram",  hw.gpu_mem_used == null ? null : ...);  // 空
setMetric("temp",  hw.gpu_temp == null ? null : ...);      // 空
setMetric("power", hw.gpu_power == null ? null : ...);     // 空
setMetric("pcie",  gen ? ... : null, ...);                 // 空
setMetric("disk",  ...);                                   // 正常
```

---

## 2 根因：config 缺 `"backend": "hip"`

### 2.1 判据链（源码）

```python
# serve/server.py:2984
self.telemetry = Telemetry(..., amd=getattr(self, "backend", None) == "hip")

# serve/server.py:5824
svc.backend = cfg.get("backend")        # "hip": the AMD cards' readings come from sysfs (#301)
```

`backend` 不是"hip" => `amd=False` => telemetry 用 **`_Nvml`**（NVIDIA 的 NVML 库）读 GPU
=> 本机**没有** `libnvidia-ml.so.1` => `_Nvml.ok()` 为假 => **`gpu_name` 为 None** => `server.py:3146`
的 `if static.get("gpu_name") else None` 让整段变 null => **5 个 GPU 指标全空**。

### 2.2 这是**上游必写的键**，不是可选项

| 证据 | 位置 |
|---|---|
| setup 会写它 | `setup.py:5459` `cfg["backend"] = "hip"` |
| 是标准配置键 | `setup.py:3652` `SETUP_KEYS = {... "backend" ...}` |
| 文档记载 | `docs/AMD_HIP.md:303`：`the config's "backend": "hip", "gpu": [1, 0]` |
| CLI 也认 | `docs/AI_SETUP.md:100`：`--backend cuda|hip` |

**而我们的 config（手做的 `gen_config.py` 产物）一直缺它**（`grep -c backend` = **0**）。

### 2.3 不是代码/挂载问题（排除法）

容器内**直接调用** telemetry 的函数，一切正常：

```
amd_device_dir(0)      = /sys/class/drm/renderD128/device
_Amd(0).ok()           = True
_Amd(0).name()         = "Radeon Instinct MI50 16GB"
_Amd(0).read()         = {'util': 0, 'mem_used': 33925976064, 'mem_total': 34342961152,
                          'temp': 45.0, 'power': 17.0, 'power_limit': 225.0}
```

且 **kfd 与 drm sysfs 在容器内都在**（无需额外挂载）：

```
/sys/class/kfd/kfd/topology/nodes = ['0','1']
  node 1: gfx_target_version=90006 simd_count=240 drm_render_minor=128   <- MI50
/sys/class/drm/renderD128/device/gpu_busy_percent = 0 ...（可读）
```

=> **纯配置缺项**。

---

## 3 影响面（`backend == "hip"` 共 9 处 ---- **W735 更正**：原写 8 处，漏了 `server.py:5724` 的 `desktop_vram_note(cfg.get("backend"), ...)` 调用点）

| 位置 | 作用 | 缺它的后果 |
|---|---|---|
| `server.py:2984` | telemetry 的 `amd=` | **GPU 读数全空**（本波症状） |
| `server.py:2367` | `hip_env_guard(env, cfg)` | **#654 的 AMD 环境防护没跑**（HIP_PATH 等两个会让 HIP runtime 崩的环境问题） |
| `server.py:2356` | `HIP_VISIBLE_DEVICES` | AMD 设备编号不设（本机无 `"gpu"` 字段，实际不触发） |
| `server.py:2778` | `free_vram_mib(..., amd=True)` | 空闲显存读取失效 |
| `server.py:5293` | `desktop_vram_note` | 显存不足的用户提示不触发 |
| `server.py:2341` | `hip = cfg.get("backend") == "hip"` | 相关分支不启用 |
| `server.py:2421` | 同上 | 同上 |
| `server.py:5824` | `svc.backend` | 源头 |

---

## 4 修复（走标准通道）

1. `gen_config.py`：**扩展 CFG scope 支持顶层字段**（原只支持 `sect.key` 形式；`backend` 无 `.`）；
   新字段插在 `env` 前，**保持既有键序不变**（diff 最小）。
2. `PARAM_REGISTER.tsv`：新增 **`B00  CFG  backend  hip  ADOPTED`**（41 行；分布 ADOPTED 23）。
3. `gen_config.py --write` => config 新增 `"backend": "hip"`，键序
   `exe,args,cwd,tokenizer,model_name,log,host,port,**backend**,env,vision`。
4. 推 166（register + config，两侧 md5 一致：`67bb2b34...` / `a8706bed...`）-> `docker restart strata166-407`。

**结果**（重启后 **~40s 就绪**）：

```json
"hardware_static": {"gpu_name": "Radeon Instinct MI50 16GB", ...}     <- 原来是 null
"hardware":  {"gpu_util": 0, "gpu_mem_used": 33895919616, "gpu_mem_total": 34342961152,
              "gpu_temp": 46.0, "gpu_power": 17.0, "gpu_power_limit": 225.0, "cpu": 0.7, ...}
"history":   gpu_util 15/15、gpu_mem_used 15/15、gpu_temp 15/15、gpu_power 15/15（非 None）
```

=> **5 个 GPU 指标全部恢复**，sparkline 也有数据了。`verify_config.py`：**PASS=19 FAIL=0**（B00 是 CFG
scope，按设计 SKIP）。

---

## 5 残留（两项，都不是"我们配错了"）

### 5.1 PCIe 卡片仍空 ---- **上游缺口（可提）**

`telemetry.py:97-103` 只在 **`_Nvml`** 里读 pcie（`nvmlDeviceGetCurrPcieLinkGeneration` 等）；
**`_Amd.read()` 完全不读 pcie**。而 **amdgpu 的 sysfs 明明有**：

```
/sys/class/drm/card0/device/current_link_speed = 16.0 GT/s PCIe
/sys/class/drm/card0/device/current_link_width = 16
/sys/class/drm/card0/device/max_link_speed     = 16.0 GT/s PCIe
/sys/class/drm/card0/device/max_link_width     = 16
/sys/class/drm/card0/device/pcie_bw            （存在）
```

=> 在 `_Amd.read()` 里加 4 行即可（解析 `current_link_speed` 的 "16.0 GT/s" 出 gen、`current_link_width` 出 width）。
**列为上游候选 2**（候选 1 = `prefill.cpp:1839` 的宏判据，见 `W724_UPSTREAM_PR.md`）。

### 5.2 独立的请求监控页（`/api-monitor`）默认关

`runconfig.py:35`：`("api_monitor", "bool", "Keep the last 100 requests' prompts and answers in memory for /api-monitor")`；
`server.py:2631` `self.api_monitor = False`（**默认关**），`:5770` 由 config 的 `"api_monitor": true` 或 `--api-monitor` 打开。
=> **这不是 `#monitor`（硬件 tab）**，而是另一个页面；要开需在 config 加 `"api_monitor": true`，
**代价 = 内存里保留最后 100 个请求的 prompt 与答案** => 默认不开，**要由机主决定**。

---

## 6 教训（本项目第 3 次同型）

**核验器只判 CLI / ENV 两个面，CFG 面一律 SKIP** => **配置的"完整性"没有任何判据守着**。
`backend` 这一漏，逃过了：`verify_config.py`（PASS=19 全绿）、此前两轮独立审计、以及多次 config 对比 ----
因为**它不体现在 args/env 里**。

=> 建议（已列入待办）：**给 register 加一个「必备键清单」**（上游 `SETUP_KEYS` 里我们该有的那部分），
让 `verify_config.py` 多一个"config 顶层必备键齐备"的判定面。同族前两次：W713 审计的**容器名硬编码**、
W718 的**核验器 ENV 面缺口**（只查容器 `Config.Env`、漏 config `env` 段）。

---

## 7 落盘

| 件 | 变动 |
|---|---|
| `deploy/params/PARAM_REGISTER.tsv` | 新增 **B00 CFG backend hip**；41 行；两侧 `67bb2b34...`；备份 `.bak_w726_*` |
| `deploy/params/gen_config.py` | CFG scope 支持顶层字段（3 处）；备份 `.bak_w726_*`；md5 `72d490e3...` |
| `deploy/params/generated/strata-huihui-ud-iq4_xs.json` | 新增 `"backend": "hip"`；md5 `a8706bed...` |
| `deploy/W726_MONITOR_BACKEND.md` | 本件 |
| 166 | register + config 已推（两侧一致）；`-407` 已重启（40s 就绪）；两侧备份各留一份 |

> 过程脚本：`C:\Users\clyde\AppData\Local\Temp\_w726*.py`。全程只读诊断 + 一次标准通道修复；未改源码、未装东西。
