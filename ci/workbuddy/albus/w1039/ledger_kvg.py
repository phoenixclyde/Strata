#!/usr/bin/env python3
"""W1039 / R104 ledger: the VMM finding, the silently-dead patch, and the candidate."""
import io

P = "deploy/PROGRESS.tsv"
add = [
    # bucket, id, title, round, scope, count, points, verdict, note, ref, kw
    ("B1参数轴", "P472", "gfx906 的 `--kv-grow` 不是硬件不支持，是**编译期假设**：`vmm.cpp:167` 的 `!defined(STRATA_HIP_GFX906)` 把它关掉，而实现里本来就有运行时属性检查",
     "W1039", "count", "1", "1", "DONE",
     "**实测（零停机、1 s GPU、不动引擎）**：独立 HIP 探针 `albus/w1039/t_vmm.cu` 在本卡（MI50，gfx906:sramecc+:xnack-）上取得 "
     "`hipDeviceAttributeVirtualMemoryManagementSupported = 1`、最小粒度 4096 B；`hipMemAddressReserve`(64 MiB)/`hipMemCreate`/"
     "`hipMemMap`/`hipMemSetAccess` 全部 `hipSuccess`；两个 chunk 分别 map 到同一 range 的不同偏移后各自写读全对；"
     "**把一个 chunk unmap+release 后，另一个 chunk 的数据仍完整可读**（这正是 `--kv-grow` 要的「还给专家缓存」语义）。"
     "源码侧的排除语句自己写着理由：`Everything else (Metal, gfx906, ROCm older than 6): no virtual memory`——那是撰写时的假设，"
     "与本卡实测相反。⇒ **R104 的前提被这一步改写：不是「零代码、一次重启」，而是「先证明 VMM 可用」已经证完，剩下的是一行条件。**",
     "P444;P472-probe", "KW:假设|t_vmm.cu|属性"),
    ("B1参数轴", "P473", "同族第四次：补丁「打上了但没编进去」——gfx906 那个 TU **没有 `-DSTRATA_USE_HIP`**，只去掉 gfx906 排除等于没改",
     "W1039", "count", "1", "1", "DONE",
     "v1 补丁把 `#if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)` 改成 `#if defined(STRATA_USE_HIP)`，"
     "重编 **BLD=0 / FAILED=0 / md5 仍是 `d24f8293`（与 b12180 位相同）**。根因在 `build.ninja`："
     "`DEFINES = ... -DSTRATA_HIP_GFX906=1 ... -D__HIP_PLATFORM_AMD__=1`，**没有 `STRATA_USE_HIP`**"
     "（与 `expert_cache.cpp` 注释「compiles this file as HIP without STRATA_USE_HIP」一致）⇒ 条件为假，stub 又编了一遍。"
     "v2 改成 `(defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906))` 后 md5 变 `a85743d7` / 43,214,976 B。"
     "**判据**：改条件编译类补丁，验证必须是「二进制变了」而不是「编译通过」——本轮靠 `strings|nm -D` 抓出来，代价 2 分钟而不是一个窗口。"
     "与 `P425`/`P441`/`P446` 同族，已是第四次。",
     "P425;P441;P446", "KW:没编进去|STRATA_USE_HIP"),
    ("B1参数轴", "P474", "候选 `strata-0.1.57-kvg`：生产源码树 + 一行 VMM 条件，静态证明 VMM 真进链；预期 +746 专家槽（+10.0%），待窗口",
     "W1039", "count", "1", "1", "OPEN",
     "**构建口径与在产完全一致**：`/src = pr/k10 @ fa8e6761`（= b12180 的源码树）+ vmm 补丁，`/out = build-masterp`，"
     "`/llama.cpp = tmp/w1037/llama-master`；增量 BLD=0 / FAILED=0。"
     "**静态证据（不只是「编过了」）**：新件动态符号表有 `hipMemAddressReserve`/`hipMemCreate`/`hipMemSetAccess`/`hipMemMap` 各 1，"
     "`elastic K/V` 字符串 7 条；在产 `b12180` 同名符号 **0 条**。"
     "**预期收益**：k8v4 全额 2.391 GiB（816 B/cell × 262144 × 12 层），`STRATA_KV_GROW_INIT` 默认 16384 cells ⇒ 起机只 map ≈160 MiB，"
     "让出 ≈2.23 GiB；槽均价 21.79 GiB / 7463 = 2.99 MiB ⇒ **+746 槽 = 7463→≈8209（+10.0%）**。"
     "**尚未验证的**：① 起机实得槽数（要窗口读 `elastic K/V: N of M cells` 那行）；② 20K 请求触发一次增长后是否真的从缓存拿 chunk、且不失败；"
     "③ 长请求期间槽数下降对 decode 的影响（这是 R104 的代价面，必须一起测）。**不装机 = 未完成。**",
     "P472;P473", "KW:8209|kvg|静态证明"),
]

lines = io.open(P, encoding="utf-8").read().splitlines()
assert lines[0].startswith("#")
for row in add:
    assert len(row) == 11, row[1]
    lines.append("\t".join(row))
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("appended", len(add), "rows:", ", ".join(r[1] for r in add))
