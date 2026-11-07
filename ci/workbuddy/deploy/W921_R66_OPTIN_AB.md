# W921 · R66：0.2.10 三个 opt-in prefill 开关的移植与 A/B

日期：2026-11-03 23:2x – 2026-11-04 00:2x
状态：**DONE_NEG**（三条全部生效，prefill 无收益）；两个副产品已记

---

## 1 移植：三条全部打上，且验证过路径

| 提交 | 开关 | 改动 |
|---|---|---|
| `fbf6e1c7` | `STRATA_PF_GROUP_SCRATCH` | `prefill.cpp` +124/−8：MMQ 的 GU/H/Hq 只持有**一个专家组**的行 |
| `5273fb66` | `STRATA_PREFILL_ROUTED_STREAM` | `prefill.cpp` +82 + 新头 `routed_stream.hpp`(160) + 测试(410)：不拷贝本 chunk 无 token 路由的流式专家，深度默认 16 |
| `3cc47f02` | `STRATA_PF_HC_REGION` | `prefill.cpp` +39/−9：HC 读的 scratch 放进共享 region |

**应用结果**：`fbf6e1c7` 12 个 hunk 全成功（offset −2）、`5273fb66` 6 个 hunk 全成功、
`3cc47f02` 在 **p1 之后** 5 个 hunk 全成功（`W918` 说的"1 处手解"是因为当时没上前置，实际不需要手解）。

**编译方式**（与 `strata-ci-build` 容器同一套路）：`ninja -t commands` 抽**单条编译行 + 归档行 + 链接行**，
逐条 `bash -e` 执行；不做全量 `ninja`——因为 cmake 会重跑而 `STRATA_GGML_DIR=/llama.cpp` 在镜像内不存在，
一旦重跑就 `add_subdirectory given source "/llama.cpp/ggml" which is not an existing directory` 而失败。

产物：`2fa104e5`（40,782,104 B，比 `e0c6f250` 大 10,344 B），三个 env 字面量全部在二进制里（9 处命中）。

---

## 2 路径断言：三条**都生效**（这是本轮最关键的一步）

`W914` 立的纪律是"只给时间差无法区分『没收益』与『没执行』"，所以先证执行：

| 证据 | 内容 |
|---|---|
| **日志** | `strata: STRATA_PREFILL_ROUTED_STREAM=1: a streamed prompt chunk drops the experts no token routes to before they are copied (at most 16 copies queued ahead of the link)` |
| **进程 env** | 三项都在（`/proc/<pid>/environ`） |
| **显存布局（决定性）** | **`prompt path borrows 1578 slots (4.62 GiB)` → `1226 slots (3.59 GiB)`**，少借 **352 slots / 1.03 GiB（−22.3%）** |

第三条最能说明问题：借用的 slots 从 1578 掉到 1226，正是 `PF_GROUP_SCRATCH`（GU/H/Hq 只留一组专家的行）
与 `PF_HC_REGION`（HC scratch 进共享区）把 prompt path 的 buffer 缩小了。**三条不是空开关。**

**副产物（重要）**：把三个 env 去掉、只换二进制时，`borrows` 回到 **1578 slots** —— 与基线逐字相同
⇒ **补丁在关闭时 bitwise 等价**（至少显存布局完全一致）。这是"opt-in + bitwise"自述的实测印证。

---

## 3 A/B：prefill −0.23%，在噪声内

两臂同脚本同口径（`bench_pair --prefill-words 4100 --n 9 --decode-tokens 256`，去掉冷启第一次，取 rep2-9）：

| 臂 | 二进制 | 三个 env | prefill median | CV | decode median |
|---|---|---|---|---|---|
| A | `a97f4479` | 无 | **8.819 s** | 1.6% | 79.24 |
| **B** | `2fa104e5` | 全开 | **8.799 s** | **1.0%** | 78.19 |

差 **−0.23%（prefill）/ −1.3%（decode）**，都够不到 2×CV ⇒ **无收益**。

decode 的 −1.3% 只出现在本轮，且本轮 `expert cache 7463 slots`、`VRAM free 920 MiB` 与基线完全相同 ⇒ 属噪声。

---

## 4 结论与处置

- **R66 = DONE_NEG**：三条 opt-in 全部生效，prefill 无收益。**不采纳**（无收益就不留复杂度）。
- 生产已恢复：二进制 `mv` 回 `a97f4479`（`cp` 会 `Text file busy`，必须换 inode）、config 回到 `51ef8837`（env 9 项）、
  `/health ok`、`restarts=0`、`ulimits` 仍保留 `memlock=-1`（`P256` 的决定不动）。
- **新立 R72（副产品）**：三条开关让 prompt path **少借 1.03 GiB**。当前 `expert cache 7463 slots / 21.79 GiB`、
  `VRAM free 920 MiB` 由 `--vram-reserve-mib 832` 卡住，所以这 1 GiB 没被利用。
  1.03 GiB ÷ 3 MiB/槽 ≈ **+350 槽（7463 → ~7800，+4.7%）**，若加到 GPU expert cache，可能抬 decode 命中率。
  **做法**：三开关常开 + 把 `--vram-reserve-mib` 从 832 降到 ~600，看槽数与 decode；判据 `|Δ|≥2×CV` 且 cache 命中率不降。
  **注意**：这条依赖 R66 的补丁常开，所以补丁要保留在实验分支上（不必进生产，除非 R72 赢）。

---

## 5 复现命令

```bash
# 建实验树（必须保留 mtime，否则 ninja 全量重编）
rsync -a --exclude=.git ~/strata166/pr/strata-fork/ ~/strata166/work/r66/
cd ~/strata166/pr/strata-fork
git show fbf6e1c7 -- src/prefill/prefill.cpp > /tmp/r66_p1.patch
git show 5273fb66 -- src/prefill/prefill.cpp include/strata/prefill/routed_stream.hpp > /tmp/r66_p2.patch
git show 3cc47f02 -- src/prefill/prefill.cpp > /tmp/r66_p3.patch
cd ~/strata166/work/r66 && patch -p1 < /tmp/r66_p1.patch && patch -p1 < /tmp/r66_p2.patch && patch -p1 < /tmp/r66_p3.patch

# 增量编译（不触发 cmake；/llama.cpp 需要 bind）
docker run --rm -v ~/strata166/work/r66:/src -v ~/strata166/gfx029-build:/out \
  -v ~/routeB/ML-gfx906/llama.cpp:/llama.cpp -w /out strata-gfx906:0.2.9-101 bash -lc '
    ninja -t commands CMakeFiles/strata_prefill.dir/src/prefill/prefill.cpp.o | tail -1 > /tmp/c1.sh
    ninja -t commands libstrata_prefill.a | tail -1 > /tmp/c2.sh
    ninja -t commands strata | tail -1 > /tmp/c3.sh
    bash -e /tmp/c1.sh && bash -e /tmp/c2.sh && bash -e /tmp/c3.sh'

# 换二进制必须 mv（cp 会 Text file busy）
mv ~/strata166/data/bin/strata-0.1.55t.new ~/strata166/data/bin/strata-0.1.55t
```
