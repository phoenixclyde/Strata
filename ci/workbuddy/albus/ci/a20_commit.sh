#!/usr/bin/env bash
# [W863 R30] Commit the controlled read probe and what it changed.
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

echo "=== 1. document the second probe ==="
python3 - <<'PY'
p = "docs/DOWNSTREAM.md"
s = open(p, encoding="utf-8").read()
marker = "## 两笔已知欠账（AUDIT19）"
add = """## 读模式探针（R30 / W863）

`ci/probe/read_probe.cpp` 回答一个方案里长期没答案的问题：**decode 的读，到底是被带宽卡住、
被并行度卡住、还是被访存宽度卡住**。做法是同字节、单变量：

  * `mode0` 每 34 字节 Q8_0 块发 17 条 2 字节 load（生产内核今天的样子）
  * `mode1` 同样的字节用 16 字节流式 load（LDS 中转的天花板）
  * `S` 把归约维切 S 份：字节数不变，只改块数

实测（gfx906，与生产同驻留）：

| 形状 | S | mode0 | mode1 |
|---|---:|---:|---:|
| HC down 10240->320 | 1 | 553 | 613 |
| | 4 | 621 | 826 |
| | 8 | 494 | 493 |
| GDN 2560->10240 | 1 | 566 | 763 |
| HC up 320->10240 | 1 | 125 | n/a（行 340 B 非 16 倍数） |

结论：split-K 给 +12%（膝盖 S=4），宽读给 +11..35%，**但生产 HC 只有 98 GB/s 而朴素 2 字节读
就有 553** —— 读模式最多解释 1.5 倍，剩下的 5.6 倍在融合内核的其它工作里。所以 R31（宽读）
降级，靶心转 R32（量清那 5.6 倍）。

两个测量陷阱，写在文件头注释里，因为都真的踩过：
  1. 每遍重读同一批行 ⇒ 命中 L2 ⇒ 报出 1.5 TB/s（高于 HBM 屋顶）。改成每遍读**独立副本**。
  2. `if (result == 不可能值) store` 这种保活写法会被优化掉，**连带读一起消失**。改成每块
     都写一个数据相关的结果。

"""
if "## 读模式探针（R30 / W863）" not in s:
    assert s.count(marker) == 1
    s = s.replace(marker, add + marker, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("docs updated")
else:
    print("docs already updated")
PY

echo
echo "=== 2. gate ==="
python3 ci/gate.py --repo . --source-only 2>&1 | tail -3

echo
echo "=== 3. commit + push ==="
git add ci/probe docs/DOWNSTREAM.md
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
perf(decode): measure what actually limits the hyper-connection read

The plan had three candidate explanations for HC reading 644 MiB in 6.89 ms and none of them
had been separated: bandwidth, parallelism (block count), or load width (a 34-byte Q8_0 block
cannot take a 32-bit load, so the kernel issues 17 two-byte loads per block).

ci/probe/read_probe.cpp isolates them. Same bytes, one variable at a time:

  mode0  17 x 2-byte loads per block    (what the kernel does today)
  mode1  16-byte streaming loads        (the ceiling if LDS staging worked)
  S      split the reduction S ways     (bytes constant, only the block count moves)

gfx906, alongside production:
  HC down 10240->320   S=1  553 / 613 GB/s      S=4  621 / 826      S=8  494 / 493
  GDN      2560->10240 S=1  566 / 763
  HC up     320->10240 S=1  125 (row is 340 B, not a multiple of 16 -> no wide read at all)

So split-K buys +12% with a knee at S=4, wide loads buy +11..35%, and the two compose to
+49%. But the number that matters is the comparison nobody had made: production HC runs at
98 GB/s while the crudest 2-byte read of the same bytes runs at 553. Load pattern is worth at
most 1.5x of the gap; the other 5.6x is inside the fused kernel (norm, cross-lane reduction,
LDS round trip, up projection) or in occupancy.

That inverts the previous plan: the wide-load rewrite is demoted, and the next experiment is to
rebuild the probe one step at a time until it becomes the real kernel, measuring the bandwidth
lost at each step.

Two measurement traps are documented in the file, because both were hit: re-reading the same
rows each pass turned the measurement into an L2 test (1.5 TB/s, above the HBM roof), and an
`if (result == impossible) store` keep-alive was optimised away together with the loads.
MSG
git --no-pager log --oneline -1
echo "--- clean? ---"
git status --porcelain --untracked-files=all | wc -l
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2

echo
echo "=== 4. tag ==="
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r5 -m 'MI50 drop r5: controlled read probe (split-K knee at S=4, wide loads +11..35%, and the finding that load pattern explains only 1.5x of the HC gap). Engine binary unchanged.' HEAD
timeout 120 git push origin mi50-0.2.9-r5 2>&1 | tail -1
git describe --exact-match --tags HEAD
