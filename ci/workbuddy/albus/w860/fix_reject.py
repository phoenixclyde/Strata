# -*- coding: utf-8 -*-
"""fix_reject.py -- 让 Tensile 无条件打印解被拒的原因。

为什么需要：config 里的 `PrintSolutionRejectionReason: true` 不会传进 `debugConfig`
（它由命令行/内部构造），于是 `_build_and_validate_solution` 里
`if solutionObject["Valid"] ... elif not silent and debugConfig.printSolutionRejectionReason: print1(...)`
整条不打印，只剩一句 "Actual Solutions: 0 / 1"，无法定位。

改法（两处，都在 BenchmarkProblems.py）：
1. 传给 Solution 的 printRejectionReason 硬置 True；
2. 两个 elif 分支去掉 debugConfig 那个条件，只留 `not silent`。
"""
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else (
    "/src/projects/hipblaslt/tensilelite/Tensile/BenchmarkProblems.py"
)

s = io.open(P, encoding="utf-8").read()

pairs = [
    (
        "                debugConfig.splitGSU,\n                debugConfig.printSolutionRejectionReason,",
        "                debugConfig.splitGSU,\n                True,  # W860 force reject",
    ),
    # print1 被 globalParameters["PrintLevel"] 门控，直接换成 print()
    (
        '                print1("rejecting solution " + str(solution))',
        '                print("W860-REJECT: " + str(solution))',
    ),
    (
        '            print1("rejecting solution " + str(solution))',
        '            print("W860-REJECT: " + str(solution))',
    ),
]

n = 0
for old, new in pairs:
    if new in s:          # 已打过这条
        n += 1
        continue
    if old in s:
        s = s.replace(old, new, 1)
        n += 1

io.open(P, "w", encoding="utf-8").write(s)
print("  BenchmarkProblems patched (%d/%d)" % (n, len(pairs)))
