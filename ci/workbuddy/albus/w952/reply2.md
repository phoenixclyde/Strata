## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T08:14:34Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | **零**；disk = build = running = `ae085365…` 三方一致 |

## 二、主线

`gfx906/mi50 @ 5f73cd15` · tag `mi50-0.2.10-r28` · 上游 `ffa80d73` · 落后 0 / 领先 37 · 工作树脏 0 行 · 与 origin 同点。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮累计重启 **1 次**（复测 PMC），停机 **≈4 分 20 秒**。

## 四、进度 + 队列

**175 条 / 已结 101 / 57.7%**；主线 147 / 101 / 68.7%；死块池 0/28。
队列：R90-S1 → R91-P1 → R91-P3 → R91-P4（KL 门）→ R88 → R86 → R87 → R64 → R63 → R60 → R81 → R79 → R80 → R49 → R50 → R30′

---

## 补丁：四处“横幅加了、结论没撤”

子审计复核我的第一轮横幅，指出一个共性缺陷：**我只改了数字口径，没撤结论**。四处已补：

| 位置 | 原来的问题 | 补法 |
|---|---|---|
| `W942` | 横幅讲清了 67.1% 的复现与形状，**R60 / R84 = DONE_NEG 仍立着** | 明写「数字保留、由它推出的关闭不保留」：R60/R63 → OPEN、R84 → INFLIGHT |
| `W944 §60` | 我的横幅末句错写「端到端预期不变」，与 `W945` 的「0 ~ −6.3% 未知」正面冲突 | 改为「−6.3% 已下调为 0 ~ −6.3% 未知，只有 13.8% 这个分母不变」 |
| `W946 §6/§7` | 只改了两个数字，R89 仍写「当场判否（A 级源码）」，与 `W832:803` 的 OPEN 矛盾 | 补「源码阅读按 `W939 §0` 是 D 级；R89 已改回 OPEN」 |
| `W947 §50-57` | 猜的根因是 `_Float16`，`W950/W951` 已证否，却没有横幅 | 补：根因是**缺 warp 归约** + host 参考多乘 scale，修正后 0.00319 / 0.06481 |

由此立 **纪律㉔**：撤回横幅必须带**结论动词**（“关闭不保留 / 改回 OPEN / 上限不作预期”），只写“口径更正”不算撤回——这四处全是同一形态，也解释了为什么第一轮看起来“都加了横幅”却仍会被下一个人读错。

另一条验证陷阱也记进了审计件：`\|Δ\|` 转义后 `awk -F'|'` 仍把它当分隔符，**“字段数=9”不再是破表判据**，只能看 `grep -c '|Δ|'`（现为 0）。

审计件已更新：`deploy/AUDIT24_W900_W951.md` 新增 §1.1（第二轮），判据仍为 **P0 2 / P1 16 / P2 12 / 需复核 4**，全部整改完毕；账本 175/101/57.7% 未变，方案表锚点 `W832@f40c8f39`。
