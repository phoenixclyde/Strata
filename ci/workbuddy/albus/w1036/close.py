#!/usr/bin/env python3
"""W1036 收工：写报告 / 加账本行 / 写方案回写块 / 追加当日记忆。

build 结果从 166 的 /home/albus/strata166/build-port2/_build.log 现取（不猜、不写死）。
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REP = os.path.join(ROOT, "albus", "w1036", "reply.md")
PROG = os.path.join(ROOT, "deploy", "PROGRESS.tsv")
PLAN = os.path.join(ROOT, "deploy", "W832_OPT_PLAN_V2.md")
MEM = os.path.join(ROOT, ".workbuddy", "memory", "2026-11-07.md")

LOG = "/home/albus/strata166/build-port2/_build.log"


def ssh(cmd, timeout=60):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "192.168.50.166", cmd],
                       capture_output=True, timeout=timeout)
    return r.stdout.decode("utf-8", "replace")


def build_state():
    out = ssh("tail -6 %s; echo ---; grep -c 'Building HIP' %s; echo ---; "
              "ls -la /home/albus/strata166/build-port2/strata 2>/dev/null" % (LOG, LOG))
    rc = "unknown"
    for line in out.splitlines():
        if line.startswith("RC="):
            rc = line.strip()
    el = ""
    for line in out.splitlines():
        if line.startswith("real"):
            el = line.strip()
    recompiled = 0
    for line in out.splitlines():
        if line.strip().isdigit():
            recompiled = int(line.strip())
    size = ""
    for line in out.splitlines():
        if "/strata" in line and "strata-" not in line:
            size = line.strip()
    return rc, el, recompiled, size


def row(rid, block, item, kind, status, note, ref, kw):
    return "\t".join([block, rid, item, "W1036", kind, "1", "1", status, note, ref, "KW:" + kw])


def main():
    rc, el, recompiled, size = build_state()

    body = f"""# W1036 报告 · gfx906 全量移植（A0 + A1 + A2/A3 + A5 + B1/B2，一分支一编译，逐项开关）

**一、生产容器（10 字段）**

| # | 字段 | 值（2026-11-07 05:3x–06:1x 只读） |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · `ulimits.memlock=-1:-1` |
| 2 | 运行中引擎 | `strata-0.1.57-001` · md5 `5e63174dbd7cc04e5fa1b5fc455b2a73` · 42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43` · `exe=/data/bin/strata-0.1.57-001` · args 37 / env 9 |
| 3a | args（19 flag） | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env（9） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `MAX=3072` `STRATA_ROCBLAS_TUNING` `GFX906_TUNED` `CKPT_MOVE_PARK` `DECODE_TIMING` `SPEC_DEPTH` `PREFILL_TIMING` |
| 4 | 健康 | `/health` ok · `running` · 本轮**无重启**（只编译，不装机） |
| 5 | 资源隔离 | 引擎 `VmLck 0` / `Locked 0.0 GiB` · `ulimit -l` unlimited |
| 6 | 显存布局 | expert cache 7463 / 21.79 GiB · VRAM free 736,862,208 B |
| 7 | 回滚件 | 40 个引擎二进制品；本轮候选件在 `build-port2/strata`，**未进 `/data/bin`** |
| 8 | 本轮改动 | 生产 **0 次装机**、引擎 **无净变更**；改动全部在新分支 `gfx906/port-all`（commit `79516b21`） |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323-0000000 · clang 24.0.0git |
| 10 | llama.cpp | b11062 · `3cf03257f219afbe7334045ff7c6a06ac68c627d`（记录值） |

**二、主线** — `gfx906/mi50` @ `e181bda5` 未动；新分支 `gfx906/port-all` 从它拉出，1 个提交 `79516b21`（4 个文件）。**未推送、未合主线**；166 生产工作树仍 `gfx906/mi50`、脏 0 行，编译走独立 worktree `pr/port-all` + 独立构建目录 `build-port2`。

**三、本次落生产** — 引擎无净变更；**重启 0 次、停机 0 分钟、回滚 0 次**。只做「新建分支 + 改 4 个文件 + 在镜像内编译」，**没有把任何二进制装进 `/data/bin`，也没有起过候选引擎**。

**四、进度** — 358 条 / 已结 276 / 77.1%（本轮 +2：`P419` `P420`）；队列 `~~R51~~`(DONE_NEG) → **`R95`（暂不结案，按机主 05:3x 指示保留）** → `R94` → `R91` → `R89` → `R46` → `R49` → `R50`。

---

## 正文

**1. 移植的对象不是「优化清单」，而是一个被清单漏掉的缺陷：`dp4a` 在 gfx906 上一直是软件模拟（A0）。**
`include/strata/hip_compat/intrinsics.hpp` 的 `dp4a()` 只给 gfx1010–1012 / gfx1030–1032 / gfx11–12 开了硬件分支，**gfx906 落到 portable 循环**。用 `--cuda-device-only -S` 编真实头文件看 ISA：

| 版本 | `dp4a()` 的一条调用编译成什么 |
|---|---|
| 移植前 | **28 条**（6 `v_cmp` + 6 `v_cndmask` + 6 `v_or` + 3 `v_mad_i32_i24` + `v_mul_i32_i24` + 2 `v_perm` + …） |
| 移植后 | **1 条 `v_dot4_i32_i8`** |

关键点：**LLVM 不会把这个循环折回指令**（我先用「强制转换写法的等价循环」试过，那种会被折；生产头文件用的是 `value < 0x80 ? value : value - 0x100` 的 select 写法，折不了）。影响面是**全树已有的 dp4a 站点**：`native_mmvq.cu` 45 处、`iq_kernels.cu`、`s2_expert_grouped.cu`、`dflash2.cu`、`q36_kernels.cuh`。语义完全一致（同样是有符号字节积、同样 mod 2³² 累加）⇒ **逐位相同**，属 G1。

**2. 为什么这条比清单里的 B1/B2 更要紧。** 清单说「decode 的 dp4a 已密布，这一侧不用动」，于是把 B1/B2 设计成「把分数相位也换成 dp4a」。但在 A0 之前，**新增一个 dp4a 站点 = 把 16 条 FP 指令换成 28 条整数指令**，B1/B2 会直接变成负收益，然后把原因错误地归到"相位不是 ALU-bound"。⇒ **A0 是 B1/B2 的前置条件，不是并列项。**

**3. 一个把清单锚点打掉的核查：B2 的落点在 gfx906 上根本不编译。**
清单写「B2 = prefill 分数 dp4a，落点 `qsa_pattn.cu:141-172`」。实测该文件第 25–30 行：

```
#if !defined(__HIPCC__) && defined(STRATA_EXPERIMENTAL_SM60)
#define STRATA_PATTN_BUILT 1
#else
#define STRATA_PATTN_BUILT 0        // ← HIP/gfx906 走这里，整个文件不编译
```

而 gfx906 的 prompt attention 真实路径是 `qsa_prompt_attn`（tensor-core 版，`prompt_attn_imma_default(HIP)=false` 拒绝）回退到 **`qsa_decode_attn_batch` ⇒ `attn_chunk_kernel`**。⇒ **B1 与 B2 是同一段代码**（`_step` 与 `_batch` 同一 `attn_chunk_body`），不是两个文件。这一条改变了移植形态：改一处，prefill 与 decode 都覆盖，靠**两个独立开关**分开测。

**4. 移植形态：一个二进制、每个移植项一个开关、一次编译逐项测。**
机主要求「一次性都移植完，再一个个测」。为了不出现「改一个编一次」的十次编译，我把 A2/A3/B1/B2 做成 `attn_chunk_kernel` 上的一个 `int OPT` 位掩码：

| 位 | 项 | 开关（env） |
|---|---|---|
| 0 | A3 归约换 DPP（分数求和 + chunk softmax） | `STRATA_GFX906_ATTN_DPP=1` |
| 1 | B1/B2 分数换 `v_dot4`（q 按 64 组量化成 int8） | `STRATA_GFX906_ATTN_DP4A=1` |
| 2 | A2 sq/sp 的 LDS 加 pad（列式读不再撞同一 bank 组） | `STRATA_GFX906_ATTN_LDS_PAD=1` |

另两项独立成开关：`STRATA_GFX906_ROUTE_DPP=1`（A1，router 三处归约 + top-k 交换）、`STRATA_GFX906_Q8_GATHER8=1`（A5，8-wide gather）。**任一位被打开时内核走「朴素版 + 该优化」**（不带 query swizzle / reduce12），因此每项的对照必须是同一条朴素基线，这一点写进了代码注释，避免将来把 swizzle 的收益算到 dp4a 头上。

**5. 逐项的可判定性（写清楚，否则测了也说不清）。**
A0 / A1 / A3 / A5 都是**逐位不变**（同样的操作数对、同样的顺序，只是换了交换指令或执行宽度）⇒ **G1**。A2 只改声明与索引、不动算法 ⇒ **G1**。B1/B2 引入 q 的 int8 量化（K 本来就是 int8，不新增误差；q 按 64 维组内最大缩放到 ±127，组内相对误差 ~1/254）⇒ **G2**（KL ≤0.001 且 argmax 全同）。

**6. 编译与验证状态（现取，不写死）。**
构建目录 `build-port2`（从生产 `build-r28` 复制，禁用 `RERUN_CMAKE`/`VERIFY_GLOBS` 两条重生成边——`ci/build.sh` 早就记过 ninja 会因 glob 校验去重跑 CMake 然后死掉；我这次先把「重跑 CMake」这条路堵掉，再挂上 `llama.cpp`，才编得动）。日志尾：`{rc}` · `{el}` · 重编 HIP 单元 **{recompiled}** 个 · 产物 `{size}`。

**7. 交付与复现。** 分支 `phoenixclyde/Strata @ gfx906/port-all`，commit `79516b21`，4 个文件：`include/strata/hip_compat/intrinsics.hpp`、`src/kernels/cuda/native_router.cu`、`src/kernels/cuda/kv_q8.cu`、`src/kernels/cuda/qsa_decode_attn.cu`。本地留证：`albus/w1036/src/`（改动后全文）、`albus/w1036/dot_real.cpp`（A0 的 ISA 探针）、`albus/w1036/isa_check.sh`（一次跑出 `dot4/dpp/bpermute` 三个计数：qsa 侧 `dot4=48 dpp=140`，router 侧 `dpp=325`）。

**8. 本轮明确没做的三件（不装成"已移植"）。**
① **B3（HC dp4a）**：`gr_q8_tail()` 产出的 q8_1 镜像只在 `STRATA_QFUSE=1` 下存在，直接做等于要新建一条激活量化路径 + 新增误差源 ⇒ 必须先决定 QFUSE 是否常开，否则是两件事混一件。
② **C1（V half2 累加）**：把 V 侧改成 fp16 累加会引入**新的精度来源**（不是换指令，是换累加精度），清单自评「取决于 V 相位占比」，而 2.5K 定长测里 V 相位没有单列 ⇒ 先补测占比再决定。
③ **A4（逐文件 max-ilp）**：属构建期 flag，不是源码；要做需要改 CMakeLists（清单也承认「不在仓库 CMake」），单独一车。
"""

    io.open(REP, "w", encoding="utf-8", newline="\n").write(body)
    print("reply.md", len(body), "chars")

    # ---- ledger
    lines = io.open(PROG, encoding="utf-8").read().rstrip("\n").split("\n")
    ids = {l.split("\t")[1] for l in lines if l.count("\t") > 5}
    add = []
    if "P419" not in ids:
        add.append(row("P419", "B8工程",
                       "dp4a 在 gfx906 上一直是软件模拟：hip_compat 的 dp4a() 只给 gfx10/11/12 硬件分支，"
                       "gfx906 落 portable 循环且后端不折回（实测 28 条指令 vs 1 条 v_dot4_i32_i8）；"
                       "补 gfx906 分支后全树 dp4a 站点（MMVQ 45 处 / iq_kernels / s2 / dflash2）逐位不变地提速",
                       "count", "DONE",
                       "ISA 实证：--cuda-device-only -S 编真实头文件，移植前 6 v_cmp + 6 v_cndmask + 6 v_or + "
                       "3 v_mad_i32_i24 + v_perm；移植后 1 条 v_dot4_i32_i8。语法同构（有符号字节积、mod 2^32）"
                       "=> G1 逐位。**这条是 B1/B2 的前置：不修它，新增 dp4a 站点反而更慢**",
                       "P420",
                       "软件模拟|v_dot4_i32_i8|hip_compat"))
    if "P420" not in ids:
        add.append(row("P420", "B8工程",
                       "gfx906 全量移植分支 gfx906/port-all（commit 79516b21）：A0+A1+A2+A3+A5+B1+B2 一次装进"
                       "一个二进制，每项一个开关，逐项可 A/B；顺带更正清单 B2 落点（qsa_pattn.cu 在 HIP 不编译）",
                       "count", "DONE",
                       "开关：ROUTE_DPP / Q8_GATHER8 / ATTN_DPP / ATTN_DP4A / ATTN_LDS_PAD；OPT 位掩码 0/1/2/4。"
                       "B2 真实落点 = qsa_decode_attn.cu 的 attn_chunk_body（与 B1 同一段），非 qsa_pattn.cu"
                       "（该文件 STRATA_PATTN_BUILT=0 on HIP）。未装机、未起候选引擎",
                       "P419",
                       "port-all|OPT 位掩码|qsa_pattn 不编译"))
    if add:
        io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines + add) + "\n")
        print("ledger +%d" % len(add))
    else:
        print("ledger already has P419/P420")

    # ---- plan writeback
    plan = io.open(PLAN, encoding="utf-8").read()
    if "### 回写 · W1036" not in plan:
        blk = """
### 回写 · W1036（gfx906 全量移植：A0 dp4a 是前置；清单 B2 落点更正；一分支一编译逐项开关）

**一、A0（清单里没有的一条，但是 B1/B2 的前置）**：`include/strata/hip_compat/intrinsics.hpp` 的 `dp4a()`
只给 gfx1010–1012/gfx1030–1032/gfx11–12 硬件分支，**gfx906 落 portable 循环**，且 gfx906 后端**不折回**
指令（实测 28 条 → 1 条 `v_dot4_i32_i8`）。全树现存 dp4a 站点（`native_mmvq.cu` 45 处、`iq_kernels.cu`、
`s2_expert_grouped.cu`、`dflash2.cu`、`q36_kernels.cuh`）因此一直在跑模拟；补 gfx906 分支后**逐位不变**（G1）。

**二、清单 B2 的落点错了**：`qsa_pattn.cu` 在 HIP 下 `STRATA_PATTN_BUILT=0`（第 25–30 行），**整个文件不编译**；
gfx906 的 prompt attention 走 `qsa_prompt_attn`（HIP 拒绝）→ `qsa_decode_attn_batch` → `attn_chunk_kernel`。
⇒ **B1 与 B2 是同一段代码**，不是两个文件；一处改动同时覆盖 prefill 与 decode，靠两个 env 分开测。

**三、移植形态**：分支 `gfx906/port-all`（commit `79516b21`）。`attn_chunk_kernel` 加一个 `int OPT` 位掩码
（bit0 = A3 DPP，bit1 = B1/B2 dp4a，bit2 = A2 LDS pad），另加 `STRATA_GFX906_ROUTE_DPP`（A1）与
`STRATA_GFX906_Q8_GATHER8`（A5）。**任一位打开时走「朴素内核 + 该优化」**，所以每项的对照是同一朴素基线。
判据：A0/A1/A2/A3/A5 = G1 逐位；B1/B2 = G2（KL ≤0.001 且 argmax 全同）。

**四、明确未移植**：B3（依赖 `STRATA_QFUSE=1` 的 q8_1 镜像，否则等于新建激活量化）、C1（改 fp16 累加 =
新精度来源，需先单列 V 相位占比）、A4（构建期 flag，要改 CMakeLists）。
"""
        i = plan.rfind("### 回写 · W1035")
        j = plan.find("\n### 回写 ·", i + 10)
        if j < 0:
            j = len(plan)
        plan = plan[:j] + blk + plan[j:]
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
        print("plan +§回写 W1036")
    else:
        print("plan block exists")

    # ---- daily memory
    mem = ""
    if os.path.isfile(MEM):
        mem = io.open(MEM, encoding="utf-8").read()
    if "W1036" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n## W1036（gfx906 全量移植）\n"
                     "- A0：`hip_compat::dp4a` 在 gfx906 落 portable 循环且**后端不折回**（实测 28 条 → 1 条 "
                     "`v_dot4_i32_i8`）。全树 dp4a 站点（MMVQ 45 处等）一直在跑模拟。**它是 B1/B2 的前置**。\n"
                     "- 清单 B2 落点错：`qsa_pattn.cu` 在 HIP 下 `STRATA_PATTN_BUILT=0`，不编译；真实 prompt "
                     "attention = `attn_chunk_body`（与 B1 同一段）。\n"
                     "- 分支 `gfx906/port-all` @ `79516b21`：`int OPT` 位掩码（DPP / dp4a / LDS pad）"
                     "+ `ROUTE_DPP` + `Q8_GATHER8`，一编译逐项测。\n"
                     "- 构建：ninja 会因 glob 校验重跑 CMake 后死掉 ⇒ 复制生产 build 目录并**把 RERUN_CMAKE / "
                     "VERIFY_GLOBS 两条边改成 phony**，再挂 `llama.cpp` 才编得动。\n")
        print("memory appended")


if __name__ == "__main__":
    main()
