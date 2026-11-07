#!/usr/bin/env bash
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

echo "=== 1. docs ==="
python3 - <<'PY'
p = "docs/DOWNSTREAM.md"
s = open(p, encoding="utf-8").read()
marker = "两个测量陷阱，写在文件头注释里，因为都真的踩过："
add = """### 第三个模式：dp4a（R35）

`gemv_block_dp4a` 把 32 条 cvt + 32 条 FMA 换成 8 条 `v_dot4_i32_i8`（gfx906 的 Vega 20 有 DL Ops）。
同一份字节：

| 形状 | S=1 只读 | 反量化+FMA | dp4a | 收益 |
|---|---:|---:|---:|---:|
| HC down 10240->320 | 658 | 262 | **454** | +73% |
| GDN 2560->10240 | 630 | 97 | **211** | +117% |
| big 10240->8192 | 665 | 263 | **472** | +79% |

S=1 时 dp4a 到只读的 69%。这就是"每字节 2 条 ALU 降到 0.5 条"的实测值。

代价：激活必须量化成 int8（`gr_quantize_q8_0_kernel` 已有），所以**数值会变**，要过 KL/argmax 门；
而且源码里现成的 dp4a 路径只覆盖 up（`gr_up_q8_q32_kernel`），还被
`#if !STRATA_GR_FAST_BUILD`（`fused_gr.cu:2318`）在 gfx906 上编掉了，down 方向要新写。

### 一条被撤回的结论（R34），留在这里当反面教材

上一版这里写过"生产的 `xs[k][v]` 有 32 路 LDS bank 冲突"。**那是错的**，错在读漏了一行：

    const int sub = lane & 7, bl = lane >> 3;
    const int v = 32 * (4 * s + bl) + 4 * sub;

按这个索引，b128 读分的每个相位（8 条 lane）起始 bank 是 0/4/8/.../28，正好 32 个 bank 全覆盖——零冲突。
我当时依据的是探针里自己编的 `xs[32*lane + i]`：lane 步长 128 B，恰好是 32 bank x 4 B，全撞一列。
**教训**：把一个内核的结论搬到另一个内核之前，先把对方的索引算式写出来、算一遍 bank。

"""
if "第三个模式：dp4a" not in s:
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
perf(decode): dp4a is worth 73-117% on the arithmetic-bound read, and a retracted bank-conflict claim

Two things, one probe.

First, the measured one. The previous round showed dequant + FMA costing 2.5-6x against a pure
read of the same bytes, so the per-byte arithmetic is the wall. gfx906 has v_dot4_i32_i8, so the
probe gained a mode that keeps the loads identical and swaps 32 converts + 32 FMAs for 8 dp4a:

  HC down 10240->320  S=1   read 658   dequant+FMA 262   dp4a 454 GB/s   (+73%)
  GDN     2560->10240 S=1   read 630   dequant+FMA  97   dp4a 211         (+117%)
  big     10240->8192 S=1   read 665   dequant+FMA 263   dp4a 472         (+79%)

At S=1 dp4a reaches 69% of the pure-read number. That is the whole case for it: 2 ALU ops per
byte down to about 0.5. The cost is that activations must be int8 as well, which changes the
numerics and therefore has to pass the decode gate; and the only dp4a path already in the tree
covers "up" alone, compiled out for gfx906 by `#if !STRATA_GR_FAST_BUILD`.

Second, the retraction. The previous commit claimed the production xs[k][v] read suffers a 32-way
LDS bank conflict. It does not. I had read `v = 32*(4*s + bl) + 4*sub` but not the line above it:
`sub = lane & 7, bl = lane >> 3`. With those, a b128 read splits into phases of eight lanes whose
start banks are 0/4/8/.../28 -- all 32 banks, no conflict. The 36-76% that padding "recovered" was
recovering a pathology I had invented in the probe itself (`xs[32*lane + i]`, a 128-byte lane
stride, exactly 32 banks).

Lesson recorded in the plan as rule 2c: before carrying a kernel's conclusion to another kernel,
write out the index arithmetic and count the banks.
MSG
git --no-pager log --oneline -1
git status --porcelain --untracked-files=all | wc -l
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2

echo
echo "=== 4. tag r7 ==="
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r7 -m 'MI50 drop r7: dp4a measured +73..117% on the arithmetic-bound decode read; the LDS bank-conflict claim withdrawn (production reads are conflict free). Engine binary unchanged.' HEAD
timeout 120 git push origin mi50-0.2.9-r7 2>&1 | tail -1
git describe --exact-match --tags HEAD
