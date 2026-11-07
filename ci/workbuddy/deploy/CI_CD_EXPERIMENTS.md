# CI/CD 与调参流程怎么合并（业内做法 + 我们的落地）

> 问题：现有的 CI/CD 只管两头——**代码门**（静态检查）和**部署门**（tag/健康/台账）。
> 中间那段真正的活（跑实验、量差异、下结论）全靠人肉 shell 脚本，结论只活在 markdown 里。
> 于是"改完到底快了没有"没有客观判据，只剩印象。

## 1 业内的分层

| 层 | 业内叫什么 | 回答什么问题 | 我们 |
|---|---|---|---|
| L1 代码门 | lint / unit / static analysis | 这段代码写得对吗 | ✅ `Downstream gate` + `strata-ci check` |
| L2 构建门 | build / link / artifact | 能编出来吗，编进去的东西对吗 | ✅ `strata-ci build`（符号 + env 字符串） |
| **L3 实验门** | **continuous benchmarking / eval gate** | **改完真的快了吗，这个差异可信吗** | ⚠️ **本轮才建** |
| L4 部署门 | release gate / canary | 能上生产吗，坏了好退吗 | ✅ tag 门 + 健康门 + 台账 |

L3 的业内标准配置是**三件套**：

| 件 | 作用 | 我们的实现 |
|---|---|---|
| **runner** | 固定 workload，产出机器可读结果 | `ci/bench.py`（固定 prompt / tokens / greedy） |
| **comparator** | 统计比较，区分信号与噪声 | `ci/compare.py`（2×CV 判据 + 运行质量门） |
| **history store** | 持久保存，可回溯、可对账 | `ci/state/runs/<run_id>.json`（含 git sha/tag/exe md5/env/逐次样本） |

**业内最反直觉、也最常被跳过的一条**：**先测噪声底，再定阈值**。
共享 runner 上通行做法是"同分支跑 20–30 次，量出变异系数，阈值设在噪声带的 2–3 倍"。
跳过这一步，阈值就是拍的，结果就是"每次都说快了"或"每次都说噪声"。

## 2 我们实测的噪声底（这是本轮最有用的数字）

固定 workload（128 tokens，greedy），n=12：

| 条件 | median | **CV** | 结论 |
|---|---:|---:|---|
| **冷机**（重启/空闲后第一发） | 66.78 tok/s | **18.36%** | 第 1 发 30.5 tok/s，慢 **2.3×** |
| **热机**（丢弃前 2 发） | 69.46 tok/s | **1.06%** | 稳态，范围 67.98–71.02 |

⇒ **判据：2 × CV = 2.12%**。小于 2.1% 的差异在这台机器上不可判。
⇒ **冷启动是第一号噪声源**：不丢前 2 发，CV 直接从 1% 涨到 18%，任何对比都失效。

这条也解释了为什么之前的 A/B 数据"看着都像噪声"——部分臂的第一发是冷启动，而 n 小，中位数被拖。

## 3 据测量的差异选工具（不要再拿相位表判一切）

| 想判的差异 | 该用什么 | 因为 |
|---|---|---|
| **> 10%** | 相位表够用 | 相位表单项 CV 约 **±30%**，只能看大变化、只能用来**定位**哪一项变了 |
| **2%–10%** | `strata-ci bench` + `compare`（n ≥ 10，丢 2 发） | 稳态 CV 1.06% ⇒ 判到 2.1% |
| **< 2%** | 秒级微基准（`q8_wave_lab` 这类小 TU） | 引擎级测量到不了这个分辨率 |

**相位表只定位、不定量**——这是对我前几轮做法的纠正：我拿"hc 6.89 ms"推带宽比，是把 ±30% 的量当精确值。
（字节数 644 MiB 是逐张量枚举的，可信；用噪声时间去除它得到的比值不可信。）

## 4 落地：五个命令

```bash
strata-ci bench --n 12 --warmup 2 --label hc-q8-off   # 一次实验 = 一份 JSON
strata-ci runs                                        # 历史实验，最新在前
strata-ci compare <run_a> <run_b>                     # 差异是否 > 2x CV
strata-ci check                                       # L1（配置面）
strata-ci deploy --apply                              # L4（tag 门 + 健康 + 台账）
```

`bench` 记录的字段（够复现、够追责）：`git_head / git_branch / git_tag / dirty / exe / exe_md5 /
cfg_md5 / env / workload / samples[] / metrics{median,sd,cv,iqr,min,max}`。

`compare` 的两条规矩：
1. **运行质量门**：任一次 run 的 CV > 10% ⇒ 拒绝比较（CV 18% 的 run 会把阈值抬到 36%，等于把噪声当挡箭牌）；
2. 判据 **2×CV**，并打印"两次之间到底变了什么"（git/exe/env/ workload），让 REAL 的结果可归因。

## 5 与 GitHub 的关系（刻意不做的部分）

| 不做 | 为什么 |
|---|---|
| 把 bench 放进每次 push 的 CI | 硬性要求 GPU（166 专用），云端 runner 测不了；硬塞进去只会测到"云端 CPU 的 tok/s" |
| 自动把 bench 结果当合并门 | 单卡平时在跑生产，bench 要抢 GPU；门应设在**部署前**（`deploy` 前跑一次），不是每次提交 |
| 上 MLflow / DVC | 那是训练侧的参数+数据版本管理；我们是指标极少（tok/s、相位、KL）的推理调优，一个 JSON + 一个 CLI 足够。重平台只会多一层要维护的东西 |
| 用相位表当回归指标 | CV ±30%，做门会天天误报，团队会学会忽略（这正是"红灯疲劳"的成因） |

**真正该进 GitHub 的**只有两件事，已经在跑：静态门（L1）和上游监视。剩下的都在 166，因为硬件在那儿。

## 6 拼起来的完整流程

```
改代码
  ├─ L1 strata-ci check          （秒级，配置面）
  ├─ L2 strata-ci build          （8-10 min，编 + 符号）
  ├─ L3 strata-ci bench --n 12   （~30 s，产 run JSON）
  │    └─ strata-ci compare A B  （差异 > 2x CV 才算数）
  ├─ (可选) 停机 A/B：env 两臂交错，各 n≥10，丢 2 发
  └─ L4 strata-ci deploy --apply （tag 门 + 健康 + 台账）
```

**每一层的产物都落盘**：gate 的 PASS/FAIL、build 的 md5、bench 的 JSON、deploy 的台账行。
账本 `PROGRESS.tsv` 的 note 里可以直接写 run id（如 `run=20261101T174000`），从此结论可回溯到原始样本。

## 7 下一步

1. 把 `hc` 这类相位指标也纳入 bench（需要 `STRATA_DECODE_TIMING=1`，得重启一次）——这样 L3 能同时量吞吐与分项。
2. 给 `deploy` 加一道：部署前自动 `bench --n 12` 并写台账，让每次落产都自带一份可比的基线。
3. 建立"回归基线"：把每个 tag 的 bench 结果固化为该 tag 的基线，下次改完直接 compare。

---

## 8 GitHub 与本机怎么分工（以及结果怎么回去）

这一节的起因是一个真实的观察：**"CI/CD 好像都是本机做的，GitHub 那边没有内容。"**
盘点后确认——不是"没做"，而是**跑完没回写**：commit `17929597` 在 GitHub 上的
`combined status` 是 `pending`、`statuses: 0`，而同一棵树已经在 166 上编译、跑过 bench。

### 8.1 谁跑什么（按硬件的边界划，不按喜好划）

| 层 | 在哪跑 | 为什么 |
|---|---|---|
| L1 静态门（配置面 + 脚本语法） | **GitHub**（`Downstream gate`） | 不需要 GPU，秒级，每次改动都跑 |
| 上游监视 | **GitHub**（`Upstream watch`，每日 09:23） | 只需网络 |
| 上游自带的服务端/监控测试 | **GitHub**（`Minimal serving runtime` 等） | 1298 用例，8m38s |
| L2 构建门 | **166** | 要 ROCm + 8–10 分钟编译 |
| L3 实验门（bench / compare） | **166** | 要那张 MI50 |
| L4 部署门 | **166** | 生产就在这台机 |

### 8.2 结果怎么回到 GitHub（这是之前缺的一环）

用 **Commit Statuses API**——GitHub 官方文档给"外部系统跑测试"的标准方案：
外部系统执行、把状态回写，**计算与数据留在内网，GitHub 只存状态和链接**。
两条文档明文要求，都已在实现里遵守：

1. **按 commit SHA 回写，不按分支名**（分支会动，SHA 不会）；
2. **带 `context`**，让多个检查并存（我们用 `strata/166`）。

```bash
python albus/ci/publish.py            # 读 166 的现状 + 最新 bench run，回写 status
python albus/ci/publish.py --dry-run  # 先看会写什么
```

写入内容形如：

```
strata/166 -> success | strata-0.1.55h · 69.462 tok/s (CV 1.06%) · VRAM 33.6 GB · env 6 · health ok
```

现在在 GitHub 的提交页/分支页就能直接看到"这个 commit 对应的生产是什么样"，
而不是只有本机的一个 markdown。

### 8.3 顺带修掉的一个结构性缺口

`ci/build.sh`、`ci/deploy.sh`、`ci/bench.py` 这些**之前不在仓库里**（只存在于 166 的工作目录），
所以 GitHub 完全看不到它们，一次都没被检查过——`deploy.sh` 里一个 typo 就能直达生产。

现在它们进了 `ci/`，并在 `Downstream gate` 里加了一步：

```bash
for f in ci/*.sh ci/strata-ci; do bash -n "$f"; done
python3 -m py_compile ci/*.py
```

`d47fca13` 上这条门 **success**。

### 8.4 仍然只在本地的东西（以及为什么）

| 东西 | 为什么不上 GitHub |
|---|---|
| `albus/ci/publish.py` | 本机持有 token；放 166 或仓库都会扩大凭据暴露面 |
| 实验原始 JSON（`ci/state/runs/`） | 在 166 上，属运行数据不是代码；只有摘要（一行）进 commit status |
| 生产 config / 二进制 | 不进货仓，只在台账里留 md5 |

**判据**：进仓库的是"别人 clone 下来应该有的东西"；不进的是"这台机器的状态"和"凭据"。
