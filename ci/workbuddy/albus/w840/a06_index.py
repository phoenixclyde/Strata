#!/usr/bin/env python3
# W840-06 更新审计索引 + 追加 AUDIT13 台账
import io

IDX = "D:/workbuddy_space/strata_ws/deploy/AUDIT_INDEX.md"
s = io.open(IDX, encoding="utf-8").read()

s = s.replace("# 审计索引（AUDIT6 → AUDIT12）", "# 审计索引（AUDIT6 → AUDIT13）")

old_tail = "| AUDIT12 | W826–W831 | 3 | 11 | 12 | - | `AUDIT12_W826_W831.md` |\n| **合计** | W776–W831 | **6** | **43** | **52** | **3** | — |"
new_tail = ("| AUDIT12 | W826–W831 | 3 | 11 | 12 | - | `AUDIT12_W826_W831.md` |\n"
            "| AUDIT13 | W832–W839 | 3 | 8 | 6 | - | `AUDIT13_W832_W839.md` |\n"
            "| **合计** | **W776–W839** | **9** | **51** | **58** | **3** | — |")
assert s.count(old_tail) == 1
s = s.replace(old_tail, new_tail)

old_rest = s[s.find("## 仍未结清的（跨轮，需实测）"):]
new_rest = """## 仍未结清的（跨轮，需实测）

| 项 | 出处 | 状态 |
|---|---|---|
| `--spec-min-p` / `--pcie-frac` | W832 §4.1（P210） | **UNRESOLVED**：效应 ≤4.4% < 噪声 6.0%，保留现值。注意原停机条件（`ms/win` <2%）结构性失效，见 AUDIT13 P0-2 |
| `--pool-workers` | W833 §4.5（P214） | **UNRESOLVED**（AUDIT13 改判）：n=3、无 ABBA；read1300 实为 3/3 同向 |
| 数值债 `GDN_PP` | P213/P229 | **未测**（GDN_HEAD 已确认位等价，GDN_PP 无臂） |
| §6.8 的 AMD 开关覆盖面 | W828 §6.8、AUDIT12 P1-2 | 19 项里 2 项默认开、5 项测过、**10 项整组否决（P212）** ⇒ 「已穷尽」仍不成立 |
| 宽窗口 bit-exact | W829 L79 | **未做**（并发轴已关，优先级低） |
| 28 个 `STRATA_USE_HIP` 死块 | W839 §6、P227 | **未打开任何一块**；候选 `pcie_frac_auto` / `decode_defaults_arch_ok` |
"""
s = s.replace(old_rest, new_rest)
io.open(IDX, "w", encoding="utf-8", newline="\n").write(s)
print("index updated:", len(s))

# ---- 台账追加 ----
LED = "D:/workbuddy_space/strata_ws/deploy/AUDIT_LEDGER.tsv"
t = io.open(LED, encoding="utf-8").read().rstrip("\n")
rows = [
 ["A13-P0-1", "AUDIT13", "P0", "W832-W834", "W832:139", "样本口径写错：36 条/36 个 sha 写成 33/33；3 条 446/318/420 token 被当 512 计入表", "正文改 36/36 + 括注；P210 evidence 追加更正", "FIXED"],
 ["A13-P0-2", "AUDIT13", "P0", "W832-W834", "W832:48", "停机条件写在 ms/win，四臂配对差 11.75/-7.24/-4.11/+2.53%、复本 +4.88% ⇒ 永不触发", "停机条件改为主判据 tok/ms + 噪声底盘；结论仍 UNRESOLVED", "FIXED"],
 ["A13-P0-3a", "AUDIT13", "P0", "W832-W834", "W832:158 / P211", "read n=2 均值含冷样本、decode 单轮 A→B，却写「0 收益 0 回归」CONFIRMED", "改 UNRESOLVED", "FIXED"],
 ["A13-P0-3b", "AUDIT13", "P0", "W832-W834", "W832:264 / P214", "read1300 实为 3/3 同向（pw13 全更快），却写「符号翻正翻负 ⇒ 抖动」", "改 UNRESOLVED 并附原始三对", "FIXED"],
 ["A13-P0-3c", "AUDIT13", "P0", "W832-W834", "W832:226 / P213", "GDN_PP 从未单独测，却与 GDN_HEAD 一并判「位等价、零债」", "改 PARTIAL；新开 P229 记未测", "FIXED"],
 ["A13-P1-1", "AUDIT13", "P1", "W835", "W835:120", "可达面 33 ms/73% 把 6.50 ms 等待算进去；✓ 项实为 24.19/53.8%", "改 24.19/53.8%", "FIXED"],
 ["A13-P1-2", "AUDIT13", "P1", "W835", "W835:120 / P218", "30–50% 局部改善 ⇒ 应 -16%~-27%，原文 -5~-10%，与自表差 3–5 倍", "改 -16~-27%；P218 CORRECTED", "FIXED"],
 ["A13-P1-3", "AUDIT13", "P1", "W835", "W835:264 / P219", "116.5/26.5 = 4.40×，原文 3.9×", "两处改 4.40×", "FIXED"],
 ["A13-P1-4", "AUDIT13", "P1", "W832-W834", "W832:236", "「0.029→≈0.045」无效相加：两样本总体不同，且 0.0171 中 88% 来自单点", "改为「另一笔，不可加」", "FIXED"],
 ["A13-P1-5", "AUDIT13", "P1", "W836", "W836:72", "configure 见 find_dependency 记成「W793 生效」；find_package ≠ 进二进制", "加更正：真判据是警告归零 + 字符串", "FIXED"],
 ["A13-P1-6", "AUDIT13", "P1", "W836", "W836:191", "「运行时 banner ✅」来自单独测试件，引擎二进制 grep MI50-class = 0", "标注来源", "FIXED"],
 ["A13-P1-7", "AUDIT13", "P1", "W836", "W836:14-17,69", "+216/-9 与 +94/-7 是不同时点混排；权威值 ahead 10 / 11 文件 / +243 -9", "加时点标注", "FIXED"],
 ["A13-P1-8", "AUDIT13", "P1", "W839", "W839:48,106-108,147", "1309b1d 是第 9 个 commit（非 10）；门禁 17 项（非 18）；12820 vs 12739 非「逐项一致」", "三处改", "FIXED"],
 ["A13-W-1", "AUDIT13", "P2", "W832-W834", "w833 EG 臂", "审计方指控「EG 开关没下发」— 撤回：配置 w833_klegdn.json 确实设 GDN_HEAD=0，位等价成立", "公开撤回", "WITHDRAWN"],
 ["A13-W-2", "AUDIT13", "P2", "W830 门禁", "verify_patches.sh", "审计方指控 BW_REFRESH_S / cudaStreamCreateWithPriority 假绿 — 撤回：上游 main 计数均 0", "公开撤回", "WITHDRAWN"],
 ["A13-W-3", "AUDIT13", "P2", "W835/W839", "97.4%", "审计方指控 33.5/34.3=97.67% 算错 — 撤回：未四舍五入 33.46/34.34=97.41%", "公开撤回", "WITHDRAWN"],
]
add = "\n".join("\t".join(r) for r in rows)
out = t + "\n" + add + "\n"
io.open(LED, "w", encoding="utf-8", newline="\n").write(out)
print("ledger rows:", len([l for l in out.split("\n") if l.strip()]) - 1)
