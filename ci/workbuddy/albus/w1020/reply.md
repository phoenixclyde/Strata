# W1020 报告补录（AUDIT27，2026-11-07）——**不是原始报告**

> **为什么要补**：`P329` 立下「报告唯一副本 = `albus/<轮>/reply.md`」，AUDIT27 机械扫 W1006–W1031
> 共 26 轮时发现 **只有 W1020 没有这个件**（`albus/audit27/scope.py` 与 `tools/audit_scope.py` 均可复算）。
> 本件是审计补录，**不伪造当时的十字段现场值**：W1020 当时的容器 id、config md5、显存布局等
> 只在后来 W1021/W1022 的复核里被间接引用，逐字回填会制造一份假证据。
> 凡要用现场数值，请读 `albus/w1021/reply.md`（W1021 的完整 review）与 `albus/w1022/reply.md`。

## 该轮实际留下的可核资产

| 来源 | 内容 |
|---|---|
| `deploy/W832_OPT_PLAN_V2.md` §6.5「回写 · W1020」 | 六段结论：两处 ggml API 变更、全量 154/154 LINK_OK、分层镜像、部署与容器重建、`-DSTRATA_VERSION` 第四指针、v0.2.11 首测 |
| `deploy/PROGRESS.tsv` | `P344`（ggml API）、`P345`（分层镜像）、`P346`（第四指针）、`P347`（首测） |
| `albus/w1020/` | `writeback.py` / `mk_dockerfile.py` / `Dockerfile-0.2.11-layered` / `build_image.sh` / `dbg_moe*.sh` |
| 166 分支 | `gfx906/mi50` 的 `30e42ca8` + `53720031`；tag `mi50-0.2.11-r33-3` |

## 四条结论（逐字来自方案与账本，不新增判断）

1. **全量重编**：v0.2.11 的 ggml 删了 `ggml_prec` 模板参数 ⇒ `mul_mat_q_case<type,prec>`→`<type>`（26 处）、
   `ggml_cuda_mmq_get_config` 去 prec（5 处）、`new_pool_for_device` 改签名（1 处）；`rm -f strata` 后 **154/154、LINK_OK**。
2. **镜像**：完整 Dockerfile 的 pip 步骤（tuna 源）不可用 ⇒ 改分层 `FROM 0.2.10-101` 只换 `/src`，
   9 分钟产出 `strata-gfx906:0.2.11-101`（15.7 GB），`/src/serve/server.py` md5 变化证明树已换。
3. **第四指针（P346）**：`build.ninja` 缓存 `-DSTRATA_VERSION="0.1.56"`，源码已是 0.1.57 ⇒
   把 `_ci_all.txt` 154 条命令全改 0.1.57 后以 `strata-0.1.57-001` 重新部署；
   **AUDIT27 已把 P346 从 OPEN 结为 DONE**（W1021 review 第 3/4/5 项复核 `--version` = 0.1.57）。
4. **首测（P347）**：prefill@2000 513.65→**532.58 tok/s（+3.7%）**、@8000 684.62→**716.14（+4.6%）**、
   decode 35.82→34.83（band 10.96，噪声内）、TTFT 4.096→3.910 s。

## 审计判定

- 该轮**结论有落点**（方案 §6.5 + 4 条账本行），不是「说完了没上账」；缺的只是面向机主的**报告件**。
- `P343`（W1019 的全量重编阻塞）在 W1020 被解除，但账本一直挂 OPEN ⇒ AUDIT27 已结清并回写 `W832` §6.5 W1019 块。
- 本补录件只用于满足「每轮有唯一可检索报告」的资产纪律，**不参与 `report_lint` / `report_depth` 的历史统计**
  （那两道门只对当轮报告跑）；`tools/audit_scope.py` 会检查它存在。
