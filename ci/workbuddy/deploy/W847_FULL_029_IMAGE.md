# W847 · 一次升到完整的 0.2.9（全树镜像 + 引擎组件），并立"升级一次到位"的规矩

> 2026-10-31 20:13–20:26。机主令：「继续解决，你升就一次解决完整。这样你每次都不需要跳版本。这个记下。」
> 上一轮（W846）只把 serve 层叠进镜像，`/src/src`、`/src/include`、`/src/tools` 仍是 0.2.8/0.2.4 的内容 —— 这一轮把它做成**内容完整**。

---

## 0 结果

| 项 | 值 |
|---|---|
| 镜像 | **`strata-gfx906:0.2.9`**，id `sha256:7905395d…`，**7,708,211,557 B（7.71 GB）** |
| `/src` | **v0.2.9 全树**（含 12 个本地补丁）**8143 个文件**；删掉 base 层遗留的 `build-906`、`__pycache__`、`*.bak-w*` |
| 引擎组件 | `/opt/strata/components/engine/0.1.55-linux-x86_64-hip-gfx906`（口径 **234/235**：`--verify` 报 **234 文件**，`find -type f` 是 235——多的是 manifest 自身（AUDIT16 P2-15）；manifest `02166a3d…`，619 MiB），`--verify` 通过，内含二进制自报 `strata 0.1.55` |
| 容器 | `strata166-407` = `907a0984809f`，started `2026-10-31T12:18:29Z`，**restarts=0**，health ready **248 s** |
| 服务 | `/health` ok、UI `200 / 23050 B`、`slots=7463 vram_free=920 pcie=0.20`、`hardware.gpu_pcie_gen=3 width=16` |
| 门禁 | **PASS**，且现在打印 `img=strata-gfx906:0.2.9`（默认已改为"取运行中的镜像"） |
| 回滚 | `strata166-407.pre-w847`（0.2.9s1，Exited(0)）+ `strata166-407.pre-w846`（0.2.8p2，Exited(0)） |

## 1 为什么要重做：上一轮只是"运行时完整"

W846 的叠层只覆盖 4 处（serve / strata_cli / strata_control / tools 两文件），所以：

- `/src/src`、`/src/include`、`/src/tests`、`/src/apps`、`/src/docs` 等仍是 **0.2.4/0.2.8** 的内容；
- `/src` 里还留着 **base 层 6 天前编译的 `build-906`（119 MB）**，等于图像里混着两代产物；
- `/opt/strata/components/engine/` 是空的 ⇒ 镜像"自带引擎"这条路径不可用，只有显式 `exe` 能跑。

## 2 做法：不重编译，按上游 packaging 流程重打包，然后整树覆盖

### 2.1 引擎组件（`package_engine.py` 要求先有 `hipblaslt_version`）

直接跑会**拒绝打包**：

```
refusing to package the AMD engine:
  BUILD.json has no hipblaslt_version (packaging/stage_tuning.py writes it): a start could not match a tuning table to this hipBLASLt
```

按 `packaging/build_hip_linux.sh` 的顺序补齐（这套顺序是从源码里读出来的，不是猜的）：

1. 写 `BUILD.json`（`version/source/variant/archs/portable/dsv41`）；
2. `collect_libs.py`：按上游参数收集 `libamd_comgr.so*`、`libhiprtc*.so*`，并把 `rocblas/library`、`hipblaslt/library` 的 gfx906 数据带进包；
3. `stage_tuning.py --stage --archs gfx906 --rocm /opt/rocm`：写入 `hipblaslt_version=100401`，并明确报告
   `no hipBLASLt table for gfx906 with hipBLASLt 100401 (the repo has: none): plain hipBLAS there`
   —— **gfx906 本来就没有 hipBLASLt 调优表**，走 plain hipBLAS，这是正常状态（我们实际用的是 rocBLAS 表 + `STRATA_ROCBLAS_TUNING`）；
4. `package_engine.py --backend hip --arch gfx906 --variant gfx906 --tree` → `0.1.55-linux-x86_64-hip-gfx906`；
5. `--verify` → `ok (234 files, manifest sha256 02166a3d…)`。

**没有重新编译引擎**：用的是 W844 已经验证过的 `strata-0.1.55g`（md5 `29b15bb4…`）。打包只做"清单 + 依赖 + 元数据"。

### 2.2 镜像

```dockerfile
FROM strata-gfx906:0.2.8p2          # 保留 ROCm 7.14 gfx906 userland（系统层，与 Strata 版本无关）
COPY src/ /src/                     # v0.2.9 全树（含 12 个补丁），排除 .git / build 符号链接
COPY engine/0.1.55-linux-x86_64-hip-gfx906 /opt/strata/components/engine/0.1.55-linux-x86_64-hip-gfx906
RUN rm -rf /src/build-906 /src/build-028 /src/build \
 && find /src -name __pycache__ -prune -exec rm -rf {} + ; find /src -name '*.bak-w*' -delete ; find /src -name '*.pyc' -delete
```

构建 6.7 s（基础层全复用），只多 10 MB 之外的组件 620 MB ⇒ 7.71 GB。

## 3 逐项自证（都在容器/镜像里跑出来的）

| 检查 | 结果 |
|---|---|
| `/src` 文件数 | **8143**（全树 5319 + base 的 `third_party/llama.cpp` 2824 等）。**这是建时的快照**：serve 跑起来会重新生成 `__pycache__`，运行后实测 8185（AUDIT16 P2-16） |
| 只在树里、镜像缺的 | **只有 `.git`**（预期排除） |
| 只在镜像里、树里没有的 | 2824 个全在 `third_party/`（llama.cpp，正是 `setup.py` 会去取的那份）；`serve/` 侧 21 个是 `__pycache__`/`.bak-w*`，**已在本次删净** |
| 关键文件 md5（镜像 vs 树） | `serve/server.py` `b1aa1d36…`、`telemetry.py` `d91877f9…`、`generate.cpp` `0668b60e…`、`arch_defaults.cpp` `d09174a7…`、`CMakeLists.txt` `6d746e16…`、`gdn_probe.hpp` `eb4c386b…` —— **六项全 same** |
| 0.2.9 独有文件 | `include/strata/prefill/gdn_probe.hpp`、`src/prefill/gdn_wmma12.inc`、`strata_control/replica_profile.py`、`include/strata/program/par_counters.hpp` 全在 |
| 组件包 | `--verify` ok；`/opt/.../strata --version` = `strata 0.1.55` |
| 运行时文件 | `/src/data/expert-profile.bin`（196,632 B，引擎参数引用它）在；`/src/bin/strata` 在 |

## 4 切换（脚本 `albus/w847/swap.sh`，日志 `data/w847_swap_201825.txt`）

`stop -t 30` → 改名 `pre-w847` → 用 `docker inspect` 复刻参数重建（env 走 `--env-file`）→ health **248 s** → 冒烟
（read 2575 tok `wall 4.54 s`；decode 128 tok `43.5 tok/s`，n=1 冷态）→ 门禁 PASS。

**顺带修了门禁一个隐患**：`verify_patches.sh` 的 `IMG` 原先**写死 `strata-gfx906:0.2.8p2`**，
换镜像后它仍在查旧镜像 —— 那三行 `image:`/`served:` 检查会变成"验的不是跑的那份"。
已改成默认取运行中的镜像：

```sh
IMG="${3:-$(docker inspect strata166-407 --format '{{.Config.Image}}' 2>/dev/null || echo strata-gfx906:0.2.9)}"
```
复跑显示 `img=strata-gfx906:0.2.9`；显式传参仍可覆盖（反向测过 `0.2.8p2`）。

## 5 立规矩：**升级就一次升完整**（机主 2026-10-31 定）

| 规格 | 内容 |
|---|---|
| 规矩 | 换上游版本时，**引擎 + serve + 镜像内容 + 组件包一次到位**，不留"下一次再补"的缺口 |
| 为什么 | 分两步会留下**版本混搭**（W846 就是这样：serve 0.2.9 但 `/src/src` 是 0.2.8），混搭会让每次结论都要先问"这层是哪一版"，而且下次还得再跳一次版本 |
| 例外（允许分批的唯一情形） | 只是为了**验证某个补丁能否生效**而临时叠一层（比如 W846），并且**当场记账、限一个会话内收口** |
| 验收三件套 | ① `/src` 关键文件 md5 == 树；② 组件 `--verify` 通过且自报版本；③ 门禁打印的 `img=` 就是运行中的镜像 |
| 落地位置 | `SESSION_STATE §1 铁律`、本节、`deploy/PROGRESS.tsv`（X14） |

## 6 现在还剩什么不是 0.2.9

> **⚠️ 本节写作时是 0.2.9 刚落地的时点；下面两行已被后续轮次推翻（AUDIT16 P2-26）：**
> ① `/opt/strata/terminal` / `seed` **当时根本不存在**（不是"0.2.4 时代产物"）——W848 才从零装进去；
> ② `/opt/rocm` **已不是 7.14**：W852 切到社区 TheRock 构建的 **10.1.0**（官方矩阵仍不含 gfx906）。
> 现状只认 `SESSION_STATE §1` 与方案 `§6.12`。

| 层 | 状态 | 影响 |
|---|---|---|
| `/opt/rocm`（5.1 GB） | 仍是 ROCm 7.14 gfx906 userland，来自 base | **与 Strata 版本无关**，AMD 官方已不再为 gfx906 出新的，这就是最新的 |
| `/opt/strata/terminal`、`/opt/strata/seed` | base（0.2.4 时代） | 我们不用终端；只有走 `strata` CLI/Terminal 才需要，届时按 `packaging/package_terminal.py` 重打一次 |
| `third_party/llama.cpp` | base 那份（166 MB） | 与 `setup.py` 拉取的 pin 一致；引擎已静态用它，运行时不需要重编译 |

⇒ 结论：**运行面 100% 0.2.9**；镜像内非 0.2.9 的只剩 ROCm（与版本无关）和 Terminal（不使用）。

## 7 产物与回滚

```
image     strata-gfx906:0.2.9    sha256:7905395debb90dd059d1e2b4207cd147e6c4b15aea67854937ed8580fcd678c7   7,708,211,557 B
container strata166-407          907a0984809f   started 2026-10-31T12:18:29Z   restarts=0
component 0.1.55-linux-x86_64-hip-gfx906   234 files   manifest 02166a3da9d79f7c908c5b32a4fdd9fe9f7783a9484345cae16af24c38a0d127
回滚      docker rm -f strata166-407 && docker rename strata166-407.pre-w847 strata166-407 && docker start strata166-407
再回滚    ... 对 pre-w846（0.2.8p2）
```
镜像与容器都**保留三代**（0.2.8p2 / 0.2.9s1 / 0.2.9），磁盘用 236 GB 余量充足，暂不清理。
