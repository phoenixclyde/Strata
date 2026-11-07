#!/usr/bin/env bash
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

echo "=== 1. docs ==="
python3 - <<'PY'
p = "docs/DOWNSTREAM.md"
s = open(p, encoding="utf-8").read()
marker = "两个测量陷阱，写在文件头注释里，因为都真的踩过："
add = """### 后来补的两个模式（R32/R33）

`gemv` 把真实内核的算术加回来（Q8 反量化 + FMA，激活在 LDS），`pad` 只把 per-lane 步长从 32 float
改成 33（消 LDS bank 冲突）。同一批字节：

| 模式 | HC down 10240->320 (S=1) | GDN 2560->10240 (S=1) | big 85 MiB (S=1) |
|---|---:|---:|---:|
| read（只读） | 581 | 631 | 666 |
| wide（16 B） | 636 | 708 | 800 |
| gemv（+反量化+FMA） | 255 | 98 | 264 |
| pad（+33 步长） | 348 | 173 | 353 |

结论：**贵的是每字节约 2 条 ALU（32 cvt + 32 FMA / 32 字节），不是读**；宽读只在纯读时有用。
LDS 填充再回 36..76%。生产 HC 的 98 GB/s 与探针 gemv 的 98 吻合。

同一个探针也量到占用率（从生产汇编取 VGPR）：down T=2 用 119 VGPR = 25% 占用率，
T=3 涨到 140 越过后 128 的线 = 12.5%，**腰斩**；`_fast_` 变体只在 T=3 有用，T=2 无收益且 up 更差
（50% vs 62.5%），所以 `STRATA_TSUM=1` 不该开。

"""
if "后来补的两个模式" not in s:
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
echo "=== 3. commit ==="
git add ci/probe docs/DOWNSTREAM.md
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
perf(decode): the hyper-connection read is not bandwidth bound, it is arithmetic bound

The previous probe showed a pure read of the HC tensors running at 581-666 GB/s while production
manages 98, so the load pattern could explain at most 1.5x of the gap. Adding the arithmetic
closes the accounting.

Two more modes, same bytes, one variable at a time:
  gemv  the same 17 x 2-byte loads, then Q8 dequantise and FMA against an LDS activation tile
  pad   identical to gemv except the per-lane activation stride is 33 floats instead of 32

  HC down 10240->320  S=1   read 581   wide 636   gemv 255   pad 348 GB/s
  GDN     2560->10240 S=1   read 631   wide 708   gemv  98   pad 173
  big     10240->8192 S=1   read 666   wide 800   gemv 264   pad 353

So: dequantise + FMA costs 2.5-6x, and it reproduces production (98) exactly. Widening the load
only helps when there is no arithmetic (708 -> 98 at S=1). The kernel moves 32 bytes per Q8_0
block and spends 32 converts plus 32 FMAs on them -- about 2 ALU ops per byte -- and that, not
HBM, is the wall.

The second finding is a bank conflict. A per-lane stride of 32 floats puts every lane in the same
LDS bank; padding to 33 recovers 36-76%. The production kernel indexes xs[k][v] with
v = 32*(4s+bl) + 4*sub, so v mod 32 = (4*sub) mod 32 is independent of the lane -- the same
pathology. Changing that is a candidate that keeps the summation order, so it can be held to
diff = 0.

Occupancy, taken from the shipped device assembly rather than guessed: the down kernel uses 119
VGPRs at T=2 (25% occupancy) and 140 at T=3, which crosses the 128 line and halves occupancy to
12.5%. The _fast_ variant exists to stay at 128 and only helps at T=3; at T=2 it changes nothing
for down and costs up 12.5 points (62.5 -> 50), so STRATA_TSUM=1 is not a win here.
MSG
git --no-pager log --oneline -1
git status --porcelain --untracked-files=all | wc -l
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2

echo
echo "=== 4. tag r6 ==="
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r6 -m 'MI50 drop r6: decode cost accounting settled -- dequant+FMA is the wall, bank conflicts are second, load width only matters without arithmetic. Engine binary unchanged.' HEAD
timeout 120 git push origin mi50-0.2.9-r6 2>&1 | tail -1
git describe --exact-match --tags HEAD
