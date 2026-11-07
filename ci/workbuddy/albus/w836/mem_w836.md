## W836　本地补丁收进分支 gfx906/0.2.8-mi50（2026-10-31 15:35–16:2x）

- **问题根因**：`src028` **根本不是 git 仓库**，7 条补丁只存在于文件系统 ⇒ 丢失无法追溯（W830 那次即如此）。
- **建分支**：`phoenixclyde/Strata` → **`gfx906/0.2.8-mi50`**，head `923c2118`，
  基线 **`c62d5e3a`**（上游 main **2026-10-31**，不是 v0.2.8 tag）。**ahead 7 / behind 0**，6 个文件 +94/−7。
  **上游在动**：第一次取还是 `870aedd9`（10-29），二十分钟后再取已变 `c62d5e3a` ⇒ 每次必须现取。
- **7 个 commit 各对应一条补丁**：W793 `c5fd0796` / W776 `01e01636` / W794 `b42e4bc0` / TEL-PCIE `46aaaba5` /
  W831 `f3d35b86` / WEB-UI `7c38cb4e` / **W830-COMPAT `923c2118`**（最后这条差点又漏，靠全量对撞捞回）。
- **落补丁方式**：上游自 v0.2.8 未改的 5 个文件直接取我们版本；`CMakeLists.txt` 上游在动（+29/−1），
  故**重跑幂等脚本** `restore_cmake.py`，锚点断言报 `applied:['W793a','W793b','W776']` ⇒ 三个锚点在上游最新树上仍成立。
- **验证**：远端分支在；改动面恰 6 文件；7 条标记齐全；`telemetry.py` py_compile 通过；
  W793 在分支树上生效的证据 = configure 输出出现
  `/opt/rocm/lib/cmake/rocblas/rocblas-config.cmake:90 (find_dependency)`。
  **完整 configure 未完成**（三次后台跑都卡在上游 `_deps` 的 FetchContent 编译，并发抢资源，容器已清）；
  **完整编译未做（约 40 min）**——但生产 `strata-0.1.54n2` 本来就是同一套补丁的 src028 构建出的。
- **166 工作副本**：`/home/albus/strata166/gfx906`（depth-1 clone，5319 文件，已跟到 `923c211`）。
  同步脚本 `/home/albus/strata166/tmp/sync_gfx906.sh`（`--check` 只读）。
- **同步脚本的边界（重要）**：**不能整文件覆盖 CMakeLists.txt**——分支=main+补丁，src028=v0.2.8+补丁，基底差 29 行。
  实测 6 个文件里 5 个 `same`、`CMakeLists.txt` `DIFF`（正常）。对 CMakeLists **只比补丁标记，不比 md5**；
  要让构建树跟上上游最新，那是"升级"动作（重跑 restore_cmake.py + 门禁 + 重建），不是"同步"。
- **两条方法错误（已写进文档 §9）**：
  1. **`git diff <tag> <branch> -- <file>` 在 shallow 仓库里静默返回空**，我据此把 **68 个"上游前进"的文件误判成"我们的补丁"**
     （含 `src/dsv41/*`，我们从未碰过）。正确判据：**不依赖历史，直接比 blob 内容**。
  2. **判据失效时数字反而整齐**（residue=0 / ours=68），更容易被当真。
     ⇒ 任何"全量分类"结果，先用 2–3 个**已知不可能属于该类**的样本反证。
- **与第三方 PR 撞车**：`#3986`（MarcoTool）、`#4766`（nfriedly）都在修 dflash2 的 gfx906 构建 = 我们的 W776，
  且都不是我们提的。我们做法不同（只给该文件加宏），可作为第三种方案提交并引用它们。
- 文档 `deploy/W836_BRANCH.md`；`deploy/patches/LOCAL_PATCHES.tsv` 加 `commit` 列（7 条全部有 sha）；
  登记 **P223（ADOPTED）**，220 行。**生产未改动**（0.2.8p2 / n2 / 33 args / 14 env / Up 45 min / health ok）。
