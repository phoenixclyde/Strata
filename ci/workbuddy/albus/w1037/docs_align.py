import io, shutil

# ---------------- ledger ----------------
P = "deploy/PROGRESS.tsv"
shutil.copyfile(P, P + ".bak_w1037c")
s = io.open(P, encoding="utf-8").read()

r1 = "\t".join([
    "B10环境与版本", "P432",
    "跟上游对齐（机主定）第一步：我们的 llama 树就是上游 pin（diff 0）；换 pin 要改 25 处 API，且必须重新 configure",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主 2026-11-07 07:1x：「跟上游对齐优先于收益，落实」）**：① `diff -rq ref/llama_3cf0325 llama.cpp` **输出为空** "
    "⇒ 生产 llama 树就是上游 b11062，**没有隐藏补丁集**，「对齐」纯粹是换 pin；② K10 的配方从上游重建："
    "`llama_b12110` 全树 + `ggml/src/ggml-cuda/mmq*`（mmq.cu/mmq.cuh/mmq-load-tiles/mmq-vec-dot + 10 个 mmq-config-*）取自 "
    "`4c1004c49221b07c3b8108977e3d1991fc9f45cc`（2026-10-19T07:41:14Z，#30553）；③ 换 pin 的真实代价是 API：上游把 "
    "`mul_mat_q_case` 从 `template<ggml_type>` 改成 `template<ggml_type, ggml_prec>`，我们树里 **25 处**调用要补 `GGML_PREC_Q8`"
    "（`mmq_kq_lib.cu` 4 / `mmq_nvfp4_w4a8.cu` 1 / `moe_mmq.cu` 20），已在 worktree `pr/k10` 改完；④ **构建坑**：`build.ninja` 用 "
    "`/out/ggml-tq-overlay/` 里的**拷贝**头文件（configure 期生成），把 `RERUN_CMAKE` 改成 phony 之后换 `/llama.cpp` 会编到旧副本——"
    "第一次「编译失败」其实是这个，不是 API。⇒ 换 llama 树必须重新 configure。",
    "P429", "KW:换 pin|ggml-tq-overlay"])

r2 = "\t".join([
    "B8工程", "P433",
    "门缺一条：装机件没要求「能再编出来」——K10 的源树已经丢了，只剩二进制；另两处丢失一并修",
    "W1037", "count", "1", "1", "DONE",
    "**W1037 立（机主：「你的门又有问题了吧。你自己看看什么丢了」）——找到三处真丢的**："
    "① `strata-0.1.57-010`（K10，md5 `6de7b937…`）在，**源树没了**；`deploy_gate` D2 只查回滚件、D6 只查报告，"
    "**没有一条门要求「这个二进制能再编一次」** ⇒ 新增 `deploy/REBUILD_RECIPE.tsv` + `tools/recipe_check.py`"
    "（4 列齐全才算候选；`LOST` 必须带 `P<数字>` 登记），本轮 **--live PASS**：3 件可重建、1 件已登记。"
    "② `albus/gfx906_survey/PORT_PLAN.md` 被机主定为「本方案的一个 R」，**却不在镜像集里 ⇒ 166 上根本没有这个文件**；"
    "`mirror_check.py` 从 6 件扩到 **7 件**（新增 `EXTRA` 机制，支持 deploy/ 之外的具名权威件），`--sync` 后 166 已有。"
    "③ 手法①的 ISA 证据原本只在 166 的 `tmp/`（断电即丢）⇒ 已抄成 `albus/w1037/STAGE_ISA_EVIDENCE.md`（md5、计数、命令、机制）。",
    "P428", "KW:能再编出来|7 件"])

out = s.rstrip("\n") + "\n" + r1 + "\n" + r2 + "\n"
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("ledger +2")

# ---------------- W832 ----------------
P2 = "deploy/W832_OPT_PLAN_V2.md"
shutil.copyfile(P2, P2 + ".bak_w1037c")
s2 = io.open(P2, encoding="utf-8").read()
a = "**373 条 / 已结 290 / 77.7%**（W1037 校正"
b = "**375 条 / 已结 292 / 77.7%**（W1037 校正"
assert a in s2
s2 = s2.replace(a, b, 1)

ADD = """
**十、K10 的源树丢了：这是「对齐」真正的拦路石，也是门缺的一条（`P432` / `P433`）。**
机主定「跟上游对齐优先于收益，落实」。查下去发现三件事：
① **我们的 llama 树就是上游 pin**（`diff -rq ref/llama_3cf0325 llama.cpp` 输出为空）⇒ 没有隐藏补丁集，对齐 = 换 pin；
② **K10 的配方这次从上游重建了**（`ref/llama_b12110` 全树 + `mmq*` 取自 `4c1004c49221b07c3b8108977e3d1991fc9f45cc` / 2026-10-19），
不再依赖那棵丢掉的树；③ 换 pin 的真实代价是 **API**：上游把 `mul_mat_q_case` 从 `template<ggml_type>` 改成
`template<ggml_type, ggml_prec>`，我们树里 **25 处**调用要补 `GGML_PREC_Q8`（`mmq_kq_lib.cu` 4 / `mmq_nvfp4_w4a8.cu` 1 / `moe_mmq.cu` 20），
已在 worktree `pr/k10` 改完、编译进行中。
**构建坑（会被误读成 API 错）**：`build.ninja` 用的是 `/out/ggml-tq-overlay/` 里的**拷贝**头文件（configure 期生成）；
把 `RERUN_CMAKE` 改成 phony 之后换 `/llama.cpp`，编的仍是旧副本 ⇒ **换 llama 树必须重新 configure**。

**十一、三处真丢的，都补了门。**
① **装机件不可重建**：`-010`(K10) 在、源树没了；`deploy_gate` 的 D2/D6 都不管这件事。
⇒ 新增 `deploy/REBUILD_RECIPE.tsv` + `tools/recipe_check.py`：四列（repo_sha / llama_base / llama_mmq / build_dir）齐全才算候选，
`LOST` 必须带 `P<数字>` 登记；本轮 `--live` PASS（3 件可重建、1 件已登记）。
② **权威件没进镜像**：`PORT_PLAN.md` 被机主定为「本方案的一个 R」，166 上却没有；`mirror_check.py` 6 件 → **7 件**
（新增 `EXTRA`，支持 deploy/ 之外的具名权威件），`--sync` 后已同步。
③ **证据在 tmp**：手法①的 ISA 证据原本只在 166 的 `tmp/`，已抄成 `albus/w1037/STAGE_ISA_EVIDENCE.md`。
"""
s2 = s2.rstrip("\n") + "\n" + ADD
io.open(P2, "w", encoding="utf-8", newline="\n").write(s2)
print("W832 +十/+十一")

# ---------------- reply ----------------
P3 = "albus/w1037/reply.md"
s3 = io.open(P3, encoding="utf-8").read()
a3 = "**373 条 / 已结 290 / 77.7%**（W1037 校正；本轮 +7：`P425`–`P431`）。"
b3 = "**375 条 / 已结 292 / 77.7%**（W1037 校正；本轮 +9：`P425`–`P433`）。"
assert a3 in s3
s3 = s3.replace(a3, b3, 1)
ADD3 = """
**12. 「跟上游对齐优先于收益」——落实的第一步撞出三处丢失（`P432` / `P433`）。**
① **我们的 llama 树就是上游 pin**：`diff -rq ref/llama_3cf0325 llama.cpp` **输出为空**（166 MB / 1632 文件逐字节相同）
⇒ 没有隐藏补丁集，「对齐」纯粹是换 pin，这比我原先担心的干净。
② **K10 这次从上游重建，不靠那棵丢掉的树**：`ref/llama_b12110` 全树 + `ggml/src/ggml-cuda/mmq*`
（`mmq.cu` / `mmq.cuh` / `mmq-load-tiles.cuh` / `mmq-vec-dot.cuh` + 10 个 `mmq-config-*.cuh`）取自
`4c1004c49221b07c3b8108977e3d1991fc9f45cc`（2026-10-19T07:41:14Z，PR #30553），叠合后 `mmq.cuh` md5 `b74eadc5…` → `627c4c62…`。
③ **换 pin 的真实代价是 API**：上游把 `mul_mat_q_case` 从 `template<ggml_type>` 改成 `template<ggml_type, ggml_prec>`
（`mmq.cuh:1536` / `DECL_MMQ_CASE` 变成 `<type, GGML_PREC_Q8>`），我们树里 **25 处**调用要补第二个实参
（`mmq_kq_lib.cu` 4 / `mmq_nvfp4_w4a8.cu` 1 / `moe_mmq.cu` 20），已在 worktree `pr/k10` 改完。
④ **一个会被误读成 API 错的构建坑**：`build.ninja` 用的是 `/out/ggml-tq-overlay/` 里的**拷贝**头文件（configure 期生成）。
我之前为了跳过 cmake 把 `RERUN_CMAKE` 改成了 phony，于是换 `/llama.cpp` 之后编的仍是旧副本；
第一次的「`strata_w4a4_mul_mat_q_case` 没有匹配函数」其实是这个。⇒ **换 llama 树必须重新 configure。**

**三处真丢的，都补了门。** ① `-010`(K10) 的**源树没了**，而 `deploy_gate` 的 D2 只查回滚件、D6 只查报告，
没有一条门要求「这个二进制能再编一次」⇒ 新增 `deploy/REBUILD_RECIPE.tsv` + `tools/recipe_check.py`
（四列齐全才算候选，`LOST` 必须带编号；本轮 `--live` **PASS**：3 件可重建、1 件已登记）。
② `PORT_PLAN.md` 被机主定为「本方案的一个 R」，**166 上却没有这个文件** ⇒ `mirror_check.py` 6 件扩到 **7 件**
（新增 `EXTRA` 机制），`--sync` 后已同步。③ 手法①的 ISA 证据原本只在 166 的 `tmp/`（断电即丢）
⇒ 已抄成 `albus/w1037/STAGE_ISA_EVIDENCE.md`。
"""
s3 = s3.rstrip("\n") + "\n" + ADD3
io.open(P3, "w", encoding="utf-8", newline="\n").write(s3)
print("reply +12")
