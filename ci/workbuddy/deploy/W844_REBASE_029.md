# W844 · 把分支落到上游最新（v0.2.9）：rebase 不可行，改用 worktree 重建

> **⚠️ 本文 §1–§6 的三处判断已被 `deploy/W845_BRANCH_TRUTH.md` 更正（2026-10-31 19:5x）**：
> ① 「浅克隆、与上游无共同祖先 ⇒ 不能 rebase」= **浅克隆伪影**：旧分支的树本来就是 v0.2.9，`--unshallow` 后 `rebase` 可用；
> ② 「分支已落到 v0.2.9」= **当时 12 个补丁未提交**，分支 HEAD 仍等于 `c62d5e3a`（ahead 0），已于 W845 补提交 `aef9d25` 并推送；
> ③ 「重建镜像约 40 min」= **未核**：serve 层仅 4.43 MB，`FROM 0.2.8p2 + COPY serve` 即可叠层，不必重跑三 stage。
> 结论/数据（构建 164/164、md5 `29b15bb4…`、门禁 17 项、三臂 A/B 中性、落产）仍然成立。

> 2026-10-31 19:0x。机主指令：把分支 rebase 到上游最新，再打下一枪。
> 结论先说：**`git rebase` 在这棵 clone 上做不了**（与会话历史有关，见 §1），
> 已改用「从 `v0.2.9` tag 建 worktree + 重放 12 个补丁文件」，产出 **引擎 0.1.55**，门禁 17 项 PASS。

---

## 1 为什么不能直接 rebase（实测，不是猜）

| 检查 | 结果 |
|---|---|
| `git rev-parse --is-shallow-repository` | **true**（depth-1 clone） |
| `git fetch upstream main --depth=1` | upstream/main = **`c62d5e3a`** = v0.2.9 |
| `git merge-base HEAD upstream/main` | **空** |
| `git rev-list --count HEAD..upstream/main` | **204**（fetch 后可见的上游历史） |
| `git rev-list --count upstream/main..HEAD` | **6**（本地可见的我们的提交） |

⇒ 本地的 6 个提交挂在一个**浅边界**上，该边界在已知的上游历史里找不到共同祖先（上游 main 的历史与 fork 不同源/被改写）。
`git rebase upstream/main` 会直接报 `no merge base`。**加深（--deepen=40）也没能补出共同祖先**。

> 这同时解释了 AUDIT15 §7 的隐患：之前所谓「分支基线 c62d5e3a」只是**内容上**对得上（W835 做过逐文件 blob 对撞），
> **图上并不连通**。所以"rebase"这个词在这棵树上本来就没有对象。

## 2 实际做法：以 tag 为基点重建

```bash
cd ~/strata166/gfx906
git remote add upstream https://gh-proxy.com/https://github.com/Niko1221/Strata.git   # 只 fetch，不配 push
git fetch upstream --tags --depth=1           # v0.2.9 -> 注解 tag d94bac6 -> commit c62d5e3
git worktree add -B gfx906/0.2.9-mi50 ~/strata166/gfx029 v0.2.9
```

然后把我们的补丁**逐文件重放到新树**（12 个文件）：

| 方式 | 文件 | 校验 |
|---|---|---|
| 整文件复制 | `qsa_decode_attn.cu`、`qsa_select.cu`、`telemetry.py`、`app.css`、`app.js`、`strata_hip.h`、`gfx_arch.hpp`、`arch_defaults.hpp`、`arch_defaults.cpp`、`arch_defaults_test.cpp` | 与旧树 **10/10 md5 相同** |
| 锚点补丁器 | `generate.cpp`（`apply_w839_generate.py`） | `W839 local` 标记 = 1 |
| 锚点补丁器 | `CMakeLists.txt`（`restore_cmake.py`） | `applied: W793a, W793b, W776`；三锚点齐全 |
| 不做 | `CMakeLists.txt` 不整文件复制（0.2.9 上游动过） | 与旧树同样处理 |

新树 `git status` = **恰好 12 个文件被改**，无多余。

## 3 构建

| 项 | 值 |
|---|---|
| 树 | `~/strata166/gfx029`（= v0.2.9 + 12 补丁，分支 `gfx906/0.2.9-mi50`） |
| 构建目录 | `~/strata166/gfx029-build`（树外，避免污染 git status） |
| 选项 | 与生产一致（`-DSTRATA_HIP_GFX906=ON -DCMAKE_HIP_ARCHITECTURES=gfx906`、rocBLAS、MMQ_KQUANTS、NATIVE_EXPERTS、PREFILL_MMQ=OFF…）；`STRATA_GGML_DIR` 指向 `src028/third_party/llama.cpp`（v0.2.9 树里没有 llama.cpp） |
| 结果 | `ninja` **164/164 通过**，产物 **38,567,520 B**，md5 **`29b15bb4418bf15a98c22ec565f2447b`** |
| 版本 | `/out/strata-0.1.55g --version` → **`strata 0.1.55`** |
| 补丁在二进制里 | `MI50-class`=2、`exact speed switches`=1、`STRATA_SELECT_SIMT=2), tiles 32/128`=1、`W839`=2 |

## 4 门禁（tree=gfx029）

**17 项全 PASS**（含 `W793` rocBLAS、`W776` dflash2、`W794` k8v4、`TEL-PCIE`×2、`WEB-UI`×3、`W831`×3、
`W830-COMPAT`、`W837`、`W839`×3、`PROVENANCE`）。
为让 `verify_patches.sh` 按原路径找得到东西，加了两个 shim：`gfx029/build-029g → gfx029-build`（目录软链）、
`gfx029/strata`（产物副本）。**这两个是门禁兼容件，不属于源码。**

## 5 一个必须写明的限制

镜像仍是 **`strata-gfx906:0.2.8p2`**，容器里的 `serve/` Python 层是 **0.2.8**。
本次只换了**引擎二进制**（0.1.54 → 0.1.55），serve 层没换。
⇒ 「完整升到 0.2.9」还需要重建镜像；本轮 A/B 判的是**引擎层**，不是整个 release。

## 6 A/B（n4 vs 0.1.55g）

| 臂 | 引擎 | 树基底 |
|---|---|---|
| A | 0.1.54n4 | 0.2.8 |
| B | 0.1.55g | **0.2.9** |
| A2 | 0.1.54n4 | 0.2.8（重复，控漂移） |

测量：read 3718/6666/24000 ×2、decode 3×200 token；**每臂比对 `/metrics` 的 `requests` 增量**（期望 11，
多出来即外来请求，AUDIT14 的纪律）。

> 结果见 §7（本轮跑完回填）。

## 7 A/B 结果（三臂，全部 `REQ delta = 11`，**无外来请求**）

| read（ms，引擎日志） | A n4 | B 0.1.55g | A2 n4 | B vs A/A2 |
|---|---:|---:|---:|---|
| 2575 tok | 4496 | **4486** | 4511 | −0.2% / −0.6% |
| 3014 tok | 5507 | **5464** | 5512 | −0.8% / −0.9% |
| 5282 tok | 8151 | **8132** | 8084 | −0.2% / +0.6% |
| 5512 tok | 8150 | **8172** | 8169 | +0.3% / +0.0% |
| 18980 tok | 27186 | **27153** | 27109 | −0.1% / +0.2% |
| 19358 tok | 27848 | **27861** | 27855 | +0.05% / +0.02% |

- **复本离散**（A vs A2，同二进制同配置）：0.3 / 0.1 / 0.8 / 0.2 / 0.3 / 0.03（%）⇒ 本轮基线极稳（<1%）。
- **read 全部落在复本离散内**：|Δ| ≤ 0.9%，方向不一致 ⇒ **0.2.9 对 read 无影响**，与 release 正文"无 gfx906 内容"一致。
- decode（`mt_gen` 3×200 tok，MEDIAN）：A **45.70**、B **47.54**、A2 **45.48**。逐条看：p0 41.7/41.8/41.5（**相同**）、
  p1 49.4/48.2/48.3（B 与 A2 相同、低于 A）、p2 45.7/**47.5**/45.5。⇒ 中位差来自 p2 一条的接受率（B 92/131；A 实为 **83/122**，A2 95/133——原写 86/127 有误，AUDIT16 P2-14），
  **不是速度差**，不足以下"decode ↑4%"的结论。

**判词**：0.2.9（引擎 0.1.55）在 gfx906 上**中性**——read 无差异、decode 无一致差异。

## 8 落产（已执行）

| 项 | 改前 | 改后 |
|---|---|---|
| 引擎 | `/data/bin/strata-0.1.54n4`（0.1.54，0.2.8 树） | **`/data/bin/strata-0.1.55g`**（0.1.55，**v0.2.9 树**）md5 `29b15bb4418bf15a98c22ec565f2447b` |
| 源码树 | `src028`（0.2.8 基底） | **`gfx029`**（v0.2.9 + 12 补丁；分支 `gfx906/0.2.9-mi50`） |
| 门禁默认 TREE | `src028` | **`gfx029`**（`verify_patches.sh` 已改；src028 留作回滚） |
| 镜像 / args / env | `0.2.8p2` / 33 / 6 | **未变** |
| 启动 | — | health ready **252 s**；`expert_slots 7463`、`vram_free 920`、`pcie_frac 0.20`；冒烟 read 2575 tok 4.57 s、decode 41.8 tok/s（n=1） |
| 回滚 | — | 配置指回 `0.1.54n4` + 重启（4 min）；`n3`/`n4` 均在 |

**限制（必须记住）**：镜像仍是 **0.2.8p2**，容器里的 `serve/` Python 层是 0.2.8。本次只换引擎。
「完整 0.2.9」还需重建镜像（`X12` 的后半段），那是另一次构建 + 全量回归。
