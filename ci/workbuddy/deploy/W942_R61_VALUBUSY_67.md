# W942 · R61 结题：MMQ 的 **VALUBusy = 67.1%**（A 级 PMC）⇒ R60 stream-k 判死，R84 的依据升级

> **【AUDIT24 P1 · 2026-11-04】67.1% 复现了，但口径与留存要补**：本轮同形状复测
> （`kq_bench 16 1024 3 12 1280 2560`，Q4_K）= **64.78 / 68.15 / 68.18 / 68.17，均值 67.3%**，
> CSV 留在 `data/w952pmc/` ⇒ **67.1% 成立**。但 ①本件的原始 csv **已被后续 Q5_1 run 覆盖**
> （`data/w941pmc2` 现存的是 type 7）；**②结论层也要撤**：本件据此把 **R60 = DONE_NEG**、**R84 = DONE_NEG**，但 `W947` 按纪律⑱ 判定「用别的量推断」不合规 ⇒ **R60/R63 改回 OPEN、R84 改 INFLIGHT**（`R91` 另立）。本件的 VALUBUSY **数字**保留，**由它推出的两条关闭不保留**。
> ③**67.1% 是 M=1024 的形状**，生产形状（每专家 ≈320 行）在 `W945` 测到
> Q4_K **60.6%** —— 两个数都要标形状，不能互相替代；④§4 仍引 dp4a 53.3%（模块口径），见 `W924` 横幅。

- 日期：2026-11-04 14:0x–14:2x
- 方法：`W941` 打通了 `rocprofv3` **启动器**路径（不是 `HSA_TOOLS_LIB` 注入），本轮把它用到**独立可执行**上 —— 进程自然退出，tool 能 finalize，输出落盘。
- 一句话：**MMQ 不是「供给不足」，是「VALU 忙」**。stream-k 解决的是前者，所以不做了；dot8 减少的是后者，所以它的依据从"推算 3.22%"升级为"实测 VALU 67% 下 −18% kernel"。

---

## 1 驱动（新产物，可复用）

`~/strata166/w941/kq_bench.cpp` → `build-r28/kq_bench`（17,293,408 B）：

```
shape: type=Q4_K w=[1280,2560] n=16 rows/expert=1024 total_rows=16384 expert_bytes=1,843,200 reps=3
```

- 16 个专家组（`kGatherGroupMax`）× 1024 token = **16,384 rows**，正是生产 `--prefill auto:16384` 的 chunk 形状；
- 走的是生产同一份 `libstrata_mmq.a`（build-r28），**不是复刻**；
- 权重是随机字节（数值无意义，只测时间与计数器），激活走 `mmq::quantize` 真实量化；
- 编译：`albus/w941/build_bench.sh`（`hipcc -c` 再 `hipcc` 链接，`-x hip` 不能把 `.a` 当源码）。

## 2 PMC 数据（`rocprofv3 --pmc VALUBusy`，csv 在 `data/w941pmc2/6d2661d4ee6a/`）

| kernel | share | ms | **VALUBusy** | n |
|---|---:|---:|---:|---:|
| `mul_mat_q<(ggml_type)12, 64, false>` | **98.59%** | 28.2 | **67.1%** | 4 |
| `quantize_mmq_q8_1<(layout)1,false>` | 1.39% | 0.4 | 72.7% | 1 |
| `__amd_rocclr_copyBuffer` | 0.03% | 0.0 | 0.0% | 1 |

- **`(ggml_type)12` = Q4_K**，**`64` = J**（生产形状选出的 tile 就是 J=64，与 `W909` 的 "MMQ tile J=64" 一致）；
- 4 次 launch（1 次 warmup + 3 rep）合计 28.2 ms ⇒ **7.05 ms/launch**；
- 事件计时（独立于 PMC）：**7.099 / 6.895 / 6.935 ms = 7.56 / 7.79 / 7.74 TMAC/s**。

**两个数放在一起才是结论**：

```
吞吐     7.7 TMAC/s ÷ dot4 微基准峰 21.52 TMAC/s = 36%      ← 供给率只有三成半
VALU     67.1% 忙                                          ← 但 VALU 并不闲
```

VALU 忙、dp4a 却只跑到峰值的 36% ⇒ VALU 的时间花在**辅助指令**上，不是 dot 本身。

## 3 R61 结题 ⇒ R60 判死

| 项 | 判据（`W923` 定） | 实测 |
|---|---|---|
| R61 | `VALUBusy ≥ 40%` ⇒ 已到 VALU 墙、**R60 不做**；`≤ 25%` ⇒ R60 必做 | **67.1%** |

⇒ **R60（MMQ stream-k）DONE_NEG**：它解决的是「in-flight bytes 不足」（`W906` 引 ki 的 480 KB 需求），
而 67% 的 VALU 占用说明瓶颈在**指令发射/执行**，不在取数排队。改 K 切分不会减少 VALU 指令数。

`W923` 的算术预判（50–65%）**方向对、数值低估**：它的上界推算依赖"微基准 0.75 instr/MAC"，而真实内核配比更差（见 §4）。

## 4 与 `W924` 三段计数对上：VALU 在干什么

`W924` 的 Q4_K 实例指令分解（dp4a 5,184 / 解包 1,437 / LDS 1,204 / 缩放 1,064 / 地址 824，合计 9,713）：

- **dp4a 只占 53.3%**，其余 46.7% 是解包 + 载入 + 缩放 + 地址；
- 所以「VALU 67% 忙」与「dp4a 36% 供给率」**不矛盾**：VALU 有近一半时间在做 dot 以外的事。

## 5 R84（dot8）的分母修正：3.65% → **2.05%**，判据翻转（见 `W943`）

初稿按 `W928` 的口径用了「dp4a 占 53.3%」，得 3.65%。**但那个分母是错的**：`W924` 的 5,184/9,713 是**整个 `mmq-instance-q4_k` 模块**（多 J / fallback 实例求和），而同一次 PMC 显示真正执行的只有 `mul_mat_q<Q4_K, J=64, false>` **一个 kernel**。

本轮对该 kernel 做了 ISA census（3,411 条指令，`W943 §1`）：**`v_dot4_i32_i8` 只有 1,024 条 = 30.0%**，不是 53.3%。

| 步 | 数 | 来源 |
|---|---|---|
| dot4 段占比（真正执行的 kernel） | 1,024 / 3,411 = **30.0%** | `W943 §1`（A，ISS） |
| dot8 把该段减半 | −512 条 ⇒ 总指令 **−15.0%** | i4×i4 一次 8 MAC（`W909` 实跑） |
| VALU 占比 | **67.1%** | 本轮 PMC（A） |
| kernel 上限 | 67.1% × 15.0% = **−10.1%** | Amdahl |
| 端到端 | × gate/up 占 prefill **20.4%** = **−2.05%** | `W927` |

**−2.05% < 2×CV 门（3.2%）⇒ R84 按 `W925` 判据不做**（DONE_NEG）。乐观情形（int4 权重顺带省掉部分解包指令，约再 −3.4% 总指令）也只到 −2.4%，仍在门下。

**方法结论（比这条本身重要）**：同一份 ISA 计数，**分母从「模块总和」换成「真正执行的 kernel」，结论从"值得做"反转为"不做"**。`W925` 的分母纪律要补一句：**组件占比的分母必须是实际 dispatch 的那个 kernel**，模块/实例库的求和只能用来做"上界的上界"。

## 6 口径限制（必须一起说）

- 单 kernel、独立进程、**无并发 PCIe 拷贝**：生产 prefill 时专家 blob 在传，MMQ 的 VALU 占用可能被轻微拉低（降频/抢占），所以 67.1% 是**上界侧**；
- `VALUBusy` 是该 kernel 所有 dispatch 的平均，不是逐 tile 峰值；
- 这是 **Q4_K gate/up** 一个实例的数据，down（Q5_1/Q8_0）没有单独测；R84 也只动 gate/up，范围一致。

## 7 复现

```bash
# 1. 编驱动（容器内）
docker run --rm -v ~/strata166/pr/strata-fork:/src -v ~/strata166/build-r28:/out \
  -v ~/strata166/llama.cpp:/llama.cpp -v ~/strata166/w941:/work -w /out \
  strata-gfx906:0.2.10-101 bash /tmp/build_bench.sh    # 见 albus/w941/build_bench.sh

# 2. 采 PMC（必须停生产：16384 rows 要 ~330 MB 显存，生产只剩 882 MiB）
docker run --rm --device=/dev/kfd --device=/dev/dri -v ~/strata166/build-r28:/out \
  -v ~/strata166/data:/data -e STRATA_MMQ_KQ=1 -w /out strata-gfx906:0.2.10-101 \
  bash -lc 'rocprofv3 --pmc VALUBusy --output-format csv -d /data/w941pmc2 -- ./kq_bench 16 1024 3'

# 3. 解析
python3 /tmp/parse_pmc.py ~/strata166/data/w941pmc2
```

## 8 生产

本轮只停了一次（~4 分钟：停 → 1.2 s 的 bench → 起），**未改任何生产件**。config 仍是 `24d66f6a…`、`--prefill auto:16384`、引擎 `ae085365`。
