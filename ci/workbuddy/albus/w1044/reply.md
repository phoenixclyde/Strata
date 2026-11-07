# W1044 报告 · R103 装机完成：`strata-0.1.57-attn` + `STRATA_GFX906_ATTN_DP4A=1` 进生产

> 一句话：**装完了，G1–G5 五道预注册门全过**（build floor 四点逐字节、四长度 KL(C)≤KL(D)、32K 比值 0.145≤0.977、
> needle 网格 18/18 命中含 64K 三深度、墙钟不劣化），冷启动后开关仍在、health ok、冒烟通过、disk=build=running 三方一致。
> 过程不粉饰：**两次停机窗口 + 一次冷启动收尾**，中间抓出三个门/取样面缺陷；第一次窗口判 NO-GO 并还原，第二次才放行。

---

**一、生产容器（10 字段，2026-11-07 18:0x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 · StartedAt `2026-11-07T09:56:22Z`（= 17:56:22 冷启动，`docker inspect` 实测） |
| 2 | 运行中引擎 | **`strata-0.1.57-attn`** · md5 `3b758f88ddad25cdad236be267810a9e` · 43,452,008 B（**本轮换件**） |
| 3 | config | md5 **`3dde880125925d785a49da69fa1ebdfb`** · `exe=/data/bin/strata-0.1.57-attn` · args 38 / env **10** |
| 3a | args 明细（19 flag） | `--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow`（38 项逐字未动） |
| 3b | env 明细（10 个） | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING`（以上 9 项未动）+ **`STRATA_GFX906_ATTN_DP4A=1`**（本轮唯一新增，来自 register `P512`） |
| 4 | 健康 | `/health` `{"status":"ok","max_context":262144,...}` · running · restarts=0 · 冷启动后冒烟 chat 返回 `content` |
| 5 | 资源隔离 | `memlock=-1:-1` · `ulimit -l` unlimited · `VmLck 0 kB` |
| 6 | 显存 | used **33,618,952,192** / total 34,342,961,152 ⇒ **VRAM free 724,008,960 B（0.67 GiB）**（18:0x 装机后重采）；expert cache **8301 槽 / 24.23 GiB**；the prompt path **borrows 2609 CUDA0 cache slots (7.62 GiB)**；`elastic K/V: 16384 of 262144 cells（0.21 of 2.65 GiB）` |
| 7 | 回滚件 | `/data/bin` **55 件**；回滚 `b12180`（`d24f8293…`）→ `k10p` → `-001`；**本轮上一版 `kvg`（`a85743d7…`）仍在册**；config 备份 `tmp/w1044/cfg_w1044b.bak`（逐字节 = `ee69ebc2`）；rollback = 停容器 → `cp` 回这份 json → 起容器（≈45 s） |
| 8 | 本轮改动 | **换引擎 1 次 + 改 config 1 次**：`kvg → attn`、`ee69ebc2 → 3dde8801`（`exe` 指针 + env 多 1 项，args 38 逐字未动）；**disk = build = running 三方一致**（冷启动后复验）；**重启 3 次 / 停机 2165 s / 装机 1 / 回滚 0** |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产源码树 `pr/k10` @ af797b90（`gfx906/lcpp-k10`，领先 2 / 落后 0，脏 0 行）。在产二进制来自候选分支 `gfx906/attn-opt @ deb41e12`（W1042 移植，已推远端），`gfx906/dot48 @ e0ce7c96` 仍未装机。上游 `upstream/main` 本轮未重算（`ghup` remote 只读），换基线是另一件事。

**三、本次落生产** — 引擎 **换件 1 次**（`kvg` → `attn`），config **改 1 次**（`ee69ebc2` → `3dde8801`）。本回合 **重启 3 次 / 停机 2165 s / 装机 1 / 回滚 0**，分三段：① 窗口 A（17:14:47→17:40:52，1565 s）判 NO-GO 并还原；② 窗口 B（17:41:58→17:51:07，549 s）G1–G5 全过开始装机，但收尾校验误报触发 trap；③ 收尾冷启动（17:56:18→17:57:09，51 s）修好 config/running 错配并验证持久化。**装机门**：`deploy_gate.py --live` D1 `3b758f88…`、D2 55 件、D3 8K −2.72% vs 2×CV 1.34%、D4 锚门四点、D5 增量只有 `exe`+`env +STRATA_GFX906_ATTN_DP4A`（`--reg-ids P512`）、D6 证据链 ⇒ 六条 PASS（D6 在报告落盘后补验）。回滚路径：`docker stop` → config 换回 `tmp/w1044/cfg_w1044b.bak` → `docker start`（≈45 s）。

**四、进度** — **461 条 / 已结 371 / 80.5%**（本轮 +4：`P513`–`P516`；`R103` 由 OPEN 收口）。队列：~~R103（已装机）~~ → R106（`gen_config` 工具链）→ R107（`AUDIT29`：W1032–W1044 **13 轮连续未审**，`audit_scope §A` 仍 FAIL）→ R108（dot8 接入，与装机分开）→ R105（`hipk`）→ R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 正文

**1. 装了什么，凭什么装**

`strata-0.1.57-attn`（`3b758f88…` / 43,452,008 B）+ 生产 config 里新增 `STRATA_GFX906_ATTN_DP4A=1`。开关真名由 `src/kernels/cuda/qsa_decode_attn.cu:1062` 的 `gfx906_attn_opt()` 核实（bit1=2）；硬件 dot4 的生效实现在 `include/strata/platform/hip_compat/strata_hip.h:237`（W1042 拆 fatbin 实证 `v_dot4_i32_i8` 384 条），本轮登记行在 `deploy/params/PARAM_REGISTER.tsv:267`，`opt!=0` 时派发切到 `attn_chunk_kernel<M,false,false,false,OPT>`（**无 query swizzle / 无 reduce12，不是单变量点积替换**）。**不加这个 env 等于没装**，所以 `deploy/params/PARAM_REGISTER.tsv` 新增 `P512`（ENV / ADOPTED），D5 增量门据此只放行 `exe` 指针与这一项 env。

预注册判据写死在 `albus/w1043/LONGCTX_GATE.md`（W1044 17:0x 修订，**改判据发生在开窗之前**）：G1 B≡A 逐位、G2 每长度 KL(C)≤KL(D 锚)、G3 `KL(C)/KL(D)`@32K 不比 20K 恶化 2×、G4 needle 网格 C 命中数≥A 且无缓存点、G5 墙钟不劣化。最终 `verdict.json`：**G1 true / G2 true（4 长度零违例）/ G3 true（ratio@20K 0.488、@32K 0.145、上限 0.977）/ G4 true（off 9/9、on 9/9）/ G5 true**，go=true。

**2. 上网核外证后，我把上一轮的机理推断改了**

上一轮写「R103 改的是 query 侧点积、KV 一个字节没动 ⇒ 长度悬崖机理上不适用」。本轮上网核到反证：量化综述（`aiknowledge.cn/article/69829`）、TrueSight《INT8 量化下的 Transformer 精度崩塌》、SageBwd、technologyonthe 2026-09 生产实践一致指出 **注意力 logits 是量化里最敏感的一层**（softmax 对 0.01 量级 pre-softmax logit 误差就敏感、指数运算非线性放大），误差随层数/decode 步/序列长度累积，且「**8K 上无法区分的配置可能在 64K 退化**」。R103 动的正是 `QK^T` 点积。⇒ 误差机制与 KV 量化不同（不是记忆条目丢失），但**长度轴照样必须测，G3 必要性反而更高**；G3 的 2× 阈值是本项目工程约定、**无外部权威依据**，已在预注册件里标死，不冒充社区标准（`P516`）。

**3. 窗口 A：取样面自己坏了，判 NO-GO 是对的**

四臂（`qq_long.py` + `set32k.ids.json`）跑完，1K/8K/20K 的 KL 与 W1041 **逐位复现**（`0.000371 / 0.003453 / 0.187498` vs `0.00037 / 0.00345 / 0.18750`），G1 build floor 四点逐字节相同。但 32K 点 `KL(C)=7.08e-08`、`KL(D)=2.11e-08`，比值 3.36 ⇒ G2/G3 判否。`albus/w1044/diag_32k.py` 实测给出根因：32K 参考分布 **top1=1.000000 / 熵 0.0000 / 三臂 argmax 同为 506** —— 我造 `set32k` 时把 20,000 ids 周期重复到 32,768，模型在重复模式下把下一 token 预测成完全确定，所有量化扰动只剩浮点尾数。**这是取样面失效，不是 DP4A 有长度悬崖**。窗口 A 按预注册 fail-closed 判 NO-GO 并完整还原（`kvg` + `ee69ebc2`），停机 1565 s；needle 网格 18/18 全命中（含 64K 三深度）作为有效证据保留。

修法（`albus/w1044/make_ids_v2.py`）：**前 20,000 ids 与 W1041 逐字相同**（1K/8K/20K 仍可对账），后 12,768 换成 940,927 字节内核源码 tokenize 出的新 ids（284,485 tokens 里取前 12,768），生成 `set32k_v2.ids.json`。重跑后 32K 点 `KL(C)=0.001457 / KL(D)=0.010032`，ratio 0.145 ⇒ G3 稳过（`P514`）。

**4. 窗口 B：门过了，却栽在最后一步校验的取样面上**

窗口 B 复用同批次 needle 网格，只重跑四臂 logits，9 分钟出 `go=true`，进入装机。写 config、`docker start`、health ok 之后，脚本用 `tr '\0' '\n' < /proc/$PID/environ | grep -q '^STRATA_GFX906_ATTN_DP4A=1$'` 校验开关 —— **在宿主机以 `albus` 用户读 `/proc/<pid>/environ`（`-r-------- root root`）读不到任何变量**，连原有的 `STRATA_GFX906_TUNED=1` 都读不到，于是误报 FAIL。trap 的 `restore()` 只 `cp` 回旧 config、**没有重启进程**，留下了「config 指向 kvg、进程却跑 attn」的错配（`P515`）。

用 `docker exec strata166-407 cat /proc/21/environ`（容器内 root 视角）复核：引擎 env 明确含 `STRATA_GFX906_TUNED=1`、`STRATA_DECODE_TIMING=1`、 **`STRATA_GFX906_ATTN_DP4A=1`** ⇒ 装机其实已生效，是校验取样面错。收尾 `albus/w1044/finish_install.sh`：写回 `cfg_new.json`（`3dde8801`）消除错配，再**冷启动一次**证明持久化（重启后 exe=attn、config md5 不变、开关 ON、`kv-grow` 未关、`could not map` 0 条、冒烟 chat 成功），停机 51 s。这是同族又一次「门验的对象错了，看起来还是绿的」。

**5. 在产复核与边界**

零停机在线复核（`albus/w1044/verify_live.py`）：10,828 token 请求、`cached=0`、墙钟 14.5 s、新日志切片 `qsa attn 1974 ms（14.5%）`、health 正常。这与窗口内 on 臂 8K 的 1975.7 ms 同量级，但**形状不同、跨 run 相位会迁移（W797），不作定量结论**，只作「开关生效、服务正常」的行为佐证。

生产形态里 `--kv-grow` 的 gfx906 守卫在 `src/core/vmm.cpp:170`，弹性 KV 的 `floor` 在 `src/program/generate.cpp:9954`，两者本轮都未改动（只换了引擎指针与一项 env）。

**仍未做 / 不冒充完成**：long-context 的 64K 只做了 needle 任务级网格，未做 64K fp32 logits（`qq_r103.py` 的 `PROMPT_LENS` 写死且 yardstick 用 CPU 专家形态，与生产不同）；decode 侧逐 token diff 只到网格里的 needle 生成，未做专门长生成门；`R108` dot8 仍无生产调用点。`audit_scope §A` 为 **13 轮连续未审**（阈值 8，仍 FAIL）——本轮三个缺陷全是**跑门时撞出来的**，不是审计查出来的，这条债继续变重。
