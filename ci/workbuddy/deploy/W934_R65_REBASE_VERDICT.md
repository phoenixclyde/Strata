# W934 · R65 结项：**不做整体 rebase**，只 cherry-pick 1–2 条

> 执行 2026-11-04 09:0x–09:2x，纯只读（含一次临时 worktree 试 cherry-pick，已清理）。

---

## 0 结论

| 项 | 值 |
|---|---|
| 上游最新（`git ls-remote` 绕过本地 ref） | **`ffa80d73`**（tag `v0.2.10`，2026-11-02）—— 与 W917 那次一致，**上游未再更新** |
| 真实差距（`git rev-list --left-right --count`） | **落后 708 / 领先 37** |
| **是否整体 rebase** | **否** |
| 值得单独 cherry-pick 的 | **1 条**：`e1b27d54`（fatal GPU error 自退）；另 1 条待定（`9aea047e`） |

---

## 1 708 条都在改什么（关键词统计）

| 类别 | 条数 | 与我们（单卡 gfx906 / Linux / 单流）的关系 |
|---|---|---|
| **split / 多卡 / DFlash2 / RCCL** | **224**（31.6%） | 完全无关（需 2–4 卡） |
| 非 Linux 平台（Windows / Metal / SYCL / Arc） | **135** | 无关 |
| UI / App / Terminal / Setup / 文档 | **109** | 无关 |
| 新架构（gfx11xx/gfx12xx/RDNA/RX 9xxx/RTX/sm_/Blackwell/Ada） | **44** | 无关（我们是 gfx906） |
| （以上类别有重叠） | | |

**「gfx906 / MI50」在 708 条里出现 0 次。** 上游的 AMD 面 = RDNA（gfx103x / gfx11xx / gfx12xx）。

### 触及我们改过的 7 个文件的提交数（冲突面）

| 文件 | 上游改了几次 |
|---|---|
| `src/program/generate.cpp` | **99** |
| `CMakeLists.txt` | **49** |
| `src/core/arch_defaults_test.cpp` | 17 |
| `src/core/arch_defaults.cpp` | 11 |
| `include/strata/core/arch_defaults.hpp` | 5 |
| `src/kernels/cuda/native_mmvq.cu` | 4 |
| `src/kernels/cuda/qsa_select.cu` | 3 |

（`arch_defaults.cpp` 的 11 次已逐条核过，**全是 gfx12/gfx1151/gfx1010/gfx1030，没有一条动 gfx906**，见 W918。）

---

## 2 逐条核过的候选（7 条）

| 提交 | 内容 | 判定 |
|---|---|---|
| **`e1b27d54`** | **fatal GPU error 后引擎自退（`ERR fatal GPU error` + exit 3），server 重启它；带 10 分钟 3 次的防抖** | **✅ 值得** —— 我们树里 grep 到 **0 处**，上游 4 处。现状是 GPU 出致命错后引擎带着死上下文继续跑，之后每个请求 400 直到人工重启 |
| `9aea047e` | 中止请求后"答案晚一个请求到达"（server 多丢一个 DONE） | 待定（需看我们 server.py 的对应段） |
| `058f6532` | HIP mlock 失败降为警告 | ❌ 只改 `src/split/src/model.cpp`（多卡），我们不用 |
| `9a352550` | split-hip 的 mlock 警告等 | ❌ 全在 `src/split/` |
| `285fa48b` | `lookup_default.hpp` 移出 HIP-only include 块 | ❌ 我们树里**没有这个文件**（0.2.10 新增） |
| `5a13c34f` | PLE table lock 先把 soft 提到 hard | ❌ **我们已绕过**：直接 `--ulimit memlock=-1`（P256），不需要软件提限 |
| **`de830800`** | **CPU prefill share 的默认上限 1024 → 3072** | **已经是** —— 我们 config 里就是 `STRATA_PREFILL_CPU_SHARE_MAX=3072`，与上游新默认一致（当时的选择被验证） |

### `e1b27d54` 的细节（唯一确定的候选）

- 改动：`src/program/generate.cpp` +43、`serve/server.py` +46、`src/dsv41/ds4_main.cpp` +38、新增测试
- 机制：decode window / commit 失败后，若 runtime 持有 sticky fatal error，立即打印 `ERR fatal GPU error:` 并 `_Exit(3)`；server 把该请求判为引擎死亡（503 retryable），下一个请求自动重启引擎；**10 分钟内第 3 次致命死亡则停止重启并返回原因**
- **cherry-pick 实测**（临时 worktree）：**1 处冲突**（`generate.cpp`），`server.py` 的 hunk 无冲突（我们 9589 行 vs 上游 10117 行）

---

## 3 为什么不做整体 rebase

| 维度 | 数值 |
|---|---|
| 要解的冲突 | **37 条本地提交 × 7 个上游也改过的文件**，其中 `generate.cpp` 被上游改了 **99 次** |
| 收益来源 | 708 条里与我们相关的**只有 1–2 条**（0.2%） |
| 额外成本 | **引擎要从 0.1.55 重建到 0.1.56**（`project(strata VERSION 0.1.55)` vs `0.1.56`）⇒ 全量重编 + 镜像重打包 + 重新 A/B |
| 风险 | `generate.cpp` 是我们的热路径主场（99 次上游改动里混着大量 split/DFlash2 分支），解错一处就可能破坏 gfx906 的单流路径 |

**收益 0.2%、成本是"重编引擎 + 解 37 条 × 99 次改动的冲突"，量级不匹配。**

⇒ **只做 cherry-pick**。已立 **R77**。

---

## 4 一条方法论：查"上游有没有更新"必须三路互证

本轮用了三个独立口径，结论一致：

```bash
git fetch --force --tags upstream            # ① 本地 ref
git log -1 upstream/main                     #   → ffa80d73
git ls-remote upstream HEAD refs/heads/main  # ② 绕开本地 ref，直接问远端
                                             #   → ffa80d73133ea5c5…（同一个）
git tag --sort=-creatordate | head -1        # ③ 最新 tag
                                             #   → v0.2.10 @ ffa80d73
```

W917 那次就是因为只看了 ①（而 SSH 远端静默不更新）连错三轮。**② 是必须的**。

---

## 5 生产

**零改动**：无重启、无编译、无 config 变更。临时 worktree `/tmp/w934` 已删除。
