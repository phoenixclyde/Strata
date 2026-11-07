#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1050 landing: R106 close + R113/R114 progress rows + W832 writeback + memory.
import io
import os
import re

ROOT = r"D:/workbuddy_space/strata_ws"
os.chdir(ROOT)

# ------------------------------------------------ PROGRESS
P = "deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
rows = [
    ["B10环境与版本", "P548", "R106 结案：gen_config 九处漂差全清，--live 无差异；负向自测 8/8",
     "W1050", "count", "1", "1", "DONE",
     "**W1050**。① P55/P56 同义重复行停止 emission（P55→SUPERSEDED by P110 语义、P56→REJECTED 对齐 P541）；② P156 name 内嵌 =/中文注释 → MEASUREMENT 行；P230 整句 name → PLATFORM 行；③ 补 P543–P546（TUNED/DECODE_TIMING/SPEC_DEPTH/PREFILL_TIMING）ENV 声明行；④ META tokenizer/model_name 对齐 UD-Q4_K_XL；⑤ 举一反三又抓出：tuned7 家族 9 行实为 arch_defaults.cpp 缺省生效（改 scope=DEFAULT 不 emission）、P138 direct(缺省)、P259 描述性 --prefill（与 P10 重复）、P254 name 混值、V02 vision.model 旧 IQ4_XS 路径、P547 --serve 行按 live 实证否决（旧报告 3a 误抄）。gen_config 新增 validate()（ENV/CLI name+value 严格校验，坏行必须报错）+ --self-test 8/8 + --live 规范化比较（键序 cosmetic、exe 归 D5、args 多重集）。",
     "P492;P543", "KW:gen_config|--live|无差异"],
    ["B10环境与版本", "P549", "R113 #30837 判定：wave64 不变量成立，断言随下次重编带上（无行为改动不换件）",
     "W1050", "count", "1", "1", "DONE",
     "**W1050**。GitHub API 取 1a24df16 真实 diff = 仅 1 行 static_assert(I % warp_size == 0)（编译期护栏，无 codegen）。双插到本树 mmq.cuh 两处模板（锚点 2 个）后 BLD=0 ⇒ gfx906/wave64 配置下不变量成立。r113 二进制 md5 e3250b72（重编元数据差异），同树重编 bit 可复现性已由 hc4b md5 复现证实。R113 余下 4 提交（c49edf09/eb4e244b/5ce06fc7/69ee2ecc）仍 OPEN 择机。",
     "P520;R113", "KW:#30837|static_assert|wave64"],
    ["B10环境与版本", "P550", "R114 推进：离线门+微基准+候选 r114 就位，G2 窗口待开",
     "W1050", "count", "1", "1", "DONE",
     "**W1050**。① 离线门（真实 GGUF 4 分片，gguf-py 解析）：ssm_alpha/beta F32 权重经引擎 bf16 舍入后 bf16→fp16 无损率 99.91%/99.96%，但 min|w| 2.8e-11 使 0.47–0.5% 落入 fp16 次正规区（max|w|≈1.1 无溢出）⇒ 无损判 FAIL、范围判 CONDITIONAL；F32→bf16 100% 精确。② 微基准 gdn_ab_bench.cu：dot2 5.75us vs fmaf 7.65us（**1.330×**），rel_rms 2.1e-4；该点是延迟/占用受限（12 blocks/call、65 GB/s）而非带宽墙，推翻先前 roofline 否决。③ 候选 strata-0.1.57-r114（gfx906/r114@7d4db2363，md5 d909d597，STRATA_GFX906_GDN_DOT2 strings=1，off 臂保留）。**未跑窗口**：G2 KL + gdn 相位 A/B 下轮开；若 G2 失败按预案上 per-row 2^k 缩放。",
     "R114;P536", "KW:gdn_ab_bench|1.330|d909d597"],
]
for r in rows:
    assert len(r) == 11 and all("\t" not in x for x in r)
    assert not any(l.split("\t")[1] == r[1] for l in lines if l.count("\t") >= 9), r[1]
    whole = " ".join(r)
    for kw in r[10].replace("KW:", "").split("|"):
        assert kw in whole, (r[1], kw)
    lines.append("\t".join(r))

n = 0
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) >= 11 and f[1] == "R106":
        f[2] = "gen_config 与生产 config 对齐（W1050 结案：九处漂差+派生漂差全清，--live 无差异，负向自测 8/8）"
        f[6] = "1"; f[7] = "DONE"
        f[8] = "**W1050 结案**。九处（P492 记录）+ 运行 --live 抓出的派生漂差（tuned7 家族 emission 归属、P138/P259/P254/V02/P547）全部修复；validate() 让坏行 fail-closed。见 P548。"
        f[10] = "KW:gen_config 对齐|无差异|P548"
        lines[i] = "\t".join(f); n += 1
assert n == 1
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("progress rows added, R106 closed")

# ------------------------------------------------ W832
P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
anchor = "### 回写 · W1049（2026-11-07 23:5x–01:1x）R103 移植面全收口：B2 闭案、A2 采纳、A1/A3/A4/A5 判否、P457 结案"
assert s.count(anchor) == 1
section = """### 回写 · W1050（2026-11-08 01:1x–02:5x）R106 结案 + R113 护栏验证 + R114 三件套就位

- **R106 结案（`P548`）**：`gen_config --live` **无差异**。九处漂差（P492）+ 派生漂差全清：同义重复行停止 emission（P55/P56）、坏 name 行降级为记录行（P156/P230）、补 TUNED/DECODE_TIMING/SPEC_DEPTH/PREFILL_TIMING 声明行（P543–P546）、tokenizer/model_name 对齐 UD-Q4_K_XL、**tuned7 家族 9 行归位 `arch_defaults.cpp` 缺省生效（scope=DEFAULT 不 emission）**、P138/P259/P254/V02 数据修复、**P547 `--serve` 按 live 实证否决**（W1047/W1049 报告 3a 误抄旧报告——已记账）。`gen_config` 新增 `validate()` fail-closed + `--self-test` 8/8；`--live` 规范化比较（键序 cosmetic、exe 归 D5、args 多重集）。
- **R113 #30837（`P549`）**：真实 diff = 1 行 `static_assert(I % warp_size == 0)`（编译护栏、零 codegen）。双插两处模板后编译通过 ⇒ **gfx906/wave64 不变量成立**；随下次重编带上，不做无意义换件。同树重编 bit 可复现性顺带证实（hc4b md5 复现）。R113 余 4 提交择机。
- **R114 三件套（`P550`）**：① 离线权重门（GGUF 真实值）：bf16→fp16 无损率 99.9%+，但 0.5% 尾部（min 2.8e-11）入次正规区 ⇒ 无损 FAIL / 范围 CONDITIONAL；② 微基准 **dot2 1.330×**（5.75 vs 7.65 us/call），延迟受限小内核（12 blocks、65 GB/s）非带宽墙——推翻 roofline 预判，ALU 换指令有效；③ 候选 `r114@7d4db2363`（`STRATA_GFX906_GDN_DOT2` 默认 off）。**G2+相位 A/B 窗口下轮开**；G2 失败则 per-row 2^k 缩放营救（外证 Chenfan：二次幂缩放保 bf16 有效位）。
- **R107**：机主 2026-11-08 01:19 指示「审计欠账继续记着，后面我处理」——只记账不代做。
- **边界**：本轮零停机零装机（微基准/离线门/工具链全零停机）；生产仍 `hc4b`+`8d234fa3`（含 LDS_PAD）。

"""
s = s.replace(anchor, section + anchor, 1)
dir_anchor = "| `回写 · W1049（2026-11-07 23:5x–01:1x）R103 移植面全收口` | B2 闭案；A2 采纳；A1/A3/A4/A5 判否；P457 结案 | W1049 |"
assert s.count(dir_anchor) == 1
row = "| `回写 · W1050（2026-11-08 01:1x–02:5x）R106 结案 + R113 护栏 + R114 三件套` | gen_config 无差异；#30837 不变量成立；dot2 1.33× | W1050 |"
s = s.replace(dir_anchor, dir_anchor + "\n" + row, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated")

# ------------------------------------------------ memory + snapshot
import re as _re
H = "albus/w1034/HANDOFF.md"
h = io.open(H, encoding="utf-8").read()
h = _re.sub(r"> SNAPSHOT:.*",
            "> SNAPSHOT: round=W1050 date=2026-11-08 prod_exe=strata-0.1.57-hc4b prod_md5=0533074826258d5f96c4b65bc0ad33df config_md5=8d234fa38261abbee0328c80416d6835 container=2d765942e041 image=strata-gfx906:0.2.11-101 branch=gfx906/mi50 picks=03509d1b", h, count=1)
io.open(H, "w", encoding="utf-8", newline="\n").write(h)
M = r"D:\workbuddy_space\strata_ws\.workbuddy\memory\2026-11-08.md"
entry = """
## W1050（01:1x–02:5x）R106 结案 + R113 护栏 + R114 三件套
- R106：gen_config --live 无差异。九处+派生漂差全清（tuned7 家族归 arch_defaults 缺省、P138/P259/P254/V02/P547）；validate() fail-closed + 自测 8/8。**旧报告 3a 的 --serve 是误抄**（live args 无此 flag）。
- R113 #30837 = 1 行 static_assert；双插编译过 ⇒ wave64 不变量成立；零 codegen 不换件。
- R114：离线门（bf16→fp16 尾部 0.5% 入次正规、无溢出）+ 微基准 dot2 1.330×（延迟受限非带宽墙）+ 候选 r114（GDN_DOT2 默认 off）。G2 窗口下轮开。
- R107 审计欠账机主自理（01:19 指示），只记账。
- 教训：①长字面量跨工具链会被改字节（`stream)>>>` 多括号、`\\n`→`/n`），编译报错要 od 对字节；②GGUF array 编码子类型只读一次；③「roofline 否决」要先量占用/launch 形态——12 block 小内核是延迟受限。
"""
if not os.path.exists(M):
    io.open(M, "w", encoding="utf-8", newline="\n").write("# 2026-11-08\n" + entry)
else:
    s2 = io.open(M, encoding="utf-8", errors="replace").read()
    if "W1050" not in s2:
        io.open(M, "a", encoding="utf-8", newline="\n").write(entry)
print("memory done")
