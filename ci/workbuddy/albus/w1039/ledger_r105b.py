import io

P = "deploy/PROGRESS.tsv"
rows = [
    ("B5本机缺口", "P480",
     "这棵树在 gfx906 上**不定义** `STRATA_USE_HIP`（全构建只有 `dflash2.cpp` 一个 TU 有），所以「HIP 但排除 gfx906」那七处是**双死**：第一个合取项已为假，`!GFX906` 是冗余的",
     "W1039", "count", "1", "1", "DONE",
     "**实测（静态，零停机）**：`grep -o \"DSTRATA_USE_HIP[=0-9]*\" build.ninja | uniq -c` → **只有 1 条 `=1`**，且落在 `CMakeFiles/strata_engine.dir/src/core/dflash2.cpp.o`；"
     "`vmm.cpp`/`mtp.cpp`/`verify.cpp`/`generate.cpp`/`prefill.cpp` 的 DEFINES 都只有 `-DSTRATA_HIP_GFX906=1`。"
     "⇒ 结论不是「gfx906 硬件少什么」，而是**构建开关没开**；要动只能逐块，不能整体 `-DSTRATA_USE_HIP=1`（会一次点亮几十条未知路径）。"
     "七处逐条分类已写成 `albus/w1039/GFX906_GATES.md`：**假设**（vmm 已推翻、queue-prime 机制与卡无关）/ **可选开关被编译掉**（MTP 草稿流优先级、拷贝流优先级）/ **不是缺口**（CPU share 默认值，我们显式设了）。"
     "反方向也记了：`verify.cpp:2210` 的 `moe_route_window` 是**专门为 gfx906 写**的整窗 router（bitwise 相同、省 ~3 ms/窗），说明这块是维护过的。",
     "P472;P479", "KW:双死|dflash2|GFX906_GATES"),

    ("B5本机缺口", "P481",
     "把三处**可选开关**从编译期排除里解开：候选 `hipk` = `67ab8836`，三个 env 只在它里面（在产/`kvg` 全是 0），默认行为不变",
     "W1039", "count", "1", "1", "OPEN",
     "**改动**：`core/mtp.cpp:486`（`STRATA_MTP_HIP_PRIO`）、`core/verify.cpp:1213`（`STRATA_COPY_HIP_PRIO`）、`program/generate.cpp:3078`+`:3371`（`prime_hw_queues` 体与调用点），条件从 `STRATA_USE_HIP && !STRATA_HIP_GFX906` 改为 `STRATA_USE_HIP || STRATA_HIP_GFX906`。"
     "**为什么默认不变**：三块都只在显式 env 下进入，且内部还有「仅 gfx12」的默认判据（`gfx_arch_is_gfx12`）；`prime_hw_queues` 默认判据本身就是 gfx1200/1201 + Linux。"
     "**静态证据（判据是「二进制变了」）**：`strings` 计数 —— 在产 `b12180` 与 `kvg`：`MTP_PRIO=0 COPY_PRIO=0 QUEUE_PRIME=0`；`hipk`：**`1 / 1 / 3`**。候选 `67ab88364817d2012b383a762ad1d5c0` / 43,219,064 B（比 `kvg` +4,088 B），BLD=0 / FAILED=0。"
     "**还原纪律**：构建后 `git checkout` 三个文件并重编，`/out` 逐位回到 `a85743d7`（= `kvg`）⇒ 树干净、`kvg` 可复现。**未装机**；三个开关各需一次重启单独测。",
     "P480", "KW:hipk|可选开关|67ab8836"),
]
lines = io.open(P, encoding="utf-8").read().splitlines()
for r in rows:
    assert len(r) == 11
    lines.append("\t".join(r))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended", ", ".join(r[1] for r in rows))

PL = "deploy/W832_OPT_PLAN_V2.md"
p = io.open(PL, encoding="utf-8").read()
p = p.replace("**422 条 / 已结 335 / 79.4%**", "**424 条 / 已结 337 / 79.5%**", 1)
a = "→ **R105（新，`P479`：把 93 处 `STRATA_HIP_GFX906` 分成硬件事实 / 假设 / workaround 三类，零停机、探针法）** "
b = ("→ **R105（进行中，`P479`–`P481`：清单已成 `albus/w1039/GFX906_GATES.md`；根因是这棵树在 gfx906 上**不定义** `STRATA_USE_HIP`（只有 `dflash2.cpp` 有）；"
     "三处可选开关已解开并建候选 `hipk`=`67ab8836`，三个 env 只在它里面，默认不变）** ")
assert a in p
p = p.replace(a, b, 1)
io.open(PL, "w", encoding="utf-8", newline="\n").write(p)
print("plan: denom + R105 state")
