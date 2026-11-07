# W775delta W28B ---- 冷路径：B4 补集账目 + B3 新测量车设计

> 时间：2026-10-11 16:2x　上游：`#1670` 更正**已发**（comment `6107050493`）
> 承接：`W775delta_W28_COLD_PATH_REDESIGN.md`

## 0 结论

- **B4：`--resident-budget-gib` 是死胡同**，不是"可以调大"。RAM 补集已经是**整块"GPU cache 装不下的专家"（33.45 GiB）**且**已建满**；budget 76 GiB 对它是过量 ⇒ **调大预算不能减少文件读**。**（AUDIT4 限定）**：该结论**逐 boot 成立**；同一 flag 下补集实测有 33.44 / 33.45 / **36.80 GiB** 三值（`_cold_raw.txt:599/770/815`），当 GPU-cache 槽数变小（8,268 槽那 boot）时补集到 36.80 GiB ⇒ "budget 过量"须按槽数逐 boot 判。
- **文件读的主体 = GPU cache 的重填**（源码注释级 + 三数字自洽）：prompt 把 GPU cache 的槽"借走"后，缓存必须从文件重新填回。
- **B3：新车主口径 = 请求级 wall time x 三态（C 冷 / W 温 / D decode）+ 系统遥测 + p50/p90/max**。第一件先做**非破坏性基线**（直接打产线，唯一前缀强制冷）。

---

## 1 B4 ---- 三层存储的真实账目（源码 + 日志，三数字互证）

### 1.1 源码（0.1.42，`deploy/tmp/src142/`）

| 位置 | 逐字 | 含义 |
|---|---|---|
| `src/core/expert_source.cpp:1605-1607` | `const uint64_t experts = expert_bytes();` / `const uint64_t arena = std::min(ram_bytes, experts);` / `file_tier_unbuffered(paths_, arena, experts - arena, why)` | `arena` = 补集；`read` = `experts - arena` |
| `src/core/expert_source.cpp:1630` | `const uint64_t read = experts > complement_bytes_ ? experts - complement_bytes_ : 0;` | 复算 `read` 用 `complement_bytes_` |
| `src/program/generate.cpp:446-448` | *"the N GiB of experts the GPU cache does not hold that the expert profile ranks hottest are copied into RAM, **the rest are read from the files in place**。**0 = the whole complement**"* | budget 的语义 |
| `src/core/expert_source.cpp:480-484` | *"#1194: the experts read from the files are a **skewed set**: a cache holding a twentieth of them (at least 1.5 GiB) serves most of the repeats ... **it reads 2 to 7 times less from the drive**"* | 上游对同一问题的量级 |
| `src/core/expert_source.cpp:1626-1628` | *"what the file cache would have to keep is exactly the experts outside it - **the GPU cache's (refilled after a prompt borrowed their slots)** and the ones neither holds"* | **文件读的主体 = GPU cache 重填** |

### 1.2 日志（现取）

```
FileExpertSource: RAM budget 76.00 GiB: 14819 of the 33.45 GiB of experts the GPU cache does not hold, by profile rank; the rest are read from the files
FileExpertSource: allocating 33.45 GiB page-locked cache complement
FileExpertSource: mapped pinned cache complement ready: resident 33.45 GiB, pinned 33.45 GiB in 117 s; page-locked and mapped
the file tier reads through the file cache (re-checked with the RAM copy built (33.45 GiB): 82.8 GiB available, 0.0 GiB of it still to be taken by the RAM copy, 22.0 GiB of experts read from the files: ...)
```

### 1.3 三数字自洽（这是本节的关键）

| 量 | 值 | 出处 |
|---|---:|---|
| RAM 补集 `complement_bytes_` | **33.45 GiB** | 日志 `resident 33.45 GiB, pinned 33.45 GiB` |
| 文件读 `read` | **22.0 GiB** | 日志 `22.0 GiB of experts read from the files` |
| ⇒ 总专家 `expert_bytes()` | **55.45 GiB** | `read = experts − complement` 反推 |

校验：GPU cache **9,761 槽 x ~2.26 MiB = 22.0 GiB** ≈ `read`；补集 **14,819 专家 x ~2.26 MiB = 33.45 GiB**；合计 **24,580 ≈ 24,576 总专家**，**55.45 GiB**。

⇒ **结论**：`--resident-budget-gib 76` **对补集是过量的**（补集 = 整块非 GPU 集，已经全进了 RAM）。**文件读的 22.0 GiB 不是"补集没装下的部分"，而是 GPU cache 那一层的量** —— 与源码注释 *"the GPU cache's (refilled after a prompt borrowed their slots)"* 一致。

### 1.4 被划掉的假设 + 真杠杆候选（待测）

| 假设 | 处置 |
|---|---|
| 「调大 `--resident-budget-gib` 能减少文件读」 | **划掉**（补集已建满，budget 非约束） |
| 「`STRATA_UNBUFFERED_LOAD=1` 能救」 | **划掉**（上游 `#773` 实测：无 RAM 预算时强制 unbuffered 重读 **163-629 GB** 并**腰斩速度**） |

| 真杠杆候选（按机制，待测） | 依据 |
|---|---|
| **`--expert-cache` 槽数 / lend-borrow 行为** | 文件读主体 = GPU cache 重填 |
| **`STRATA_IO_PREFETCH`（`P54`，已重开）** | 上游 `#577`：整块 pread + 预测读，正是打这条路 |
| **`STRATA_FETCH_THREADS`（`P46`，已重开）** | 文件层读线程 |
| **页缓存保持** | `#1194`：*"a cache holding a twentieth of them serves most of the repeats"* |
| **prompt chunk**（每 chunk 重读一次全层专家） | 已撞 8192 上限 |

---

## 2 B3 ---- 新测量车设计（冷路径）

### 2.1 主口径（替换 decode `ms/step`）

| 态 | 定义 | 强制办法 |
|---|---|---|
| **C 冷** | `reused == 0` | 每次新**唯一前缀**（随机 nonce） |
| **W 温** | `reused > 0` | 重复同一前缀 |
| D decode 稳态 | 现口径 | 保留，但**只描述 decode 阶段** |

### 2.2 每次请求同时采（缺一不可）

1. 引擎行 `strata serve: prompt N tokens = R reused + K read in MS ms`（wall 分解）
2. 引擎行 `file tier I/O this request: the OS read X MB (F major faults) for Y MB of expert reads`（I/O 归因）
3. 引擎行 `strata serve: resident RAM: 33.45 GiB ..., N exchanged with the VRAM tier, N blob reads from the file`（层级动作）
4. **系统遥测**（并行采样）：`amdgpu.gpu_utilization` · `system.cpu{user,system,iowait}` · `disk.sda` reads/ops
5. 报告 **p50 / p90 / max**（禁只报均值）

### 2.3 两段式

| 段 | 是否停生产 | 目的 |
|---|---|---|
| **基线（本次做）** | **否**（直接打产线，等同真实用户请求） | 建立 C/W 两态的读写数与 wall time 基线 + 验新 harness |
| **旋钮车（下次）** | 是（`flock` + `trap restore EXIT`） | 单变量 A/B（同路径不可组合，W723） |

### 2.4 旋钮车第一靶（据 B4 排序）

1. `--expert-cache`（槽数）—— 直击"GPU cache 重填"这条主体
2. `STRATA_IO_PREFETCH=1`（`P54` 重开后的第一测）
3. `STRATA_FETCH_THREADS`（`P46`）
> **不再测** `--resident-budget-gib`（B4 已否）。

---

## 3 复现命令

```bash
# B4 账目
grep -a 'FileExpertSource:' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'the file tier reads through the file cache' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
# B3 遥测
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=amdgpu.gpu_utilization_unknown_AMD_GPU_card0&after=-3600&points=120'
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=disk.sda&after=-3600&points=120'
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=system.cpu&after=-3600&points=120'
```
