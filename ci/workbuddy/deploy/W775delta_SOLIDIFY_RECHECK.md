# W775delta 固化回溯核查 ---- 「该固化的没固化 / 该落生产的没落」双向查（2026-10-11 19:5x）

> 机主令：「回溯一下，有没有该固化的参数没有固化，有没有该落生产的配置没有落。」
> 做法：**全量对照**（生产 config 的每一项 x register status）+ **反向扫**（register verdict 里的判死/采纳信号 x status）。
> 0 发车、生产未动。

## 0 结论（先行）

1. **生产侧无遗漏**：生产 config 的 **17 个 CLI + 3 个 ENV + CFG 键**逐项回 register，**每一旋钮都命中且 status = ADOPTED**（唯一"多命中"的是 `--kv` 与 `--prefill`，见 §1 说明）。`verify_config` **PASS=27 FAIL=0** 与本核查相互独立、结论一致。
2. **发现一处「账实不符」（新，W7 已记）**：`--spec 4` **名不副实** ---- 运行期被 `generate.cpp:2406-2408` 改写为 **`spec=6 / mtp_max=4 / lookup=3`**（`GET /metrics` 硬证）。它**不是**"没固化"，而是**固化的值 ≠ 实际运行值** => 已在 `W750 §0.0` 加警告：**以 `--spec` 为臂的车必须同时钉 `--mtp-max-t`**。
3. **status 收口落差（8 项，建议批量收口但属签字项）**：CANDIDATE 19 个里有 **8 个的 verdict 已含"判死"信号**却仍挂 CANDIDATE（见 §2）。其中 **3 项是"本机形态/配置不匹配"而非永久判死**（`P55`/`P56`/`P47`），需区别对待。
4. **反向查**：REJECTED 34 个里**无一项**带"建议采纳"信号 [OK]（`P59`/`P60` 的 verdict 出现 "CANDIDATE" 字样是被引用的历史表述，非重开主张）。

## 1 生产 config 逐项对照（现算）

### 1.1 CLI args（17 项）

| arg | 值 | register | status |
|---|---|---|---|
| `--pack` | `huihui-ud-iq4_xs` | `P00` | ADOPTED |
| `--native` | `.../Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf` | `P01` | ADOPTED |
| `--expert-profile` | `/src/data/expert-profile.bin` | `P08` | ADOPTED |
| `--expert-cache` | `auto` | `P07` | ADOPTED |
| `--pcie-frac` | `0.20` | `P25` | ADOPTED |
| **`--spec`** | **`4`（cmdline）** | `P05` | ADOPTED ---- **但运行期 = `spec 6 / mtp_max 4`（见 §0.2）** |
| `--spec-min-p` | `0.70` | `P06` | ADOPTED |
| `--mtp` | `/data/mtp/rt` | `P02` | ADOPTED |
| `--max-context` | `262144` | `P03` | ADOPTED |
| `--kv` | `k8v4` | `P04`（+ `P42` CAND / `P50` REF） | **ADOPTED**（三行同名，`P04` 即该项） |
| `--prefill` | `auto` | `P10`（+ `P22` REJECTED） | **ADOPTED**（`P22` 是"`--prefill` 改答案"的另一条裁定） |
| `--prompt-cache-every` | `8192` | `P34` | ADOPTED |
| `--expert-profile-save` | `.../learned.bin` | `P20` | ADOPTED |
| `--conversation-cache-mib` | `4096` | `P31` | ADOPTED |
| `--vision` | (flag) | `P99` | ADOPTED |
| `--mtp-window` | `8192` | `P43` | ADOPTED |
| `--resident-experts` | (flag) | `P66` | ADOPTED |

### 1.2 ENV（3 项）

| env | 值 | register | status |
|---|---|---|---|
| `HSA_OVERRIDE_GFX_VERSION` | `9.0.6` | `P11` | ADOPTED |
| `STRATA_PREFILL_CPU_SHARE` | `0` | `P23` | ADOPTED |
| `STRATA_RESIDENT_HEADROOM_GIB` | `0.5` | `P65` | ADOPTED |

### 1.3 CFG 顶层键

`exe` / `backend` / `vision` 有 register 行且 ADOPTED；其余（`args` / `cwd` / `tokenizer` / `model_name` / `log` / `host` / `port` / `env`）是**结构性键（不是旋钮）**，不在 register 口径内 —— `verify_config` 的 `X00` 面已单独覆盖（SETUP_KEYS 17 键 + serve 覆写 2 项，PASS）。

## 2 status 收口落差（**共 10 项 = 关键词命中 8 项 + 人工补判 2 项**）

> **[!] 口径更正（机主 2026-10-11 19:53 指出）**：本件初稿的表格标题只写「8 项」，漏了紧随其后的「另有 2 项备查」（`P46` / `P47`）=> 实际处置 **10 项**。
> **已执行（2026-10-11 19:5x，机主「你定就好」授权）**：**7 项收口为 REJECTED**（`P41` `P42` `P46` `P61` `P62` `P63` `P67`）+ **3 项保留 CANDIDATE 并加条件注**（`P47` `P55` `P56`）。现计数 `27 ADOPTED / 41 REJECTED / 12 CANDIDATE / 7 REFERENCE`（87 数据行）。

| ID | 名称 | verdict 里的信号 | 我的处置建议 |
|---|---|---|---|
| `P41` | `STRIX_HALO §4` 族 | 不发车 / exact but no gain | **-> REJECTED**（族级已判完：2 实测无增益 + 1 源码判不发车） |
| `P42` | `--lookup-chain` / `--suffix-draft` | 不发车 | **-> REJECTED**（`--suffix-draft` 默认已开；`--lookup-chain K<=2` 空操作） |
| `P67` | `STRATA_STAGER_SSD` 族 | 无增益（B8 车） | **-> REJECTED**（温页缓存下无增益；**"决定性需对称 drop_caches"这一条件已由 B7 取代**：真收益来自 resident 模式） |
| `P61` | `STRATA_ARENA_MMAP` | 机制不匹配 | **-> REJECTED**（本机四条判据全不符、两条方向相反） |
| `P62` | `--vram-reserve-mib` | 机制不匹配 | **-> REJECTED**（为需驱动桌面的卡设计；本机无头专卡） |
| `P63` | `--kv-resident` | 收益路径不成立 | **-> REJECTED** |
| `P55` | `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | 判死 / 不可达 | **保留 CANDIDATE（加条件）** ---- "不可达"是**因 `--kv k8v4`（`kv_mode=3`）**，换 `--kv int8` 即 `active=1`。属**配置条件性**，不是永久死 |
| `P56` | `STRATA_GFX906_ATTN_REDUCE12` | 判死 / 不可达 | **同上**（保留 CANDIDATE + 条件） |

**另有 2 项虽未被关键词命中，但已具备收口条件**（同批处置，**已执行**）：
- `P46`（io-预取族）：`W23` 已判「本机无 decode 杠杆」（`FILL_AHEAD` 启动期 / `FS_AHEAD` 未激活 / `FETCH_THREADS` 只服务文件层 / `IO_PREFETCH` 已 `P54`）=> 建议 **-> REJECTED**。
- `P47`（drafter 族）：`W17B` 判「暂不发车」但**前置缺失**（需代表语料 + decode 轴观测）=> **保留 CANDIDATE + 标注前置**（不宜判死）。

> **[纪律]** 改 status 属**签字项**（`W17B §6` 立的规矩）。且 `CANDIDATE -> REJECTED` **不触碰生产**（`gen_config.py` 只吃 ADOPTED）=> 风险为零，但仍待机主点头。
> 本次**不动 status**，只出清单。

## 3 反向查（该用而未用）

- **REJECTED 34 项**：无一项带"建议采纳"信号 [OK]
- **生产 config 与 `generated/` 与 166**：三方 md5 一致（`ff8cb97379f0bdbe76ee555da6d8729c` / 1,393 B）[OK]
- **配置面之外**：引擎补丁面 **0**、serve 覆写 **2**（telemetry + app.js）均在位且生效（`verify_config` `X00` 面 PASS）[OK]

## 4 复现

```bash
python3 deploy/tmp/_solidify_check.py     # 生产 config x register status 全量对照
python3 deploy/tmp/_verdict_scan.py       # register verdict 的判死/采纳信号扫描
# 运行期账实核对（spec 那处）：
ssh albus@192.168.50.166 'curl -s http://127.0.0.1:8090/metrics' | python3 -m json.tool | sed -n '1,25p'
```

## 5 局限

- 本核查只覆盖**参数/配置面**；"该落生产但属于代码/容器层"的项（如引擎补丁）由 `verify_config` 的 `X` 面覆盖，本件只引用其结论。
- §2 的"收口建议"基于 **verdict 文本的关键词** + 逐条人工判断；`P55`/`P56`/`P47` 的"条件性保留"是我的判断，可被推翻。
- `--spec` 的账实不符是**引擎内部行为**，本件只记录事实与其对"以 spec 为臂的车"的影响，**未主张改 config**。
