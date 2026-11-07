# W957 · R90-S4 第一轮：0.8.0 跑起来了，但**不逐位**（前缀 7 / 64）

- 日期：2026-11-04 18:0x–18:5x
- 分支 `exp/R90-080`（commit **`999b9121`**，6 文件 +59/−35）；生产只被停过 4 次做测量，每次自动恢复
- 一句话：**0.8.0 能端到端跑 native pack；但它与 0.4.1 的贪心输出在第 8 个 token 分叉**。
  这**不是**"0.8.0 不行"的证据——还差一个对照（同二进制重复跑），见 §5。

---

## 1 先纠正方法：`--dump-logits` 在 native pack 上写不出东西

原计划比 logits。实跑两臂都得到 **0 字节**文件，日志却打印 `logits dumped`。源码给了原因（`generate.cpp:8760` 注释逐字）：

> "The logits header is written WITH THE FIRST ROW, not at open: **a native pack never reaches the per-token dump site**,
> and a header promising rows that were never written is worse than no file."

⇒ **native pack 走的是另一条 prefill 路径，`--dump-logits` 不适用**。改用引擎自己打印的
`output : <token ids>`（`--max-new 64 --top-k 1` 贪心），这也正是本项目"比 argmax 序列"的本意。

## 2 第一次跑：B 臂直接 abort，`J_best=412`

```
J_best=412
/ref/ggml/src/ggml-cuda/template-instances/../mmq.cuh:1594: fatal error     (GGML_ABORT)
```

根因在 `mmq_args` 的结构变化：

| 版本 | 结构体末尾 |
|---|---|
| 0.4.1 | `int64_t ncols_max; int64_t ncols_opt;` |
| **0.8.0** | `int64_t ncols_max; **int J_best**; ggml_cuda_mm_fusion_args_device fusion;` |

我们的初始化是**位置式**的，最后两个 `p.max_rows` 在 0.8.0 里第二个落进 `J_best`（412），
而 `mul_mat_q_switch_J` 遇到 8..128 之外的值就 `GGML_ABORT`。

**修法**：`pick_J()` —— 上游的 `ggml_cuda_mmq_get_J_best` 在 0.8.0 里是 `mmq.cu` 的 **static**，
我们的 TU 调不到，所以照它的规则（"fewest tiles that fit the shared memory"）重写 12 行，
放在 `fits()` 旁边（两者走同一条 J 阶梯）。

> 这条正好是 `W955` 判据②存在的理由：**"编过"不等于"等价"**，甚至不等于"能跑"。

## 3 结果：64 个贪心 token，前 7 个相同

同一 prompt（2048 个合成 token id）、同一套 args（`--kv k8v4 --prefill auto:16384 --spec 4 --pcie-frac 0.20`）：

| 臂 | 二进制 | 输出 | prefill |
|---|---|---|---|
| A | `strata-0.1.56`（= 0.4.1 生产件） | 64 token，RC=0 | 2047 tok / 3384.5 ms = **604.8 tok/s** |
| B | `build-080c/strata`（= 0.8.0） | 64 token，RC=0 | 2047 tok / 3601.3 ms = **568.4 tok/s** |

- **相同前缀 = 7**；第 8 个 token：A `33413` vs B `1666`
- 前 7 个：`248045 271 248045 487 198 262 328`（两臂逐字相同）

**速度差 −6.0% 不作判据**：单次、且这是合成 prompt（随机 id 路由分散、无缓存局部性），
与生产 800 tok/s 的口径不同；要判必须多 rep + 真实文本。

## 4 怎么解读"前缀 7"

三种可能，**目前还不能区分**：

1. **上游算法变了**（`mmq.cuh` 585 行、fatbin +10.9%）⇒ 数值路径本就不同，分叉属预期；
2. **我们的适配有 bug**（`GGML_PREC_Q8` 选错 / `pick_J` 与上游不等价 / 结构体还有字段错位）；
3. **引擎本身 run 间不确定**（`W899 §7.11` 记过"不比文本哈希 ⇒ 引擎 run 间不确定"）。

第 3 条最要命：如果同二进制两次跑也不一致，那"前缀 7"就**不能**当升级的证据。
**下一轮第一件事就是打这个对照**（见 §5），不是继续调 0.8.0。

## 5 下一步（按顺序，先证伪再取证）

| # | 实验 | 判据 |
|---|---|---|
| 1 | **同二进制重复跑**：A 跑两次、B 跑两次（各 64 token） | 若 A vs A 也不一致 ⇒ 该项测试作废，改用 §6 的容差判据 |
| 2 | 若 A/B 各自稳定：定位分叉在**哪一段** | 用 `--max-new 1` 逐 token 追加（前缀 8/9/10）看第几个 token 起分叉，判断是 prefill（MMQ）还是 decode（GEMV） |
| 3 | 若 prefill 就分叉：关 `STRATA_MMQ_KQ=1` 复跑 | 关掉后两臂若一致 ⇒ 差异在我们的 MMQ 适配，不在上游 |
| 4 | 端到端 A/B（六长度档，真实文本） | `|Δ| ≥ 2×CV`，decode 只守不劣化 |

## 6 判据要改（建议写进 `W954`）

原判据"argmax 序列相同"是**同一版本内做优化**时的纪律；跨 4 个 minor 的基线升级，上游自己就改了数值路径，
要求逐位相同等于要求"升级不做任何数值改进"。建议改成：

- **升级类**：`KL ≤ 0.005 且 top-1 ≥ 99%`（与 `R59` 同一把尺子），**或** 与 0.4.1 的 64 token 前缀 ≥ 48（75%）；
- **同版本优化**：仍守逐位（`R55`/`R91` 那种）。

## 7 复现

```bash
# 两臂（生产会停 ~4.5 min/臂，脚本自动恢复）
bash albus/w957/ab_logits.sh          # 需要 /models、/src、/data 三个挂载
# 比 token
python3 - <<'EOF'
def ids(p):
    for l in open(p):
        if l.startswith("output"): return [int(x) for x in l.split(":",1)[1].split()]
a,b=ids("data/w957/A.out"),ids("data/w957/B.out")
i=next((k for k in range(min(len(a),len(b))) if a[k]!=b[k]), min(len(a),len(b)))
print("prefix",i,"div",(a[i],b[i]))
EOF
```
