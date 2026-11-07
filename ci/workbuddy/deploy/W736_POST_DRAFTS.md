# W736 待发布文本（评论 x4 + 新 issue x2）---- 可直接粘贴

> 背景：三个 PR 分支已推好（见 `W736_PR_CANDIDATES.md` §7），但**创建 PR / 发评论 / 开 issue
> 需要 GitHub API 凭据**，而 166 与本机都没有可用的 token（本机 git 走的是 Git Credential Manager，
> `git credential fill` 会起交互流程，已停手）。下面是全部现成文本，粘贴即可。
> 每段都只用了**我们自己的实测**，不引用任何第三方数字作为自己的结论。

---

## 1 评论 -> #1595（V100：默认无收益、1,000 token 慢 ~4.8%）

```
Matches what we see on AMD. There the default is on for a structural
reason: the gfx906 compat build compiles as HIP *without* STRATA_USE_HIP,
so the guard at src/prefill/prefill.cpp:1839 (#if !defined(STRATA_USE_HIP))
does not exclude it - src/core/expert_cache.cpp:5-6 states that build has
no STRATA_USE_HIP, and guards the same question with
#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906).

One MI50 32 GB (gfx906), CLI generate, 4-token prompt, one binary with
one set of weights and one config, only the environment differing:

  default  on the CPU 197 (share 0.90)   prefill 928.3 ms
  =0       on the CPU 0 (share 0.00)     prefill 929.5 ms

Output token ids identical, so 0.13%, inside our run-to-run spread - the
same shape as your 1,000-token case: the share engages and buys nothing.
One-line fix for the AMD side: add && !defined(STRATA_HIP_GFX906) at
prefill.cpp:1839.
```

## 2 评论 -> #1729（RTX 5090 D：解码 110 -> 46 tok/s）

```
This one is CUDA, so the AMD build's guard bug does not explain it; posting
the AMD side for completeness because it is the same feature and a
different mechanism.

On gfx906 the CPU share is on by default because that build never defines
STRATA_USE_HIP (see src/core/expert_cache.cpp:5-6), so prefill.cpp:1839
takes the CUDA branch. Measured on one MI50 32 GB, CLI generate, 4-token
prompt, two arms, identical output:

  default  experts streamed 309 (295 by DMA, host 174.0 ms), resident 607,
           on the CPU 197 (share 0.90)   prefill 928.3 ms
  =0       experts streamed 506 (492 by DMA, host 177.3 ms), resident 606,
           on the CPU 0 (share 0.00)     prefill 929.5 ms

We only measured prompt time here, so we cannot say anything about decode
on gfx906 either way - if it helps, we can run your 3-round protocol on
that box and report decode as well.
```

## 3 评论 -> #1479（HIP 门硬关）

```
The mirror image of this one: while head_mix_multi_enabled() and
one_token_self_commit() are hard-off on HIP, Prefill::arm_cpu_share() is
hard-*on* there for the same underlying reason - the gfx906 compat build
does not define STRATA_USE_HIP, so its #if !defined(STRATA_USE_HIP) at
src/prefill/prefill.cpp:1839 takes the CUDA branch and arms the CPU share
by default (and prints the banner).

src/core/expert_cache.cpp:5-6 states that build explicitly, and guards the
same question with #if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906);
seven other sites use that form. Worth folding into the gate audit you are
doing here: the failure mode is not only "cannot opt in", it is also
"something AMD was never meant to get is on by default". Measured effect on
a 4-token prompt: 197 experts on the CPU, 928.3 vs 929.5 ms (0.13%), output
token ids identical.
```

## 4 评论 -> #1670（layer-major prefill，作者已放分支）

```
Data point from a very different box, in case it helps decide where this
pays. On one MI50 32 GB (gfx906) in a Gen3 x16 slot, prompt reading is not
PCIe-bound: the engine streams 1.83 distinct experts per layer and moves
roughly 0.5-1.2 GB/s against a 15.75 GB/s link (about 7%), and the experts
it needs are mostly already resident. So the S/512 re-read reduction you
measured on a 6 GB card may translate to much less here, where the file
tier is not the bottleneck.

If a third data point is useful, we can run your branch on that box - note
it is a HIP/gfx906 build, so STRATA_PREFILL_LAYER_MAJOR would have to
compile there first.
```

## 5 新 issue（C2）：PCIe 吞吐字段的口径问题

**标题**

```
Monitor: the PCIe tile asks for pcie_rx_mb, but amdgpu only exposes a total
```

**正文**

```
serve/telemetry.py fills five PCIe readings from NVML (_Nvml.read():
pcie_gen, pcie_gen_max, pcie_width, pcie_rx_mb, pcie_tx_mb) while
_Amd.read() reports none of them, so on Linux the Monitor's PCIe tile is
empty for AMD cards. The link half of that is unambiguous and we have a
patch for it (the narrowest hop between the root port and the card).

The rate half is the question. amdgpu exposes one file, pcie_bw, as three
integers: messages received, posted requests sent, and the maximum payload
size. The kernel documents those three values and calls the product an
estimate; measured on an MI50 32 GB, idle reads (50, 0, 256) and a long
prompt read (4571, 4709165, 256) - and the two counters differ by three
orders of magnitude, because a card pulling experts over PCIe posts the
requests and receives the completions.

_Nvml's pcie_rx_mb is receive-only bytes. So filling that name from
pcie_bw would put a combined figure (or a request count times payload)
under a label that says one direction, and the tile's own subtitle says
"to GPU X MB/s".

What would you prefer: fill pcie_rx_mb from the received counter alone,
add a separate combined field, or change the tile's wording so the number
is not directional? We can do any of them, but we did not want to guess.
```

## 6 新 issue（D）：AMD 型号串来自 FRU，可能与实物不符

**标题**

```
Monitor: the AMD GPU name is the board's FRU string and can disagree with
the memory that is fitted
```

**正文**

```
_Amd.name() returns amdgpu's product_name sysfs file, which the kernel
documents as "the product name as returned from the FRU". On our board
that string is "Radeon Instinct MI50 16GB" while the card is a 32 GB part:
PCI ID 1002:66a1, lspci's own name for it, and mem_info_vram_total
(34,342,961,152 B = 31.98 GiB) all say 32 GB, and the Monitor's VRAM tile
correctly shows "/ 32 GB" right next to a name that says 16GB.

The FRU is board data, so this is not a driver or a Strata bug - but the
dashboard ends up contradicting itself. Would you take a consistency rule
in name(): if the name contains a capacity and mem_info_vram_total
disagrees once rounded, report the memory figure; leave names without a
capacity untouched? That is a few lines and cannot affect a board whose
FRU is right (the 16 GB MI50, Radeon Pro VII and MI60 keep their own
strings).
```

---

## 7 三个 PR 的正文

单 commit 的 PR，GitHub 会**自动用 commit message 填正文** ---- 不用手打。若你想另附说明，
正文要点已在各分支的 commit message 里（含 `Hardware the numbers come from:` 段与两臂数据）。
