import io

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()

block = """
---

### 回写 · W1039 §十五（`R105`：gfx906 的能力缺口，一半是构建开关）

- **根因（静态实测）**：这棵树在 gfx906 上**不定义** `STRATA_USE_HIP`——全 `build.ninja` 只有 1 条 `-DSTRATA_USE_HIP=1`，落在 `dflash2.cpp`。其余 TU 只有 `-DSTRATA_HIP_GFX906=1`。所以 `STRATA_USE_HIP && !STRATA_HIP_GFX906` 这类条件在本构建里是**双死**，`!GFX906` 半句冗余（`P473` 的「编了个寂寞」即此）。
- **七处分类**（全文 `albus/w1039/GFX906_GATES.md`）：**假设** = `vmm.cpp`（已推翻，候选 `kvg`）、`generate.cpp` 的 `prime_hw_queues`（机制与卡无关）；**可选开关被编译掉** = `STRATA_MTP_HIP_PRIO`、`STRATA_COPY_HIP_PRIO`；**不是缺口** = CPU share 默认值（我们显式设 env）、`verify.cpp:4` 的头。
- **反方向**：`verify.cpp:2210 moe_route_window` 是专门为 gfx906 写的整窗 router（bitwise 相同、省 ~3 ms/窗）⇒ 这块维护过，「gfx906 落后」不能当默认假设。
- **候选 `hipk`（`P481`）**：三处可选开关解开，`67ab88364817d2012b383a762ad1d5c0` / 43,219,064 B；`strings` 计数 `MTP_PRIO/COPY_PRIO/QUEUE_PRIME` 在产与 `kvg` 为 `0/0/0`、`hipk` 为 `1/1/3`；默认行为不变（三块都 env-gated，内部还有「仅 gfx12」判据）。**未装机。**
- **判据纪律**：条件编译类改动一律「`strings`/`nm -D` 证明二进制变了」+「`git checkout` 后重编证明可复现」（本轮 `/out` 回到 `a85743d7`）。
- **顺序**：先测 `kvg`（+767 槽 @16K）→ 再单测 `STRATA_HIP_QUEUE_PRIME=nn`（可能解释「重启后首请求偏慢」）→ 再 `MTP_HIP_PRIO` / `COPY_HIP_PRIO`（decode 侧判据）。
"""

anchor = "### 回写 · W1039 §十四（R104：`--kv-grow` 的前置条件被实测改写）"
assert anchor in p
# append the new block at the end of the file (the §6.5 sections are sequential)
if not p.endswith("\n"):
    p += "\n"
p += block

# the §6.5.0 directory row
L = p.splitlines()
d0 = next(i for i, l in enumerate(L) if l.startswith("### 6.5.0"))
d1 = next((i for i in range(d0 + 1, len(L)) if L[i].startswith("> **【AUDIT27 更正")), len(L))
last = max(i for i in range(d0, d1) if L[i].startswith("| 回写"))
row = ("| 回写 · W1039 §十五（R105：gfx906 的能力缺口一半是构建开关） | 全构建只有 dflash2.cpp 定义 STRATA_USE_HIP；"
       "七处分类成清单，三处可选开关解开建 hipk（默认不变） |")
L.insert(last + 1, row)
io.open(PL, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("plan: 回写 §十五 + directory row")

M = ".workbuddy/memory/2026-11-07.md"
add = """
### W1039 / R105（13:3x）gfx906 的能力缺口一半是构建开关

- **根因**：这棵树在 gfx906 上**不定义** `STRATA_USE_HIP` —— 全 `build.ninja` 只有 1 条 `-DSTRATA_USE_HIP=1`，落在 `dflash2.cpp`。其余只有 `-DSTRATA_HIP_GFX906=1`。所以 `STRATA_USE_HIP && !STRATA_HIP_GFX906` 是**双死**（`P473` 的「编了个寂寞」即此）。
- **七处分类**：假设 = `vmm.cpp`（已推翻，候选 kvg）、`generate.cpp` 的 `prime_hw_queues`（机制与卡无关）；可选开关被编译掉 = `STRATA_MTP_HIP_PRIO` / `STRATA_COPY_HIP_PRIO`；不是缺口 = CPU share 默认值、`verify.cpp:4`。清单 `albus/w1039/GFX906_GATES.md`。
- **反方向**：`verify.cpp:2210 moe_route_window` 是专门为 gfx906 写的整窗 router（bitwise、省 ~3 ms/窗）⇒ 这块维护过。
- **候选 `hipk`** = `67ab8836` / 43,219,064 B：三处可选开关解开；`strings` 计数 `MTP_PRIO/COPY_PRIO/QUEUE_PRIME` = `1/1/3`（在产与 kvg 全 0）；默认行为不变。未装机。
- **纪律**：条件编译改动必须 `strings`/`nm -D` 证明二进制变了，再 `git checkout` 重编证明可复现（本轮 `/out` 回到 `a85743d7`）。
- vmm 补丁已提交 `af797b90`，`kvg` 进 `REBUILD_RECIPE.tsv`（`--live` PASS）。
"""
io.open(M, "a", encoding="utf-8", newline="\n").write(add)
print("memory appended")
