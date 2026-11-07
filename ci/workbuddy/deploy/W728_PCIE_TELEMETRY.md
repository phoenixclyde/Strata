# W728 ---- Web Monitor 的 PCIe 卡片：根因、修法与落地

- 日期：2026-10-09 21:1x - 21:3x（本机时间）
- 缘起：机主报「pcie 现在还是没数据」（W726 只做了根因定位与上游候选登记，未修）
- **结论**：根因是上游 `_Amd.read()` **完全不读 pcie**（只有 NVML 分支读）。**修点只有一处**，
  已改为 21 行 patch 并在生产落地 => 重启后 `/metrics` 出现
  `gpu_pcie_gen=4 / gpu_pcie_gen_max=4 / gpu_pcie_width=16`，页面显示 **Gen4 / x16**。
  核验器新增**数据面 (6)** 守这个覆写（**PASS=25 FAIL=0**），并做了反事实自证。

---

## 1 症状与根因（精确到行）

`/metrics` 修前：

```json
"hardware": {"cpu":..., "gpu_util":..., "gpu_mem_used":..., "gpu_temp":..., "gpu_power":...,
             "ram_used":..., "disk_read_mb":...}          <- 没有 gpu_pcie_gen / gpu_pcie_width
"history":  {"gpu_pcie_rx_mb": [null, null, ...]}
```

`app.js:293-297` 的 PCIe 卡片正是读这两个：

```js
const gen = hw.gpu_pcie_gen_max || hw.gpu_pcie_gen;
setMetric("pcie", gen ? `Gen${gen}` : null, hw.gpu_pcie_width ? `x${hw.gpu_pcie_width}` : "", ...);
spark("sp-pcie", h.gpu_pcie_rx_mb);
```

=> `gen` 为假 => 整张卡是 null。

**根因**（`telemetry.py`）：

| 位置 | 内容 |
|---|---|
| `_Nvml.read()` `:97-103` | 设 `pcie_gen` / `pcie_gen_max` / `pcie_width` / `pcie_rx_mb` / `pcie_tx_mb` |
| `_Amd.read()` `:169-182` | 只返回 `util` / `mem_used` / `mem_total` / `temp` / `power` / `power_limit` ---- **一个 pcie 键都没有** |

**关键：修点只有一处。** `Telemetry.sample()` 的映射**不是白名单**：

```python
s.update({f"gpu_{k}": v for k, v in g.items()})     # 上游原文 :335（本站 v5 :461）-- W735 更正，原写 :328
```

reader 返回什么就透传什么 => **只要 `_Amd.read()` 多返回三个键，`/metrics` 自动就有**，
`sample()` / `snapshot()` / `app.js` 一行都不用动。

---

## 2 改动（= 上游候选 2 的 patch 正文）

新增一个静态方法 + `read()` 里加三行（共 **21 行 diff**，`deploy/tmp/` 下有原版与改后件可逐行对）：

```python
    @staticmethod
    def _link_gen(path):
        """The PCIe link generation from an amdgpu link-speed file ("16.0 GT/s PCIe" -> 4), or None.
        The file holds the negotiated speed while the card is up; amdgpu has no PCIe throughput counter."""
        try:
            with open(path, encoding="utf-8") as f:
                return {2.5: 1, 5.0: 2, 8.0: 3, 16.0: 4, 32.0: 5, 64.0: 6}[float(f.read().split()[0])]
        except (OSError, ValueError, TypeError, IndexError, KeyError):
            return None
```

```python
        out["pcie_gen"] = self._link_gen(os.path.join(self.dev, "current_link_speed"))
        out["pcie_gen_max"] = self._link_gen(os.path.join(self.dev, "max_link_speed"))
        out["pcie_width"] = self._int(os.path.join(self.dev, "current_link_width"))
```

另更新模块 docstring 与类 docstring 各一处（说明 AMD 侧也读链路了）。

**为什么不读吞吐（`pcie_rx_mb`）**：amdgpu 只有 `/sys/class/drm/card0/device/pcie_bw`，
实测是**三个整数**：

```
空载  : 50 0 256      （t=1..5 依次 50 / 50 / 60 / 50 / 82）
负载中: 4571 4709165 256
负载后: 60 0 256
```

第 1 个数随负载变化（像速率）、第 2 个负载时跳到 4.7e6 之后又回 0（既不像单调计数器也不像字节数）、
第 3 个恒为 256。**内核侧无该文件的语义文档，本轮也未能独立坐实单位** =>
按本项目「不凭印象下结论」的规矩**不采用**（`gpu_pcie_rx_mb` 保持 None，卡片只显示链路、不显示 MB/s）。
=> 这是**有意的留白**，不是遗漏。

---

## 3 落地方式与风险（**引擎补丁面仍为 0**）

`/src` 是容器的**可写层**（不是 bind mount：Binds 只有 `data` 与 `models`）=> 覆写写进去后
**`docker restart` 可存活，但容器一重建就丢**。所以落到三件套：

| 件（166 `/home/albus/strata166/patches/`） | 作用 |
|---|---|
| `serve-telemetry.py.orig`（16643 B，md5 `e0a011fe...`） | 上游原文持久留档 |
| `serve-telemetry.py.patched`（17684 B，md5 `a37b4824...`） | 覆写版持久留档 |
| `apply_telemetry_pcie.sh` | 重建容器后重跑（含 `ast.parse` 语法门 + 打印 md5） |
| `revert_telemetry_pcie.sh` | 一键回滚到上游原文（+ `docker restart`） |
| `check_telemetry_pcie.sh` | 打 `OVERLAY=ON/OFF`，重建后一眼可判 |

**账实一致**：`MEMORY.md §0` 里「补丁面归零」这句必须跟着改 ---- 现在的准确表述是
**引擎补丁面 0 / serve 层本地覆写 1（已登记 + 可一键回滚）**，且这 1 处**由核验器守着**（见 §4）。

---

## 4 实测与核验

**a. 单测**（`_link_gen`，输入取真实 sysfs 字符串）：`16.0 -> 4` / `8.0 -> 3` / `5.0 -> 2` /
`2.5 -> 1` / `32.0 -> 5` / 乱串 -> `None` ---- **6/6 PASS**。

**b. 容器内实测**（改后件 `import` 后跑真实 sysfs）：

```
ok    = True
dev   = /sys/class/drm/renderD128/device
name  = Radeon Instinct MI50 16GB
read  = {..., 'temp': 46.0, 'power': 17.0, 'power_limit': 225.0,
         'pcie_gen': 4, 'pcie_gen_max': 4, 'pcie_width': 16}
```

**c. 落地后端到端**（`docker restart strata166-407`，15 s 就绪）：

```json
"hardware": {..., "gpu_pcie_gen": 4, "gpu_pcie_gen_max": 4, "gpu_pcie_width": 16}
```

`docker logs` 近 200 行**无 traceback**；`check_telemetry_pcie.sh` => `OVERLAY=ON`。

**d. 核验器新增数据面 (6)**（`scope=PATCH` 行 -> 判"在位 + 生效"，两侧 md5 与效果值全部现算）：

```
X00   (数据面6) serve 覆写 serve/telemetry.py   PASS   容器内 md5 == 持久留档 a37b4824451b；
                                                      /metrics 效果键 "gpu_pcie_gen":4 "gpu_pcie_width":16
PASS=25  FAIL=0
```

**e. 判据非空性自证**（**不重启**即可判，因为比对的是文件 md5）：

| 步骤 | 数据面 6 | 总计 |
|---|---|---|
| 覆写在位（现状） | **PASS** | PASS=25 FAIL=0 (rc=0) |
| **反事实**：换回上游原文 | **FAIL** ---- `覆写不在位 ... 重跑 apply_telemetry_pcie.sh` | PASS=24 FAIL=1 (rc=1) |
| 复原 | **PASS** | PASS=25 FAIL=0 (rc=0) |

=> **判据非空**：它真能在"容器重建导致覆写丢失"时响，而不是恒 PASS。

---

## 5 副产品：一个值得留意的硬件读数

`current_link_speed = 16.0 GT/s` / `current_link_width = 16` => MI50 那条链路**协商在 Gen4 x16**。
而路径是 `00:02.0 -> 03:00.0 -> 04:00.0 -> 05:00.0`（一串 PCIe bridge/switch），
宿主 CPU 是 Xeon E5-2696 v4（Broadwell，PCIe 3.0 世代）---- 与"整条链路都到 Gen4"需要解释，
但**这属于硬件侧问题，本轮只登记读数、不下结论**（另：`card2` 是另一张设备，`2.5 GT/s x8`，与本卡无关）。

---

## 6 上游候选 2 升级

W726 时候选 2 只是"sysfs 有数据、代码没读"的空口建议；本波把它变成了**已实测的 patch**
（21 行 diff + 单测 + 端到端 + 反事实）。将来提上游时直接用 §2 的正文。

**待办的对外件数不变，仍是 3 件**（2 PR + 1 feature request）---- 本条本来就是那 2 个 PR 之一，
只是**证据强度提高了**（从"建议"变成"我们已在 gfx906 上跑通"）。

---

## 7 落盘

| 件 | 变动 |
|---|---|
| `166:/src/serve/telemetry.py` | **本地覆写**（md5 `a37b4824...`）；原文留档 `166:patches/serve-telemetry.py.orig` |
| `166:patches/{apply,revert,check}_telemetry_pcie.sh` | 三件运维脚本（重建后重跑 / 一键回滚 / 一眼可判） |
| `deploy/tmp/_w728_telemetry_{pristine,patched}.py` | 原版与改后件（可逐行 diff） |
| `deploy/params/PARAM_REGISTER.tsv` | 新增 **X00 `PATCH serve/telemetry.py (本地覆写)`**；**50 行 / ADOPTED 24 / REJECTED 25 / CANDIDATE 1**；两侧 md5 `43fdcc1d...`；备份 `.bak_w728_*` |
| `deploy/params/verify_config.py` | 新增**数据面 (6)** + `patch_state()`；docstring 六面 |
| `deploy/params/generated/*.json` | **未变**（`--live` 无差异） |
| `deploy/W728_PCIE_TELEMETRY.md` | 本件 |

**166 终态**：`-407` Up、HTTP 200、`verify_config.py` **PASS=25 FAIL=0**、无异常日志；
config 未变、`-406` 仍是回滚位。

---

## 8 追加：机主质疑「你确定 pcie 是这么显示？」---- 真机渲染复核（2026-10-09 21:3x）

**方法**：不再靠读代码推断，直接用本机 Chrome **无头渲染真机页面**并截图：

```
chrome.exe --headless=new --disable-gpu --no-sandbox --user-data-dir=<tmp>
           --virtual-time-budget=15000 --dump-dom          http://192.168.50.166:8090/#monitor
chrome.exe ... --window-size=1500,1400 --screenshot=...     （同上）
```

证据件：`deploy/tmp/_w729_dom.html`（34935 B，渲染后的 DOM）· `deploy/tmp/_w729_monitor.png`（100292 B，截图）。

**结果（DOM 原文）**：

```html
<span class="st-metric__value" id="mv-pcie">Gen4<small>x16</small></span>
<span class="st-metric__sub"   id="ms-pcie"></span>
```

同页对照（同一时刻的真实取值）：GPU load `0%`（副行 `Radeon Instinct MI50 16GB`）· VRAM `31.6 / 32 GB`（副行 `9,757 experts cached`）·
GPU temp `45 °C` · Power `17 W`（副行 `of 225 W limit`）· PCIe **`Gen4` + 小号 `x16`** · CPU `3%`（副行 `22 cores · 44 threads`）·
Disk read `0.0 MB/s`（副行 `write 12.3 MB/s`）。

**=> 「PCIe 显示 Gen4 x16」成立**，截图可见。但要把措辞**精确化**（我上一条说粗了）：

1. **不是**一行 `Gen4 / x16` 文本。`setMetric(key, value, unit, sub)` 的渲染是
   `mv-<key>.innerHTML = value + <small>unit</small>`、`ms-<key>.textContent = sub`
   => 实际是**主值 `Gen4` + 小号 `x16`**，**副行是空的**（因为 `gpu_pcie_rx_mb == null` 时 sub 给空串）。
2. `METRICS` 里 pcie 那条的静态 `unit` 是 `""` ---- **卡片模板根本不用 `m.unit`**，单位一律由 `setMetric` 第三参传入。
3. **sparkline 仍是一条贴底的直线**：它的数据源是 `series: "gpu_pcie_rx_mb"`，而该 series 实测
   **60/60 全 None**；`spark()` 把 `null` 当 0 => 顶值退化到 `1e-9`，所有点 y=30 => 画一条贴底线。
   **视觉上与 GPU temp / Power 那种"稳定值"一样**，不会像"缺数据"（缺数据时主值是 `-`）。
   => 也就是说：**主值那半张卡补上了，吞吐那半张卡依然空着**（这是 §2 有意的留白）。

**新增查证（本波）**：`pcie_bw` 的语义**内核是有文档的**（kernel.org `driver-misc.html`、ROCm SMI 文档、
以及引入它的原始 commit v4）---- 输出 `"%llu %llu %i"` = **packets-received / packets-sent / mps**
（mps = 最大有效载荷字节数，我机 = 256），估算带宽 = `(received + sent) * mps`。

=> **吞吐在原理上可做**，但**本轮仍不采用**，理由是两条硬的：
- **方向对不上**：我机实测空载 `(50, 0, 256)`、负载中 `(4571, 4709165, 256)`、负载后 `(60, 0, 256)`；
  两个计数差 1000 倍。而本工作负载是 **host -> VRAM 送专家**（GPU 是**收**的一方），
  按文档顺序（先 received）读出来的方向跟直觉相反 => **顺序需要一次独立标定**，不能凭文档一句话就写死。
- **字段名会错标**：`telemetry.py` 的字段是 `pcie_rx_mb`，前端标签是 `to GPU X MB/s`；
  把"合计"或方向不明的数塞进去 = **主动写一个错标签**，比留白更坏。

**要补的话需要什么**（留给下一波，若机主要在）：一次标定 ---- 用引擎自报的专家搬运量
（`experts streamed N (N by DMA, host X ms)` 或请求记录里的 `pcie_share`）与 `pcie_bw` 的增量对账，
钉死"哪个计数是 RX"与 `mps` 的单位，再决定填 `pcie_rx_mb`。

> **[!] 本节（§8）的"不采用"结论已被 §9 推翻** ---- 语义由**内核源码**钉死了，吞吐已经做出来并落地。

---

## 9 机主三连质疑后的逐值审计与三处更正（2026-10-09 21:4x - 22:0x）

机主原话：「你这里面有很多值都取错了。你的显卡型号取得哪？你所有的数据都在机器也就是166上有实际依据吗？
pcie那个肯定不对。你不会都是写得死数据吧？你重新来」，随后又给出上游的 Monitor 参考图。

**方法**：不再只盯代码 ---- 做**逐值回溯 + 独立通道交叉核对 + 动态证明 + 与上游参考图对比**。

### 9.1 逐值审计表（每个显示值 -> 代码路径 -> 166 原始来源 -> 独立复核）

| 卡片 | 显示（同一刻） | 代码路径 | 166 上的原始来源 | 独立复核（另一条通道） | 判定 |
|---|---|---|---|---|---|
| Model state | Idle / Generating | `/metrics.live.state` | 服务状态 | -- | 一致 |
| Speed / Prefill | 26.6 / 44 t/s | `live.tok_s` / `prefill_tok_s_mean` | 引擎 | 长生成实测 40-58 t/s | 一致 |
| GPU load | 0 % / 99 % | `gpu_util` <- `_Amd.read()['util']` <- `gpu_busy_percent` | `/sys/.../gpu_busy_percent` | 生成中 99-100 | 一致 |
| 副行 型号 | `Radeon Instinct MI50 16GB` | `hardware_static.gpu_name` <- `_Amd.name()` <- **`product_name`** | `/sys/class/drm/card0/device/product_name` | `sudo lspci`: `Vega 20 [Radeon Pro VII/Radeon Instinct MI50 **32GB**]`；`rocm-smi`: `gfx906` / `0x66a1`；VRAM 34,342,961,152 B = 32 GiB | **字符串与实物不符** |
| VRAM | 31.6 / 32 GB | `gpu_mem_used` / `gpu_mem_total` <- `mem_info_vram_used` / `_total` | 33,895,923,712 / 34,342,961,152 | `rocm-smi` 同两值，逐字节相同 | 一致 |
| 副行 | 9,757 experts cached | `engine.expert_slots` | 引擎 info | 引擎日志 `expert cache 9757 slots` | 一致 |
| GPU temp | 52 °C | `hwmon/temp1_input`（m°C / 1000） | 52000 | `rocm-smi` Sensor edge 52.0 | 一致 |
| Power | 133 W（of 225 W limit） | `hwmon/power1_average` / `power1_cap` | 133 / 225 | `rocm-smi` 同值 | 一致 |
| **PCIe** | **Gen3 x16 / to GPU 508 MB/s** | 见 §9.2 / §9.3（本波改的） | `link()` + `pcie_bw` | `sudo lspci -vv` 全链；内核源码 | **本波修** |
| CPU | 40 % | psutil | -- | -- | 一致 |
| Disk read | 4.0 MB/s（write 0.0） | psutil `disk_io_counters` | -- | -- | 一致 |
| Context fill | 199 / 256K | `engine.max_context` / `live.prompt_tokens` | config `--max-context 262144` | register P03 | 一致 |
| System RAM | 43.6 / 126 GB | psutil `virtual_memory` | 134,952,771,584 B（125.7 GiB） | -- | 一致（上游按 GiB 显示） |
| Conversation cache | 0 / 4 · 0.0 / 4.0 GB | config `--conversation-cache-mib` | register P31 | -- | 一致 |
| Recent requests | 长生成后逐条出现 | `self.history`（`server.py:3685` 无条件 append） | 服务 | §9.4 | 一致 |

=> **结论**：15 项里 **13 项逐值可回溯且经独立通道复核一致**；**2 项有问题** ---- `PCIe`（1 处显示错 + 1 处设计错，见 §9.2）
与 **型号串**（板载 FRU EEPROM 串写 16GB，实物是 32GB 卡；归属见 §9.5，W733 已更正此前的"VBIOS 串"说法）。

### 9.2 PCIe 那一格：两处错，逐条更正

**(a) 我把"设备自身那一跳"当成了"整条链路的链路"。** 用 `sudo lspci -vv`（独立工具，不是 amdgpu）拿到全链：

| BDF | 角色 | LnkCap | LnkSta（实况） |
|---|---|---|---|
| `00:02.0` | CPU 根口（Broadwell） | 8 GT/s x16 | **8 GT/s x16** |
| `03:00.0` | AMD 桥（卡上 PLX） | 16 GT/s x16 | **8 GT/s (downgraded) x16** |
| `04:00.0` | AMD 桥（卡内） | 16 GT/s x16 | 16 GT/s x16 |
| `05:00.0` | **MI50 本卡** | 16 GT/s x16 | 16 GT/s x16 |

=> sysfs 在 `05:00.0` 读到 16 GT/s 是**真的**，但它只是**最后一跳**；**瓶颈是 Gen3 的根口**，
所以 host<->VRAM 的实际上限是 **Gen3 x16 约 15.75 GB/s**，不是 Gen4 x16 的 31.5 GB/s。
**改成路径瓶颈**（`link()` 取每跳 `max_link_speed` / `max_link_width` 的**最小值**；用 `max_` 以免省电降速把读数压低）
=> 卡片显示 **Gen3 x16**，同时在 `/metrics` 留 `gpu_pcie_own_gen = 4`（本卡跳是 Gen4，与瓶颈不同时才说明问题）。

**(b) 我一度改了 `app.js` 把主值换成吞吐 ---- 已还原。** 机主给出上游 `docs/media/runpagoda.png`（维护者自己的 Monitor），
形状一目了然：**主值 = `Gen4 x16`（静态链路）**、**副行 = `to GPU 13.237 MB/s`（实时吞吐）**、sparkline 走
`series: "gpu_pcie_rx_mb"`。=> 正确做法是**别动 `app.js`**，只把实时吞吐填进上游本来的字段。
容器内 `app.js` 现为**上游原文**（md5 `476da51688ecaa2f2541789e5fa503f3`），patch 面收回到**单文件 `telemetry.py`**。

### 9.3 吞吐怎么来的（语义由内核源码钉死，不是猜的）

- `pcie_bw` = `"<received msgs> <posted requests sent> <mps>"`：`soc15.c` 里 `EVENT0_SEL = 40`（注释 `# received msgs`）、
  `EVENT1_SEL = 108`（注释 `# of posted requests sent`）；内核文档（`driver-misc.rst`）**只给这三个值的含义与"用于快速估算"，并未给出该公式** ---- 公式是据此推导的（**W735 更正**：原写"文档给的带宽估计"，署名不实）；事件源 `EVENT0_SEL=40 / EVENT1_SEL=108` 由 `soc15.c` 独立证实。
- 本卡实测：空载 `(50, 0, 256)`；长生成中 `(4571, 4709165, 256)`。
- **`received` 单独只有约 1 MB/s，而 GB 级专家搬运落在 `posted requests sent` 上** => 取文档的**合计**
  （注释里写明为什么），否则卡在忙时会显示 "1 MB/s"，看着像坏的。
- **读一次阻塞约 1 秒**（驱动 `msleep(1000)` 计数；实测 1022-1154 ms，其它 sysfs 仅 3 ms）
  => 放**独立线程** `_bw_loop`，5 s 刷一次并缓存给 1 Hz 采样器；否则 Monitor 所有序列会降到 0.5 Hz。

### 9.4 动态证明（回答"是不是死数据"）

同一页面，空闲 vs 长生成中（1800 token），各自无头渲染：

| 项 | 空闲（`_w729_monitor.png`） | 长生成中（**`_w732_monitor_busy.png`**） |
|---|---|---|
| Model state | Idle | Generating · 26.6 t/s |
| Speed | `-` | 26.6 t/s（副行 Prefill this request 44 t/s） |
| GPU load | 0 % | **99 %** |
| GPU temp | 45 °C | **52 °C** |
| Power | 17 W | **133 W** |
| CPU | 3 % | **40 %** |
| Disk read | 0.0 MB/s | 4.0 MB/s |
| **PCIe** | `Gen3 x16` · `to GPU 0.0 MB/s` | `Gen3 x16` · **`to GPU 508 MB/s`** |
| 各卡 sparkline | 平线 | 全部起波形 |

`history.gpu_pcie_rx_mb`：**60/60 非 None**，min 0.01 / max 159.64。=> **不是死数据**。

### 9.5 顺带查实（不改，只登记）

- **同机有三块"显卡"**：MI50（AMD `05:00.0` = `card0` = `renderD128`，驱动 amdgpu）、
  **RTX 2070**（NVIDIA `07:00.0` = `card2`，驱动 nvidia）、**ASPEED BMC VGA**（`09:00.0` = `card1`，驱动 ast）。
  §5 里把 `card2` 的 `2.5 GT/s x8` 只说成"另一张设备" ---- 现在知道那是 **2070 空闲降速**。
- **型号串**：`product_name` = `Radeon Instinct MI50 16GB`，
  而 PCI ID `1002:66a1` + `lspci` 的 ID 名 + VRAM 31.98 GiB 都说是 **32GB** 卡。
  **归属（W733 更正）**：这个串来自 **FRU EEPROM**，不是 VBIOS 串 ---- 依据是内核文档
  （`docs.kernel.org/.../amdgpu/driver-misc.html` 原文 "returns the product name **as returned from the FRU**"）
  加上本机同族字段齐备（`product_number` = `102-D16314-13`、`serial_number` = `692112000711`、
  `fru_id` = `113-AMDD16314130A100-1.02`、`manufacturer` = `AMD`；这几个只由 FRU 提供）。
  => 上游 `_Amd.name()` 只是**照抄板子的 FRU 数据**，既不是驱动在判断 SKU，也不是上游的 bug。
  **本轮不改**：改它就得按卡硬编码容量，会坑 16GB MI50 / Radeon Pro VII / MI60 等其它用户；
  容量的真值本来就已经由 VRAM 那一格（`/ 32 GB`）显示出来了。**这不是我们的缺陷，是这块板的 FRU 数据如此。**
- **对 `--pcie-frac` 的含义**：有效链路是 15.75 GB/s 而不是 31.5 GB/s ---- 这解释了 W716 里
  "专家几乎全在 cache、PCIe 不是瓶颈"（实测流量 0.5-1.2 GB/s，远未打满 Gen3）。

### 9.6 本波落盘

| 件 | 变动 |
|---|---|
| `166:/src/serve/telemetry.py` | 覆写为定稿（md5 `a6d2d2d8...`）；原文留档 `patches/serve-telemetry.py.orig` |
| `166:/src/serve/web/app.js` | **还原为上游原文**（md5 `476da516...`）；原文另留档 `patches/serve-web-app.js.orig` |
| `deploy/tmp/` | 证据：`_w729_monitor.png`、`_w732_monitor_busy.png`、`_w729_dom.html`、`_w732_dom_busy.html`、`_w731_runpagoda.png`（上游参考图）、`_w732_telemetry_final.py`、`_w728_telemetry_{pristine,patched_v1_deviceonly}.py`、`_w730_telemetry_patched_v2.py` |
| `deploy/params/PARAM_REGISTER.tsv` | X00 evidence/verdict 重写；50 行 / 24-25-1；两侧 md5 `d799a895...` |
| `deploy/W728_PCIE_TELEMETRY.md` | 本节 |

---

## 10 追加（2026-10-09 22:0x，W733）---- 归属更正 + 覆写加固 + 对外影响评估

### 10.1 三处更正

1. **`product_name` 的归属**：§9.5 写的"VBIOS 串"**错了** ---- 它是 **FRU EEPROM** 串（内核文档原文
   "as returned from the FRU"；本机 `product_number` / `serial_number` / `fru_id` / `manufacturer` 四个
   同族 FRU 字段齐备）。"VBIOS" 这个说法在本报告与 register 里都已改掉。
2. **`W724_UPSTREAM_PR.md` §10 里的 "MI50 16GB" 是我写错的** ------我们这台机器是 **MI50 32GB**
   （PCI ID `1002:66a1` + lspci 名 + VRAM 31.98 GiB）。已改。**这正是把"型号串"当真值采信的后果。**
3. **§9.6 表里的覆写 md5 已过期**：现为 v4 `7433869abef54c8fba0012ca9fad59db`（见 §10.2）。

### 10.2 覆写加固到 v4（本波改的两处）

| # | v3 的隐患 | v4 的处置 |
|---|---|---|
| 1 | `sample()` 里 `s["gpu_pcie_rx_mb"] = self._bw[1]` **无条件覆盖** ---- 多卡机（issue #112）下会把上游**逐卡求和**的合计换成**卡 0 一个数** | 改成**逐卡读数求和**，且只在**全部**卡都是 amdgpu-sysfs 读者时才接手该字段；混合机型完全不碰 |
| 2 | `link()` 对**读不到的 hop 静默跳过** => `/sys` 被裁剪时报本卡 Gen4 冒充整条链（**偏乐观**） | 新增 `pcie_path`（如 `4/4`）；**只有全链可读**才声称瓶颈，否则回退本卡自身链路并在 `pcie_path` 标明 |

单测 **23/23 PASS**（Linux 侧用假 sysfs 树跑真代码路径：`amd_device_dir` -> `_hops` -> `link`；
含反事实"根口文件读不到" => 回退 + `pcie_path 2/3`；含多卡聚合三态）。

### 10.3 对别的用户意味着什么（机主之问）

**不会崩**：全部读取都有 fallback（`_read` / `_int` / `_gen` 各自吞 `OSError`/`ValueError`），
`_bw_loop` 外层再包 `except Exception`；NVIDIA 路径**完全不受影响**（默认 `amd=False`，且 `bw` 只有 `_Amd` 有）。
**但有三处会给出"不准确"的读数**（第 1、2 条本波已修，第 3 条无解）：

1. **多卡合计被单卡值顶掉**（已修，见 §10.2）
2. **路径不全时偏乐观**（已修，见 §10.2）
3. **方向口径**：`pcie_rx_mb` 在 NVML 那边是**纯 RX**（`NVML_PCIE_UTIL_RX_BYTES`），
   而 AMD 只有 `pcie_bw`，内核给的是 `(received + sent) * mps` 的**双向合计**，**没有方向可拆**
   （本卡实测 `received` 单独只有 ~1 MB/s，而 GB 级专家搬运落在 `posted requests` 上）
   => 同一个字段在 AMD 上含义是"总流量"，而前端副行文案写的是 `to GPU X MB/s`。**这条改不了**，
   只能据实标注；所以**这份覆写只适合自用，不应原样提上游**。

**正确的提法**（若要提）：按"一个 PR 一件事"拆成两件 ---- ① 链路（`link()` + `pcie_path`，口径无歧义）
② 吞吐（必须同时提出口径问题：要么改名、要么前端文案改成不含方向的 "PCIe X MB/s"）。

### 10.4 为什么一开始没抓到（过程分析）

- W726 之前 `gpu_name` **一直是 `null`**（config 缺 `backend`，telemetry 走了 NVML）=> 串根本没出现过。
- W726 修好 `backend` 后，那一波的任务是"把 GPU 数据找回来"，我核的是**有没有值**，不是**值对不对**。
- W729/W730 我把每个**数值**都回溯到了原始文件（util / mem / temp / power 全部一致），
  但 `gpu_name` 是**字符串**，我只回溯到 "`product_name` 的文件" 就停了，**没有做交叉核验**
  （没跟 PCI ID / 实际显存容量 / 硬件标签对）。
- 更根本：**我的核验器只判"配置与运行态是否一致"，从不判"读数与硬件是否一致"**。
  这是同族的第 5 次 ---- W713（核验器硬编码容器名）、W718（ENV 面缺口）、W726（CFG 面全 SKIP）、
  W727（技能 BAN 清单缺 6 码位）、W733（读数 vs 硬件）。**共性永远是"判据的覆盖面"，不是"判据写错"。**
