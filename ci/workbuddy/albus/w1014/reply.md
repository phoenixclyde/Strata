**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`（三条 A/B 全部自动回滚到改前逐字节，`HC_Q8`/`GR_V3`/`PREFILL_RING` 残留 **0** 处）；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T16:22:11Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free`（启动横幅复现一致） |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json`（本轮**未动用**：三条 A/B 由 `cfg_apply` 自动 REVERT/ROLLBACK，终态已回到 `e62685e6…`） |
| 8 | 本轮改动 | config 试装 3 次、全部自动回滚（终态 md5 `e62685e6…`）；引擎/镜像/args 未变；disk = build = running = `eea5ea37…` 三方一致 |

**二、主线** gfx906/mi50 @ 759a4edb · tag `mi50-0.2.10-r32-19-g759a4edb` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0（3 次试装全部回滚）；重启 3 次；停机合计约 2.5 分钟；回滚件未用；代码面 1 提交 `759a4edb`（2 文件 +6/−4，BUNDLE 行与 candidates 求和）。
**四、进度** 258 条 / 已结 178 / **69.0%**；队列 R95（P309）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、你问的第一条：去 HC_Q8 比过吗 —— 没比过，现在比了

上一轮我只证明「v3 不执行」，就把它判死，这是**推论不是实测**。本轮补三臂（`cfg_apply`，冷 prompt，n=6/3，逐长度 2×CV 带）：

| 臂 | env | prefill@2000 | @8000 | @16000 | 判决 |
|---|---|---|---|---|---|
| 基线 | — | 513.65 tok/s | 684.62 | 767.22 | — |
| **B 去 HC_Q8** | `HC_Q8=0` | 513.47（−0.04%） | 685.81（+0.17%） | 765.21（−0.26%） | REVERT（全在带内） |
| **C 去 HC_Q8 + v3** | `HC_Q8=0,GR_V3=1` | 511.64（−0.36%） | 683.46（**−0.34%**，band 0.20） | 767.12（+0.25%） | **ROLLBACK** |
| **D 加深 ring** | `PREFILL_RING=768` | 510.94（−0.53%） | 680.43（**−0.61%**） | 763.03（**−0.55%**） | **ROLLBACK** |

三条结论：

1. **`HC_Q8` 在速度上免费**（−0.04/+0.17/−0.26%，全在带内）。它买的是比特（KL 0.0011、argmax 100%）不是吞吐 ⇒「去掉它换 v3」的前提成立，我上轮没验这一步是漏的。
2. **v3 真跑了也没用**：C 对 B 是 −0.36/**−0.34**/+0.25%，net 对基线 −0.39/−0.17/−0.01%；8K 那条超带。与上游自述一致（`fused_gr.cu:2653` 注释、`fused_gr.cu:2899` 的 `split` 条件：A4000 −3.0/−5.9%、3060 +1.0/−3.4%，只有 sm_120 正）。**R21 从「永不执行」升级为「实测否决」**。
3. **R98 我上轮是算术否决，没有实测** —— 这是本轮要更正的错误。实测 384→768：三个长度一致慢 **0.53/0.61/0.55%**（两条超带）⇒ **符号与我上轮的估计相反**：不是「最多能省 0.58%」，是「加深就慢」。`R98` 现在才是实测否决。

顺带一条：三次 `apply` 都按预期自动回滚，终态 md5 回到 `e62685e6…`、残留 0 处 —— 上一轮修的 `cfg_apply` 在本轮第一次被真正依赖。

## 六、你问的第二条：「三」进方案了吗，编号是多少

进了，两处，都可 grep：

| 内容 | 落点 | 编号 |
|---|---|---|
| 5% 单条门 → 组合门（按和 ≤−5%、每条 2×CV、`Q:` 覆盖整包、estimate 不计入和） | `deploy/W832_OPT_PLAN_V2.md:1404`（`bundle.py:139` 实现校验） §6.5「回写 · W1013」第 3 节 + `:26` §0.1「采纳判据（prefill）」行 | **P323** |
| 组合预算的机器账（份额由 `PREFILL_PHASES.tsv` 反算） | `ci/bundle_budget/{BUNDLE.tsv,bundle.py,README.md}`，`round_gate --ci` 与 `round_close` 都跑 | **P323** 的落点 |

## 七、你问的第三条：关闭的有没有实测依据

- **R21**：W1013 只有源码 + 「不执行」A/B（当时算实测但**没覆盖「去 HC_Q8 让它执行」**）；本轮 C 臂补齐 ⇒ 现在有实测否决（8K −0.34% 超带）。台账 note 已改写。
- **R98**：W1013 **没有实测**，是算术（37 ms 砍半 = −0.58%）。本轮 D 臂补齐，且结论反转。台账 note 已改写。
- 这两条是本轮对上一轮的**自我更正**：判死可以快，但不能拿「算术」当「实测」，否则和 1.91× 那种口径错误同源。

## 八、你问的第四条：本轮该进方案的进了哪些，编号

| 编号 | 内容 | 状态 |
|---|---|---|
| **P325** | `HC_Q8=0` 速度免费（−0.04/+0.17/−0.26%，全在带内） | DONE |
| **P326** | v3 真跑也没用（C 对 B：−0.36/**−0.34**/+0.25%，8K 超带） | DONE_NEG |
| **P327** | R98 实测：ring 384→768 三档 −0.53/−0.61/−0.55%，**越深越慢** | DONE_NEG |
| **P328** | 外网 gfx906 dot 实测：`sdot4` 21.7–22.3 TOPS（链式）/43–44（ILP4），`sdot8` 43.5–44.4，FP32 峰值 13.4 TFLOPS（`arch_defaults.cpp:221` 那条 tuned 项买的就是比特）；**`v_mfma` 不在 gfx906 指令表**（只有 gfx908+） | DONE_NEG |

`BUNDLE.tsv` 同步：`R21-v3hc`、`R98-wc` 两行由 BLOCKED/算术拒改为 **实测拒**；新增 candidates 列 ⇒ **候选只剩两条：R86-dn −3.20%（实测）+ R95-plan −2.85%（估计）= −6.05%**。

## 九、举一反三：R21 的三个死因是同一个形状

「上游优化 + 我们的开关」这类冲突，本轮集齐三种死法：①**结构冲突**（v3 只读 bf16 行，我们的 HC 是 Q8 码）；②**指令集**（给 v3 写 int8 版要用 dp4a，而 R35 已测 548 vs 673 µs，慢 15–23%）；③**硬件**（`v_mfma` 不在 gfx906，GDN 分块只能 FMA，公开实现的 4.5×/2–3× 都骑矩阵核）。**判一个上游移植前，先按这三层各问一次，比跑一次 A/B 便宜得多** —— 本轮 B/C/D 三个臂 15 分钟，而三层里有两层本来能在读码阶段就否掉。

**门**：`ROUND_GATE: PASS`；`ROUND_CLOSE` 十一项 PASS；六件权威件双侧逐字节（`W832`/`PROGRESS`/`PARAM_REGISTER`/`ID_MAP`/`AUDIT_INDEX`/`AUDIT26`）；`ledger` 29 项、`param_pair` 15 处与上轮持平。提交 `759a4edb`。
