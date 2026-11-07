#!/usr/bin/env python3
import io
sec = """
## 12:5x W938 · 三件事：回溯补账 / rebase 到 v0.2.10 / 容器跟主线（生产已换引擎+镜像）
- **①回溯**：部署账本 `ci/state/prod_history.tsv` 15→**26 行**（补 r17 前 11 个历史引擎，按 `/data/bin` mtime+md5，tag 列 ` -`；补 11-02 后漏记三次 a97f4479/8e92c662/cf2ba243 标 `retro-recorded`）。`rollback --last` 从错误的 r26 修正为 `strata-0.1.55v`。实验记录 `state/runs` 4→**21 条**，补 17 条全部带 `reconstructed:true` + `provenance:<文档>` + `samples:[]`，只搬文档已有中位数。r1–r16 **不补**（无 md5/无文件，不编造）。
- **②rebase**：`bundle --all`(76MB) + 6 个 `pre-rebase/*` + rerere → 37 条重放到 `upstream/main ffa80d73`。**三处冲突**：`arch_defaults.hpp` 两边各加声明⇒都留；`qsa_select.cu` 上游已完整实现 W842（SIMT=2+社区调优+alt_min_tokens）⇒取上游；`generate.cpp` 两处（MTP_ROOM 块 / spec 阶梯重构）⇒保上游结构，把我们的话放在语义正确位置（trace 打点放块前；`/data/strata-spec` 读取提到派生值之前，否则 S_mtp_wide 等按旧 S 算）。结果 **0/37**、无残留标记、7 项 tuned 表完整。
- **补丁债归零（重要）**：`e1b27d54`(fatal GPU)、`5a13c34f`(PLE 提限)、`243fdb21`、`ed76b12f`、`fbf6e1c7`、`af6ba4c6` **全是 upstream 祖先** ⇒ 0.2.10 原生含，`work/r77` 手工补丁树作废。以后不要重复移植已有的上游提交——先 `git merge-base --is-ancestor` 查。
- **分支（业内做法）**：已否定的实验分支（r54-port / exp-R55-swizzle / bench-mi50-32gb-262k / w863-main）打 `archive/*` tag 保留提交后删除，**不 rebase**；main 快进到 origin/main；`push --force-with-lease origin gfx906/mi50` 成功，远端=5f73cd15=HEAD，tag `mi50-0.2.10-r28` 已推。
- **③容器**：新 Dockerfile `FROM mixa3607` 试过——**构建期无外网**（pip 到 tuna `No matching distribution found`，apt 能过）⇒ 改 `FROM strata-gfx906:0.2.9-101` 只替换 `/src`（ROCm/clang/python 逐字节不变）。镜像 `strata-gfx906:0.2.10-101`(5267df6d)，/src 266MB，`/src/BUILD-IMAGE.json` 记 provenance。**/data 是 bind ⇒ 引擎不进镜像**：引擎走 `ci deploy`，/src 走镜像。
- **部署（走正门）**：`ci/strata-ci deploy --src build-r28 --exe strata-0.1.56 --apply` → gate 18/18、tag 门禁过、health 243s、账本行 tag=`mi50-0.2.10-r28` git_head=5f73cd15 ⇒ **provenance 断裂修复**（账本末条 tag == HEAD tag）。容器参数由 `docker inspect` 程序化生成重建，旧容器留 `strata166-407.pre-210`。
- **性能**：prefill 8.868→**8.810/8.814**(−0.6%, CV1.3%)；decode 稳态 79.44→**~83.7**(+5%)；官方 `strata-ci bench --n 12` = **73.49 tok/s CV1.84%**（已存 state/runs）。显存布局与之前完全一致（cache 7463 / borrows 2606 / PLE 26.82 GiB）。
- **行为变化**：`window up to 6` → **`up to 12 tokens`**（buffer 96.2→131.3 MiB）。已立 **R81** 拆归因（扫 `--spec`/`--mtp-max-t`，看按深度接受率）。
- **ci/config.sh** 改 `BUILD=build-r28`、`IMG=strata-gfx906:0.2.10-101`。旧 `gfx029-build`(0.1.55) 保留作回滚对照。
- 纪律新增（W832）：⑫开新活前先 rebase（别攒 700 条）；⑬rebase 前 bundle+pre-rebase 指针+rerere，死分支不 rebase；⑭`--force-with-lease` 永不裸 force；⑮跨代版本必须同时换 /src 与引擎（只换引擎会让 serve 层落后一代）。
- 产物：`deploy/W938_REBASE_AND_CONTAINER.md`；PROGRESS R82/R83(DONE)+R81(OPEN)；P263；备份 `~/strata166/backup/strata-all-refs-20261104.bundle`；镜像 ctx `build-ctx-210/`。
"""
p = "D:/workbuddy_space/strata_ws/.workbuddy/memory/2026-11-04.md"
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("appended", len(sec))
