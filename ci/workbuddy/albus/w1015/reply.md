**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T16:22:11Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（host **16,473,712 KB**）；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_235103 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407`（本轮**未动用**，零改动零重启） |
| 8 | 本轮改动 | 生产零改动、零重启；disk = build = running = `eea5ea37…` 三方一致；只读源码与权威件 |

**二、主线** gfx906/mi50 @ 759a4edb · tag `mi50-0.2.10-r32-19-g759a4edb` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行。
**三、本次落生产** 改动 0；重启 0 次；停机 0；回滚件未用；代码面 0 提交（只动 `deploy/` 与 `albus/w1002/round_close.py`）。
**四、进度** 261 条 / 已结 181 / **69.3%**；队列 R95（P331 双缓冲，前置 P309 事件）→ R94（相对门）→ R91 → R89 → R46 → R49 → R50。

---

## 五、报告规矩：一个副本，门看得见的那一个

上两轮（W1013/W1014）的**文件版**都过了门——`report_lint` 12 字段、`report_depth` 的 3a 需 19 个 `--flag`、正文 ≥1500 字符、≥4 处 `file:line`；但**聊天里发出去的是压缩版**：8 行表、没有 3a/3b、M/P/Q 并成一行。门从没看见那个版本。

这是「同一份事实存在两个副本、而校验只覆盖一个」的第三次（前两次是 W832 本机↔166、AUDIT_INDEX↔审计件）。写死两条：

- 报告的唯一副本是 `albus/<轮次>/reply.md`；聊天贴的就是**全文**，不改写、不删行。
- `albus/w1002/round_close.py` 新增 `--post`：PASS 之后打印 `POST: md5=<…> chars=<…>`，再打印全文。**贴的时候连校验头一起贴**，两侧 md5 对得上才算发过（本轮就是按这个发的）。

## 六、R94 的金标不存在，原因是缺件不是缺方法

`data/quant_quality/v1/` 里只有 5 段文本（`code`/`docs`/`english`/`multilingual`/`agent`，各 5 KB 级）与 `set.ids.json`（已分词），**没有 `REF.tsv`**；而 `tools/quant_quality.py` 的参照臂要求 Q8_0 pack，我们的 pack 是 `ud-q4_k_xl`——`native_experts.txt` 里 Q8_0 **只作为专家的 d_type 出现**，dense 部分不是 Q8_0。⇒ **「对金标 KL/top-1」没有参照物可对。**

改成相对门（W806/W807 一直用的口径）：

> 每条改比特的候选与**现役配置**在同一 prompt 集各跑一次 teacher-forced LOGPOS，比 KL 与 top-1；判据 KL ≤ **0.0139**、top-1 ≥ **99%**；同配置两次跑作底噪。

这条也解释了为什么它一直没做：它需要独占 GPU（`quant_quality run` 自起引擎），停机 4–6 分钟；本轮**没做**，把它从「欠账」改成「有明确口径、等一次停机窗口」。

## 七、R95 的 91 ms：不是建表，是复用等待（更正上两轮我说的机制）

读 `prefill.cpp:4655` 起的 host 建组段，两行就够：

- `prefill.cpp:4663` — `m.up_ring.d2h_sync(m.ids_host.data(), m.ids, (size_t) T * K * 4, m.cs)`，**同步** D2H；
- `prefill.cpp:4656-4657` 注释逐字：*"(the sync below also orders this layer's writes of slot/src/bounds after the previous layer's kernels that read them)"* —— 这个 sync **同时承担缓冲复用排序**。

算术：`T*K*4` = 2084×8×4 = **66 KB/层**，48 层 **3.2 MB**，PCIe D2H 约 **0.5 ms**；直方图是 `T*K` 级整数操作（10⁴–10⁵/层，微秒级）。而相位里是 **91 ms**（2K 的 2.9%）。⇒ **91 ms 既不是拷贝也不是建表，是「等上一层把 slot/src/bounds 读完」的停顿。**

所以 W1013/W1014 里我写的「把建组计划挪到 issuer 线程」是**错的机制**——搬线程不解决复用冲突。正解是**双缓冲**：`ids/slot/src/bounds` 各开两份、按层奇偶交替，本层的 host 写就不必等上一层读完；上限仍是 2.85%，前置 `P309`（launch 前后两个事件量 `busy/phase`）确认这段停顿确实吃满 91 ms。

## 八、举一反三：三件事我都先说过一次错的机制

- **R98**：先说「最多能省 0.58%」，实测是**反向**（ring 越深越慢 0.5–0.6%）；
- **R21**：先说「开关无效」，但没测「去掉 `HC_Q8` 让它真跑」，补测后仍是没用，可理由换了一层；
- **R95**：先说「把建组挪到 issuer 线程」，读到 `prefill.cpp:4656` 的注释才发现是缓冲复用。

共同点：**把「数字」当成了「机制」**。数字只说明有 91 ms，机制必须由注释、事件或差分实验支撑。规矩收紧成：机制句后面必须跟 `file:line` 的注释原文或一次事件实验，否则只能写「待归因」。

## 九、门与同步

`plan_lint` A–F PASS（未结项全部在方案里、71 个 R 号都有账）；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` 全 PASS；`ledger` 29 项、`param_pair` 15 处与上轮持平（旧债）。六件权威件双侧逐字节（`W832` / `PROGRESS` / `PARAM_REGISTER` / `ID_MAP` / `AUDIT_INDEX` / `AUDIT26`）。本轮新增：`§6.5 回写·W1015`、`P329`（报告唯一副本）、`P330`（R94 改相对门）、`P331`（91 ms 归因）、R95 机制更正。
