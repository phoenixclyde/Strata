# W763 倒查：昨晚（10-09 19:0x）到现在（10-10 02:45）有没有漏固化的参数

触发：机主问「**从昨天晚上到现在有没有遗漏了，该固化的参数是不是都固化了**」。

## 1 方法（机械，不靠印象）

1. 抽出**两个日志的全部段标题** => 10-09 有 **20 段**（W717~W736）、10-10 有 **23 段**（W737~W760），**合计 43 波**。
2. 抽出**日志里出现过的全部参数名**（CLI `--xxx` 46 个 + ENV `STRATA_*` 22 个）。
3. 逐个到 `PARAM_REGISTER.tsv` 里查有没有对应行。
4. 对查不到的字面，**回源码树核实它是不是真的 Strata 参数**（排除 Chrome / rocm-smi / gen_config 的 flag）。

## 2 结论：**有遗漏，共 17 个参数从未入账**（已补登记）

| 分类 | 字面 | 判定 |
|---|---|---|
| **Strata 的真实参数、register 里没有** | `STRATA_IO_PREFETCH` · `STRATA_FILL_AHEAD` · `STRATA_FS_AHEAD` · `STRATA_FETCH_THREADS` · `STRATA_EXPERT_V2K` · `STRATA_EMB_REUSE_ACCOUNT` · `STRATA_PF_SWITCH_MIN_T` · `STRATA_KV_GROW_HOLD` · `STRATA_GFX1151_DEFAULTS` · `--pcie-mode` · `--coupled-draft` · `--lookup-chain-min` · `--mtp-draft-vocab` · `--no-spec-split` · `--spec-follow` · `--spec-split` · `--window-hashes` | **17 个 => 已补登记为 P46/P47/P48** |
| 不是 Strata 的（**不登记**） | `--dump-dom` `--headless` `--no-sandbox` `--screenshot` `--user-data-dir` `--virtual-time-budget` `--window-size`（Chrome）· `--showperflevel`（rocm-smi）· `--live` `--write`（gen_config）· `--disable-gpu`（Chrome）· `--tokens`（请求体字段） | 排除 |
| 别的项目（**不登记**） | `STRATA_PREFILL_LAYER_MAJOR` => 源码树里 **17/18 命中、只有它未命中**；它是 **routeK** 的（W746 提到"前提是它能在 HIP 编过"） | 排除 |
| 环境必需（**不登记**） | `STRATA_SRC` | 排除 |

**回源码核实**（`deploy/tmp/src411/Strata-0.1.41` 逐字 grep）：17 个里 **17 个命中**，
主要在 `src/program/generate.cpp`，另有 `iq_kernels.cu` / `prefill.cpp` / `qsa_prompt_attn.cu` / `arch_defaults.cpp`；
其中 **11 个也在 `docs/` 里有登记**（`DETAILS.md` / `BATCHED_DMA.md` / `AMD_HIP.md` / `STRIX_HALO.md`）
=> **不是我的幻觉，是账漏了**。

## 3 新增的三行（分族，避免 register 膨胀）

| id | 族 | 覆盖 | 为什么值得单列 |
|---|---|---|---|
| **P46** | `io-prefetch` | `STRATA_{IO_PREFETCH,FILL_AHEAD,FS_AHEAD,FETCH_THREADS}` | 本机是**专家从文件层流式读**（每请求 18-20 MB、命中率只到 0.96）=> **预取/读线程直接对着这个瓶颈** |
| **P47** | `drafter` | 七个 `--*draft*` / `--spec-*` / `--window-hashes` | 本机 **MTP 有效接受长度只有 1.797**（<2.0），而 `kShape[]` 是 **RTX 5070 曲线** => **选择器从未在本卡标定**；**须与 P42 串行测** |
| **P48** | `misc` | `STRATA_EXPERT_V2K` / `EMB_REUSE_ACCOUNT` / `PF_SWITCH_MIN_T` / `KV_GROW_HOLD` / `GFX1151_DEFAULTS` / `--pcie-mode` | 含 **`GFX1151_DEFAULTS`（即 P41 那族的总开关）** 与 W738 查到的 **K-quant 流 `EXPERT_V2K`** |

三行 status 全 **CANDIDATE**（未测）=> 不影响核验器（只判 ADOPTED）。

## 4 逐段核对（43 波里，哪些产生了参数级结论）

| 波次 | 参数级结论 | register |
|---|---|---|
| W717 | P31 采纳 4096 | `P31 ADOPTED` |
| W718 | P23 = 0 | `P23 ADOPTED` |
| W719 | P33 保持待定 | `P33 CANDIDATE` |
| W720 | P28/P32/P29 关项 | 三行 `REJECTED` |
| W721~W724 | 无（方法 / 对外候选） | - |
| W725 | vision 核验 | `V00-V02 ADOPTED` |
| W726 | **backend=hip** | `B00 ADOPTED` |
| W727 | SETUP_KEYS 六个不设 + api_monitor | `B01-B07` + `P35` 全 `REJECTED` |
| W728 | serve 层覆写 | `X00 ADOPTED` |
| W729/W730/W732 | 更正 PCIe 链路与覆写 | `P25`（已在）· `X00` 更新 |
| W733/W734 | telemetry 加固 | `X00` 更新 |
| W735/W736 | 无（审计 / 对外） | - |
| W737/W738 | **只读源码看到一族未探索参数** | **本次补 `P46/P47/P48`** |
| W739 | EXPERT_V2 / TSUM | `P36/P37 REJECTED` |
| W740 | ISA 探针 + dot 判决 + 接受长度 | `P38 ADOPTED` · `P39 REJECTED` |
| W741~W748 | 无（读数 / 归因 / 复现） | - |
| W749/W750/W751/W752/W753 | 无（计划 / 审计） | - |
| W754 | routeK T1 前提不成立 | **`P45 REJECTED`（本次补）** |
| W755 | 发车器（工具） | - |
| W756 | 上游 bench 规范 | 无（非参数） |
| W758/W759/W761 | 无（记忆件） | - |
| W760 | **`--mtp-window` 采纳 / `SH_STREAM` 否决** | **`P43 ADOPTED` · `P40 REJECTED`** |

**=> 43 波里产生参数级结论的 12 波，现在全部有着落。**

## 5 现状（本次倒查后）

`PARAM_REGISTER.tsv` **63 行**：**ADOPTED 26 / REJECTED 29 / CANDIDATE 7 / REFERENCE 1**；
CANDIDATE = `P33`（pin）· `P97`（并发）· `P41`（§4 族）· `P42`（lookup-chain / kv 档）· `P46/P47/P48`（本次补）。
两侧 md5 一致（`c0ad6c17668d...`）；`verify_config.py` **PASS=26 FAIL=0**。

**生产 config**：ADOPTED 26 行 => `--mtp-window 8192` 已并入，`6261ddf8a81b...` 两侧一致，已重启生效。

## 6 局限（照实写）

- 本次倒查的是 **"日志里提到过的参数名"**；**引擎里存在但两个日志都没提到**的参数**不在覆盖面内**
  （那是"未知的未知"，只能靠再次通读源码或上游文档扩面）。若要更严，下一步可做
  **「`--help` 全量 vs register 全量」的差集**（引擎自带 help，是一份权威的参数清单）。
- `P46/P47/P48` 是**未测**（CANDIDATE），**不构成任何收益承诺**。
