# W1043 报告 · 四项报告「第一张空表」查清并固化 + R103 装机前置（全程零停机）

> 一句话：机主指出的「第一张是空表」不是文件没数据，而是 **W1038–W1042 连续五轮把 `3a`/`3b` 写成两列**，
> GFM 给第三列补出**空的「值」单元格**、超长第二列又把表撑出视口；已修回三列并加 T0–T4 结构门。
> 顺着这条线又查出装机门三处判据错误（方向 / 旧标尺 / SKIP 假绿），以及我自己一处「凭上轮印象代替本轮核实」的误判。

---

**一、生产容器（10 字段，2026-11-07 16:3x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 · StartedAt `2026-11-07T07:09:04Z`（= 15:09:04，W1042 窗口还原后的启动） |
| 2 | 运行中引擎 | `strata-0.1.57-kvg` · md5 `a85743d7f554159e8ac1e2d432d2e5ea` · 43,214,976 B（**本轮未换件**） |
| 3 | config | md5 `ee69ebc272ce41a116f50ecb3bf0edc2` · `exe=/data/bin/strata-0.1.57-kvg` · args 38 / env 9（**未改**） |
| 3a | args 明细（19 flag） | `--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细（9 个） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1`；本轮一个都没动 |
| 4 | 健康 | `/health` `{"status":"ok","max_context":262144,"model":"qwen3.8-flash-next-ud-q4_k_xl-abliterated",...}` · running · restarts=0 |
| 5 | 资源隔离 | `memlock=-1:-1` · `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | used **33,577,705,472** / total 34,342,961,152 ⇒ **VRAM free 765,255,680 B（0.71 GiB）**；expert cache **8301 槽 / 24.23 GiB**；the prompt path **borrows 2609 CUDA0 cache slots (7.62 GiB)**；`elastic K/V: 16384 of 262144 cells（0.21 of 2.65 GiB）` |
| 7 | 回滚件 | `/data/bin` **55 件**（`attn` `3b758f88…`、`dot48` 同 md5 均**未装机**）· 上一版 `b12180`（`d24f8293…`）→ `k10p` → `-001`；rollback = 停容器 → `cp` 回 `tmp/w1040/cfg_w1040.bak` → 起容器（≈45 s） |
| 8 | 本轮改动 | **引擎无变更 / config 无变更 / disk = build = running 三方一致**（`docker exec md5sum /data/bin/strata-0.1.57-kvg` = `a85743d7…`）；纯本地工具链与文档工作：**重启 0 次 / 停机 0 s / 装机 0 / 回滚 0** |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产源码树 `pr/k10` @ af797b90（`gfx906/lcpp-k10`，相对 `origin/gfx906/mi50` **领先 2 / 落后 0**，脏 0 行）。候选分支 `gfx906/attn-opt @ deb41e12`、`gfx906/dot48 @ e0ce7c96` 均已推远端、**未合主线、未装机**。上游 `upstream/main` 本轮未重算（`ghup` remote 只读、`upstream` 走 gh-proxy，上次读数 behind 0），换基线是另一件事，不在本轮。本轮**一行生产源码都没改**。

**三、本次落生产** — **零**：引擎未换件、config 未改字节（`ee69ebc2` 全程不变）。本回合 **重启 0 次 / 停机 0 s / 装机 0 / 回滚 0**。所有改动都在本机工具链、权威件与 `albus/w1043/` 目录里：五轮历史报告的三列修复、`tools/report_lint.py` 的 T0–T4 门、`tools/deploy_gate.py` 的 D3/D4/SKIP 三处纠错、`deploy/REPORT_TEMPLATE.md` 与 `deploy/REPORT_STANDARD.md` 的字段同步、R103 装机前置包。**R103 装机仍需你单独批准一次停机**：估 **20–30 min（推测**，由 W1042 的 28,695 token needle 39.0 s 线性外推，未实测），窗口脚本 `albus/w1043/window_install_attn.sh` 默认 DRY RUN，必须显式 `APPROVED=1 DRY_RUN=0` 才会停生产。

**四、进度** — **457 条 / 已结 366 / 80.1%**（本轮 +6：`P506`–`P511`，其中 `P511` OPEN）。队列：**R103（已移植过门、装机前置已预注册、等停机批准）** → R106（`gen_config` 工具链九处漂移）→ R107（`AUDIT29`：W1032–W1043 **12 轮连续未审**，`audit_scope §A` 已 FAIL）→ R108（dot8 接入，与装机分开）→ R105（`hipk` 搭车测 `STRATA_HIP_QUEUE_PRIME`）→ R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 正文

**1. 「第一张是空表」到底是什么（`P506`）**

先把观测手段验干净：第一版扫描脚本用 heredoc 正则，被本机 shim 吞掉后**自测返回 False**，那次结果不可信；改写成 `albus/w1043/audit_tables.py` 落盘再跑，才得到可复核的数据。普查 w1000–w1042 全部 `reply.md` 的第一张表：**w1000–w1037 全 OK**（表头 3 列、数据行 12 行、列数一致），**w1038 / w1039 / w1040 / w1041 / w1042 连续五轮 RAGGED**（列数 2,3 混用，第 11/12 行只有 2 列）。另 `w1020` 是 THIN（4 行数据），是更早的另一类退化。

装上 python-markdown 3.11.3 做**真实渲染**（`albus/w1043/render_check.py`）：四轮第一张表都生成 `<table>` 与 `<tbody>`、各有 **12 个 `<tr>`**，所以文件里**并不是空白表**；但第 9、10 行各只有 **3 个 `<td>` 且第三个是空的**，这两行文本长度 **272–434 字符**。按 GFM 规范（2026-11-07 上网核，GitHub spec + markdownlint MD056/MD058）：表头与分隔行列数不等 ⇒ 整段**不被识别为表**；数据行少一列 ⇒ **补空单元格**；没有数据行 ⇒ 不生成 `<tbody>`；表格前后没有空行 ⇒ 部分解析器把首行并进段落。所以机主看到的「空表」= **「值」列被补空 + 超长单元格把表格撑出视口**，两者叠加。

根因在 `albus/w1037/reply.md:10` 与 `albus/w1037/reply.md:11`：正常形态是三列 `| 3a | args（19 flag） | … |`、`| 3b | env 明细（9 个） | … |`；W1038 起被压成两列 `| 3a args 明细 | … |`。`albus/w1043/fix_tables.py` 把五轮共 **10 行**修回三列，复验 `survey_fourpart.py` 全 OK、渲染后无空单元格。

**固化**（机主反复要的「不许只靠我记得」）：`tools/report_lint.py` 新增 `check_first_table()` 的 **T0–T4** —— 表头/分隔列数、≥10 数据行、逐行列数、值列非空、表前后空行；`--self-test` **6/6**（空表 / 少列 / 空值 / 列数不等 / 无空行 / 正常）。这是同族第五次「门验的对象错了，看起来还是绿的」：旧 lint 只查**全文有没有关键词**，从不看表里有没有内容，与 `P493`（日志整文件 grep）、`P496`（交接门 md5 写死旧件）、`P500`（读死文件）同源。

**2. 权威模板也漂了 18 轮（`P507`）**

`deploy/REPORT_TEMPLATE.md:9` 与 `deploy/REPORT_STANDARD.md:8` 都写「固定 8 项」，而 W1025 起报告里已有第 9 项 ROCm、第 10 项 llama.cpp，外加 3a/3b 明细。本轮把两份模板同步成「**10 项 + 3a/3b**」，补上表格结构铁律与 `--self-test` 自检项。`tools/report_depth.py:52` 的阈值文字仍是历史下限（≥9 行，早期达标报告的实测下限），本轮**不动阈值**，把结构判定集中到 `tools/report_lint.py:1` 的 T 门，避免两处重复设卡。

**3. 装机门被真实用例撞出三处错（`P508` / `P509`）**

拿 `albus/w1043/ab_attn.json` 跑 `tools/deploy_gate.py:1 --live`，D3c 报 `prefill_16000_gpu Δ=-1.72% vs 带宽 0.36% ⇒ REFUSE` —— **变快 1.72% 被判成劣化**。根因是护栏写成 `abs(gd) <= gb`（双向），而语义是「不许变慢」；同一段里 D3b 写成 `abs(delta) >= band`，**显著变慢 2.72% 也会被当成真收益**。W1040 的 `kvg` 装机没暴露，只因为那次每条护栏的 Δ 都小于自己的 2×CV。修法：抽出 `latency_target_ok()`（`delta <= -band`）与 `guard_ok()`（`gd <= gb`，变快不限），`--self-test` **11/11**，含「D3b 显著变慢」「D3c 大幅变快」「D3c 变慢超带宽」六个方向用例。

D4 只有 `bitident` 与绝对 `KL<=0.0139` 两种模式，而 **0.0139 属于已退役的 LOGPOS 取样面**：W1041 用同一对臂测过，旧仪器读 0.04、fp32 全词表 logits 在 8K 只读 0.00345，差一个量级，跨仪器引用必然误杀。新增 `mode=anchor`：要求 ≥4 个长度每个 `KL(C) <= KL(D)` 且 build floor 逐位相同。锚 D 是 `--kv fp16` —— 我们为省显存主动放弃的那一档；四点实测 `0.00037 / 0.00345 / 0.01429 / 0.18750` 对 `0.00155 / 0.01113 / 0.01699 / 0.38387`，全在预算内。

第三处更隐蔽：D5/D6 判据是 `SKIP` 时，横幅照样打印「PASS — 六条判据全部有证据，可以装」。现在 **SKIP 一律 fail-closed**，输出 `INCOMPLETE — 2 条判据是 SKIP（D5 配置面、D6 证据链），不能据此装机` 并返回 1。顺手复验 W1040 的历史用例，也变成 INCOMPLETE（那次 D6 确实 SKIP）——**那次装机的门不是全绿的**，如实记账，不粉饰。

**4. 我自己一处误判，在落权威件之前抓到了（`P510`）**

初稿把 W1041「四臂为隔离变量去掉 `--kv-grow`」的旧信息套到 W1042，写成「`attn` + `ATTN_DP4A=1` + `--kv-grow` 组合未测」，还写进了 `ab_attn.json` 的 caveat 和 `LONGCTX_GATE.md` 的 §0。看到 W1042 窗口脚本自己注释着 "production-shaped config incl. --kv-grow" 才起疑，逐层核到 argv：`tmp/w1042/cfgP_{kvg,attn}.json` 都是 **38 args 且 `--kv-grow` 为 True**；`qq_r103.py` 的 `DROP_VALUE` / `DROP_FLAG` **不含** `--kv-grow`，所以数值臂的引擎参数保留它；P2/P3 的 `serve/server.py --config cfgP_attn.json` 用的是同一份 config。⇒ **组合已测**，G1 从「首测」降级为跨窗口复验，装机窗口不必重跑 1K–20K 四点，停机估算相应下调。与 `P500` 同源（凭印象代替源码核实），区别是这次在写入权威件之前拦住了。

**5. R103 装机前置：`albus/w1043/LONGCTX_GATE.md` 预注册（`P511`，OPEN）**

两个真缺口：① W1042 的任务级门只有 16K / 28K 各一个深度的 needle（两臂 4/4），而 20K 点两臂都翻 argmax（参考分布 p=0.683、熵 0.83，近掷硬币），单点不能当质量结论；② `PARAM_REGISTER.tsv` 里**没有** `STRATA_GFX906_ATTN_DP4A` 的 ADOPTED 行，开关真名由 `src/kernels/cuda/qsa_decode_attn.cu:1062` 的 `gfx906_attn_opt()` 核实（bit1=2）——**装引擎不加这个 env 等于没装**，D5 会 REFUSE。

外证（上网核，用于设计门、不代替实测）：NeurIPS 2026《Length, Not Bit Width》用 190 runs、5 深度 × 7 长度（4K–128K）证明 KV 量化把检索悬崖从 96K 推到 32K、失败是**长度悬崖**而非深度衰减、int8 与 int4 失败模式几乎相同；vLLM 的 128K needle 在 FP8 KV 下 91%→13%，而延迟、短上下文 eval、PPL 全绿；RULER / NoLiMa / HELMET 指出只报 vanilla NIAH 是常见错误。**不能直接照搬**：那些改的是 **KV 条目本身**，R103 改的是 **query 侧点积算术**（`v_dot4_i32_i8`），KV 一个字节没动 ⇒ 本门用「相对锚的比值随长度是否稳定」去**证伪这个推断**，而不是拿别人的失败模式当判据。

判据 G1–G5 已在 `LONGCTX_GATE.md:1` 写死：B≡A 逐位、每长度 KL(C)≤KL(D)、`KL(C)/KL(D)`@64K 不比 20K 恶化 2×、needle 网格 C 命中数≥A 且无缓存点、8K/16K 墙钟不比 A 慢超当次 2×CV；任一不过就原样还原。零停机自测：`longctx_needle.py --self-test` **9/9**（深度 0/50/100% 的定位）、`judge.py --self-test` **7/7**（每个 G 各有一条负向用例）；`window_install_attn.sh` fail-closed（缺 `verdict.json` 拒装、trap 无条件还原、必须显式批准才停）。`ab_attn.json` 的装机门预检现在是 **INCOMPLETE**（D5/D6 SKIP，按设计），不是「可以装」。

**6. 仍未做，不冒充完成**

G2/G3 的 32K / 64K logits 需要先造 `set32k` / `set64k` ids 集并跑 D 锚，窗口脚本里该段明确标 `TODO-BEFORE-RUN`；`PARAM_REGISTER.tsv` 的开关登记、D5 增量门也留到装机窗口第一件事。停机 20–30 min 是**推测**（长上下文 prefill 有 attention 平方项，实测后必须回填）。`R108` 不与装机合并（一次只动一个变量），`R106` / `R107` 是零停机项另做。`audit_scope §A` 现在是 **12 轮连续未审**（W1032–W1043，阈值 8）——本轮四个门缺陷全是**跑门时撞出来的**，不是审计查出来的，这条债在变重。
