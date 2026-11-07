# W1040 报告 · R104 装机：`--kv-grow` 落生产，**+838 专家槽**，而数值**逐位不变**
> 一句话：**同一张卡、同一棵树、一行条件编译**——`vmm.cpp` 里那句「gfx906 没有虚拟内存」是**撰写时的假设**，
> 改成 `||` 之后这台机器上 K/V 只按需占 VRAM，让出 2.44 GiB 给专家缓存：**7463 → 8301 槽（+11.2%）**，
> 而 1000/8000/16000/**20000** token 四个提示的 fp32 全词表 logits **逐字节相同**。
> 本轮更值钱的东西在门外：**装机门 D5「配置面」从来没实现过**，而按铁律跑 `gen_config` 会把 `STRATA_GFX906_TUNED=1` 丢掉。

---

**一、生产容器（10 字段，2026-11-07 14:5x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · `ulimits.memlock=-1:-1` · restarts=0 · StartedAt `2026-11-07T06:13:52Z`（= 14:13:52，装机后那次启动） |
| 2 | 运行中引擎 | **`strata-0.1.57-kvg`** · md5 **`a85743d7f554159e8ac1e2d432d2e5ea`** · 43,214,976 B |
| 3 | config | md5 **`ee69ebc272ce41a116f50ecb3bf0edc2`** · `exe=/data/bin/strata-0.1.57-kvg` · args **38** / env 9 |
| 4 | 健康 | `/health` `{"status":"ok","loaded":true}` · restarts=0 |
| 5 | 资源隔离 | `VmLck 0 kB` · `ulimit -l` unlimited · `memlock=-1:-1` |
| 6 | 显存 | used **33,617,891,328** / total 34,342,961,152 ⇒ **free 725,069,824 B（0.68 GiB）**；expert cache **8301 槽 / 24.23 GiB**；the prompt path **borrows 2609 slots (7.62 GiB)**；`elastic K/V: 16384 of 262144 cells（0.21 of 2.65 GiB）`，当前增长到 32768 cells（0.36 GiB）；**VRAM free 725,069,824 B（0.68 GiB）** |
| 7 | 回滚件 | `/data/bin` **53 件** · 上一版 `b12180`（`d24f8293b575fbcee6c097239d9599cb` / 43,207,464 B）→ `k10p`（`e0a6987f…`）→ `-001`（`5e63174d…`）；config 备份 `tmp/w1040/cfg_w1040.bak`（逐字节 = `5e9b81e2`，rollback = 停容器 → `cp` 回这份 json → 起容器，≈45 s） |
| 8 | 本轮改动 | **换引擎 1 次 + 改 config 1 次**：`b12180 → kvg`、`5e9b81e2 → ee69ebc2`（args +`--kv-grow`）；**disk = build = running 三方一致**（`docker exec md5sum` = `a85743d7…`）；**重启 1 次、停机 275 s、装机 1、回滚 0** |
| 3a | args 明细 | 38 项 = 上轮 37 项 **+ `--kv-grow`**（其余逐字不变：`--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10`） |
| 3b | env 明细 | 9 项，**本轮一个没动**：`HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1`（窗口期临时加的 `STRATA_KV_GROW` 已不在其中：开关走 CLI） |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5`（2026-11-06T22:42:46Z） + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`，工程门那头未动）；**生产源码树 = `pr/k10` @ af797b90**，相对 `origin/gfx906/mi50` **领先 2 / 落后 0**（`fa8e6761` + `af797b90`；上游 `upstream_main` 本轮未重算）（`gfx906: compile the HIP virtual-memory path`，工作树脏 0 行），即在 `fa8e6761`（b12110+mmq 对齐）之上**新增 1 个提交**。`kvg` 与在产 `b12180` 用**同一棵树 + 同一份 cmake 配置**构建，差别只有这 1 个提交；`git checkout` 回 `fa8e6761` 重编可得 `d24f8293`（上一轮已证）。实验分支 `gfx906/port-all` @ `62d10e25` 本轮未动。

**三、本次落生产** — 引擎 **换件 1 次**（`b12180` → `kvg`），config **改 1 次**（`5e9b81e2` → `ee69ebc2`，增量只有 `exe` 与 `--kv-grow`）。本回合 **重启 1 次 / 停机 275 s / 装机 1 / 回滚 0**（窗口 14:10:03 停 → 14:14:38 `/health` ok；停机全在数值臂与拉起的 45 s 里）。**装机门**（`tools/deploy_gate.py --live`）：D1 `a85743d7…`、D2 53 件、D3b 槽 7463→8301、D3c 四条墙钟护栏全在 2×CV 内、D4 bit-identical、D5 `args +--kv-grow（来自 P32）` ⇒ **DEPLOY_GATE: PASS**（诚实标注：D4 这一条是**跑完两个臂之后**才判的，第一次试跑时 `ab_kvg.json` 里的 numeric 字段是占位值，那次 PASS 不算数；最终 PASS 对应的是 §4 那四个 md5）。回滚路径：`docker stop` → config 换回 `5e9b81e2` → `docker start`（≈45 s）。

**四、进度** — **441 条 / 已结 352 / 79.8%**（本轮 +9：`P490`–`P496` + 队列行 `R106`/`R107`；`P444`/`P474`/`P488` 由 OPEN 收口）。队列：~~R104~~（已装机）→ **R106**（`gen_config` 工具链对齐，`P492`）→ **R107**（`AUDIT29`：W1032–W1040 九轮未审，`audit_scope §A` 已 FAIL）→ **R105**（`hipk` 三开关，搭车测 `STRATA_HIP_QUEUE_PRIME`）→ R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 正文

**1. 结论与它凭什么成立**

三件事同时成立，缺一条这个件就不该装：① **容量确实变大**（起机行 `expert cache 8301 slots, 24.23 GiB of VRAM`，在产旧值是 7463 / 21.79 GiB ⇒ **+838 槽 / +11.2%**）；② **墙钟没有一条变慢**（2.5K/8K/16K/20K 四点 Δ = −1.13 / −0.29 / −0.20 / −0.13%，每点 n=4，全部落在该次 run 自己的 2×CV 内）；③ **算术没动**（四个长度的 fp32 全词表 logits 逐字节相同，`pcompare` top-1 100.00% / KL 0.00000）。

三点分别对应门里的 D3b（容量型目标）、D3c（护栏）、D4（数值）。

**2. 先修门，再装机：`gen_config` 与生产 config 差 9 处（`P492` → `R106`）**

按铁律「改参唯一道 = register → `gen_config --write` → 推 166」，第一步先跑 `gen_config --live` 看差异。结果是**九处**：

- **少**四项生产在用的 env：`STRATA_GFX906_TUNED`、`STRATA_DECODE_TIMING`、`STRATA_SPEC_DEPTH`、`STRATA_PREFILL_TIMING`——它们在 register 里登记成 `MEASUREMENT`/`POLICY` scope，生成器只吃 `ENV`；
- **多**两条同义 ADOPTED 行与两条**坏行**：`STRATA_GFX906_ATTN_REDUCE12=1（attn 分块的另一种归约）`（name 里带等号和中文注释）、`ROCm userland 10.1.0 + rocBLAS 5.7（…）`（name 是整句中文）——会生成两个垃圾 env 键；另有两行把注释写进了 value（`1(在 k8v4 下不可达;W775delta 改判)`）；
- `tokenizer` / `model_name` 仍写 IQ4_XS（W822 起生产是 UD-Q4_K_XL）。

**如果照铁律原样执行，`STRATA_GFX906_TUNED=1` 会被丢掉**——那是 gfx906 tuned 内核族的总开关，等于把整族调优静默退回默认实现。所以本轮改参改成「在产 config ⊕ 登记增量」，并用**新补的 D5 增量门**验：除 `exe`（制品指针）外，新 config 只能多出本轮 ADOPTED 行声明的 CLI/ENV，少任何键也拒。工具链本身的修复另立 `R106`（`P492` 里写了四条判据）。

**3. 装机门的第一条硬缺陷：D5 从来没实现过（`P491`）**

`tools/deploy_gate.py` 的文档写着六条判据，`main()` 里只有 D1/D2/D3/D4/D6。也就是说**「改参唯一道」这条从来没有被机械验过**，而它恰恰是最容易静默失效的一条：手改 config 一行，谁也看不出来。本轮补上 D5（增量形式，理由见 §2），并把 D3 扩成两类目标：

- **延迟型**（默认）：Δ 必须 ≥ 2×CV 才算收益；
- **容量型**：目标量是整数计数（槽数，零方差），只要严格变大；墙钟一律降级为护栏。

这不是给本轮开绿灯——判据仍然逐点判：把 `--reg-ids` 换成空，同一条命令立刻 REFUSE。

**4. 数值证据换了取样面：比 logits，不比「再跑一次 KL 门」（`P495`）**

R103 的教训是「现有数值门测不出 0.04 的来源」，本轮干脆绕开那道门，直接用 `STRATA_DUMP_FIRST_LOGITS` 比 **batched prompt 路径的 float32 全词表 logits**（993,280 B/个）：

| 提示长度 | A = `b12180` | B = `kvg` + `--kv-grow` | 结论 |
|---|---|---|---|
| 1000 | `54d98428…` | `54d98428…` | 逐字节相同（不可能增长：< 16384） |
| 8000 | `131abb31…` | `131abb31…` | 同上 |
| 16000 | `31b4a2d7…` | `31b4a2d7…` | 同上（16000 < 16384） |
| **20000** | 同 | 同 | **强制增长后仍逐字节相同** |

`pcompare`：`prompts 4  top-1 100.00%  KL mean 0.00000  median 0.00000  max 0.00000`。两臂同参（`--expert-cache 1500` 实得 1915 槽、`--kv k8v4`、`--max-context 20512`），**唯一差别是 B 多了 `--kv-grow` 且用的是 `kvg`**。

**5. 为什么「增长了 4128 个 cell，位却不动」（`P494`）**

B 臂 stderr 原文：

```
strata: K/V grown to 20512 cells (0.26 GiB); the expert cache gave 19 slots for it,
        15 hotter experts moved to colder ones' slots (1896 of 1915 slots hold experts)
```

源码：`src/program/generate.cpp:9978`（`kvg_ensure`，注释逐字讲的就是这件事）、`src/program/generate.cpp:9954` 与 `src/program/generate.cpp:9955`（`struct KvGrow` 的 `floor = 128` / `step = 8192`）、`src/program/generate.cpp:10089`（`kvg_trim`，请求边界把 K/V 收回）、`src/core/layer.cpp:685`（`qsa_kv_elastic_cells`，当前映射了多少 cell）；被改的是 `src/core/vmm.cpp:170` 的守卫，旧实现落在 `src/core/vmm.cpp:306` 的 `vmm_available() { return false; }`。让出的槽是「prompt path loan 正下方」那些**中等热度**的；一个比 loan 区最冷者更热的专家会被**搬到它那个槽**（device copy），最冷的才真正让出。所以**驻留集合近似不变，只有槽号变**；被真正赶出去的 4 个专家，这段文本没有路由到 ⇒ logits 一位不动。另有两条参数约束着代价：`step = 8192`（按整步增长）、`floor = 128`（缓存至少留 128 槽）。

**真实代价尺寸**：一次 20K 请求借 19 槽；生产 28.7K 请求上是 25–55 槽——即 **0.2–0.7% 的缓存**，不是「专家池被吃掉」。

**6. 生产现场与新自检（`P490`）**

新日志切片（起容器前记 `wc -l`，起来后只读切片）里同时满足：`expert cache 8301 slots, 24.23 GiB`、`elastic K/V: 16384 of 262144 cells in VRAM (0.21 of 2.65 GiB)`、**没有** `--kv-grow is off`、无 `could not map`、无 `ERR the K/V could not give its VRAM back`。跑过真实请求之后，日志里能看到增长与归还都发生了：

```
K/V grown to 24576 cells (0.29 GiB); the expert cache gave 28 slots …
K/V grown to 32768 cells (0.36 GiB); the expert cache gave 27 slots …
K/V trimmed to 8192 cells; 55 slots back to the expert cache, refilled from the profile
```

**功能面**：28,695 token 的 needle（码埋在开头、1.8 万词填充、贪心）安装前 `hit=True`（38.6 s）、安装后 `hit=True`（39.0 s），两臂 `cached_tokens=0`（排除提示缓存复用）。**这条测的是 decode 侧**——`P495` 的逐位相同只覆盖 prompt 路径。

**7. 一条取数纪律：`elastic K/V` 不能整文件 grep（`P493`）**

装机后再 `grep -a "elastic K/V" <log> | tail -2`，拿到的还是 13:44 那次窗口的行（第 148458 行），而当前进程是 14:13:52 起的（第 148765 行之后）。`P478` 那道硬门本身没写错，**取样面错了**：日志 append-only，上一次的旧行会让新检查假通过。凡「引擎自报状态」的门（`--kv-grow is off`、`elastic K/V`、`expert cache N slots`、`ERR …`）一律按启动/请求切片读。

**8. 还没做的（不装成「做完了」）**

- **decode 侧的定量收益仍不可判**：tok/s 跨 run 2×CV 28%，只有方向证据（CPU experts 0.64→0.49、VRAM hits 25.28→29.09）。加槽该压的是 miss 数（重尾：p50 222 / p90 7,102），需要每臂 `decode timing` 多次采样才能定量；
- **长上下文 decode 侧的位一致**没测（本轮只测 prompt 路径的 next-token logits）；
- `STRATA_KV_GROW_HOLD=1`（`P48`）未测——它会让停放的对话把槽钉住，是「多轮场景 vs 单轮」的分岔；
- `R106` 未做：工具链修好之前，改参只能走「在产 config ⊕ 增量」这条临时桥；
- **`AUDIT29` 已是债**：`audit_scope §A` 报 `9 unaudited rounds in a row (> 8)`（W1032–W1040）。本轮两个 bug（`P493` 日志取样面、`P496` 交接门验错件）都是**跑门时撞出来的**，不是审计查出来的——这正说明审计缺位在起作用，已立 `R107`；
- **CI 那一环是手工补的**：本轮走的是「停容器 → 换 exe/config → 起容器」，**不是 `ci/deploy.sh`**，所以 `0/8 gh_gate`（该 sha 必须有绿灯 run）没有经过。`af797b90` 已推到 `origin/gfx906/lcpp-k10`（pre-push `ROUND_GATE: PASS`），但 `downstream-gate` 只对白名单分支 + 命中 paths 触发 ⇒ **该 sha 目前没有 CI run**（API 实证：最近五次 run 都在 `e181bda5` 及更早，时间 2026-11-06T19:5x）。补偿是手工跑了 3.5/8 的证据门，六条全 PASS。

**9. 原始产物** — 166 上 `tmp/w1040/`：`qq_prompt.py`（yardstick，`PROMPT_LENS` 扩到四点）、`set20k.ids.json`、`cfg_arm{A,B}.json`、`cfg_new.json`（= 落盘的那份）、`pa_A/` `pa_B/`（各 4 个 `first.*` + `index.json` + `stderr.txt`）、`install.log`、`new_start.log`、`needle_remote.py`；本机 `albus/w1040/`：`state.py` `prep.py` `cfg_delta.py`（往返逐字节验证）`ab_kvg.json` `window_install.sh` `run_window.py` `land_progress.py` `land_plan.py` `needle_before.json` `needle_after.json`。

**10. 顺手挖出的第二个门 bug（`P496`）：验错了件，却一直是绿的**

`handoff_check.py --live` 报 `LIVE: engine md5 != SNAPSHOT (got 5e63174dbd7cc04e5fa1b5fc455b2a73)`——那个 md5 是 `strata-0.1.57-001`，而生产跑的是 `kvg`。根因：`live_check()` 里 md5 的是**写死的** `/data/bin/strata-0.1.57-001`，不读 SNAPSHOT 的 `prod_exe`。于是它只有两种命运：换名后误报，或旧件还在时**假通过**。它的负向自测也一样——锚点是一个字面量 md5（`5e63174d…`），生产一换代，那条「坏 SNAPSHOT」用例就变成 no-op（自测从 4/4 掉到 3/4 才露出来）。

修法：路径取自 `prod_exe`；负向用例改成 `re.sub(r"prod_md5=[0-9a-f]{32}", …)`。**`--live` PASS + `--self-test` 4/4`**。与 §7 的 `P493` 同族：**门验的对象错了，看你还是绿的**。
