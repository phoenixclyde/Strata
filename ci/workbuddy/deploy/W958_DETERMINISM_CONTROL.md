# W958 · R90-S4 第二轮：确定性对照——**生产件自己就不复现，"逐位"判据作废**

- 日期：2026-11-04 18:4x–19:2x
- 触发：`W957` 得到"0.8.0 vs 0.4.1 前缀 7"，按计划先证伪（同二进制重复跑），再做归因。
- 一句话：**A（0.4.1 生产件）两次跑只有 7/64 个 token 相同；B（0.8.0 移植版）两次跑 64/64 完全相同。**
  ⇒ token 序列**不能**用来判升级；而且"更可复现"的一方是待升级的 0.8.0。

---

## 1 设计与执行

同一 prompt（2048 个合成 id）、同一套 args；本轮加 `--dump-routing`（想区分"路由不同"还是"算术不同"）。
一次停服里跑三次：`A1`、`A2`（都是 `/data/bin/strata-0.1.56`）、`B1`（`build-080c/strata`）。

| 臂 | 二进制 | 输出长度 | 全同位置 vs B1 |
|---|---|---:|---:|
| A1 | 0.4.1 | 64 | **7 / 64** |
| A2 | 0.4.1 | 64 | — |
| B1 | 0.8.0 | 64 | — |

## 2 结果：A 自己就不复现

| 对照 | 相同前缀 | 全同位置 |
|---|---:|---:|
| **A1 vs A2（同一二进制、同一 args）** | **3** | **7 / 64** |
| A1 vs B1（跨版本） | 7 | 7 / 64 |
| **B1 vs `W957` 的 B（跨会话、跨 flag）** | — | **64 / 64** |

前 8 个 token 实测：

```
A1 : 248045 271 248045 487 198 262 328  846  763 328
A2 : 248045 271 248045 271 248045 271 248045 248046 198      <- 第 4 个就分叉
B1 : 248045 271 248045 487 198 262 328 1666 41882 763
B  : 248045 271 248045 487 198 262 328 1666 41882 763        <- 与 B1 逐字相同
```

⇒ **`W957` 的"前缀 7"落在 A 自己的噪声里**（A1/A2 前缀只有 3）。用它判升级是**无效测量**。

## 3 为什么不可复现（源码已写明，不是猜）

`src/program/generate.cpp:12706` 的注释，讲专家竞技场换入换出：

> "**Not bit-exact run to run**: which window first computes a swapped-in expert on the GPU
> (**which rounds differently from the CPU**) depends on when its copy lands."

我们的模型 77 GB / 卡 32 GB，换出换入是常态：三次跑各换了 **1436 / 576 / 1372** 个专家
（`adaptive tier … experts swapped into the VRAM tier`），落在哪个窗口由拷贝完成时刻决定 ⇒ 数值抖动。

**但这条解释不了"B 为什么 64/64 稳定"**：B1 也换了 1372 个专家，也开了 adaptive tier，也开了 rocBLAS tuning。
待查的假设（按成本排序）：

1. **`rocBLAS` 的启发式选解**：日志两臂都有 `rocBLAS tuning enabled (84 rows, 75 with a solution)`；
   若运行期按计时重选 GEMM 算法，A 会在两次跑里选到不同算法（⇒ 不同累加序）。B 的同类形状可能被 MMQ 接管、不再走 rocBLAS。
   **测法**：`--rocblas-tuning 0`（或固定表）下跑 A 两次，看是否变成 64/64。
2. **CPU/GPU 混算的比例**：A1/A2 的 `pcie experts` 读数不同会改变"哪些 token 用 CPU 算专家"。
   **测法**：`--expert-cache` 给死值（不 auto）+ `--adapt-async 0`，让换入序列固定。
3. **我们的 30 行适配**恰好修掉了某个竞争（可能性低，但不能排除）。

## 4 结论（两条，都影响方案）

1. **"逐位/同 token 序列"这条判据在 0.4.1 上不成立**，不是"0.8.0 不逐位"。
   `W954 §5` 里我写的"① 逐位"必须撤掉，换成可执行的判据。
2. **升级不能按"输出相同"验收**。能验收的只有：
   - **性能**：六长度档 A/B（`|Δ| ≥ 2×CV`），decode 只守不劣化；
   - **质量**：对**金标**比 KL/top-1（不是两臂互比），且**先测噪声地板**（同二进制两次的 KL，若不是 0 就以它为门槛）。

## 5 下一步（改过的顺序）

| # | 实验 | 判据 | 停服 |
|---|---|---|---|
| 1 | **找确定性配置**：A 两次，`--adapt-async 0` + `--rocblas-tuning 0`（或固定表） | A1 vs A2 = 64/64 ⇒ 配置可用 | 2 次载入 |
| 2 | 用该配置：**A vs A 的 KL 地板**（serve + `STRATA_DUMP_FIRST_LOGITS`） | 地板 = 0.0000 才算"可判"（`W913` 曾得到 0.0000） | 2 次 |
| 3 | 该配置下 **A vs B 的 KL + top-1** | `KL ≤ 0.005` 且 top-1 ≥ 99% | 2 次 |
| 4 | **六长度档吞吐 A/B**（真实文本） | `|Δ| ≥ 2×CV` | 2 次 |

> 注意：`--dump-logits` 在 generate 的 native pack 上不写文件（`W957 §1`），而 **serve 的 `STRATA_DUMP_FIRST_LOGITS`
> 是另一条路径**（`generate.cpp:18572`，在 serve 的首窗口分支里）——质量测量必须走 serve。

## 6 复现

```bash
bash albus/w958/det.sh      # A1 A2 B1 三次，含 --dump-routing，自动恢复生产
python3 - <<'EOF'
def ids(p):
    for l in open(p):
        if l.startswith("output"): return [int(x) for x in l.split(":",1)[1].split()]
a1,a2,b1 = (ids("data/w958/%s.out" % n) for n in ("A1","A2","B1"))
print("A1/A2 全同", sum(x==y for x,y in zip(a1,a2)), "A1/B1 全同", sum(x==y for x,y in zip(a1,b1)))
EOF
```
