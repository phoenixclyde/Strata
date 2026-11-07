#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: P32 (--kv-grow) REJECTED -> ADOPTED, with the evidence that overturned it.
Rule: change a verdict by ID (grep by ID), never by row number."""
import io, hashlib, os, shutil, time

P = r"D:/workbuddy_space/strata_ws/deploy/params/PARAM_REGISTER.tsv"
S = io.open(P, encoding="utf-8-sig").read()
bak = P + ".bak_w1040_" + time.strftime("%Y%m%d_%H%M%S")
shutil.copy2(P, bak)
lines = S.splitlines()
hdr = lines[0].split("\t")
assert hdr[0] == "id" and len(hdr) == 11, hdr

ADD = ("【W1040 改判 REJECTED->ADOPTED 2026-11-07】原判据的两根支柱都被实测推翻，逐条对上："
       "①『gfx906 无 VMM』是**编译期假设**，不是硬件事实——独立 HIP 探针 `albus/w1039/t_vmm.cu` 在本卡"
       "（gfx906:sramecc+:xnack-，ROCm 10.1 自建）取得 `hipDeviceAttributeVirtualMemoryManagementSupported=1`、"
       "粒度 4096 B，`hipMemAddressReserve`/`hipMemCreate`/`hipMemMap`/`hipMemSetAccess` 各返回 hipSuccess，"
       "两 chunk 同 range 不同偏移各自写读全对，且**unmap+release 一个 chunk 后另一个仍完整**——正是 kv-grow 归还语义；"
       "②『最多 +93 槽』是**算术错**：816 B/cell 是**每层**，全额 = 816×262144×12 层（含 MTP 草稿层实为 **2.65 GiB**，起机日志给出），"
       "不是 214 MiB。"
       "**改法**：`src/core/vmm.cpp:167` 的 `#if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)` 改为 "
       "`(defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906))`（该 TU 的 DEFINES 里根本没有 -DSTRATA_USE_HIP，只有 "
       "-DSTRATA_HIP_GFX906=1，所以第一次只删 `!defined` 编出来 md5 不变的正是同族第四次『改了没在跑』）。"
       "**静态证据**：候选 `strata-0.1.57-kvg` md5 `a85743d7f554159e8ac1e2d432d2e5ea` / 43,214,976 B，`nm -D` 有 "
       "`hipMemAddressReserve`/`hipMemCreate`/`hipMemMap`/`hipMemSetAccess` 各 1，`elastic K/V` 字符串 7 条；在产 `b12180` 同名符号 0 条。"
       "**运行期（W1039 窗口 13:42:01–13:53:16，两次重启各 39 s）**：起机行 `expert cache 8301 slots, 24.23 GiB of VRAM` "
       "（在产 7463 / 21.79 GiB）⇒ **+838 槽（+11.2%）**；`elastic K/V: 16384 of 262144 cells in VRAM (0.21 of 2.65 GiB)`。"
       "**A/B（每点 n=4，两臂各 2 pass，同形状同流程）**：2.5K −1.13%、8K −0.29%、16K −0.20%、20K −0.13%，"
       "每个点都落在该次 run 自己的 2×CV 内（3.45/0.50/0.56/0.19%）；20K 点强制越过 16384 初始映射，请求跑完且日志无 "
       "`could not map`、无 `ERR the K/V could not give its VRAM back` ⇒ 增长与归还都真的执行。"
       "**代价面**：`kvg_trim` 每个请求边界把 K/V 收回本请求长度（`STRATA_KV_GROW_HOLD` 默认关）⇒ 16K 只占 149 MiB、仍让出 2.24 GiB，"
       "只有 ≥128K 才回落。"
       "**判据（装机门）**：目标量是**容量**（槽数是整数、零方差），不是墙钟；墙钟作为**不劣化护栏**，四点全部在带内。"
       "**仍缺**：decode 侧的定量收益（tok/s 跨 run 2×CV 28%，不可判）——只作方向证据（CPU experts 0.64->0.49、VRAM hits 25.28->29.09）。")

VERDICT = ("**采纳（W1040）**：容量收益是确定的 +838 槽 / +11.2%，墙钟四点无一劣化（全部在 2×CV 内）；"
           "decode 增益仍不可判，按方向证据记账，不计入收益。落地形态 = 二进制 `strata-0.1.57-kvg`（`a85743d7`）+ "
           "CLI `--kv-grow`；回滚件 `b12180`（`d24f8293`）仍在 `/data/bin`。"
           "**遗留**：`STRATA_KV_GROW_HOLD=1` 未测（P48，会让长对话把槽钉住）。")

out, hit = [], 0
for ln in lines:
    f = ln.split("\t")
    if f and f[0] == "P32":
        assert len(f) == 11, len(f)
        assert f[5] == "REJECTED", f[5]
        assert f[3] == "(flag)", f[3]
        f[5] = "ADOPTED"
        f[9] = f[9] + " " + ADD
        f[10] = f[10] + " | " + VERDICT
        for x in f:
            assert "\t" not in x and "\n" not in x
        hit += 1
        ln = "\t".join(f)
    out.append(ln)
assert hit == 1, hit
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("P32 -> ADOPTED; backup", os.path.basename(bak))
print("md5", hashlib.md5(io.open(P, "rb").read()).hexdigest())
