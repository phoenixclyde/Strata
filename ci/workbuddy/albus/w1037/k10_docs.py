import io, shutil

# ---- rebuild recipe: add the K10p row ----
P0 = "deploy/REBUILD_RECIPE.tsv"
shutil.copyfile(P0, P0 + ".bak_w1037")
s0 = io.open(P0, encoding="utf-8").read()
ROW = ("strata-0.1.57-k10p\te0a6987f732a401f780f5dad5812812f\t43207464\tgfx906/lcpp-k10 @ fa8e6761\t"
       "b12110（ref/llama_b12110）\t4c1004c49221b07c3b8108977e3d1991fc9f45cc\t"
       "build-k10p（/src=pr/k10，/llama.cpp=tmp/w1037/llama-k10）\t"
       "K10 重建件，**未装机**；TQ overlay ON；见 P437\n")
s0 = s0.rstrip("\n") + "\n" + ROW
io.open(P0, "w", encoding="utf-8", newline="\n").write(s0)
print("recipe +1")

# ---- ledger ----
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_w1037g")
s = io.open(P, encoding="utf-8").read()
r = "\t".join([
    "B10环境与版本", "P437",
    "K10 搞定：换成 llama.cpp b12110 + mmq@4c1004c，TQ overlay 保持 ON，编译通过（e0a6987f / 43,207,464 B）",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主：「把 llama.cpp 那个搞定」「关掉干嘛，开」）**：从上游重建 K10 并编译通过，"
    "**TQ overlay 保持 ON**（不是关掉绕过）。四处 API delta 全部实测定位并适配："
    "① `mul_mat_q_case<type>` → `<type, GGML_PREC_Q8>`（#30168）**25 处**；"
    "② `ggml_cuda_mmq_get_config(.., cc)` → `(.., cc, GGML_PREC_Q8)` **5 处**；"
    "③ `ggml_backend_cuda_context::new_pool_for_device` 多一个 ctx 形参 **1 处定义**；"
    "④ `cmake/strata_ggml_tq_overlay.cmake` 里 `\", false\"` 那个第 5 个模板实参是**从 get_nthreads 推断**出来的，"
    "b12110 已去掉 ⇒ 改为**直接探测 write-back 自己的签名**（推断是这次 `no matching constructor` 的根因）。"
    "另一个坑：`build.ninja` 用的是 `/out/ggml-tq-overlay/` 的**configure 期拷贝**，换 `/llama.cpp` **必须重新 configure**。"
    "候选件 `/data/bin/strata-0.1.57-k10p` = `e0a6987f732a401f780f5dad5812812f` / 43,207,464 B（未装机），"
    "分支 `gfx906/lcpp-k10` @ `fa8e6761`（父 = 主线 e181bda5，脏 0），配方已进 `deploy/REBUILD_RECIPE.tsv`。"
    "上游三个 PR 已逐个核过：`#29953` OOB 修复 2026-10-08 / `#30168` prec 参数 2026-10-09 / `#30553` Stream-K 封顶 2026-10-19（= 4c1004c）。",
    "P430", "KW:K10|tq_overlay"])

out = s.rstrip("\n") + "\n" + r + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +1 (P437)")

# ---- W832 ----
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_w1037g")
s2 = io.open(P2, encoding="utf-8").read()
a = "**378 条 / 已结 295 / 78.0%**（W1037 校正"
b = "**379 条 / 已结 296 / 78.1%**（W1037 校正"
assert a in s2
s2 = s2.replace(a, b, 1)
ADD = """
**十四、llama.cpp 那个搞定了：K10 从上游重建并编译通过，TQ overlay 保持 ON（`P437`）。**
机主「把 llama.cpp 那个搞定」「关掉干嘛，开」。结果：分支 `gfx906/lcpp-k10` @ `fa8e6761`（父 = 主线 `e181bda5`，脏 0），
候选件 `/data/bin/strata-0.1.57-k10p` = `e0a6987f732a401f780f5dad5812812f` / 43,207,464 B，**未装机**。
llama 树 = `ref/llama_b12110` + `ggml/src/ggml-cuda/mmq*` 取自 `4c1004c49221b07c3b8108977e3d1991fc9f45cc`（2026-10-19）。
**四处 API delta（全部实测定位，不是猜的）**：

| # | 上游改动 | 我们的改法 | 处数 |
|---|---|---|---|
| 1 | `mul_mat_q_case<type>` → `<type, GGML_PREC_Q8>`（#30168） | 每个调用点补 `GGML_PREC_Q8` | **25** |
| 2 | `ggml_cuda_mmq_get_config(.., cc)` → `(.., cc, GGML_PREC_Q8)` | 同上 | **5** |
| 3 | `ggml_backend_cuda_context::new_pool_for_device` 多一个 ctx 形参 | 定义处补形参 | 1 |
| 4 | `cmake/strata_ggml_tq_overlay.cmake` 的 `", false"` 第 5 个模板实参 | 原来是**从 get_nthreads 推断**，b12110 已去掉 ⇒ 改为直接探测 write-back 自己的签名 | 1 |

**两个坑值得记**：① `build.ninja` 用的是 `/out/ggml-tq-overlay/` 的 **configure 期拷贝**，换 `/llama.cpp` 之后不重新
configure 就会编到旧副本（第一次「编译失败」是这个，不是 API）；② TQ overlay 的版本探测靠推断，上游删一个模板实参就会
在 `ggml_cuda_mmq_util_funcs` 的构造函数上报错 —— 推断改成实测（grep write-back 签名）之后就通了。
"""
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 +十四")

# ---- reply ----
P3 = "albus/w1037/reply.md"
s3 = io.open(P3, encoding="utf-8").read()
a3 = "**378 条 / 已结 295 / 78.0%**（W1037 校正；本轮 +12：`P425`–`P436`）。"
b3 = "**379 条 / 已结 296 / 78.1%**（W1037 校正；本轮 +13：`P425`–`P437`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
ADD3 = """
**15. llama.cpp 那个搞定了：K10 从上游重建、编译通过、TQ overlay 保持 ON（`P437`）。**
分支 `gfx906/lcpp-k10` @ `fa8e6761`（父 = 主线 `e181bda5`，脏 0）；候选 `/data/bin/strata-0.1.57-k10p`
= `e0a6987f732a401f780f5dad5812812f` / 43,207,464 B（**未装机**）。四处 API delta：`mul_mat_q_case` 补 `GGML_PREC_Q8` **25 处**、
`ggml_cuda_mmq_get_config` **5 处**、`new_pool_for_device` 补 ctx **1 处**、
`cmake/strata_ggml_tq_overlay.cmake` 的 `", false"` 第 5 实参改为**直接探测 write-back 签名**（原来是从 get_nthreads 推断，b12110 已去掉）。
两个坑：换 `/llama.cpp` 必须重新 configure（否则编的是 `/out/ggml-tq-overlay` 里的旧拷贝）；TQ overlay 的版本探测不能靠推断。
上游三个 PR 已逐个核过：#29953（2026-10-08 OOB）、#30168（2026-10-09 prec 参数）、#30553（2026-10-19 = 4c1004c）。
"""
s3 = s3.rstrip("\n") + "\n" + ADD3
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply +15")
