import io
import re

P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
n435 = n107 = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 11 and f[1] == "P435":
        f[8] += " **W1046/P523 再更正**：在 gfx906 上 qsa_prompt_attn_batch 会被调用但拒绝执行其 CUDA 内核，实际回退 qsa_decode_attn_batch；因此 B1/B2 的 DP4A 已由 W1044 覆盖，不是 qsa_pattn 的新空缺。"
        lines[i] = "\t".join(f); n435 += 1
    if len(f) >= 11 and f[1] == "R107":
        f[2] = f[2].replace("W1032–W1042 **14 轮连续未审**", "W1032–W1046 **15 轮连续未审**")
        f[8] = re.sub(r"W1032–W1042[^）]*", "W1032–W1046；W1046 复核后更新", f[8])
        f[10] = "KW:AUDIT29|15 轮连续未审|audit_scope"
        lines[i] = "\t".join(f); n107 += 1
assert n435 == 1 and n107 == 1
row = ["B8工程", "P526",
       "重建配方把在产 attn 当成未装机：note 里 W1042 的历史「未装机」让 recipe_check 跳过它，W1044 的「已装机」没有抵消",
       "W1046", "count", "1", "1", "DONE",
       "**实测**：W1046 复跑 `recipe_check --live` 时 `strata-0.1.57-attn` 显示 `[skip] 未装机`，尽管 SNAPSHOT/进程均为 attn。根因是 note 同时含历史「未装机」和后来「已装机」，工具按子串判。已将历史句改为「W1042 候选阶段生产仍 kvg」；复跑 `[ok] attn md5=3b758f88ddad`，hc4 仍正确 skip。**判据**：在产件不能再被配方门跳过。",
       "P499;P513", "KW:recipe_check|历史标记|attn"]
assert len(row) == 11 and all("\t" not in x for x in row)
assert not any(l.split("\t")[1] == "P526" for l in lines if l.count("\t") >= 9)
for kw in row[10].replace("KW:", "").split("|"):
    assert kw in " ".join(row), kw
lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

tot = done = 0
for l in lines:
    f = l.split("\t")
    if len(f) >= 10 and f[0] != "block" and not l.startswith("#"):
        try: tot += int(f[5]); done += int(f[6])
        except ValueError: pass
pct = 100.0 * done / tot
print("TOTALS", tot, done, round(pct, 1))

PLAN = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(PLAN, encoding="utf-8").read()
s, n = re.subn(r"\| 进度分母 \| \*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1046；",
               "| 进度分母 | **%d 条 / 已结 %d / %.1f%%**（W1046；" % (tot, done, pct), s, count=1)
assert n == 1
anchor = "- **生产零变更**：引擎仍 `attn` / config `3dde8801`；本轮重启 0 / 停机 0 / 装机 0 / 回滚 0。quant_quality 技能的旧三臂设计稿未跑，不冒充实测。"
add = ("- **配方门修正（`P526`）**：`attn` 的 note 同时含 W1042「未装机」和 W1044「已装机」，`recipe_check` 按子串把在产件跳过；已去掉历史标记并实测 `[ok] attn md5=3b758f88…`。\n"
       "- **审计债**：`audit_scope §A` 已为 **15 轮连续未审**（W1032–W1046），R107 同步；不冒充已解决。\n"
       + anchor)
assert s.count(anchor) == 1
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s.replace(anchor, add, 1))

H = "albus/w1034/HANDOFF.md"
h = io.open(H, encoding="utf-8").read()
h, n = re.subn(r"> SNAPSHOT: round=W\d+ date=2026-11-07", "> SNAPSHOT: round=W1046 date=2026-11-07", h, count=1)
assert n == 1
io.open(H, "w", encoding="utf-8", newline="\n").write(h)

M = ".workbuddy/memory/2026-11-07.md"
m = io.open(M, encoding="utf-8").read()
addmem = """
### W1046（19:08–19:4x）R103 后续入权威并实施：B3 hc4 已建；k8v4 dot8 原型有上限但质量未过

- **生产未变**：`attn`（`3b758f88`）+ config `3dde8801`；零停机/零装机。候选分支 `gfx906/hc-dp4a@179bd6b5` 已推 origin，pre-push ROUND_GATE PASS。
- **B2 落点纠错（P523）**：`qsa_pattn.cu` HIP 下 `STRATA_PATTN_BUILT=0`；gfx906 prompt 实际回退 `qsa_decode_attn_batch`，W1044 DP4A 已覆盖 B1/B2。旧「B2 还可再拿 2–4%」作废。
- **B3（P524/R109）**：`strata-0.1.57-hc4` `df33d3a6…`/43,675,416 B，默认 off `STRATA_HC_DOWN_DP4A`。Q8_0 权重×staging 量化 int8 激活走 DP4A，原内核保留。gr_parity 0 failures、bench 0 differing；fused_gr ISA `v_dot4=720/dot8=0`；Q8 mixed rel-RMS 0.0009→0.0012 ⇒ 必须数值门。cold 子模式两臂 timeout，无性能结论。
- **dot8q ≠ dot8**：前者是 8 次 FP32 FMA 的函数名；硬件 `v_dot8_i32_i4` 按 ROCm/LLVM 是 **i4x8×i4x8**，不是 int4×int8。
- **k8v4 dot8（R110/P525）**：只能优先看 PV，QK 的 K=int8 不兼容 dot8。PV 原型 P*Vscale→int4、V int4，CPU/GPU 对齐；预打包 6.511→4.391 µs（1.483×），合成 rel-rms 6.23%，且量化/打包未计时 ⇒ 只过可行性上限，真实模型门未做。
- **配方门（P526）**：attn note 的历史「未装机」导致 recipe_check 跳过在产件；已修并实测 ok。
- 进度 **473 条 / 已结 382 / 80.8%**；R107=15 轮未审。下一步 B3 需独立停机窗口（干净 HC 计时 + logits/needle/decode 长生成 + A/B），dot8 先做真实模型 P(int4) 数值门。
"""
io.open(M, "w", encoding="utf-8", newline="\n").write(m.rstrip("\n") + "\n" + addmem)
print("snapshot/memory/final ledger done")
