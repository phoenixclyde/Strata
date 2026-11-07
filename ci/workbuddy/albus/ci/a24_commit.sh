#!/usr/bin/env bash
set -eu
REPO=/home/albus/strata166/pr/strata-fork
cd "$REPO"

echo "=== 1. correct the dp4a claim in docs ==="
python3 - <<'PY'
p = "docs/DOWNSTREAM.md"
s = open(p, encoding="utf-8").read()
old = """代价：激活必须量化成 int8（`gr_quantize_q8_0_kernel` 已有），所以**数值会变**，要过 KL/argmax 门；
而且源码里现成的 dp4a 路径只覆盖 up（`gr_up_q8_q32_kernel`），还被
`#if !STRATA_GR_FAST_BUILD`（`fused_gr.cu:2318`）在 gfx906 上编掉了，down 方向要新写。"""
new = """代价有三条，都不小：

1. **HC 路径里一条 `__dp4a` / `sdot4` 都没有**。全树的 `__dp4a` 只在 DeepSeek 路径
   （`dsv41/ds4_gguf.cu`）真用，其余四处是注释。`gr_up_q8_q32_kernel` 看着像，其实是
   "每 block 拥有一个 q8_1 组"的**量化输出**变体，不是 dp4a 矩阵乘。⇒ **down 和 up 都要新写**。
2. **激活要量化成 int8**，而 upstream 自己量过这个代价：`s2_gemv_q8.cu:9` 写「激活走 int8 与走
   FP16 的输出差 **0.9498% 相对**」，并因此把 dp4a 推到"数值定下来之后"的阶段。数值会变，要过 KL/argmax 门。
3. **HC 全段只占窗口 7.49 ms = 15.9%**（123 张相位表中位），所以 dp4a 的墙钟上限约 **6.1%**。

顺带一个改变了优先级的事实：同一份中位表里 **专家读 11.78 ms = 24.9%，比整个 HC 还大**，
而它的字节从来没算过。所以下一步先建专家读的账（R26），不是先写 dp4a 内核（R35）。"""
if old in s:
    s = s.replace(old, new, 1)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("docs corrected")
else:
    print("docs pattern not found (already corrected?)")
PY

echo
echo "=== 2. gate ==="
python3 ci/gate.py --repo . --source-only 2>&1 | tail -3

echo
echo "=== 3. commit ==="
git add docs/DOWNSTREAM.md
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com commit -q -F - <<'MSG'
docs(decode): the window budget, and a correction about dp4a

Two things the plan had wrong, both caught by looking at more than one phase table.

First, the budget. Every HC number in the plan came from a single table (6.89 ms). Taking the
median of all 123 tables the engine has logged, at 47.22 ms per window:

  expert read   11.78 ms  24.9%   (VRAM hits 8.85 + waitB 1.28 + PCIe 0.81 + copy 0.84)
  HC             7.49 ms  15.9%   (down 3.46 / up 3.44 / norm 0.59)
  router+plan    3.80 ms   8.0%
  q8+qkv gemv    3.24 ms   6.9%

So the largest block in a decode window is the expert read, not the hyper-connection read, and
its byte count has never been worked out. At 400 GB/s, 11.78 ms implies ~4.7 GB per window --
more than the dense weights (4.26 GB). That points at "reading too much" rather than "reading
too slowly", which is a routing/residency question, not a kernel one.

Second, the correction. The previous commit said the dp4a path "exists but is compiled out for
gfx906". It does not exist. There is no __dp4a or sdot4 anywhere in the HC kernels; the four
other hits in the tree are comments, and the one real user is the DeepSeek path. The kernel
whose name suggested otherwise (gr_up_q8_q32_kernel) is a quantise-the-output variant.

And that matters because upstream measured what int8 activations cost: 0.9498% relative
difference against FP16, which is why they deferred dp4a themselves. Add that to writing two new
kernels for 15.9% of the window and the priority order changes: build the expert-read ledger
first, then look at routing, then consider dp4a.
MSG
git --no-pager log --oneline -1
git status --porcelain --untracked-files=all | wc -l
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2

echo
echo "=== 4. tag r8 ==="
git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com tag -a mi50-0.2.9-r8 -m 'MI50 drop r8: median window budget over 123 tables (expert read 24.9% > HC 15.9%) and the dp4a correction. Engine binary unchanged.' HEAD
timeout 120 git push origin mi50-0.2.9-r8 2>&1 | tail -1
git describe --exact-match --tags HEAD
