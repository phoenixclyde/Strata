# -*- coding: utf-8 -*-
"""Generate deploy/AUDIT_LEDGER_A24.tsv (closure ledger) and verify every marker exists."""
import io, os, hashlib, sys

D = "D:/workbuddy_space/strata_ws/deploy/"
ROWS = [
 # id, level, doc, marker, status, fix
 ("A24-1",  "P0", "W909_DP4A_DOT8_EVIDENCE.md",        "的「专家格式」判断作废",            "RESOLVED", "横幅+算术复核(3,072,000B/专家)"),
 ("A24-2",  "P0", "W832_OPT_PLAN_V2.md",               "这句不再成立",                      "RESOLVED", "方案 §6.5 五处回写"),
 ("A24-3",  "P1", "W944_REASSESS_GFX906_PROJECTS.md",  "专家总字节 35%",                    "RESOLVED", "88.6%->35%/86%/89.6%; 60.5->77.0GB"),
 ("A24-4",  "P1", "W945_MX_Q51_REPACK_SOURCE.md",      "9.1–9.6%",                          "RESOLVED", "PMC 标形状(16x320 vs 16x1024)"),
 ("A24-5",  "P1", "W942_R61_VALUBUSY_67.md",           "结论层也要撤",                      "RESOLVED", "R60/R63->OPEN, R84->INFLIGHT; 67.3% 复测"),
 ("A24-6",  "P1", "W943_R63_R84_ISA_CENSUS.md",        "628 / 3,411 = 18.4%",               "RESOLVED", "地址类 19.7%->18.4%"),
 ("A24-7",  "P1", "W923_R61_PMC_FAILED.md",            "均已撤回",                          "RESOLVED", "rocprof 只在 HSA_TOOLS_LIB 注入下不可用"),
 ("A24-8",  "P1", "W924_R58_MMQ_THREE_SEGMENTS.md",    "模块口径",                          "RESOLVED", "53.3% 标模块口径, 真核 30.0%"),
 ("A24-9",  "P1", "W926_R64_ATTN_INT8.md",             "14.8–15.3%",                        "RESOLVED", "占比/上限/机制三处"),
 ("A24-10", "P1", "W940_DOT4_DOT8_AND_PLAN_GAP.md",    "W4A8",                              "RESOLVED", "3.22% 只在 W4A8; R84 上限已重算"),
 ("A24-11", "P1", "W946_GFX906_PROJECTS_LANDSCAPE.md", "796 是",                            "RESOLVED", "796=一slot起点; 887/867/877 才是基线"),
 ("A24-12", "P1", "W948_REPORT_LINT_AND_LLAMA_VERSION.md", "W953 更正",                     "RESOLVED", "版本锚点 0.4.1/e6ab7c1a4 (本条曾自身判错)"),
 ("A24-13", "P1", "W922_R68_STOP_BOUND.md",            "基本持平（−0.02pp",                 "RESOLVED", "99.72 低于 99.74"),
 ("A24-14", "P1", "W919_RELEASE_NOTES_READ.md",        "已撤回（`W920` 实测为 0",           "RESOLVED", "PLE 现成损失撤回"),
 ("A24-15", "P1", "W907_KERNEL_CORRESPONDENCE.md",     "19 个 / 5,703 行",                  "RESOLVED", "以 W912 的 19 个为准"),
 ("A24-16", "P1", "W912_KI_PORT_VERDICT.md",           "stale ref",                         "RESOLVED", "落后 0 -> 708"),
 ("A24-17", "P1", "PROGRESS.tsv",                      "【AUDIT24 复测",                    "RESOLVED", "R53/R54 证据列修复 + R61/R86/R90 注记"),
 ("A24-18", "P1", "W927_DOT8_Q4K_PORT.md",             "模块级分母",                          "RESOLVED", "5.5% 模块分母; gfx926 引用不可核"),
 ("P2-1",   "P2", "W832_OPT_PLAN_V2.md",               "\\|Δ\\|≥2×CV",                      "RESOLVED", "12 行竖线转义 + R89 两格"),
 ("P2-2",   "P2", "W913_R59_PRECISION_LEDGER.md",      "0.0220",                            "RESOLVED", "逐开关 KL 不可相加"),
 ("P2-3",   "P2", "W918_UPSTREAM_708_READ.md",         "W921",                              "RESOLVED", "冲突判断被推翻"),
 ("P2-4",   "P2", "W947_BACKTRACK_AND_DOT8_V1.md",     "缺 warp 归约",                      "RESOLVED", "根因更正"),
 ("P2-5",   "P2", "W941_PREFILL_800_REOPEN.md",        "【AUDIT24 口径注记】",              "RESOLVED", "801.4 -> 日志原值 804.1/800.2"),
 ("P2-6",   "P2", "W932_R75_AND_CHUNK16384_ADOPT.md",  "【AUDIT24 口径注记】",              "RESOLVED", "吞吐/时长两口径"),
 ("P2-7",   "P2", "W931_R70_CHUNK_SCAN.md",            "【AUDIT24 口径注记】",              "RESOLVED", "2.61% < 2xCV; 64K 臂被污染"),
 ("P2-8",   "P2", "W933_R76_PARTIAL_PREFIX.md",        "【AUDIT24 口径注记】",              "RESOLVED", "7.5% -> 6.96%"),
 ("P2-9",   "P2", "W929_M3_K8V8_PREFILL.md",           "【AUDIT24 口径注记】",              "RESOLVED", "decode 代价为外推"),
 ("P2-10",  "P2", "W930_R69_PENALTY_WINDOW.md",        "【AUDIT24 口径注记】",              "RESOLVED", "贪心单样本灵敏度"),
 ("P2-11",  "P2", "W935_PLE_RAISE_LIMIT_ADOPT.md",     "【AUDIT24 口径注记】",              "RESOLVED", "A 档是代理件"),
 ("C-1",   "P1", "W955_R90_S1S2_FEASIBILITY.md",          "build-r28",                         "RESOLVED", "ci/config.sh -> build-r28 + 0.2.10-101 (commit 03381d82, tag r29)"),
 ("V-3",   "P1", "W955_R90_S1S2_FEASIBILITY.md",          "S2",                                "RESOLVED", "R90-S1/S2 完成: 0.8.0 编通, overlay 静默 off 已记"),
 ("V-4",   "P1", "W956_R90_S3_MMQ_API_PORT.md",          "全量链接成功",                        "RESOLVED", "0.8.0 + 30 行适配 -> strata 39,599,200 B, 冒烟通过"),
 ("V-5",   "P1", "W957_R90_S4_NOT_BITEXACT.md",         "前缀 7",                              "RESOLVED", "0.8.0 端到端可跑; 与 0.4.1 前缀 7/64, 待同二进制对照"),
 ("V-6",   "P1", "W958_DETERMINISM_CONTROL.md",           "A1 vs A2",                            "RESOLVED", "逐位判据作废: A 自身 7/64, B 64/64"),
 ("V-7",   "P0", "W960_R90_PERF_REGRESSION.md",          "prefill −6.0%",                       "RESOLVED", "0.8.0 prefill 慢 6%(3v3); R90 降级, R88 上位"),
 ("V-8",   "P1", "W962_BISECT_FUSION.md",                "fusion",                             "RESOLVED", "0.7.0=594 vs B=566 vs A=602 -> fusion #29948 是 -5%"),
 ("V-9",   "P0", "W966_CODE_LEVEL_VERDICT.md",          "23,164",                              "RESOLVED", "内核逐字节等价; 热态 503/497/506 -> 0.8.0 可跟"),
 ("V-10",  "P0", "W969_UNIFIED_PREFILL_REGIMES.md",      "1.7 s",                               "RESOLVED", "冷读 t≈1.7s+n/822; 600/800/500 是三口径"),
 ("V-11",  "P0", "W970_R90_DEPLOY.md",                    "209d8f50",                          "RESOLVED", "0.8.0 已上生产; overlay ON; 回滚到 ae085365"),
 ("V-1",    "P1", "W953_VERSION_ANCHOR_AND_SELF_CORRECTION.md", "0.4.1",                     "RESOLVED", "版本锚点(替代 A24-12 的错误处置)"),
 ("V-2",    "P1", "W954_PLAN_RERANK.md",               "R90",                               "RESOLVED", "方案重排"),
 ("R-M1",   "需复核", "W925_CRITERION_AMDAHL.md",      "-",                                 "DEFERRED", "Amdahl 经验线引文无出处; 结论不依赖它"),
 ("R-M2",   "需复核", "W927_DOT8_Q4K_PORT.md",         "gfx926",                            "DEFERRED", "外部数据不可核, 已降为线索"),
]

lines = ["id\tlevel\tdoc\tmarker\tstatus\tfix\tmd5_asof"]
bad = []
for aid, lv, doc, mk, st, fix in ROWS:
    p = os.path.join(D, doc)
    if not os.path.exists(p):
        bad.append((aid, "doc missing"))
        continue
    s = io.open(p, encoding="utf-8").read()
    if st == "RESOLVED" and mk not in s:
        bad.append((aid, "marker missing: " + mk[:30]))
        continue
    md5 = hashlib.md5(io.open(p, "rb").read()).hexdigest()[:8]
    lines.append("\t".join([aid, lv, doc, mk, st, fix, md5]))

io.open(D + "AUDIT_LEDGER_A24.tsv", "w", encoding="utf-8", newline="").write("\n".join(lines) + "\n")
print("ledger rows:", len(lines) - 1, "| problems:", len(bad))
for b in bad:
    print("  ", b)
