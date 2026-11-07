**一、生产容器（8 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0） |
| 3 | config | md5 `e62685e6ff21d9e2b60c1cd622fd5a67`；exe=`/data/bin/strata-0.1.56-090`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-05T15:33:28Z`（上一轮事故恢复时的重启） |
| 5 | 资源隔离 | `ulimit -l` = unlimited；`VmLck` 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free`（启动时值） |
| 7 | 回滚件 | `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` + `docker restart strata166-407`（本轮未用） |
| 8 | 本轮改动 | 生产**零改动、零重启**；disk = build = running = `eea5ea37…` 三方一致；本轮只改本机 `tools/` |

**二、主线** gfx906/mi50 @ c409936f · tag `mi50-0.2.10-r32-17-gc409936f` · 落后 0 / 领先 0 · 上游 `ffa80d73` · 工作树脏 0 行 · 远端一致。
**三、本次落生产** 改动 0；重启 0 次；停机 0；回滚件未用；代码面 0 提交（只动本机 `tools/report_depth.py` 与 `round_close.py`）。
**四、进度 + 队列** 250 条 / 已结 170 / **68.0%**。队列：R95（建计划挪 issuer，代码）→ R98 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、你说对了，而且它能被数出来

把 11 轮报告放到一起量（`args` = 3a 行里的 `--flag` 个数，`引用` = 正文里的 `file:line`）：

| 轮 | 字数 | 3a 的 flag 数 | 正文引用 | 带单位数值 |
|---|---:|---:|---:|---:|
| W1000 | **5,147** | **19** | 1 | 18 |
| W1001 | 3,611 | 19 | 1 | 27 |
| W1002 | 5,082 | 19 | 0 | 5 |
| W1003 | 3,005 | **1**（改成「未变」） | 2 | 10 |
| W1005 | 4,740 | 1 | 3 | **46** |
| W1007 | 3,644 | 1 | 0 | 10 |
| W1009 | 2,651 | 1 | 0 | 23 |
| W1010 | 2,803 | **0** | 1 | 10 |
| W1011 | **2,428** | 4 | 2 | 10 |

字数从 5,147 掉到 2,428（**−53%**），`args` 从 19 条掉到 0–1 条，正文引用最多只有 **3 处**。

## 六、根因：门只认标签，不认内容

`tools/report_lint.py:19` 的 F3 规则要的是 `args\s*[0-9]+`、`env\s*[0-9]+` —— **只查计数，不查明细**。于是 3a 行写「未变」、3b 行写「9 项」都能过。

更刺眼的是这个门自己写过教训：`tools/report_lint.py:10` 的注释逐字是「config 必须同时写 md5 / exe / args 数 / env 数（**机主两次指出这里被缩水**）」。也就是说这是**第三次**同一个毛病——前两次补的是"要写计数"，这次缩的是"明细"。**每次整改只把当时的形态写进规则，形态一变就再漏一次。**

## 七、整改：把「够不够」变成阈值

新增 `tools/report_depth.py`，阈值不是拍脑袋，是照历史分布取"最好的一轮再上一档"：

| 项 | 阈值 | 历史最好 | 备注 |
|---|---:|---:|---|
| 一、字段行数 | ≥9 | 11 | 8 字段 + 3a + 3b |
| 3a 的 `--flag` 数 | **≥15** | 19 | `report_depth.py:57`；「未变」直接判负 |
| 3b 的 env 名数 | ≥8 | 9 | 名字要列出来，不许写「9 项」 |
| 32 位 md5 个数 | ≥2 | 2–6 | 引擎 + config |
| 正文字符 | ≥1500 | 5,147 | `report_depth.py:74` |
| 正文 `file:line` | **≥4** | **3** | `report_depth.py:77`，这一档历史上**从未达到** |
| 带单位量化值 | ≥3 | 46 | %/ms/GiB/字符/处 才算单位 |
| 数字事实总数 | ≥15 | 46+ | 本轮可没有性能数据，但不能没有数量 |

**回测 14 份历史报告：0 份达标。** 这不是门坏了，而是说明"以前觉得合格"的标准本来就低——最好的一轮正文也只有 3 处引用。所以门槛定在 4，并写明：**本轮是第一份按新标准写的报告**。

**负向自测 4/4**（都在本文件上改坏一处再判）：

| # | 改坏什么 | 判据命中 |
|---|---|---|
| N1 | 3a 行换成「未变」 | `3a args 明细只有 0 个 --flag` |
| N2 | 正文截断到 121 字符 | `正文只有 121 字符（要 ≥1500）` |
| N3 | 去掉 config 的 32 位 md5 | `少于 2 个 32 位 md5` |
| N4 | 队列只留 3 个 ID | `四、队列 ID 少于 6 个` |

已接进 `albus/w1002/round_close.py:23` 的 `HARD` 列表（与本文件同路径传参，见 `round_close.py:42`），硬门不过不许发报告。

## 八、举一反三

1. **门的层次要分开**：`report_lint` 管"字段在不在"，`report_depth` 管"内容够不够"。混在一个脚本里，改一处就会把另一处的判据带松。
2. **阈值要能从历史里读出来**：这次每一项都写了"历史最好是多少"，所以 0/14 这句是可复核的结论，不是自我批评。
3. **同一个毛病第三次出现，说明整改的位置不对**：前两次都在补"要写什么"，这次补的是"写多少"。下一轮若再缩，缩的一定是"写得对不对"（数字与账本一致性）——那已经由 `plan_retired`/`pointer_lint` 覆盖。
