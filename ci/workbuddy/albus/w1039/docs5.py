#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039 (4th batch): the device-ISA fact, and what it does to the P461 conclusion."""
import io

ROW = ("B6判定探针", "P463",
       "设备 ISA 打脸「同一段算术」这个前提：`<..,16>` 编成 **7087 条 / 408 个 dwordx2 载入点**，而 `<..,0>` 只有 **886 条 / 1 个**",
       "W1039", "count", "1", "1", "DONE_NEG",
       "**W1039 静态反汇编（零 GPU、零窗口；`.hip_fatbin` 是 clang offload bundle，要先用 "
       "`clang-offload-bundler -unbundle -targets=hip-amdgcn-amd-amdhsa--gfx906` 解出 `code906.o` 再 `llvm-objdump -d`）**。"
       "同一份 pa7 目标文件里五个实例规模："
       "`<3,false,true,true,0>` = **886 条**（dwordx2 载入点 **1**、`ds_read_b128` 24、`s_waitcnt` 94）；"
       "`<..,2>`(int8) = **879 条**（`v_dot4_i32_i8` 24）；`<..,8>`(fp16 dot2) = **824 条**（`v_dot2_f32_f16` 48）；"
       "`<..,32>`(F16Q) = **860 条**；而 `<..,16>`(CTLREAD) = **7087 条**（dwordx2 载入点 **408**、`s_waitcnt` **761**、"
       "`s_mul_i32` 158、`v_mul_lo_u32` 60）。"
       "⇒ 我那条 bit-16 分支（`sq` + 逐字节 `kb[j]` + `qflip`）**让编译器把整个内核展平了约 8 倍**，"
       "所以「它与基线只差 `pp*ks` 与 `(c*sc)*q` 的结合次序（O(1e-7)）」这个前提**不成立**：源码等价不等于生成的代码等价。"
       "**效力**：`P461` 里「C16 证明 OPT 分支读法有问题」这一步**降级为未定**——C16 的 0.041 可能来自展平带来的重排，"
       "而 DP4A / F16D / F16Q 三个臂规模正常（824–879 条）却给出几乎相同的 0.038–0.045，这一致性仍然没被解释。"
       "**下一步（一次臂、约 5 min）**：跑 `ATTN_DPP=1`（bit1，只把 `warp_sum` 换成 DPP 归约、不碰任何算术）——"
       "它在设计上必须与基线逐位相同。若它也给 0.04 ⇒ 「任何 OPT 臂都偏」与开关无关；若它给 0 ⇒ 只有读 K 的臂偏，回到读法。",
       "P461;P460", "KW:7087|展平")

with io.open("deploy/PROGRESS.tsv", "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\t".join(ROW) + "\n")
print("ledger: +P463")

P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
add = """
**九、ISA 把「同一段算术」这个前提打掉了（`P463`）。**

`.hip_fatbin` 是 clang offload bundle，得先 `clang-offload-bundler -unbundle` 再反汇编。同一份 pa7 目标文件：

| 实例 | 指令数 | dwordx2 载入点 | 特征 |
|---|---|---|---|
| `<3,false,true,true,0>` 基线 | **886** | **1** | `ds_read_b128` 24 / `s_waitcnt` 94 |
| `<..,2>` int8 dot4 | 879 | 2 | `v_dot4_i32_i8` 24 |
| `<..,8>` fp16 dot2 | 824 | 1 | `v_dot2_f32_f16` 48 |
| `<..,32>` F16Q | 860 | 1 | — |
| `<..,16>` CTLREAD | **7087** | **408** | `s_waitcnt` 761 |

我那条 bit-16 分支让整内核展平约 8 倍。**⇒「源码等价」不能当作「生成的代码等价」**，
所以 `P461` 用 C16 去证明「OPT 分支读法有问题」这一步**降级为未定**。
同时它还留下一个更硬的一致性事实：DP4A / F16D / F16Q 三个臂规模都正常（824–879 条），却给出 0.0380 / 0.0413 / 0.0448 三个几乎相同的 KL —— 这一致性才是真正要解释的东西。

**判据（下一臂）**：`ATTN_DPP=1`（bit1，只换 `warp_sum` 的实现、不碰算术，设计上必须逐位相同）。
它若也给 0.04 ⇒「任何 OPT 臂都偏」；它若给 0 ⇒ 只有读 K 的臂偏。一次臂约 5 min。
"""
if "ISA 把「同一段算术」这个前提打掉了" not in s:
    io.open(P, "a", encoding="utf-8", newline="\n").write("\n" + add)
    print("plan: appended 九")

M = ".workbuddy/memory/2026-11-07.md"
mem = """
### W1039 收尾：ISA 反汇编（零窗口）把「源码等价」这个借口打掉

- **`.hip_fatbin` 不是 ELF**，是 clang offload bundle：`clang-offload-bundler -list -type=o -input=fat.bin` 看到
  `hip-amdgcn-amd-amdhsa--gfx906`，再 `-unbundle -targets=hip-amdgcn-amd-amdhsa--gfx906` 解出 `code906.o`，然后
  `llvm-objdump -d --mcpu=gfx906` 才看得到设备码（`.o` 上直接 `-d` 只有 50 条 host stub）。
  `--cuda-device-only` 重编那条路走不通：TU 里的 host-only 符号（`__nanosleep` / `gfx_arch_is`）会挡住。
- **规模差 8 倍**：`<3,false,true,true,0>` 886 条 / 1 个 dwordx2 载入点；`<..,16>` **7087 条 / 408 个**；
  `<..,2>` 879、`<..,8>` 824、`<..,32>` 860。⇒ 我那条 bit-16 分支把内核展平了 8 倍，
  「它只是结合次序不同」的前提不成立。**教训：源码等价 ≠ 生成代码等价；验证等价要用 ISA，不是读源码。**
- **仍然没解释的一致事实**：三个规模正常的臂（DP4A / F16D / F16Q）给出 0.0380 / 0.0413 / 0.0448 —— 几乎同一个数。
  下一个判别臂 = `ATTN_DPP=1`（只换归约实现、不碰算术，设计上必须逐位相同），一次臂约 5 min。
- **ssh 内联的坑（第二次踩）**：`docker run ... bash -lc "…$OBJ…"` 经 python→ssh 传递时 `$OBJ` 会被吃成空串；
  一律把命令写成容器内可见的脚本文件再 `bash /w/x.sh`。
"""
s2 = io.open(M, encoding="utf-8").read()
if "ISA 反汇编（零窗口）把" not in s2:
    io.open(M, "a", encoding="utf-8", newline="\n").write(mem)
    print("memory: appended")
