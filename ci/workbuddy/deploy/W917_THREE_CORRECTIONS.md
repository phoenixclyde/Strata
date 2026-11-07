# W917 · 三处更正：四件套每轮必报 / ROCm 唯一口径 / 上游其实落后 708 条

> 2026-11-03 22:1x。零停服（只读 + 改了一个 git remote URL）。机主三点指正，前两点是我口径反复，第三点是我**用假数据下的结论**。

---

## 1 四件套每轮必报（制度）

从现在起**每一条回复**都带这四节，不因任务大小省略：

```
一、生产容器   容器/镜像、运行件 md5、config md5、health/restarts、arg 数、env 数（config + 套装展开）
二、主线       branch @ commit、tag、工作树、相对上游 领先/落后
三、本次落生产  本轮对生产做了什么（没有就写"零"），含副作用
四、方案进度   条数/已结、主线口径、队列顺序
```

---

## 2 ROCm 到底什么版本：**内容 10.1.0，包名 7.14**（唯一口径，不再改）

我此前先说 10.1、又改成 7.14、再改回 10.1 —— 原因是每次只看了**一层**。四层一次性摆开：

| 层 | 值 | 命令 |
|---|---|---|
| **内容版本（运行时/编译器）** | **10.1.0** | `cat /opt/rocm/.info/version` |
| HIP | **7.16.26323** | `hipconfig --version` |
| HIP CMake | `PACKAGE_VERSION "7.16.26323"` | `grep PACKAGE_VERSION /opt/rocm/lib/cmake/hip/hip-config-version.cmake` |
| 编译器 | **AMD clang 24.0.0git** | `clang --version` |
| rocBLAS | 5.7.0.962d0059 | `strings librocblas.so.5` |
| **源码树** | **`therock-10.1`**（commit `39d8d603`，2026-09-16） | `cd ~/strata166/rocm-libs && git describe --tags` |
| **二进制包名** | `amdrocm-core7.14-gfx906` **`7.14.0-gfx906+20260802001858`** | `dpkg -l \| grep amdrocm-core7` |

**为什么两个号**：官方 release history 里 `7.14.x` 与 `10.x` 是**两条并行轨道**，且 10.1.0 的 release notes 写明
"**Since ROCm 7.14, ROCm uses TheRock as its build and release system**"。我们这套是 gfx906 社区栈
（`mixa3607/ML-gfx906`，其 README 的 release 戳正是 `20260802001858`）——**沿用了 7.14 的打包基线，装的是 10.1 的内容**。

**交叉验证**：AMD 官方性能页写 "Container ROCm **10.1.0** (HIP **7.16.26385**)"，我们是 HIP 7.16.26323 —— 同一条 7.16 线。

> **口径定稿**：说版本时一律写 **`ROCm 10.1.0（TheRock；HIP 7.16.26323；clang 24）`**，
> 包名 `amdrocm-*7.14*` 只在谈"哪个 deb"时出现。已写进 `ENV_PACKAGING_RULE` 与本文件，避免第四次反复。

---

## 3 上游：**落后 708 条，不是 0**，上游已发 **v0.2.10**

### 3.1 实测

```
$ git rev-list --left-right --count upstream/main...HEAD
708     37          # 落后 708，领先 37
$ git log -1 --format="%h %ad" upstream/main
ffa80d73 2026-11-02
$ git describe --tags upstream/main
v0.2.10
```

我们：`gfx906/mi50 @ d963c791`，tag **`mi50-0.2.9-r27`** —— 差一个**次版本**（0.2.9 → 0.2.10）。

### 3.2 根因（两个，都是我方的）

1. **`upstream` 远端是 SSH**（`git@github.com:Niko1221/Strata.git`），`git fetch --all` 只打印 "Fetching upstream"
   **却没有更新任何 ref**（无报错）⇒ 本地 `upstream/main` 停在 `c62d5e3a`（10-31）。
2. 我拿这个**过期 ref** 算出"落后 0"，并连续多轮把它写进汇报。**这是数据源没校验，不是判断失误。**

### 3.3 已修

```
git remote set-url upstream https://gh-proxy.com/https://github.com/Niko1221/Strata.git
git fetch upstream        # c62d5e3a..ffa80d73, 并拉到新 tag v0.2.10
```

`upstream/main` 现在 = `ffa80d73`，之后 `--all` 也能正常更新。

### 3.4 这 708 条落在哪（决定要不要 rebase）

| 路径 | 提交数 |
|---|---|
| `src/include` | 100 |
| `src/program` | 99 |
| `src/core` | 88 |
| `src/kernels` | 77 |
| `src/prefill` | 38 |
| `ggml` | **0**（我们把 ggml 单独 pin 在 `third_party/ggml`，不受影响） |

最近几条是 0.2.10 的"全卡拆分引擎 / DFlash2 单请求 / App 层"—— 与我们 gfx906 的 prefill/decode 优化**不直接冲突，但基线差一个版本**。
我们的 37 条领先是 gfx906 专属改动（MMQ 配置、dp4a 垫片、QSA、gfx906 开关等），rebase 到 0.2.10 需要逐个解冲突，
**这不是一条能顺手做掉的活**，要单独立项评估（下一步）。

---

## 4 方法纪律追加

**任何"相对上游"的数字，必须先 `git fetch` 再从 ref 算，并把 ref 的 commit 一起写进汇报。**
只写"落后 N"不写"对哪个 commit"，等于不可复核 —— 这次就是活例子。

---

## 5 复现

```bash
cd ~/strata166/pr/strata-fork
git remote get-url upstream          # 应为 gh-proxy https
git fetch upstream && git log -1 --format="%h %ad" upstream/main
git rev-list --left-right --count upstream/main...HEAD
git describe --tags upstream/main
```
