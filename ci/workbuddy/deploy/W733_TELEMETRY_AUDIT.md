# W733 telemetry 覆写审计 ---- 机主三问（改了什么 / 为什么没抓到 / 会不会坑别的用户）

> 时点：2026-10-09 21:5x ~ 22:1x CST。对象：`http://192.168.50.166:8090/#monitor` 的
> serve 层 `telemetry.py` 覆写与前端 `app.js`。机主三问：① 刚刚是改了还是退回上游，并分析源码意图；
> ② 为什么一开始没抓到型号串的问题；③ 这么改会不会让别的用户抓不到正确数据。

## 0 一句话结论

- **前端 `app.js`：退回上游原文**（md5 与上游**逐字节相同**）。**后端 `telemetry.py`：仍是我们的本地覆写**，
  本波从 v3 加固到 **v4**。
- **型号串写 16GB 而实物 32GB**：它来自**板载 FRU EEPROM**（不是 VBIOS，也不是驱动判断 SKU）。
  **我们不改它** ---- 改了就是按卡硬编码，会坑 16GB MI50 / Radeon Pro VII / MI60 等其它用户。
- **对别的用户：不会崩，但有三处会拿到不准的数** ---- 两条本波已修，一条（方向口径）**无解**
  => **这份覆写不该原样提上游**。

## 1 当前状态（逐字节）

| 对象 | 上游原文 md5 | 我们的现状 | 判定 |
|---|---|---|---|
| `src/serve/web/app.js` | `476da51688ecaa2f2541789e5fa503f3`（59,958 B） | **同值**（本机工作副本、166 容器、166 留档三处一致） | **已退回上游，零改动** |
| `src/serve/telemetry.py` | `e0a011fefd954d5c93e433b8e8899799`（16,643 B） | **`7433869abef54c8fba0012ca9fad59db`**（23,243 B，v4） | **本地覆写**，+102/-3 行（删的 3 行全是 docstring） |

`telemetry.py` 的 diff（`difflib` 行级）：上游 372 行 -> v4 488 行；**新增 119 / 删除 3**（372+119-3=488）。**W735 更正**：原写"新增 102 / 删除 3"是 **v3** 的增删数（v3 = 372->471），与 v4 的 488 行不自洽。另：**v5 = 新增 135 / 删除 4（372->503）**。
删除的 3 行**全部是文档字符串**；**`name()` 一个字都没动**（`grep product_name` 在增删两侧均无命中）。

覆写位置与回滚（166）：

```
/src/serve/telemetry.py                                  <- 容器**可写层**，重建即丢
/home/albus/strata166/patches/serve-telemetry.py.orig     <- 上游原文留档
/home/albus/strata166/patches/serve-telemetry.py.patched  <- 我们的 v4
/home/albus/strata166/patches/serve-telemetry.py.patched.v1_deviceonly / .v3_*  <- 历史版本
bash patches/apply_telemetry_pcie.sh    # 重建后重跑
bash patches/check_telemetry_pcie.sh    # 判 OVERLAY=ON/OFF
bash patches/revert_telemetry_pcie.sh   # 一键回滚
```

## 2 上游源码意图（三处，附原文）

### 2.1 `_Amd.name()` ---- 意图是"照抄板子的产品名"，不是"识别 SKU"

```python
    def name(self):
        try:
            with open(os.path.join(self.dev, "product_name"), encoding="utf-8") as f:
                return f.read().strip() or "AMD Radeon"
        except (OSError, TypeError):
            return "AMD Radeon"
```

它做且只做一件事：把 amdgpu 暴露的 `product_name` sysfs 文件读出来（读不到就退成 `"AMD Radeon"`）。
`product_name` 的**定义**在内核文档（`docs.kernel.org/.../gpu/amdgpu/driver-misc.html`）：

> The amdgpu driver provides a sysfs API for reporting the product name for the device.
> The file `product_name` is used for this and returns the product name **as returned from the FRU**.
> NOTE: This is only available for certain server cards.

=> 它是**板载 FRU EEPROM 里烧的字符串**，由内核原样转出。**既不是驱动在判断 SKU，也不是上游在猜型号。**
本机同族 FRU 字段齐备，佐证这条链：`product_number` = `102-D16314-13`、`serial_number` = `692112000711`、
`fru_id` = `113-AMDD16314130A100-1.02`、`manufacturer` = `AMD`。**（此前我写的"VBIOS 串"是错的，已更正。）**

### 2.2 `read()` ---- 意图是"两个后端交同一组读数"

`_Nvml.read()`（`:97-103`）交 5 个 PCIe 键：`pcie_gen`（当前代）/ `pcie_gen_max`（最大代）/
`pcie_width` / `pcie_rx_mb`（`NVML_PCIE_UTIL_RX_BYTES`，**纯 RX**）/ `pcie_tx_mb`。
`_Amd.read()`（`:169-182`）**一个 PCIe 键都不交** ---- 上游的注释自己写着 AMD 后端到
"load, VRAM, temperature and power" 为止。

=> **AMD 侧的 PCIe 卡片全空，是上游的一个功能缺口**（不是配置错），与 W726 那个 `backend` 缺项是两回事。

### 2.3 `sample()` ---- 透传，所以修点很小

```python
            s.update({f"gpu_{k}": v for k, v in g.items()})
```

**不是白名单**：reader 交什么键，`/metrics` 与前端就能看到什么。=> 修点**只需在 `_Amd` 内**，
`/metrics` 与 `app.js` 一行都不用改。这也是为什么本波能只动一个文件。

### 2.4 PCIe 卡片的原设计（上游自己的截图 `docs/media/runpagoda.png`）

维护者的 RTX 5070 上，PCIe 卡是：**主值 `Gen4` + 小字 `x16`（静态链路）**、**副行 `to GPU 13.237 MB/s`（实时，变动）**、
sparkline 走 `gpu_pcie_rx_mb`。=> **主值本来就该是链路，副行才是吞吐**；我一度把主值改成吞吐，
是把设计看反了（已还原）。

## 3 型号串：16GB 从哪来，为什么一开始没抓到

### 3.1 出处（三条独立证据）

| 来源 | 值 | 说的是几 GB |
|---|---|---|
| `product_name`（**FRU EEPROM**） | `Radeon Instinct MI50 16GB` | **16** |
| `lspci -nn`（独立通道） | `Vega 20 [Radeon Pro VII/Radeon Instinct MI50 **32GB**] [1002:66a1]` | 32 |
| `mem_info_vram_total` | 34,342,961,152 B = **31.98 GiB** | 32 |

=> **两票对一票，实物是 32GB**；那一票（板子的 FRU 字符串）与实物不符。
FRU 是**板厂烧进去的**：这块板（或它的 FRU 烧录）就是这样。**不是驱动 bug，也不是上游 bug。**

### 3.2 为什么一开始没抓到（四条，按时间）

1. **W726 之前，`gpu_name` 一直是 `null`**：config 缺 `backend: hip`，telemetry 走了 NVML 分支，
   本机没有 `libnvidia-ml.so.1` => `server.py:3146` 的 `if static.get("gpu_name") else None` 让整段变 null。
   **串根本没在页面上出现过，无从发现。**
2. **W726 修好 `backend` 后**，那一波的目标是"把 GPU 数据找回来"。我核的是**有没有值**，不是**值对不对**。
3. **W729/W730 做逐值回溯时**，数值项（util / mem_used / mem_total / temp / power）我都回溯到原始文件
   并做了独立通道复核（`rocm-smi` 逐字节相同）；但 `gpu_name` 是**字符串**，我只回溯到
   "它来自 `product_name` 文件" 就停了 ---- **没有做交叉核验**（没跟 PCI ID / 显存容量 / 硬件标签对）。
4. **更根本**：我的核验器（`verify_config.py`）只判"**配置与运行态是否一致**"，
   从不判"**读数与硬件是否一致**"。这属于同族第 5 次：

   | # | 波次 | 缺陷类型 |
   |---|---|---|
   | 1 | W713 | 核验器硬编码容器名 |
   | 2 | W718 | 核验器只查容器 Env，漏了 config 的 env 段 |
   | 3 | W726 | 核验器对 CFG 面全 SKIP => `backend` 漏了 6 个波次 |
   | 4 | W727 | 技能 `mem_slim` 的 BAN 清单缺本项目 6 个码位 |
   | 5 | **W733** | **核验器不判"读数 vs 硬件"** |

   **共性永远是"判据的覆盖面"，不是"判据写错"。**

### 3.3 处置：**不改**

- 改它就得**按卡硬编码**容量（或者把 FRU 串覆盖掉）=> 对 16GB MI50 / Radeon Pro VII / MI60 等其它用户是**引入 bug**。
- **容量的真值已经在页面上**：VRAM 那一格显示 `/ 32 GB`，副行还有 `9,757 experts cached`。
- 上游若想改，正确方向是"**不要依赖单一字符串**"（例如名字与容量分开呈现），**不是**在校验层塞特例。
  => 作为观察留档，不单独开 PR。

## 4 对别的用户的影响（机主之问第 ③ 条）

**先说不会崩**：所有读取都有 fallback（`_read` / `_int` / `_gen` 各自吞 `OSError` / `ValueError`），
`_bw_loop` 外层再包 `except Exception`；**NVIDIA 路径完全不受影响**（默认 `amd=False`，
且 `bw()` 只有 `_Amd` 有 => `hasattr` 判定自然跳过）。

**但三处会给出不准的读数**：

| # | 风险 | 对别的用户会怎样 | 本波处置 |
|---|---|---|---|
| 1 | **多卡合计被单卡值顶掉** | v3 的 `s["gpu_pcie_rx_mb"] = self._bw[1]` **无条件覆盖**，而多卡机（issue #112）上游是**逐卡求和**的 => 显示的是卡 0 一个数，**低估** | **已修**：改逐卡求和；且只在**全部**卡都是 sysfs 读者时才接手该字段，混合机型完全不碰 |
| 2 | **路径读不全时偏乐观** | v3 对**读不到的 hop 静默跳过** => `/sys/devices` 被裁剪的环境（部分容器/虚拟化）会拿本卡 Gen4 冒充整条链 | **已修**：新增 `pcie_path`（如 `4/4`）；**只有全链可读**才声称瓶颈，否则回退本卡自身链路并标明 |
| 3 | **方向口径不符** | `pcie_rx_mb` 在 NVML 是**纯 RX**；AMD 只有 `pcie_bw` = `(received + sent) * mps` 的**双向合计**，**没有方向可拆**（本卡实测 `received` 单独只有 ~1 MB/s，GB 级专家搬运落在 `posted requests` 上）=> 同名字段在 AMD 上是"总流量"，而前端文案写 `to GPU X MB/s` | **无解**，只能据实标注 |
| 4 | **字段语义分叉** | `pcie_gen_max` 在 NVML 是**设备能力**（`nvmlDeviceGetMaxPcieLinkGeneration`），我方 `link()` 给的是**整链瓶颈**（`min(各跳 max_link_speed)`）=> 该字段的"能力"含义在 AMD 侧被改写，上游前端那句 `hw.gpu_pcie_gen < gen ? " · idle GenN"` 在 AMD 侧永不触发 | **W735 审计补记**：属行为差异（我方语义对"预算"更有用），但**必须写进偏差清单**，不能默认无副作用 |

**正确的提法**（若要提上游）：按上游 `AGENTS.md` 的"one change per pull request"拆成两件 ----
① **链路**（`link()` + `pcie_path`，口径无歧义，可独立成立）；
② **吞吐**（必须**同时提出口径问题**：要么改成不含方向的字段名，要么前端文案去掉 "to GPU"）。
**在此之前，这份覆写只适合自用。**

## 5 本波改动与验证

### 5.1 v4 的两处加固（对应 §4 的 1、2 条）

```python
        # 多卡：只在**全部**卡都是 amdgpu-sysfs 读者时才接手该字段；读数逐卡求和
        self._bw_cards = [g for _, g in self.gpus if hasattr(g, "bw")]
        if self._bw_cards and len(self._bw_cards) == len(self.gpus):
            threading.Thread(target=self._bw_loop, daemon=True).start()
...
            if self._bw:
                v = [x for x in self._bw[1] if x is not None]
                if v:
                    s["gpu_pcie_rx_mb"] = round(sum(v), 2)
```

```python
        whole = bool(hops) and read == len(hops)          # 全链可读才声称瓶颈
        gen = min(gens) if (whole and gens) else own_gen
        ...
        return {..., "pcie_path": "%d/%d" % (read, len(hops))}
```

### 5.2 单测（Linux 侧，用**假 sysfs 树**跑真代码路径）

`amd_device_dir` -> `_hops` -> `link` 全部真跑（假树里带真实 colons 的 BDF 目录 + `renderD128/device` 软链）：

- 路径读全：`gen 3 / own_gen 4 / width 16 / pcie_path 3/3`（取瓶颈，不是本卡的 Gen4）
- **反事实**：把根口的 `max_link_*` 删掉 => 回退 `gen 4` + `pcie_path 2/3`（**判据非空**）
- 多卡聚合三态：两卡 `7.0`（不是卡 0 的 3.0）· 一卡读不到 `3.0` · 全读不到 `None`
- 非 AMD 卡 => `_bw_cards` 为空 => **不起线程**

**`PASS=23 FAIL=0`**（中途 1 个 FAIL 是我**判据写错**：多卡路径下上游聚合会先把该键置 `None`，
"不加"不等于"键不存在"；已改成判"值为 None"，见 §7 教训）。

### 5.3 生产实测与复验

- 137 s 重启完成（`ready` 后 45 s 量到 HTTP 200）；`/metrics`：
  `gpu_pcie_gen 3 / gen_max 3 / own_gen 4 / width 16 / **path 4/4** / rx_mb 0.01`（与 v3 逐项相同，单卡场景无行为变化）
- `docker logs` **无 traceback**；`check_telemetry_pcie.sh` => `OVERLAY=ON (7433869abef5...)`
- `verify_config.py` => **PASS=25 FAIL=0**（数据面 6 与持久留档比对，自动跟到新 md5）
- register `X00` 两侧 md5 一致（`36faff7da7149a77591cfd19c5119418`，30,312 B）

## 6 落盘

| 件 | 变动 |
|---|---|
| `deploy/tmp/_w733_telemetry_final.py` | **v4 定稿**（md5 `7433869abef5...`，23,243 B） |
| `deploy/tmp/_w733_telemetry_v3.py` | v3 快照（md5 `a6d2d2d8...`） |
| `166:patches/serve-telemetry.py.patched` | 已换 v4；旧版留 `.patched.v3_*` |
| `deploy/W733_TELEMETRY_AUDIT.md` | 本件 |
| `deploy/W728_PCIE_TELEMETRY.md` | §9.5 归属更正（FRU）；新增 §10（加固 + 对外影响 + 没抓到原因） |
| `deploy/W724_UPSTREAM_PR.md` | §10 更新：v1 片段标"仅存史"、"不含吞吐"的判断被推翻、**MI50 16GB -> 32GB 更正** |
| `deploy/params/PARAM_REGISTER.tsv` | X00 重写（v4 + FRU 归属 + 偏差据实列出）；两侧一致 |

## 7 本波我自己的错（如实记）

1. **归属写错**：把 `product_name` 说成 "VBIOS 串" ---- 是 **FRU EEPROM** 串。
2. **把型号串当真值**：在 `W724_UPSTREAM_PR.md` 的对外文案里写了 "MI50 **16GB**"，而我们的机器是 32GB。
   这正是"采信单一字符串、不做交叉核验"的直接后果。
3. **判据写错**（测试侧）：多卡聚合那一条把"值应为 None"写成"键应不存在"，报了一个假 FAIL。
4. **一处分寸**：最初把 PCIe 卡片主值改成吞吐 ---- 上游自己的截图就写着主值应是链路，**改前端前应先照参考件**。

## 9 W734 追加：机主报的"两张卡片还是不对"（2026-10-09 22:1x）

### 9.1 型号那份 16GB ---- 出处定案 + 处置

**出处 = 板载 FRU EEPROM**（不是 VBIOS，也不是驱动判断 SKU）。三条证据：

| 证据 | 值 |
|---|---|
| 内核文档 `driver-misc` 原文 | `product_name` "returns the product name **as returned from the FRU**. NOTE: This is only available for certain server cards" |
| 同族 FRU 字段在本机**齐备**（这几个只由 FRU 提供） | `product_number` `102-D16314-13` · `serial_number` `692112000711` · `fru_id` `113-AMDD16314130A100-1.02` · `manufacturer` `AMD` |
| 试着走 ROM 反证 | **走不通** ---- `cat /sys/class/drm/card0/device/rom` 报 `Invalid argument`（amdgpu 未解锁 ROM） |

=> 那块板的 FRU 就烧着 `Radeon Instinct MI50 16GB`，而实测是 **32GB**（`1002:66a1` + `lspci` 的 ID 名 + VRAM 31.98 GiB）。

**处置：一致性规则，不是按卡硬编码。** `_Amd.name()` 把名字里的 `NNGB` 与 `mem_info_vram_total`（取整）比对，
**只有不一致才替换**；名字里没有容量 token、或实读读不到，**原样返回**。=> 真 16GB 卡 / Radeon Pro VII / MI60
等其它用户**不受影响**（这条规则可证伪、可测，不是特例表）。单测 **8/8**（含反事实：v4 给 16GB、v5 给 32GB）。

### 9.2 "显示 0.0 但图上有读数" ---- 根因是两个不同的东西叠在一起

**根因 A（真缺陷，本波修）**：上游 `app.js` 的 `spark()` 第 142 行

```js
  const top = Math.max(max || 0, ...v, 1e-9);
```

**没给上限时，y 轴按"该序列自己的最大值"缩放**。而 GPU load（`spark("sp-gpu", h.gpu_util, 100)`）、
温度（90）、CPU（100）、VRAM（总量）、Power（上限）都**给了显式上限**，只有 **PCIe / Speed / Prefill / Disk**
是自动缩放。PCIe 空闲时的真值是 **0.01~0.02 MB/s**（驱动计数粒度：50 包 x 256 B = 12.8 KB/s），
于是这 1 像素级的抖动被放大成 **满幅方波** ---- 真机 busy DOM 的折线 y **只取 {4.0, 30.0} 两个值**（4 = 满幅，30 = 贴底），即被拉到满幅。**W735 更正**："4.00~17.00" 是**合成单测**里的数，不是真机读数，原文混用了。
**图上画的确实是真数据，但幅度是在骗人。**

**根因 B（上游设计，不是错）**：副行文字读的是 **当前瞬时值**（`hw.gpu_pcie_rx_mb`），
而折线是 **最近 60 s 的窗口**；且文字只有 1 位小数，`0.02` 显示成 `0.0`。所有卡片都这样
（GPU load 0% 与它的历史波形同理）。

**处置两处**：① `spark()` 的轴下限 `1e-9 -> 1`（**只降不升**，永远不会裁掉真信号）；
② PCIe 副行改 **2 位小数**，并在窗口峰值 `>= 1 MB/s` 时补一句 `peak X MB/s`（空闲时不出现，免得噪音）。
node 直跑**真函数**单测 **7/7**，含反事实：`1e-9` 时抖动 span = **13.00**（满幅），改成 `1` 后 span = **0.26**（贴底）。

### 9.3 实测（改后）

```
/metrics   gpu_name = 'Radeon Instinct MI50 32GB'      (改前 ...16GB)
无头渲染   #ms-gpu   = Radeon Instinct MI50 32GB
           #ms-pcie  = to GPU 0.01 MB/s                (改前 0.0)
           #sp-pcie line y = 29.48~29.74               (改前真机 y in {4.0,30.0} 满幅方波)
           #sp-gpu  line y = 30.00 平线
verify_config.py  PASS=25 FAIL=0
```

截图：`deploy/tmp/_w734_monitor.png`；DOM：`deploy/tmp/_w734_dom.html`。
**顺带查实**：前端 JS 的真实路径是 **`/web/app.js`**（`/app.js` 返回 404）---- 以后核前端要走对路径。

### 9.4 对别的用户意味着什么

- **`name()` 的一致性规则**：对所有人都是"更准确"，且对 FRU 正确的卡**零改动**。
- **`spark()` 的轴下限**：对所有自动缩放的卡片（PCIe / Speed / Prefill / Disk，NVIDIA 侧同样存在）
  都是**通用改进** ---- 与后端无关，可以单独提上游。
- **telemetry 的吞吐字段**：口径问题未解（§4），**仍不提上游**。

### 9.5 本波落盘

| 件 | 变动 |
|---|---|
| `deploy/tmp/_w734_telemetry_final.py` | **v5**（md5 `3d464198e925926914cbd62c2c4dcf24`）：`name()` 一致性规则 + `import re` |
| `deploy/tmp/_w734_app_js_final.js` | app.js 定稿（md5 `026ceb188117f412a7d320c4657db8c0`）：轴下限 + PCIe 副行 |
| `166:patches/{serve-telemetry.py,serve-web-app.js}.patched` | 已换新；旧版留 `.v4_*` / `.upstream_*` |
| `166:patches/{apply,check}_telemetry_pcie.sh` | **重写为覆盖两个文件**（重建后一键恢复 / 逐文件判 ON-OFF） |
| `deploy/params/verify_config.py` | **数据面 6 扩为逐文件**（两个覆写都守住；含反事实报红） |
| `deploy/params/PARAM_REGISTER.tsv` | X00 更新（两个文件 + v5 + 一致性规则）；两侧 md5 `b917ba1e...` |
| `deploy/W713_PLAN.md` §6.1 | 新增第 22 条 |
