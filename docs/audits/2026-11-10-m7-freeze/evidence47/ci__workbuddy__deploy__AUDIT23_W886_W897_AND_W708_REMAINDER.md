# AUDIT23 · W886–W897 + W708–W775 剩余件（30 件从未被任何审计引用）

> VERDICT: AUDIT23 P0=1 P1=2 P2=1 P3=0 src=AUDIT_INDEX:23（AUDIT28 回填，不新增结论）


> 2026-11-02 23:0x。范围由机械判定给出：`W*.md` 230 件中，**32 个编号从未出现在任何 `AUDIT*.md` 里**
> （去重后 30 件；W712/W736 各两份）。方法分三层：
> ①**机械层**——抽标题、结论行、作废横幅，并查它是否仍被 `PROGRESS.tsv` / `PARAM_REGISTER.tsv` 引用；
> ②**事实层**——凡依赖外部事实的主张，去源码/容器/官方文档复核，不引用二手转述；
> ③**三态判定**——仍成立 / 已撤回未标 / 仅历史。

---

## 0 总判

**P0 = 1，P1 = 2，P2 = 1；已全部整改。**

| id | 级别 | 位置 | 问题 | 处置 |
|---|---|---|---|---|
| A23-1 | **P0** | `W893 §0` 第 2 条 | 「**CK 不是 MI50 的路**」只查了 GitHub 主线（0 处 gfx906），没查宿主安装的 CK（1.1.0 有 **17 处**），且未标撤回 ⇒ 违反本项目「撤回必须回写源头横幅」 | **已加横幅**，指向 `W894 §1` 的正确表述 |
| A23-2 | **P1** | `W894 §1` | 「生产容器 ROCm **10.1.0**」是版本串，不是官方组件集合：官方 10.1.0 带 rocBLAS **5.5.0**，我们是 **5.7.0.962d0059** ⇒ 复现者按官方装会让 `gfx906-rocblas-5.7.0.txt` 失效 | **已补口径**（含官方矩阵与实测版本） |
| A23-3 | **P1** | `W712_PLAN.md` / `W749_OPT_PLAN.md` | 作废横幅指向 `W713_PLAN` / `W750_MASTER_PLAN`，两者**都已被 W832 取代** ⇒ 指针腐坏，顺横幅走会落到另一个死方案 | **已改指 `W832_OPT_PLAN_V2.md`** |
| A23-4 | **P2** | `.workbuddy/memory/2026-11-02.md` | 「4945→4936 文件」笔误（无 4945 这个数） | 已改为 4,936（交付件本身一直是对的） |

---

## 1 正面核验（这些主张经查**成立**，不是走过场）

| 主张 | 出处 | 复核方式与结果 |
|---|---|---|
| ROCm **10.1.0** 是真实发行版 | W894 | 官方 release history：**10.1.0 / 2026-10-05**（10.0.0 2026-08-26、7.14.1 2026-09-02） |
| 官方 10.1.0 组件 = CK 1.2.0 / rocBLAS 5.5.0 / hipBLASLt 1.4.1 / HIP 7.14 / LLVM 23 | W894 | ROCm 兼容矩阵原文；与我们容器不一致处已按 A23-2 标注 |
| 宿主 CK 1.1.0 **有** gfx906、主线 **无** | W893/W894 | `grep -rn gfx906 /opt/rocm-6.4.4/include/ck` = **17**；`ROCm/composable_kernel@d84d8e2` = **0** |
| 容器 CK **未装**、hipBLASLt **无 gfx906 内核** | W894 | `/opt/rocm/include/ck` 不存在；`find /opt/rocm -path '*hipblaslt*' -name '*gfx906*'` = **0** |
| 容器 221 个 gfx906 代码对象 | W894 | `find /opt/rocm -name '*gfx906*' \| wc -l` = **221** |
| rocBLAS 调优表**真的在生效** | W894（新增） | 引擎日志逐字：`rocBLAS tuning enabled (84 rows, 75 with a solution, gfx906, rocBLAS 5.7.0.962d0059)` |
| MMQ 编译期开、且比 FP16 快 1.57× | W897 | `build.ninja` 有 `-DSTRATA_PREFILL_MMQ=1`；A/B：8.975 s vs 14.079 s（CV 1.0/1.1%） |
| 引擎有多流 | W897 | `generate.cpp:141 set_batch_slots` / `:797` / `batch_rows.hpp` / CLI `--batch`、`--batch-groups` |

---

## 2 老段 W708–W775：22 件逐件三态

**仍被账本引用（13 件）**——逐件比对标题结论与当前 `P` 行，**无矛盾**：

| 轮次 | 结论要点 | 与现账本 |
|---|---|---|
| W719 | `strata_prefix` 契约确认、实测无增量 | 一致（P33 关） |
| W723 | 三项组合全在分辨力以下、不建议组合 | 一致（P28/P29/P32 关） |
| W726 | telemetry 缺 `"backend":"hip"` 键导致走 NVML 分支 | 一致（已修，AUDIT19/A11 同族） |
| W728 | 上游 `_Amd.read()` 不读 pcie；按纪律不采用 | 一致（登记为上游缺口） |
| W736 | 待发布文本（评论 ×4 + issue ×2），只用自有实测 | 历史件，无结论冲突 |
| W738 | ki 引擎不可用（吃不了我们权重、绑 torch/vLLM），结论与工具可用 | 与 W892/W894/W895 同向 |
| W739 | `STRATA_EXPERT_V2`/`TSUM` 单变量 A/B | 与 W824（EXPERT_V2K 三次无差异）、W890（TSUM 净负）一致 |
| W740 | ISA 探针不能替代读源；引 routeK 须读自有库 | 铁律，仍有效 |
| W748 | 「59.9 tok/s」复现性结论 | 历史件，未被推翻 |
| W749 | 方向/计划（**已并入 W750，W750 又被 W832 取代**） | **指针已改**（A23-3） |
| W754 | routeK T1 前提在 Strata 不成立，另立新目标 | 与 W892 的 T1/T5 判定一致 |
| W760 | `--mtp-window` / `SH_STREAM` 单变量 A/B，不构成改答案 | 一致（P43 在产 8192） |
| W774 | 上游 v0.1.42 升级 + 对外件回音 | 历史件，无冲突 |

**仅历史、未被账本引用（7 件）**：W712（方案，已标取代 → 指针已改）、W721（组合视角）、W722（记忆技能铁律）、
W747（生产自比，结论被后续 A/B 覆盖）、W756（社区 bench 规范）、W764/W765（参数落地审计，已被 W886 的 27 参数机械表覆盖）。
⇒ 这 7 件**不需要**进账本，但 W712/W749 的**指针**必须指向当前权威（已改）。

---

## 3 新段 W886–W897：10 件逐件判定

| 件 | 结论 | 审计判定 |
|---|---|---|
| W886 | R44：27 个现役参数逐条追源，修正 3 条现役值（`--pack/--native/--expert-profile-save` 仍写 IQ4_XS） | **成立**；3 条修正确已落 `PARAM_REGISTER` |
| W887 | prompt attention 有效算力仅 FP32 峰值 11–16% | 成立（源码 roofline，未受本次改动影响） |
| W888 | needle 证据只到 128k、现役权重已补测 | 成立 |
| W889 | HC 不是带宽受限，是占用率随窗口 T 减半 | 成立（W890 用 A/B 收口） |
| W890 | R38 DONE_NEG：down −19.5% 但 up +26.1%，合计 +2.8% | 成立 |
| W892 | 26 条主张逐条对账；R47 关闭、R48 证否；`v_dot8` 7 个 fork 均无实现 | 成立（本件自带 §3/§4 撤回说明） |
| W893 | ki 内核清单 + wave64 | **P0-1 已修**（CK 段），其余成立 |
| W894 | 版本/30 条/10 项/ki 最新 | **P1-1 已修**（ROCm 口径），其余成立 |
| W895 | 项目清单全量 + furnace 校准（MoE 单流 decode 62→62） | 成立；数字已与源码/README 对齐 |
| W897 | 多流确认 + 两臂实测（IO_THREADS 无收益、FP16 慢 1.57×） | 成立；两臂均已回滚 |

---

## 4 复算命令

```bash
# 未审计面（机械）
python - <<'EOF'
import re,glob
w=sorted({int(re.match(r'W(\d+)',p).group(1)) for p in glob.glob('W*.md') if re.match(r'W(\d+)',p)})
t=''.join(open(p,encoding='utf-8',errors='replace').read() for p in glob.glob('AUDIT*.md'))
print([n for n in w if n not in {int(x) for x in re.findall(r'\bW(\d{3})\b',t)}])
EOF
# 事实层
grep -rn gfx906 /opt/rocm-6.4.4/include/ck | wc -l          # 17
docker exec strata166-407 bash -lc 'ls /opt/rocm/lib/librocblas.so*; grep -ai "rocBLAS tuning enabled" /data/*.log | tail -1'
```
