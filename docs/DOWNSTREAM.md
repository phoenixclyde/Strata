# Downstream: gfx906 / MI50 维护说明

本仓是 [Niko1221/Strata](https://github.com/Niko1221/Strata) 的**下游厂商分支**：
我们跟随上游，但**不向上游提交 commit、不提 PR**。上游对本仓是只读的
（`remote.upstream.pushurl = DISABLED-no-push-to-upstream`）。

## 锚点

| 项 | 值 |
|---|---|
| 基于上游 | **v0.2.9** = `c62d5e3a15b40ea51c96aae9e8d36928965f53ab` |
| 长期分支 | `gfx906/mi50`（版本号不进分支名） |
| 发布 tag | `mi50-0.2.9-r1` |
| 生产引擎 | `strata-0.1.55h`（md5 `9a2ff8742f9918f657a468a7baeb177c`） |
| 与上游距离 | 落后 **0** / 领先 4（`git rev-list --left-right --count upstream/main...gfx906/mi50`） |

## 下游提交台账（rebase 时逐条重放；被上游吸收的立刻删）

| 序 | 提交 | 为什么 | 怎么验 |
|---|---|---|---|
| 1 | `docs: hipBLASLt on gfx906 (MI50) …` | 20 轮调查记录，结论 DONE_NEG（结构等价 + 上游路径未维护） | 文档 |
| 2 | `gfx906: replay the 0.2.8 local patches onto v0.2.9` | 0.2.8 线已验证的 gfx906 改动整体重放到 0.2.9（内容见下表） | 引擎起得来、48 层全 MMQ、decode 47 tok/s 量级 |
| 3 | `gfx906: rows-per-wavefront table for the Q8_0 wave kernel` | 单请求 decode 走投机验证窗口（ncols>1），wave kernel 每波只算 1 行，激活与 dp4a 不跨行共享 | 9 形状 × ncols 1/6 逐位 `diff=0`；同镜像 A/B **+4.0%** |
| 4 | `docs: downstream maintenance note` | 本文件 | 文档 |

### 提交 2 里打包的历史通用修复（**已并入主线，来源分支已归档**）

| 原分支 | 内容 | 归档 tag | 现状 |
|---|---|---|---|
| `amd-monitor-name-consistency` | AMD 板名容量校验（`serve/telemetry.py`） | `archive/amd-monitor-name-consistency` | 逻辑已在主线（`telemetry.py` 读 `product_name` 并按显存校正容量） |
| `amd-monitor-pcie-link` | PCIe 代际识别（Monitor 图块） | `archive/amd-monitor-pcie-link` | 已在主线 |
| `gfx906-cpu-share-guard` | prefill 的 `arm_cpu_share` 误走 CUDA 分支 | `archive/gfx906-cpu-share-guard` | 已在主线 |
| `web-sparkline-axis-floor` | 迷你折线图纵轴下限 | `archive/web-sparkline-axis-floor` | 已在主线 |
| `gfx906-build-fixes-402` | q6_k MMQ 在 gfx9 下没编（CMake） | `archive/gfx906-build-fixes-402` | 上游重构 CMake 后 `_strata_mmq_types` 无条件含 `q6_k`；`libstrata_mmq.a` 里确有 `mmq-instance-q6_k.cu.o` |

> 这 5 条都不含硬件专属逻辑，本来该上游化；本仓不提 PR，所以靠「重放补丁」传递。
> **rebase 后必须逐条确认它们还在**（`git grep` 关键行即可），这是这套模式最脆的环节。

## 归档记录（2026-11-01，14 条 → 4 条）

| 删除的分支 | 归档 tag | 理由 |
|---|---|---|
| `gfx906/0.2.9-mi50` | `archive/gfx906-0.2.9-mi50` | 旧命名的副本（= `gfx906/mi50` 少一个 docs 提交） |
| `gfx906/0.2.8-mi50` | `archive/gfx906-0.2.8-mi50` | 上一条线，内容已并入主线 |
| `gfx906/hipblaslt-vega20` | `archive/gfx906-hipblaslt-vega20` | 实验已结（DONE_NEG） |
| `gfx906/mmq-plan-banner` | `archive/gfx906-mmq-plan-banner` | R17 诊断 banner，结论已拿到 |
| `gfx906/routed-stream` | `archive/gfx906-routed-stream` | R5/#4283 判否（REJECT） |
| 上面 5 条通用修复 | 各自 `archive/*` | 内容已在主线 |

保留：`gfx906/mi50`（主线）、`main`（上游镜像 + docs）、`bench-mi50-32gb-262k`（社区数据）、`rc/0.1.30`（上游的 rc）。

## 规矩

1. **只 fetch 上游，永不 push 上游**；分支与 commit 只在本仓。
2. **rebase，不 merge**：上游发新版就 `git rebase upstream/main`，保持薄补丁栈。
3. **分支名不带版本号**；版本信息进 tag（`mi50-<上游版本>-r<N>`）。
4. 补丁必须进本表；合并上游后逐条核对，能删的立刻删。
5. 二进制 / bench 副本 / `*.bak` **不进仓库**（放 `/home/albus/strata166/w863/`）。
6. 生产只跑「发布 tag 对应的 HEAD」；未打 tag 的提交不进生产。
7. **分支用完即归档删**：打 `archive/<名字>` tag 后删远端与本地，别让影子分支堆着。

## 跟随上游（四步）

```bash
cd /home/albus/strata166/pr/strata-fork
git fetch upstream
git log --oneline upstream/main ^HEAD          # 看上游多了什么
git rebase upstream/main                       # 薄补丁栈整体上移
# 重编 + 验证（deploy/W863_R23_DEPLOY.md 的 d11/d13/d14）
git tag -a mi50-<新版本>-r1 -m "..." && git push origin gfx906/mi50 --force-with-lease && git push origin --tags
```

## 已知限制

~~浅克隆~~ **已于 2026-11-01 16:0x 修复**：`git fetch --unshallow upstream` ⇒ `git rev-parse --is-shallow-repository` = `false`，
4933 个提交可达，`.git` 137 MB。历史类判断（落后/领先、merge-base）现在可信。

> 修复前的教训：浅克隆上 `rev-list --count` 把「落后 3528 个提交」算成「落后 1 个」，
> `merge-base` 直接报错，在 main 上 rebase 会把老提交当根整树重放。历史不全时一律用 GitHub API 交叉验证。
