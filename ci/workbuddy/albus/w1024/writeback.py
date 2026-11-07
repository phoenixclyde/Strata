import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

BLOCK = '''
### 回写 · W1024（容器内版本实测 + rebase 全程复核 + 最新 llama.cpp 的真实阻塞）

**一、容器内版本（`docker exec strata166-407`，不是宿主、不是镜像台账）**

| 项 | 值 | 取法 |
|---|---|---|
| ROCm 打包标记 | **10.1.0** | `cat /opt/rocm/.info/version`（唯一文件，7 字节） |
| HIP 运行时 | **7.16.26323-0000000** | `hipconfig --version`；库名 `libamdhip64.so.7.16.26323-0000000` |
| 编译器 | **clang 24.0.0git**（ROCm LLVM `e3dd2f54`） | `hipcc --version` |
| 构建标识 | **7.14.0-gfx906+20260802001858** | 容器 env `ROCM_BUILD`（自建 gfx906 分支） |
| rocprofv3 | 1.3.5 | `rocprofv3 --version` |
| llama.cpp | **b11062 = `3cf03257f219afbe7334045ff7c6a06ac68c627d`** | `/src/BUILD-IMAGE.json` 的 `llama_cpp` / `llama_cpp_build` |
| llama.cpp 树 | 2824 文件 / 166,037,690 B / hash `6feee589…`，**无 `.git`** | 容器内 `find … md5sum \\| md5sum` |

三个数字不同不是笔误：这是自建 gfx906 树，`.info/version` 是打包字符串，`ROCM_BUILD` 是构建 ID，HIP 运行时才是组件版本。

**二、rebase 全程复核（结论：树逐字节等价，无丢失）**

| 检查 | 结果 |
|---|---|
| rebase 后 vs merge 后的树 | `git diff 85297483 22abb0c0` **输出为空** ⇒ 零丢失、零多余 |
| 提交数 | merge 版 66 = **2 个 merge commit** + 64 实质；rebase 版 64 ⇒ **64/64 全部保留** |
| 线性 | `merges=0`、`behind=0`、`ahead=71`、`origin == HEAD`、`dirty=0` |
| 上游引擎 TU 是否被覆盖 | `src/prefill/prefill.cpp`、`gemm.cu`、`gemm_w16_parity.cu` 相对 9f7d977d **零改动** ⇒ 上游修复完整保留 |
| tag | `r33-2..8` 均在主线祖先链上；`r33-1`（`85297483`）是 **merge 版快照**，ORPHAN 但由 tag 固定，正好是上面那条等价性判据的基准 |
| 分支 | `main` 已对齐（ahead 3 / behind 0）；`exp/R90-080` 曾落后主线 5 且 **0 个独有提交** ⇒ 本轮 `reset --hard` 对齐到 `372106ed`；`exp/lcpp-b12129` 保留 1 个独有提交 |

**三、最新 llama.cpp：b12169，但它不能直接换（阻塞点已定位到一行代码）**

- 最新 tag **`b12169` = `3ed7284f2d9e22b2d1a7d05c1416c00c5a9f0bc7`**，比 `b12129` 多 **40 个提交**；
- 这 40 个里碰 MMQ 的只有 **`69ee2ecc` = #31047**（6 文件、+230/−231），其余是 vulkan/metal/opencl/webgpu/hexagon/server；
- **修正 W1023 的归因错误**：#31047 **不在** b12129 里，而在 b12129..b12169 之间 ⇒ 上次那 −4% 是"**没有**这个优化的版本"，不能说成"抄不到"；
- 把 #31047 单独打到 b12129 上（patch 干净应用，dry-run rc=0）后编译，**只余 1 个错误**：

```
src/prefill/moe_mmq.cu:505:73: error: cannot initialize a member subobject of type
'const ggml_cuda_mm_id_tile_spec *' with an lvalue of type 'const int32_t *const'
```

原因：`mmq_args` 的第二组字段被换掉了 —— `expert_bounds`（`int32_t*`）→ **`tile_spec`（`ggml_cuda_mm_id_tile_spec*`）**，`ncols_max` → `ntj`；spec 每条 16 字节 `{expert, col_low, col_high, padding}`，由 `mmid.cu` 的 helper **预计算 tile 分配**（`ceil(n_tokens*n_expert_used/J) + n_expert` 条）。

这不是"改签名"，是"**改分派数据的形状**"：我们 `moe_mmq.cu:505` 自己构造 `mmq_args`、`p.bounds` 在显存里（`src/prefill/prefill.cpp:2252` 传入），要换成 spec 就得在 device 端把「每专家列区间」按 J 切成「每 tile 一条」。**算错不报错**，所以必须整体重写 + 逐字节验证，不能今晚顺手改。

**四、下一步（P359，需要 2–3 小时，单独立项）**

1. 在 `exp` 分支写 `bounds → tile_spec`（device kernel，避免 D2H 同步；参照 `mmid.cu:120-140` 的 seam 对齐）；
2. 先过**数值门**：贪心指纹逐字节 == b11062，再谈速度；
3. 判据同 W1023：任一档超 2×CV 即回滚；
4. 收益预期：PR 自报 MI50 Q4_0 mb64 **1.23×**，但我们的专家是 Q4_K/Q5_K —— 是否适用**必须实测**，不能外推。

**五、本轮没有动生产**

`strata-0.1.57-001` / config `53ac61e0…` / 容器 `2d765942e041` 全部未变；`RELEASE_CHECK` 仍 10/10；`build-lcpp` 与 `exp/lcpp-b12129` 是离线的，主线 `372106ed` dirty 0。
'''
if "回写 · W1024" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK

s = s.replace("| 进度分母 | **286 条 / 已结 206 / 72.0%** |", "| 进度分母 | **289 条 / 已结 209 / 72.3%** |", 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P357",
  "容器内版本实测：ROCm 打包 10.1.0 / HIP 7.16.26323 / clang 24.0.0git；llama.cpp b11062 = 3cf03257",
  "W1024", "DONE",
  "**W1024 立**：`docker exec` 逐条取——`/opt/rocm/.info/version`=**10.1.0**、`hipconfig --version`=**7.16.26323-0000000**、"
  "`hipcc`=clang **24.0.0git**（ROCm LLVM e3dd2f54）、env `ROCM_BUILD=7.14.0-gfx906+20260802001858`、rocprofv3 1.3.5。"
  "llama.cpp=`/src/BUILD-IMAGE.json` 的 `llama_cpp`=`3cf03257…`、`llama_cpp_build`=**b11062**、树 hash `6feee589…`（2824 文件/166,037,690 B，无 .git）。"
  "三套 ROCm 数字不同是因为自建 gfx906 树：打包字符串 / 构建 ID / HIP 运行时分别独立。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1024"),
 ("B3git", "P358",
  "rebase 复核：`git diff 85297483 22abb0c0` 为空（树等价）、66=64+2 merge、上游 3 个引擎 TU 零改动、exp/R90-080 已对齐",
  "W1024", "DONE",
  "**W1024 立**：①树等价——merge 版 `85297483` 与 rebase 版 `22abb0c0` 的 diff **输出为空**；②提交 66 = **2 个 merge commit** + 64 实质，rebase 保留全部 64；"
  "③`merges=0 behind=0 ahead=71 origin==HEAD dirty=0`；④`src/prefill/prefill.cpp`/`gemm.cu`/`gemm_w16_parity.cu` 相对 9f7d977d **零改动** ⇒ 上游修复未被覆盖；"
  "⑤tag `r33-2..8` 可达，`r33-1` 是 merge 版 ORPHAN 快照（等价性判据的基准）；⑥`exp/R90-080` 0 独有提交、落后 5 ⇒ 已 `reset --hard 372106ed`；`exp/lcpp-b12129` 保留 1 个独有提交。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1024"),
 ("B8工程", "P359",
  "#31047 把 mmq_args 的 expert_bounds 换成 tile_spec（16 字节/条），b12169 需重写 MoE 分派层，不是改签名",
  "W1024", "OPEN",
  "**W1024 立**：最新 tag `b12169`=`3ed7284f…`，比 b12129 多 40 提交，其中碰 MMQ 的只有 `69ee2ecc`(#31047，6 文件 +230/−231)。**修正 W1023**：该提交不在 b12129 里。"
  "把 #31047 单打到 b12129 后编译，仅剩 1 错：`src/prefill/moe_mmq.cu:505:73 cannot initialize 'const ggml_cuda_mm_id_tile_spec *' with 'const int32_t *const'`——`mmq_args.expert_bounds`→`tile_spec`、`ncols_max`→`ntj`。"
  "spec=ceil(n_tokens*n_expert_used/J)+n_expert 条 {expert,col_low,col_high,pad}，由 `mmid.cu:120-140` 的 seam 对齐逻辑生成。"
  "下一步：device 端 bounds→spec，先过贪心指纹逐字节一致，再 bench；预期 PR 自报 MI50 Q4_0 mb64 1.23×，Q4_K 是否适用必须实测。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1024"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
ID = lines[hi].split("\t").index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("plan block + %d rows" % len(add))
